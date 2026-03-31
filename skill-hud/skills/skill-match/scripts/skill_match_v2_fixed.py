#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill-Match 数据收集核心脚本 (修复版 v2.2)

修复内容：
1. 添加可信度评分机制 - 防止误匹配低质量仓库
2. 添加黑名单/白名单机制 - 允许用户手动控制
3. 添加用户确认模式 - 对不确定的匹配要求确认
4. 提高匹配阈值 - 对 stars=0 的仓库要求更高相似度
5. 添加仓库质量检测 - 排除空仓库、占位仓库

新配置：
- QUALITY_THRESHOLD_MIN_STARS: 最低 stars 要求
- QUALITY_THRESHOLD_MIN_FORKS: 最低 forks 要求
- CONFIDENCE_LEVEL: 匹配置信度 (strict/standard/relaxed)
- AUTO_CONFIRM: 是否自动确认匹配
- SKIP_LIST: 跳过匹配的 skill 列表
"""

import os
import sys
import json
import re
import glob
import time
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import quote
from dataclasses import dataclass, asdict, field
from collections import defaultdict
from difflib import SequenceMatcher

# 尝试导入可选依赖
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("警告: requests 未安装，部分功能不可用")

# ============================================
# 配置
# ============================================
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
SKILLS_BASE_PATH = os.path.expanduser("~/.claude/skills")
CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache')
CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'config')
USER_GITHUB_MAP_PATH = os.path.join(CONFIG_DIR, 'user_github_map.json')
CATEGORY_RULES_PATH = os.path.join(CONFIG_DIR, 'category_rules.json')
MATCH_HISTORY_PATH = os.path.join(CONFIG_DIR, 'match_history.json')
SKIP_LIST_PATH = os.path.join(CONFIG_DIR, 'skip_list.json')

# 请求配置
REQUEST_DELAY = 1.0  # API请求间隔（秒）
MAX_RETRIES = 3  # 最大重试次数
REQUEST_TIMEOUT = 10  # 请求超时（秒）

# ============================================
# 匹配配置（修复版）
# ============================================
# 置信度级别: strict(严格) / standard(标准) / relaxed(宽松)
CONFIDENCE_LEVEL = os.environ.get('MATCH_CONFIDENCE', 'standard')

# 自动确认: True=自动接受匹配, False=需要用户确认
AUTO_CONFIRM = False  # 默认需要确认，防止误匹配

# 质量阈值
QUALITY_THRESHOLD_MIN_STARS = 0     # 最低 stars 要求
QUALITY_THRESHOLD_MIN_FORKS = 0     # 最低 forks 要求
QUALITY_REQUIRE_ACTIVITY = True     # 要求仓库有活动
QUALITY_MIN_DAYS_SINCE_UPDATE = 365 # 仓库更新时间要求（天）

# 相似度阈值（根据置信度级别调整）
SIMILARITY_THRESHOLDS = {
    'strict': {
        'high_quality': 0.6,    # 高质量仓库 (stars>=10)
        'medium_quality': 0.8,  # 中质量仓库 (stars>=1)
        'low_quality': 0.95,    # 低质量仓库 (stars=0)
    },
    'standard': {
        'high_quality': 0.5,
        'medium_quality': 0.75,
        'low_quality': 0.9,
    },
    'relaxed': {
        'high_quality': 0.4,
        'medium_quality': 0.65,
        'low_quality': 0.85,
    }
}

# 自动搜索开关
AUTO_SEARCH_ENABLED = True

# 自动保存匹配结果
AUTO_SAVE_MATCHES = False  # 默认不自动保存，等待用户确认

# ============================================
# 日志配置
# ============================================
def setup_logging():
    """配置日志系统"""
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, f'skill_match_{datetime.now().strftime("%Y%m%d")}.log'), encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================
# 修复 Windows 控制台编码问题
# ============================================
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

# ============================================
# 数据类定义
# ============================================
@dataclass
class SkillInfo:
    """Skill信息数据类"""
    name: str
    path: str
    trigger_words: str = ""
    description: str = ""
    size_mb: float = 0.0
    install_date: str = ""
    last_modified: str = ""
    github_url: str = ""
    has_trigger_words: bool = False
    category: str = ""
    source: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MatchResult:
    """匹配结果数据类"""
    skill_name: str
    github_url: str
    similarity: float
    confidence: float  # 可信度 (0-1)
    repo_name: str
    stars: int
    forks: int
    description: str
    quality_level: str  # high/medium/low
    match_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    matched_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def is_high_quality(self) -> bool:
        """是否为高质量匹配"""
        return self.confidence >= 0.8 and self.quality_level in ['high', 'medium']

    @property
    def needs_confirmation(self) -> bool:
        """是否需要用户确认"""
        return not self.is_high_quality or len(self.warnings) > 0


# ============================================
# 仓库质量评估器
# ============================================
class RepoQualityAssessor:
    """仓库质量评估器"""

    @staticmethod
    def assess_quality(repo: dict) -> Tuple[str, float, List[str]]:
        """
        评估仓库质量

        返回: (质量级别, 质量分数, 警告列表)
        质量级别: high / medium / low
        质量分数: 0-1
        """
        warnings = []
        score = 0.0

        stars = repo.get('stargazers_count', 0)
        forks = repo.get('forks_count', 0)
        has_language = repo.get('language') is not None
        has_description = repo.get('description') is not None and len(repo.get('description', '')) > 10
        is_archived = repo.get('archived', False)
        size = repo.get('size', 0)

        # 检查更新时间
        try:
            updated_at = datetime.fromisoformat(repo.get('updated_at', '').replace('Z', '+00:00'))
            days_since_update = (datetime.now(updated_at.tzinfo) - updated_at).days
            is_active = days_since_update < QUALITY_MIN_DAYS_SINCE_UPDATE
        except:
            is_active = False
            days_since_update = 999

        # 评估各项指标
        if stars >= 10:
            score += 0.4
        elif stars >= 1:
            score += 0.2

        if forks >= 5:
            score += 0.2
        elif forks >= 1:
            score += 0.1

        if has_language:
            score += 0.15
        else:
            warnings.append("⚠️ 仓库没有语言标记")

        if has_description:
            score += 0.15
        else:
            warnings.append("⚠️ 仓库没有描述")

        if size > 100:  # 大于100KB
            score += 0.1
        elif size < 10:  # 小于10KB，可能是空仓库
            warnings.append("⚠️ 仓库太小，可能是空仓库或占位仓库")

        if is_archived:
            warnings.append("⚠️ 仓库已归档")

        if not is_active:
            warnings.append(f"⚠️ 仓库已 {days_since_update} 天未更新")

        # 确定质量级别
        if score >= 0.7:
            quality_level = 'high'
        elif score >= 0.4:
            quality_level = 'medium'
        else:
            quality_level = 'low'

        return quality_level, score, warnings


# ============================================
# 名称相似度计算器
# ============================================
class SimilarityCalculator:
    """名称相似度计算器"""

    @staticmethod
    def calculate_similarity(skill_name: str, repo_name: str) -> float:
        """
        计算skill名称与仓库名称的相似度

        策略：
        1. 完全匹配 -> 1.0
        2. 包含关系 -> 0.9
        3. 去除分隔符后匹配 -> 0.85
        4. SequenceMatcher相似度 -> 原始值
        """
        skill_lower = skill_name.lower().strip()
        repo_lower = repo_name.lower().strip()

        # 1. 完全匹配
        if skill_lower == repo_lower:
            return 1.0

        # 2. 包含关系（skill名包含在仓库名中，或反之）
        if skill_lower in repo_lower or repo_lower in skill_lower:
            return 0.9

        # 3. 去除常见分隔符后匹配
        def normalize(name: str) -> str:
            return re.sub(r'[-_\s]+', '', name)

        if normalize(skill_lower) == normalize(repo_lower):
            return 0.85

        # 4. 使用 SequenceMatcher 计算相似度
        return SequenceMatcher(None, skill_lower, repo_lower).ratio()

    @staticmethod
    def calculate_combined_similarity(skill_name: str, repo_name: str, repo_description: str = "") -> float:
        """
        综合相似度计算（名称 + 描述）
        """
        name_similarity = SimilarityCalculator.calculate_similarity(skill_name, repo_name)

        # 如果有描述，且描述中包含skill名，提高相似度
        if repo_description:
            desc_lower = repo_description.lower()
            skill_lower = skill_name.lower()
            if skill_lower in desc_lower:
                name_similarity = min(1.0, name_similarity + 0.1)

        return name_similarity


# ============================================
# 跳过列表管理器
# ============================================
class SkipListManager:
    """跳过列表管理器 - 管理不需要自动匹配的 skills"""

    def __init__(self):
        self.skip_list_path = SKIP_LIST_PATH
        self.skip_list = self._load_skip_list()

    def _load_skip_list(self) -> Dict[str, str]:
        """加载跳过列表"""
        if os.path.exists(self.skip_list_path):
            try:
                with open(self.skip_list_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载跳过列表失败: {e}")
        return {}

    def _save_skip_list(self):
        """保存跳过列表"""
        try:
            os.makedirs(os.path.dirname(self.skip_list_path), exist_ok=True)
            with open(self.skip_list_path, 'w', encoding='utf-8') as f:
                json.dump(self.skip_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存跳过列表失败: {e}")

    def is_skipped(self, skill_name: str) -> bool:
        """检查是否在跳过列表中"""
        return skill_name in self.skip_list

    def add_skip(self, skill_name: str, reason: str = "用户手动跳过"):
        """添加到跳过列表"""
        self.skip_list[skill_name] = {
            'reason': reason,
            'added_at': datetime.now().isoformat()
        }
        self._save_skip_list()
        logger.info(f"已添加到跳过列表: {skill_name} ({reason})")

    def remove_skip(self, skill_name: str):
        """从跳过列表移除"""
        if skill_name in self.skip_list:
            del self.skip_list[skill_name]
            self._save_skip_list()
            logger.info(f"已从跳过列表移除: {skill_name}")


# ============================================
# 匹配历史管理器
# ============================================
class MatchHistoryManager:
    """匹配历史管理器"""

    def __init__(self):
        self.history_path = MATCH_HISTORY_PATH
        self.history = self._load_history()

    def _load_history(self) -> Dict[str, dict]:
        """加载匹配历史"""
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载匹配历史失败: {e}")
        return {}

    def _save_history(self):
        """保存匹配历史"""
        try:
            os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存匹配历史失败: {e}")

    def get_match(self, skill_name: str) -> Optional[dict]:
        """获取历史匹配记录"""
        return self.history.get(skill_name)

    def add_match(self, match_result: MatchResult):
        """添加匹配记录"""
        self.history[match_result.skill_name] = match_result.to_dict()
        self._save_history()

    def is_recent_match(self, skill_name: str, days: int = 7) -> bool:
        """检查是否最近匹配过"""
        record = self.get_match(skill_name)
        if not record:
            return False

        try:
            matched_at = datetime.fromisoformat(record['matched_at'])
            days_since_match = (datetime.now() - matched_at).days
            return days_since_match < days
        except:
            return False


# ============================================
# 配置管理
# ============================================
class ConfigManager:
    """配置管理器"""

    @staticmethod
    def load_category_rules() -> Dict[str, List[str]]:
        """加载分类规则配置"""
        default_rules = {
            "开发工作流": ["code", "git", "debug", "test", "deploy", "commit", "review", "branch", "implementation", "verification"],
            "文档写作": ["writing", "article", "blog", "document", "prd", "prompt", "wechat", "content", "author"],
            "设计创意": ["design", "ui", "ux", "art", "image", "canvas", "ppt", "presentation"],
            "项目管理": ["plan", "task", "brainstorm", "requirement", "solution", "workflow"],
            "数据处理": ["json", "markdown", "obsidian", "base", "file"],
            "监控分析": ["monitor", "analytics", "report", "statistics", "dashboard"],
            "AI助手": ["ai", "assistant", "agent", "llm", "chatbot"]
        }

        os.makedirs(CONFIG_DIR, exist_ok=True)

        if os.path.exists(CATEGORY_RULES_PATH):
            try:
                with open(CATEGORY_RULES_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载分类规则失败: {e}，使用默认规则")

        # 保存默认规则
        try:
            with open(CATEGORY_RULES_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_rules, f, ensure_ascii=False, indent=2)
        except:
            pass

        return default_rules

    @staticmethod
    def load_github_map() -> Dict[str, str]:
        """加载GitHub地址映射"""
        os.makedirs(CONFIG_DIR, exist_ok=True)

        if os.path.exists(USER_GITHUB_MAP_PATH):
            try:
                with open(USER_GITHUB_MAP_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载GitHub映射失败: {e}")

        return {}

    @staticmethod
    def save_github_map(github_map: Dict[str, str]):
        """保存GitHub地址映射"""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(USER_GITHUB_MAP_PATH, 'w', encoding='utf-8') as f:
                json.dump(github_map, f, ensure_ascii=False, indent=2)
            logger.info(f"GitHub映射已保存: {USER_GITHUB_MAP_PATH}")
        except Exception as e:
            logger.error(f"保存GitHub映射失败: {e}")


# ============================================
# 已知的GitHub地址映射
# ============================================
KNOWN_GITHUB_MAP = {
    "anthropic-skills": "https://github.com/anthropics/anthropic-skills",
    "awesomeAgentskills": "https://github.com/Nick-Armstrong/awesomeAgentskills",
    "brainstorming": "https://github.com/anthropics/anthropic-skills",
    "dispatching-parallel-agents": "https://github.com/anthropics/anthropic-skills",
    "document-illustrator": "https://github.com/anthropics/anthropic-skills",
    "executing-plans": "https://github.com/anthropics/anthropic-skills",
    "finishing-a-development-branch": "https://github.com/anthropics/anthropic-skills",
    "image-assistant": "https://github.com/YaoYS2024/image-assistant",
    "json-canvas": "https://github.com/anthropics/anthropic-skills",
    "mcp-builder": "https://github.com/anthropics/anthropic-skills",
    "ms-image": "https://github.com/ModelScope/OpenPromptOps",
    "n8n-skills": "https://github.com/anthropics/anthropic-skills",
    "notebooklm": "https://github.com/anthropics/claude-code",
    "obsidian-bases": "https://github.com/obsidian-skills/obsidian-skills",
    "obsidian-markdown": "https://github.com/obsidian-skills/obsidian-skills",
    "obsidian-skills": "https://github.com/obsidian-skills/obsidian-skills",
    "planning-with-files": "https://github.com/OthmanAdi/planning-with-files",
    "ppt-generator": "https://github.com/op7418/NanoBanana-PPT-Skills",
    "pptx": "https://github.com/anthropics/anthropic-skills",
    "prd-doc-writer": "https://github.com/cursor-shadowsong/prd-doc-writer",
    "prompt-copilot": "https://github.com/System-Engineering-Prompt-Copilot/prompt-copilot",
    "receiving-code-review": "https://github.com/anthropics/anthropic-skills",
    "req-change-workflow": "https://github.com/cursor-shadowsong/req-change-workflow",
    "req-record": "https://github.com/cursor-shadowsong/req-record",
    "requesting-code-review": "https://github.com/anthropics/anthropic-skills",
    "skill-creator": "https://github.com/anthropics/anthropic-skills",
    "solution-creator": "https://github.com/cursor-shadowsong/solution-creator",
    "subagent-driven-development": "https://github.com/anthropics/anthropic-skills",
    "superpowers": "https://github.com/obra/superpowers",
    "systematic-debugging": "https://github.com/anthropics/anthropic-skills",
    "test-driven-development": "https://github.com/anthropics/anthropic-skills",
    "thought-mining": "https://github.com/thought-mining/thought-mining",
    "ui-ux-pro-max-skill": "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill",
    "using-git-worktrees": "https://github.com/anthropics/anthropic-skills",
    "using-superpowers": "https://github.com/anthropics/anthropic-skills",
    "verification-before-completion": "https://github.com/anthropics/anthropic-skills",
    "webapp-testing": "https://github.com/anthropics/anthropic-skills",
    "wechat-writing": "https://github.com/dingfeihu2023/wechat-writing",
    "wechat-item": "https://github.com/wechat-skills/wechat-item",
    "writing-plans": "https://github.com/anthropics/anthropic-skills",
    "writing-skills": "https://github.com/anthropics/anthropic-skills",
    "x-article-publisher": "https://github.com/Claude-Code-Skills/x-article-publisher",
}


# ============================================
# 修复的GitHub搜索器
# ============================================
class FixedGitHubSearcher:
    """修复的GitHub搜索器（带可信度评分）"""

    def __init__(self):
        self.history_manager = MatchHistoryManager()
        self.skip_manager = SkipListManager()
        self.similarity_calculator = SimilarityCalculator()
        self.quality_assessor = RepoQualityAssessor()
        self._last_request_time = 0

    def _make_request(self, url: str, headers: dict) -> Optional[dict]:
        """发送HTTP请求（带延迟和重试）"""
        if not HAS_REQUESTS:
            logger.error("requests 未安装")
            return None

        # 请求延迟
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)

        # 重试机制
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
                self._last_request_time = time.time()

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403:
                    logger.warning("GitHub API限流，等待60秒...")
                    time.sleep(60)
                    continue
                else:
                    logger.warning(f"GitHub API请求失败: {response.status_code}")
                    return None

            except requests.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.warning(f"请求异常 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)

        return None

    def search_repositories(self, skill_name: str) -> List[dict]:
        """
        搜索GitHub仓库

        搜索策略：
        1. 精确搜索（skill名）
        2. 模糊搜索（skill名关键词）
        3. 组合搜索（skill名 + skill/claude等关键词）
        """
        if not HAS_REQUESTS:
            return []

        queries = [
            f'{skill_name} in:name',  # 精确搜索
            f'{skill_name.replace("-", " ")} in:name',  # 去连字符
            f'{skill_name.replace("_", " ")} in:name',  # 去下划线
            f'{skill_name} skill in:name,description',  # 带skill关键词
            f'{skill_name} claude-skill in:name,description',  # 带claude-skill关键词
        ]

        headers = {'Accept': 'application/vnd.github.v3+json'}
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'

        all_results = []
        seen_repos = set()

        for query in queries:
            encoded_query = quote(query)
            search_url = f'https://api.github.com/search/repositories?q={encoded_query}&per_page=10&sort=stars&order=desc'

            result = self._make_request(search_url, headers)
            if result and result.get('items'):
                for repo in result['items']:
                    repo_url = repo['html_url']
                    if repo_url not in seen_repos:
                        seen_repos.add(repo_url)
                        all_results.append(repo)

            # 收集到足够结果就停止
            if len(all_results) >= 20:
                break

        return all_results

    def find_best_match(self, skill_name: str, search_results: List[dict]) -> Optional[MatchResult]:
        """
        从搜索结果中找到最佳匹配（修复版）

        修复内容：
        1. 评估仓库质量
        2. 根据质量调整相似度阈值
        3. 计算综合可信度
        4. 添加警告信息
        """
        if not search_results:
            return None

        best_match = None
        best_confidence = 0

        # 获取当前置信度级别的阈值
        thresholds = SIMILARITY_THRESHOLDS.get(CONFIDENCE_LEVEL, SIMILARITY_THRESHOLDS['standard'])

        for repo in search_results:
            repo_name = repo.get('name', '')
            repo_description = repo.get('description', '')

            # 计算名称相似度
            similarity = self.similarity_calculator.calculate_combined_similarity(
                skill_name, repo_name, repo_description
            )

            # 评估仓库质量
            quality_level, quality_score, warnings = self.quality_assessor.assess_quality(repo)

            # 根据质量级别获取相似度阈值
            threshold = thresholds.get(quality_level, 0.8)

            # 如果相似度低于阈值，跳过
            if similarity < threshold:
                continue

            # 计算可信度（相似度 + 质量分数）
            confidence = (similarity * 0.7) + (quality_score * 0.3)

            # 如果可信度更高，更新最佳匹配
            if confidence > best_confidence:
                best_confidence = confidence

                match_reasons = []
                if similarity >= 0.9:
                    match_reasons.append("✅ 名称高度相似")
                elif similarity >= 0.7:
                    match_reasons.append("✓ 名称较为相似")
                else:
                    match_reasons.append(f"名称相似度: {similarity:.2f}")

                if quality_score >= 0.7:
                    match_reasons.append("✅ 高质量仓库")
                elif quality_score >= 0.4:
                    match_reasons.append("✓ 中等质量仓库")

                best_match = MatchResult(
                    skill_name=skill_name,
                    github_url=repo['html_url'],
                    similarity=similarity,
                    confidence=confidence,
                    repo_name=repo_name,
                    stars=repo.get('stargazers_count', 0),
                    forks=repo.get('forks_count', 0),
                    description=repo_description or "",
                    quality_level=quality_level,
                    match_reasons=match_reasons,
                    warnings=warnings,
                    matched_at=datetime.now().isoformat()
                )

        return best_match

    def search_and_match(self, skill_name: str) -> Optional[MatchResult]:
        """
        搜索并自动匹配GitHub仓库（修复版）

        修复内容：
        1. 检查跳过列表
        2. 检查历史匹配记录
        3. 执行搜索
        4. 质量评估
        5. 可信度计算
        6. 用户确认（如果需要）
        """
        # 检查跳过列表
        if self.skip_manager.is_skipped(skill_name):
            skip_info = self.skip_manager.skip_list[skill_name]
            logger.info(f"  [跳过] {skill_name}: {skip_info.get('reason', '在跳过列表中')}")
            return None

        # 检查历史
        if self.history_manager.is_recent_match(skill_name):
            history = self.history_manager.get_match(skill_name)
            if history:
                logger.info(f"  [历史] {skill_name}: {history['github_url']} (可信度: {history.get('confidence', 0):.2f})")
                # 兼容旧历史记录格式
                return MatchResult(
                    skill_name=history.get('skill_name', skill_name),
                    github_url=history.get('github_url', ''),
                    similarity=history.get('similarity', 0),
                    confidence=history.get('confidence', 0),
                    repo_name=history.get('repo_name', ''),
                    stars=history.get('stars', 0),
                    forks=history.get('forks', 0),
                    description=history.get('description', ''),
                    quality_level=history.get('quality_level', 'unknown'),
                    match_reasons=history.get('match_reasons', []),
                    warnings=history.get('warnings', []),
                    matched_at=history.get('matched_at', '')
                )

        # 执行搜索
        logger.info(f"  [搜索] {skill_name}...")
        search_results = self.search_repositories(skill_name)

        if not search_results:
            logger.warning(f"  [未找到] {skill_name}: 无搜索结果")
            return None

        # 找到最佳匹配
        best_match = self.find_best_match(skill_name, search_results)

        if best_match:
            # 显示匹配信息
            logger.info(f"  [候选] {skill_name} -> {best_match.repo_name}")
            logger.info(f"         相似度: {best_match.similarity:.2f} | 可信度: {best_match.confidence:.2f} | 质量: {best_match.quality_level}")
            logger.info(f"         Stars: {best_match.stars} | Forks: {best_match.forks}")

            # 显示匹配原因
            for reason in best_match.match_reasons:
                logger.info(f"         {reason}")

            # 显示警告
            if best_match.warnings:
                logger.warning(f"         警告:")
                for warning in best_match.warnings:
                    logger.warning(f"           {warning}")

            # 判断是否需要用户确认
            if best_match.needs_confirmation and not AUTO_CONFIRM:
                logger.warning(f"  [需要确认] {skill_name}: 此匹配可信度较低或有警告")
                logger.info(f"         请手动确认是否接受此匹配")
                logger.info(f"         仓库地址: {best_match.github_url}")

                # 保存到历史（未确认状态）
                best_match.matched_at = datetime.now().isoformat()
                self.history_manager.add_match(best_match)

                return None  # 不自动接受

            # 高可信度匹配，自动接受
            logger.info(f"  [匹配成功] {skill_name}: 已接受（可信度: {best_match.confidence:.2f}）")

            # 保存到历史
            best_match.matched_at = datetime.now().isoformat()
            self.history_manager.add_match(best_match)

            return best_match
        else:
            logger.warning(f"  [低相似度] {skill_name}: 未找到足够相似的仓库")

            # 显示搜索结果供参考
            if search_results:
                logger.info(f"  [参考] 找到 {len(search_results)} 个可能的结果:")
                for i, repo in enumerate(search_results[:3], 1):
                    quality, _, _ = self.quality_assessor.assess_quality(repo)
                    logger.info(f"    [{i}] {repo['name']} - Stars: {repo.get('stargazers_count', 0)} - 质量: {quality}")
                    desc = repo.get('description', 'No description')[:60]
                    logger.info(f"        {desc}...")

            return None


# ============================================
# 工具函数
# ============================================
def extract_github_url(content: str) -> str:
    """从内容中提取GitHub URL"""
    patterns = [
        r'github\.com/([^/\s]+)/([^/\s]+)',
        r'github\.com/([^/\s]+)/([^/\s]+)\.git',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return f"https://github.com/{match.group(1)}/{match.group(2)}"
    return ""


def format_size(mb: float) -> str:
    """格式化大小"""
    if mb < 0.01:
        return "很小"
    elif mb < 1:
        return f"{mb*1024:.0f}KB"
    elif mb < 1024:
        return f"{mb:.1f}MB"
    else:
        return f"{mb/1024:.1f}GB"


def format_age(iso_date: str) -> str:
    """计算友好的时间显示"""
    if not iso_date:
        return "未知"
    try:
        dt = datetime.fromisoformat(iso_date)
        delta = datetime.now() - dt
        days = delta.days
        if days == 0:
            return "今天"
        elif days == 1:
            return "昨天"
        elif days < 7:
            return f"{days}天前"
        elif days < 30:
            weeks = days // 7
            return f"{weeks}周前"
        else:
            return dt.strftime("%Y-%m-%d")
    except:
        return "未知"


# ============================================
# 演示：修复的匹配逻辑
# ============================================
def demo_fixed_matching():
    """演示修复的匹配逻辑"""
    print("\n" + "=" * 60)
    print("       GitHub 智能搜索与匹配演示 (修复版)")
    print("=" * 60)
    print(f"       配置: 置信度级别={CONFIDENCE_LEVEL}, 自动确认={AUTO_CONFIRM}")
    print("=" * 60 + "\n")

    # 初始化搜索器
    searcher = FixedGitHubSearcher()

    # 测试案例
    test_skills = [
        "wechat-writing",      # 用户自己的 skill（未发布）
        "obsidian-markdown",   # 已知skill
        "my-custom-skill",     # 未知skill
        "test-driven",         # 部分匹配
    ]

    print("📋 测试Skills列表:")
    for skill in test_skills:
        if searcher.skip_manager.is_skipped(skill):
            print(f"  - {skill} (已跳过)")
        else:
            print(f"  - {skill}")
    print()

    # 执行匹配
    print("🔍 开始智能匹配...\n")

    results = []
    skipped = []
    need_confirm = []

    for skill_name in test_skills:
        match = searcher.search_and_match(skill_name)
        if match:
            if match.needs_confirmation and not AUTO_CONFIRM:
                need_confirm.append(match)
                print(f"⚠️  {skill_name}")
                print(f"   需要确认")
                print(f"   GitHub: {match.github_url}")
                print(f"   可信度: {match.confidence:.2f} | 质量: {match.quality_level}")
                print()
            else:
                results.append(match)
                print(f"✅ {skill_name}")
                print(f"   GitHub: {match.github_url}")
                print(f"   相似度: {match.similarity:.2f} | 可信度: {match.confidence:.2f}")
                print(f"   质量: {match.quality_level} | Stars: {match.stars}")
                desc_preview = (match.description or "无描述")[:60]
                print(f"   描述: {desc_preview}...")
                if match.match_reasons:
                    print(f"   匹配原因: {' | '.join(match.match_reasons)}")
                if match.warnings:
                    print(f"   警告: {' | '.join(match.warnings)}")
                print()
        else:
            if searcher.skip_manager.is_skipped(skill_name):
                skipped.append(skill_name)
            else:
                print(f"❌ {skill_name} - 未找到匹配")
                print()

    # 统计
    print("=" * 60)
    print(f"匹配统计:")
    print(f"  自动接受: {len(results)}")
    print(f"  需要确认: {len(need_confirm)}")
    print(f"  已跳过: {len(skipped)}")
    print(f"  未匹配: {len(test_skills) - len(results) - len(need_confirm) - len(skipped)}")
    print("=" * 60)

    # 显示需要确认的匹配
    if need_confirm:
        print("\n⚠️  以下匹配需要手动确认:")
        for match in need_confirm:
            print(f"\n  {match.skill_name}:")
            print(f"    GitHub: {match.github_url}")
            print(f"    可信度: {match.confidence:.2f} | 质量: {match.quality_level}")
            print(f"    Stars: {match.stars} | Forks: {match.forks}")
            if match.warnings:
                print(f"    警告: {' | '.join(match.warnings)}")
            print(f"    如果要接受，请在 user_github_map.json 中添加:")
            print(f'      "{match.skill_name}": "{match.github_url}"')


if __name__ == '__main__':
    demo_fixed_matching()
