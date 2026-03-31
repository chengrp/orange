#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill-Match 优化版 v3.0

主要优化：
1. 自动匹配结果不直接写入，生成待确认列表
2. 高质量仓库 (Stars > 1000) 单独标注
3. 统计 skill 使用频率（基于修改时间和大小）
4. 重度使用的 skill 特别标注
5. 无匹配结果时不强行匹配
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
from typing import Dict, List, Optional, Tuple
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

# ============================================
# 配置
# ============================================
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
SKILLS_BASE_PATH = os.path.expanduser("~/.claude/skills")
CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache')
CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'config')
USER_GITHUB_MAP_PATH = os.path.join(CONFIG_DIR, 'user_github_map.json')
PENDING_CONFIRM_PATH = os.path.join(CONFIG_DIR, 'pending_confirm.json')
CATEGORY_RULES_PATH = os.path.join(CONFIG_DIR, 'category_rules.json')

# 请求配置
REQUEST_DELAY = 1.0
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10

# 质量阈值
HIGH_QUALITY_STARS = 1000  # 高质量仓库的最低 stars
HEAVY_USE_DAYS = 30  # 最近使用天数阈值
HEAVY_USE_SIZE_MB = 1.0  # 大型 skill 阈值

# API 限流处理
USE_CACHE_DATA = False  # 标记是否使用了缓存数据
RATE_LIMIT_HIT = False  # 标记是否遇到限流

# ============================================
# 日志配置
# ============================================
def setup_logging():
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
    # 使用频率统计
    usage_frequency: str = "unknown"  # heavy/medium/low/unknown
    days_since_modified: int = 0
    # 质量标注
    is_high_quality: bool = False
    stars: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PendingMatch:
    """待确认的匹配结果"""
    skill_name: str
    github_url: str
    similarity: float
    confidence: float
    repo_name: str
    stars: int
    forks: int
    description: str
    quality_level: str
    match_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggested_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


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
            url = f"https://github.com/{match.group(1)}/{match.group(2)}"
            # 过滤掉无效地址
            if url not in ["https://github.com/user-attachments/assets"]:
                return url
    return ""


def get_dir_size(path: str) -> float:
    """获取目录大小（MB）"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception:
        pass
    return round(total_size / (1024 * 1024), 2)


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
# 配置管理
# ============================================
class ConfigManager:
    """配置管理器"""

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

    @staticmethod
    def load_pending_confirm() -> List[PendingMatch]:
        """加载待确认列表"""
        if os.path.exists(PENDING_CONFIRM_PATH):
            try:
                with open(PENDING_CONFIRM_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [PendingMatch(**item) for item in data]
            except Exception as e:
                logger.warning(f"加载待确认列表失败: {e}")

        return []

    @staticmethod
    def save_pending_confirm(pending: List[PendingMatch]):
        """保存待确认列表"""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(PENDING_CONFIRM_PATH, 'w', encoding='utf-8') as f:
                data = [p.to_dict() for p in pending]
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"待确认列表已保存: {PENDING_CONFIRM_PATH}")
        except Exception as e:
            logger.error(f"保存待确认列表失败: {e}")

    @staticmethod
    def clear_pending_confirm():
        """清空待确认列表"""
        try:
            if os.path.exists(PENDING_CONFIRM_PATH):
                os.remove(PENDING_CONFIRM_PATH)
                logger.info("待确认列表已清空")
        except Exception as e:
            logger.error(f"清空待确认列表失败: {e}")


# ============================================
# 仓库质量评估器
# ============================================
class RepoQualityAssessor:
    """仓库质量评估器"""

    @staticmethod
    def assess_quality(repo: dict) -> Tuple[str, float, List[str]]:
        """评估仓库质量"""
        warnings = []
        score = 0.0

        stars = repo.get('stargazers_count', 0)
        forks = repo.get('forks_count', 0)
        has_language = repo.get('language') is not None
        has_description = repo.get('description') is not None and len(repo.get('description', '')) > 10
        size = repo.get('size', 0)

        # 评估各项指标
        if stars >= 1000:
            score += 0.5
        elif stars >= 100:
            score += 0.3
        elif stars >= 10:
            score += 0.1

        if forks >= 10:
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

        if size > 100:
            score += 0.1
        elif size < 10:
            warnings.append("⚠️ 仓库太小，可能是空仓库")

        # 确定质量级别
        if score >= 0.7:
            quality_level = 'high'
        elif score >= 0.4:
            quality_level = 'medium'
        else:
            quality_level = 'low'

        return quality_level, score, warnings


# ============================================
# 使用频率分析器
# ============================================
class UsageFrequencyAnalyzer:
    """使用频率分析器"""

    @staticmethod
    def analyze(skill_path: str) -> Tuple[str, int]:
        """
        分析 skill 使用频率

        返回: (频率级别, 距今天数)
        频率级别: heavy/medium/low/unknown
        """
        try:
            # 获取修改时间
            mtime = os.path.getmtime(skill_path)
            modified_date = datetime.fromtimestamp(mtime)
            days_since = (datetime.now() - modified_date).days

            # 获取大小
            size_mb = get_dir_size(skill_path)

            # 综合判断使用频率
            if days_since < HEAVY_USE_DAYS and size_mb > HEAVY_USE_SIZE_MB:
                return "heavy", days_since
            elif days_since < HEAVY_USE_DAYS:
                return "medium", days_since
            elif days_since < 90:
                return "low", days_since
            else:
                return "unknown", days_since

        except Exception:
            return "unknown", 999


# ============================================
# GitHub 客户端（简化版）
# ============================================
class GitHubClientSimple:
    """简化的 GitHub 客户端"""

    def __init__(self):
        self._last_request_time = 0

    def get_repo_info(self, github_url: str) -> Optional[dict]:
        """获取仓库信息（带缓存和重试）"""
        if not HAS_REQUESTS or not github_url or 'github.com' not in github_url:
            return None

        # 检查缓存
        cache_key = f"repo_info_{github_url}"
        cache_file = os.path.join(CACHE_DIR, f"{hashlib.md5(cache_key.encode()).hexdigest()}.json")

        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    # 缓存1小时有效
                    if time.time() - cache_data.get('timestamp', 0) < 3600:
                        return cache_data.get('data')
            except:
                pass

        match = re.search(r'github\.com/([^/]+)/([^/]+?)(\.git)?$', github_url)
        if not match:
            return None

        owner = match.group(1)
        repo = match.group(2).replace('.git', '')

        # 重试机制
        for attempt in range(MAX_RETRIES):
            try:
                # 请求延迟
                elapsed = time.time() - self._last_request_time
                if elapsed < REQUEST_DELAY:
                    time.sleep(REQUEST_DELAY - elapsed)

                headers = {'Accept': 'application/vnd.github.v3+json'}
                if GITHUB_TOKEN:
                    headers['Authorization'] = f'token {GITHUB_TOKEN}'

                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                response = requests.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
                self._last_request_time = time.time()

                if response.status_code == 200:
                    data = response.json()

                    # 保存到缓存
                    try:
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump({
                                'data': data,
                                'timestamp': time.time()
                            }, f)
                    except:
                        pass

                    return data

                elif response.status_code == 403:
                    global RATE_LIMIT_HIT, USE_CACHE_DATA
                    RATE_LIMIT_HIT = True

                    # 第一次遇到限流时询问用户
                    if attempt == 0:
                        print("\n" + "=" * 80)
                        print("⚠️  GitHub API 限流警告")
                        print("=" * 80)
                        print("当前遇到了 GitHub API 速率限制（每小时最多 60 次请求）。")
                        print("您可以选择：")
                        print("  1. 等待 60 秒后自动重试（可能需要等待多次）")
                        print("  2. 使用最近的缓存数据生成报告（数据可能不是最新的）")
                        print("=" * 80)

                        # 尝试使用缓存数据
                        if os.path.exists(cache_file):
                            try:
                                with open(cache_file, 'r', encoding='utf-8') as f:
                                    cache_data = json.load(f)
                                    cache_age = (time.time() - cache_data.get('timestamp', 0)) / 3600  # 小时
                                    print(f"\n💾 发现有缓存数据（{cache_age:.1f} 小时前）")
                                    choice = input("是否使用缓存数据？(y/n，默认 n): ").strip().lower()
                                    if choice == 'y':
                                        USE_CACHE_DATA = True
                                        logger.info(f"使用缓存数据: {github_url} (缓存时间: {cache_age:.1f}小时前)")
                                        return cache_data.get('data')
                            except:
                                pass

                        print(f"\n⏳ 等待 60 秒后重试... (尝试 {attempt + 1}/{MAX_RETRIES})")

                    logger.warning(f"GitHub API限流，等待60秒后重试... (尝试 {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(60)
                    continue
                else:
                    logger.warning(f"GitHub API返回 {response.status_code}: {github_url}")
                    return None

            except requests.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{MAX_RETRIES}): {github_url}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.warning(f"获取仓库信息异常 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)

        logger.warning(f"获取仓库信息失败 {github_url}")
        return None


# ============================================
# 智能搜索器（优化版）
# ============================================
class SmartGitHubSearcher:
    """智能 GitHub 搜索器（优化版）"""

    def __init__(self):
        self.github_client = GitHubClientSimple()
        self.quality_assessor = RepoQualityAssessor()
        self.pending_confirm = ConfigManager.load_pending_confirm()

    def search_repositories(self, skill_name: str) -> List[dict]:
        """搜索 GitHub 仓库"""
        if not HAS_REQUESTS:
            return []

        queries = [
            f'{skill_name} in:name',
            f'{skill_name.replace("-", " ")} in:name',
            f'{skill_name.replace("_", " ")} in:name',
        ]

        headers = {'Accept': 'application/vnd.github.v3+json'}
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'

        all_results = []
        seen_repos = set()

        for query in queries:
            encoded_query = quote(query)
            search_url = f'https://api.github.com/search/repositories?q={encoded_query}&per_page=10&sort=stars&order=desc'

            try:
                # 请求延迟
                elapsed = time.time() - self.github_client._last_request_time
                if elapsed < REQUEST_DELAY:
                    time.sleep(REQUEST_DELAY - elapsed)

                response = requests.get(search_url, headers=headers, timeout=REQUEST_TIMEOUT)
                self.github_client._last_request_time = time.time()

                if response.status_code == 200:
                    data = response.json()
                    if data.get('items'):
                        for repo in data['items']:
                            repo_url = repo['html_url']
                            if repo_url not in seen_repos:
                                seen_repos.add(repo_url)
                                all_results.append(repo)

                if len(all_results) >= 20:
                    break

            except Exception as e:
                logger.warning(f"搜索失败 {query}: {e}")

        return all_results

    def find_best_match(self, skill_name: str, search_results: List[dict]) -> Optional[PendingMatch]:
        """从搜索结果中找到最佳匹配"""
        if not search_results:
            return None

        best_match = None
        best_confidence = 0

        for repo in search_results:
            repo_name = repo.get('name', '')
            repo_description = repo.get('description', '')
            stars = repo.get('stargazers_count', 0)

            # 计算相似度
            skill_lower = skill_name.lower()
            repo_lower = repo_name.lower()

            if skill_lower == repo_lower:
                similarity = 1.0
            elif skill_lower in repo_lower or repo_lower in skill_lower:
                similarity = 0.9
            else:
                similarity = SequenceMatcher(None, skill_lower, repo_lower).ratio()

            # 质量评估
            quality_level, quality_score, warnings = self.quality_assessor.assess_quality(repo)

            # 综合可信度
            confidence = (similarity * 0.7) + (quality_score * 0.3)

            # 动态相似度阈值：低质量仓库需要更高的相似度
            if stars < 10:
                min_similarity = 0.95  # 低质量仓库需要几乎完全匹配
            elif stars < 100:
                min_similarity = 0.85  # 中低质量仓库需要高相似度
            else:
                min_similarity = 0.75  # 高质量仓库可以稍微宽松

            # 只接受高相似度的匹配
            if confidence > best_confidence and similarity >= min_similarity:
                best_confidence = confidence

                match_reasons = []
                if similarity >= 0.95:
                    match_reasons.append("✅ 名称高度相似")
                else:
                    match_reasons.append(f"名称相似度: {similarity:.2f}")

                if stars >= HIGH_QUALITY_STARS:
                    match_reasons.append(f"⭐ 高质量仓库 ({stars} stars)")
                elif quality_score >= 0.4:
                    match_reasons.append("✓ 中等质量仓库")

                best_match = PendingMatch(
                    skill_name=skill_name,
                    github_url=repo['html_url'],
                    similarity=similarity,
                    confidence=confidence,
                    repo_name=repo_name,
                    stars=stars,
                    forks=repo.get('forks_count', 0),
                    description=repo_description or "",
                    quality_level=quality_level,
                    match_reasons=match_reasons,
                    warnings=warnings,
                    suggested_at=datetime.now().isoformat()
                )

        # 提高置信度阈值，只返回高质量匹配
        if best_match and best_match.confidence >= 0.75:
            return best_match

        return None

    def search_and_suggest(self, skill_name: str) -> Optional[PendingMatch]:
        """搜索并建议匹配（不直接写入）"""
        # 先检查是否已在待确认列表
        for pending in self.pending_confirm:
            if pending.skill_name == skill_name:
                logger.info(f"  [待确认] {skill_name}: 已有待确认的匹配")
                return pending

        # 执行搜索
        logger.info(f"  [搜索] {skill_name}...")
        search_results = self.search_repositories(skill_name)

        if not search_results:
            logger.info(f"  [无结果] {skill_name}: 未找到匹配的仓库")
            return None

        # 找到最佳匹配
        best_match = self.find_best_match(skill_name, search_results)

        if best_match:
            logger.info(f"  [候选] {skill_name} -> {best_match.repo_name} (相似度: {best_match.similarity:.2f}, 置信度: {best_match.confidence:.2f})")

            # 添加到待确认列表
            self.pending_confirm.append(best_match)
            ConfigManager.save_pending_confirm(self.pending_confirm)

            return best_match

        logger.info(f"  [低相似度] {skill_name}: 未找到足够相似的仓库")
        return None


# ============================================
# 主要评估器
# ============================================
class SkillMatchEvaluator:
    """Skill 匹配评估器（优化版）"""

    def __init__(self):
        self.user_map = ConfigManager.load_github_map()
        self.searcher = SmartGitHubSearcher()
        self.usage_analyzer = UsageFrequencyAnalyzer()

    def evaluate_all(self) -> Tuple[List[SkillInfo], List[PendingMatch]]:
        """评估所有 skills"""
        print("\n" + "=" * 80)
        print(" " * 20 + "Skills GitHub 匹配评估（优化版 v3.0）")
        print("=" * 80)
        print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"高质量阈值: >{HIGH_QUALITY_STARS} stars")
        print(f"重度使用阈值: {HEAVY_USE_DAYS}天内修改 + >{HEAVY_USE_SIZE_MB}MB")
        print("=" * 80 + "\n")

        # 扫描所有 skills
        skill_files = glob.glob(os.path.join(SKILLS_BASE_PATH, '**/SKILL.md'), recursive=True)

        all_skills = {}
        for skill_file_path in skill_files:
            path_parts = skill_file_path.replace('\\', '/').split('/')
            skill_name = ""

            for i, part in enumerate(path_parts):
                if part == 'skills' and i < len(path_parts) - 1:
                    skill_name = path_parts[i + 1]
                    break

            if not skill_name:
                skill_name = os.path.basename(os.path.dirname(skill_file_path))

            if skill_name not in all_skills:
                skill_dir = os.path.dirname(skill_file_path)
                all_skills[skill_name] = skill_dir

        skills_list = sorted(all_skills.items(), key=lambda x: x[0].lower())

        print(f"📋 扫描到 {len(skills_list)} 个 Skills\n")

        # 评估每个 skill
        results = []
        new_pending = []

        for skill_name, skill_path in skills_list:
            # 获取基本信息
            try:
                with open(os.path.join(skill_path, 'SKILL.md'), 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except:
                content = ""

            # 获取时间信息
            try:
                install_time = datetime.fromtimestamp(os.path.getctime(skill_path)).isoformat()
                modified_time = datetime.fromtimestamp(os.path.getmtime(skill_path)).isoformat()
            except Exception:
                install_time = ""
                modified_time = ""

            size_mb = get_dir_size(skill_path)

            # 分析使用频率
            usage_freq, days_since = self.usage_analyzer.analyze(skill_path)

            # 获取 GitHub 信息
            github_url = ""
            stars = 0
            is_high_quality = False
            source = "none"

            # 1. 用户配置
            if skill_name in self.user_map:
                github_url = self.user_map[skill_name]
                source = "user_config"

                # 如果是有效 URL，获取仓库信息
                if github_url.startswith("https://"):
                    repo_info = self.searcher.github_client.get_repo_info(github_url)
                    if repo_info:
                        stars = repo_info.get('stargazers_count', 0)
                        is_high_quality = stars >= HIGH_QUALITY_STARS

            # 2. 从 README 提取
            elif not github_url:
                readme_path = os.path.join(skill_path, 'README.md')
                if os.path.exists(readme_path):
                    try:
                        with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                            url = extract_github_url(f.read())
                            if url:
                                github_url = url
                                source = "readme"

                                repo_info = self.searcher.github_client.get_repo_info(github_url)
                                if repo_info:
                                    stars = repo_info.get('stargazers_count', 0)
                                    is_high_quality = stars >= HIGH_QUALITY_STARS
                    except:
                        pass

            # 3. 已知映射（不自动写入，只是用于显示）
            elif not github_url and skill_name in KNOWN_GITHUB_MAP:
                github_url = KNOWN_GITHUB_MAP[skill_name]
                source = "known_map"

                repo_info = self.searcher.github_client.get_repo_info(github_url)
                if repo_info:
                    stars = repo_info.get('stargazers_count', 0)
                    is_high_quality = stars >= HIGH_QUALITY_STARS

            # 4. 自动搜索（不直接写入，生成待确认）
            elif not github_url:
                pending = self.searcher.search_and_suggest(skill_name)
                if pending:
                    github_url = pending.github_url
                    source = "pending"
                    stars = pending.stars
                    is_high_quality = pending.stars >= HIGH_QUALITY_STARS
                    new_pending.append(pending)

            # 提取描述和触发词
            desc_match = re.search(r'Description:\s*(.+?)[\n\r]+(?:[\n\r]+|#)', content, re.IGNORECASE)
            description = desc_match.group(1).strip() if desc_match else ""

            trigger_match = re.search(r'Trigger:\s*(.+?)[\n\r]+', content, re.IGNORECASE)
            trigger_words = trigger_match.group(1).strip() if trigger_match else ""

            skill_info = SkillInfo(
                name=skill_name,
                path=skill_path,
                trigger_words=trigger_words,
                description=description,
                size_mb=size_mb,
                install_date=install_time,
                last_modified=modified_time,
                github_url=github_url,
                has_trigger_words=bool(trigger_words),
                source=source,
                usage_frequency=usage_freq,
                days_since_modified=days_since,
                is_high_quality=is_high_quality,
                stars=stars
            )

            results.append(skill_info)

        return results, new_pending


# ============================================
# 报告生成器
# ============================================
class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        pass

    def generate(self, skills: List[SkillInfo], new_pending: List[PendingMatch]):
        """生成评估报告"""

        # 统计
        total = len(skills)
        has_github = sum(1 for s in skills if s.github_url and not s.github_url.startswith("自定义"))
        custom_skills = sum(1 for s in skills if s.github_url.startswith("自定义"))
        pending = sum(1 for s in skills if s.source == "pending")
        high_quality = sum(1 for s in skills if s.is_high_quality)
        heavy_use = sum(1 for s in skills if s.usage_frequency == "heavy")

        # 打印统计
        print("📊 统计概览")
        print("-" * 80)
        print(f"  总 Skill 数:        {total}")
        print(f"  有 GitHub 地址:     {has_github} ({has_github/total*100:.1f}%)")
        print(f"  自定义未发布:       {custom_skills}")
        print(f"  待确认匹配:         {pending}")
        print(f"  ⭐ 高质量仓库:      {high_quality} (>{HIGH_QUALITY_STARS} stars)")
        print(f"  🔥 重度使用:        {heavy_use} (最近{HEAVY_USE_DAYS}天修改)")
        print()

        # 数据来源标注
        if USE_CACHE_DATA or RATE_LIMIT_HIT:
            print("=" * 80)
            print("📌 数据来源说明")
            print("=" * 80)
            if USE_CACHE_DATA:
                print("  ⚠️  部分数据来自缓存（非最新）")
            if RATE_LIMIT_HIT:
                print("  ⚠️  遇到了 GitHub API 限流")
            print("  💡 建议设置 GITHUB_TOKEN 环境变量以提高 API 限额")
            print("     或稍后重新运行获取最新数据")
            print("=" * 80)
            print()

        # 按来源分组
        grouped = defaultdict(list)
        for s in skills:
            if s.github_url.startswith("自定义"):
                grouped["custom"].append(s)
            elif s.source == "pending":
                grouped["pending"].append(s)
            elif s.source == "user_config":
                grouped["user"].append(s)
            elif s.source == "readme":
                grouped["readme"].append(s)
            elif s.source == "known_map":
                grouped["known"].append(s)
            else:
                grouped["none"].append(s)

        # 打印待确认匹配
        if grouped["pending"]:
            print("=" * 80)
            print("⚠️ 待确认的自动匹配")
            print("=" * 80)
            print(f"\n有 {len(grouped['pending'])} 个 skills 需要确认 GitHub 地址:\n")
            print("💡 请检查以下匹配是否正确，确认后添加到 user_github_map.json\n")

            for skill in grouped["pending"]:
                print(f"  **{skill.name}**")
                print(f"    候选仓库: {skill.github_url}")
                print(f"    Stars: {skill.stars} | 高质量: {'⭐ 是' if skill.is_high_quality else '否'}")

            print("\n" + "-" * 80 + "\n")

        # 打印高质量仓库
        all_high_quality = [s for s in skills if s.is_high_quality]
        if all_high_quality:
            print("=" * 80)
            print(f"⭐ 高质量仓库 (>{HIGH_QUALITY_STARS} stars)")
            print("=" * 80)
            print(f"\n找到 {len(all_high_quality)} 个高质量仓库:\n")

            # 按 stars 排序
            sorted_by_stars = sorted(all_high_quality, key=lambda x: x.stars, reverse=True)

            for skill in sorted_by_stars:
                heavy_icon = "🔥 " if skill.usage_frequency == "heavy" else ""
                print(f"  {heavy_icon}**{skill.name}**")
                print(f"    GitHub: [{skill.github_url}]({skill.github_url})")
                print(f"    Stars: {skill.stars:,} | 大小: {format_size(skill.size_mb)}")

                if skill.usage_frequency == "heavy":
                    print(f"    🔥 重度使用: 最近修改于 {format_age(skill.last_modified)}")

                print()

            print("-" * 80 + "\n")

        # 打印重度使用的 skills
        all_heavy = [s for s in skills if s.usage_frequency == "heavy"]
        if all_heavy:
            print("=" * 80)
            print(f"🔥 重度使用的 Skills (最近{HEAVY_USE_DAYS}天修改)")
            print("=" * 80)
            print(f"\n找到 {len(all_heavy)} 个重度使用的 skills:\n")

            for skill in all_heavy:
                quality_icon = "⭐" if skill.is_high_quality else ""
                print(f"  🔥 **{skill.name}** {quality_icon}")
                print(f"    大小: {format_size(skill.size_mb)} | 最近修改: {format_age(skill.last_modified)}")

                if skill.github_url:
                    if skill.github_url.startswith("https://"):
                        print(f"    GitHub: [{skill.github_url}]({skill.github_url})")
                    else:
                        print(f"    GitHub: {skill.github_url}")

                print()

            print("-" * 80 + "\n")

        # 打印完整清单
        print("=" * 80)
        print("📋 完整 Skill 清单")
        print("=" * 80)
        print()

        # 图例
        print("图例:")
        print("  🔥 重度使用 | ⭐ 高质量仓库(>1000 stars) | 🏠 自定义未发布")
        print("  ⚠️  待确认")
        print()

        # 按类别分组
        for source_name, source_skills in [
            ("user_config", grouped.get("user", [])),
            ("readme", grouped.get("readme", [])),
            ("known_map", grouped.get("known", [])),
            ("pending", grouped.get("pending", [])),
            ("custom", grouped.get("custom", [])),
            ("none", grouped.get("none", [])),
        ]:
            if not source_skills:
                continue

            labels = {
                "user_config": "✅ 用户配置",
                "readme": "✅ README提取",
                "known_map": "✓ 预定义映射",
                "pending": "⚠️ 待确认",
                "custom": "🏠 自定义未发布",
                "none": "❌ 未匹配"
            }

            print(f"### {labels[source_name]} ({len(source_skills)}个)\n")

            for skill in source_skills:
                # 构建图标
                icons = []
                if skill.usage_frequency == "heavy":
                    icons.append("🔥")
                if skill.is_high_quality:
                    icons.append("⭐")
                if skill.github_url.startswith("自定义"):
                    icons = ["🏠"]

                icon_str = " ".join(icons) + " " if icons else ""

                print(f"{icon_str}**{skill.name}**")

                if skill.github_url:
                    if skill.github_url.startswith("自定义"):
                        print(f"  GitHub: {skill.github_url}")
                    elif skill.github_url.startswith("https://"):
                        print(f"  GitHub: [{skill.github_url}]({skill.github_url})")
                    else:
                        print(f"  GitHub: {skill.github_url}")

                    if skill.stars > 0:
                        quality_mark = " ⭐" if skill.is_high_quality else ""
                        print(f"  Stars: {skill.stars}{quality_mark}")
                else:
                    print(f"  GitHub: 未找到")

                if skill.usage_frequency == "heavy":
                    print(f"  🔥 重度使用: {format_age(skill.last_modified)}")

                print()

        # 保存报告
        self.save_report(skills, {
            'total': total,
            'has_github': has_github,
            'custom_skills': custom_skills,
            'pending': pending,
            'high_quality': high_quality,
            'heavy_use': heavy_use
        })

        # 显示配置建议
        if new_pending:
            self.print_config_suggestion(new_pending)

    def save_report(self, skills: List[SkillInfo], stats: dict):
        """保存报告到文件"""
        report_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        os.makedirs(report_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(report_dir, f'skills_evaluation_v3_{timestamp}.json')

        report_data = {
            'generated_at': datetime.now().isoformat(),
            'data_source': {
                'used_cache': USE_CACHE_DATA,
                'rate_limit_hit': RATE_LIMIT_HIT,
                'note': '部分数据可能来自缓存，非最新' if USE_CACHE_DATA else ''
            },
            'statistics': stats,
            'skills': [s.to_dict() for s in skills]
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        cache_note = " (使用缓存数据)" if USE_CACHE_DATA else ""
        print(f"\n📄 报告已保存到: {report_file}{cache_note}")

    def print_config_suggestion(self, new_pending: List[PendingMatch]):
        """打印配置建议"""
        print("\n" + "=" * 80)
        print("💡 配置建议")
        print("=" * 80)
        print("\n以下匹配需要确认后才能添加到配置文件:\n")

        print("请在 user_github_map.json 中添加:")
        print("{")
        for pending in new_pending:
            print(f'  "{pending.skill_name}": "{pending.github_url}",  # 相似度: {pending.similarity:.2f}, Stars: {pending.stars}')
        print("}")
        print("\n添加后请重新运行评估脚本验证")
        print()


# ============================================
# 主函数
# ============================================
def main():
    """主函数"""
    print("\n🔍 开始评估 Skills...")

    evaluator = SkillMatchEvaluator()
    skills, new_pending = evaluator.evaluate_all()

    generator = ReportGenerator()
    generator.generate(skills, new_pending)

    print("\n" + "=" * 80)
    print("✅ 评估完成")
    print("=" * 80)
    print("\n下一步:")
    print("  1. 查看待确认的匹配")
    print("  2. 确认后添加到 user_github_map.json")
    print("  3. 重新运行脚本验证")
    print()


if __name__ == '__main__':
    main()
