#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill-Match 数据收集核心脚本 (增强版 v2.1)

新增功能：
1. 自动在 GitHub 上搜索缺失的仓库
2. 基于名称相似度智能匹配
3. 自动保存匹配结果到配置文件
4. 可配置相似度阈值
5. 匹配历史记录，避免重复搜索
"""

import os
import sys
import json
import re
import glob
import time
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import quote
from dataclasses import dataclass, asdict
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

# 请求配置
REQUEST_DELAY = 1.0  # API请求间隔（秒）
MAX_RETRIES = 3  # 最大重试次数
REQUEST_TIMEOUT = 10  # 请求超时（秒）

# 匹配配置
SIMILARITY_THRESHOLD = 0.6  # 相似度阈值 (0-1)
AUTO_SAVE_MATCHES = True  # 是否自动保存匹配结果
AUTO_SEARCH_ENABLED = True  # 是否启用自动搜索

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
    repo_name: str
    stars: int
    description: str
    matched_at: str

    def to_dict(self) -> dict:
        return asdict(self)

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

    def add_match(self, skill_name: str, github_url: str, similarity: float, repo_info: dict):
        """添加匹配记录"""
        self.history[skill_name] = {
            'github_url': github_url,
            'similarity': similarity,
            'repo_name': repo_info.get('name', ''),
            'stars': repo_info.get('stargazers_count', 0),
            'description': repo_info.get('description', ''),
            'matched_at': datetime.now().isoformat()
        }
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
    "wechat-item": "https://github.com/wechat-skills/wechat-item",
    "wechat-writing": "https://github.com/wechat-skills/wechat-writing",
    "writing-plans": "https://github.com/anthropics/anthropic-skills",
    "writing-skills": "https://github.com/anthropics/anthropic-skills",
    "x-article-publisher": "https://github.com/Claude-Code-Skills/x-article-publisher",
}


# ============================================
# 增强的GitHub搜索器
# ============================================
class EnhancedGitHubSearcher:
    """增强的GitHub搜索器（支持智能匹配）"""

    def __init__(self):
        self.history_manager = MatchHistoryManager()
        self.similarity_calculator = SimilarityCalculator()
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
        从搜索结果中找到最佳匹配

        匹配逻辑：
        1. 计算名称相似度
        2. 考虑描述相似度
        3. 考虑 stars 数量（作为置信度权重）
        4. 返回相似度最高的结果
        """
        if not search_results:
            return None

        best_match = None
        best_similarity = 0

        for repo in search_results:
            repo_name = repo.get('name', '')
            repo_description = repo.get('description', '')

            # 计算综合相似度
            similarity = self.similarity_calculator.calculate_combined_similarity(
                skill_name, repo_name, repo_description
            )

            # 如果相似度更高，更新最佳匹配
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = MatchResult(
                    skill_name=skill_name,
                    github_url=repo['html_url'],
                    similarity=similarity,
                    repo_name=repo_name,
                    stars=repo.get('stargazers_count', 0),
                    description=repo_description,
                    matched_at=datetime.now().isoformat()
                )

        # 只有相似度达到阈值才返回
        if best_match and best_match.similarity >= SIMILARITY_THRESHOLD:
            return best_match

        return None

    def search_and_match(self, skill_name: str) -> Optional[MatchResult]:
        """
        搜索并自动匹配GitHub仓库

        流程：
        1. 检查历史匹配记录
        2. 如果最近匹配过，直接返回
        3. 否则进行GitHub搜索
        4. 找到最佳匹配
        5. 保存到历史记录
        """
        # 检查历史
        if self.history_manager.is_recent_match(skill_name):
            history = self.history_manager.get_match(skill_name)
            if history:
                logger.info(f"  [历史] {skill_name}: {history['github_url']} (相似度: {history['similarity']:.2f})")
                return MatchResult(
                    skill_name=skill_name,
                    github_url=history['github_url'],
                    similarity=history['similarity'],
                    repo_name=history['repo_name'],
                    stars=history['stars'],
                    description=history['description'],
                    matched_at=history['matched_at']
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
            logger.info(f"  [匹配] {skill_name} -> {best_match.repo_name} (相似度: {best_match.similarity:.2f})")

            # 保存到历史
            self.history_manager.add_match(
                skill_name,
                best_match.github_url,
                best_match.similarity,
                {
                    'name': best_match.repo_name,
                    'stargazers_count': best_match.stars,
                    'description': best_match.description
                }
            )

            return best_match
        else:
            logger.warning(f"  [低相似度] {skill_name}: 未找到足够相似的仓库")

            # 显示搜索结果供参考
            if search_results:
                logger.info(f"  [参考] 找到 {len(search_results)} 个可能的结果:")
                for i, repo in enumerate(search_results[:3], 1):
                    logger.info(f"    [{i}] {repo['name']} - {repo.get('description', 'No description')[:50]}")

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
# 演示：增强的匹配逻辑
# ============================================
def demo_enhanced_matching():
    """演示增强的匹配逻辑"""
    print("\n" + "=" * 60)
    print("       GitHub 智能搜索与匹配演示")
    print("=" * 60 + "\n")

    # 初始化搜索器
    searcher = EnhancedGitHubSearcher()

    # 测试案例
    test_skills = [
        "wechat-writing",      # 已知skill
        "obsidian-markdown",   # 已知skill
        "my-custom-skill",     # 未知skill（测试搜索）
        "test-driven",         # 部分匹配
    ]

    print("📋 测试Skills列表:")
    for skill in test_skills:
        print(f"  - {skill}")
    print()

    # 执行匹配
    print("🔍 开始智能匹配...\n")

    results = []
    for skill_name in test_skills:
        match = searcher.search_and_match(skill_name)
        if match:
            results.append(match)
            print(f"✅ {skill_name}")
            print(f"   GitHub: {match.github_url}")
            print(f"   相似度: {match.similarity:.2f}")
            print(f"   Stars: {match.stars}")
            desc_preview = (match.description or "无描述")[:60]
            print(f"   描述: {desc_preview}...")
            print()
        else:
            print(f"❌ {skill_name} - 未找到匹配")
            print()

    # 统计
    print("=" * 60)
    print(f"匹配成功率: {len(results)}/{len(test_skills)} ({len(results)/len(test_skills)*100:.1f}%)")
    print("=" * 60)

    # 显示匹配历史
    print("\n📜 匹配历史:")
    history = searcher.history_manager.history
    for skill_name, record in history.items():
        print(f"  {skill_name}: {record['github_url']} (相似度: {record['similarity']:.2f})")


if __name__ == '__main__':
    demo_enhanced_matching()
