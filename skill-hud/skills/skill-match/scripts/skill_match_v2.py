#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill-Match 数据收集核心脚本 (优化版 v2.0)

功能：
1. 扫描本地技能目录，提取元数据
2. 关联GitHub仓库地址（带缓存和重试）
3. 检查版本更新（支持并发）
4. 评估更新优先级
5. 提示用户补充缺失的GitHub地址（支持自动搜索）
6. 生成skills溯源检查报告

优化：
- 添加请求延迟和重试机制
- 文件大小缓存
- 支持YAML格式
- 更好的错误处理和日志
- 并发请求优化
- 自定义分类规则配置
"""

import os
import sys
import json
import re
import glob
import time
import hashlib
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import quote
from dataclasses import dataclass, asdict
from collections import defaultdict

# 尝试导入可选依赖
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

# ============================================
# 配置
# ============================================
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
SKILLS_BASE_PATH = os.path.expanduser("~/.claude/skills")
CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache')
CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'config')
USER_GITHUB_MAP_PATH = os.path.join(CONFIG_DIR, 'user_github_map.json')
CATEGORY_RULES_PATH = os.path.join(CONFIG_DIR, 'category_rules.json')

# 请求配置
REQUEST_DELAY = 1.0  # API请求间隔（秒）
MAX_RETRIES = 3  # 最大重试次数
REQUEST_TIMEOUT = 10  # 请求超时（秒）
GITHUB_RATE_LIMIT = 60  # GitHub API每小时限制（无token）

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
        with open(CATEGORY_RULES_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_rules, f, ensure_ascii=False, indent=2)

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
# 缓存管理
# ============================================
class CacheManager:
    """缓存管理器"""

    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def get_dir_size(self, path: str) -> float:
        """获取目录大小（带缓存）"""
        # 使用文件修改时间和路径作为缓存key
        cache_key = hashlib.md5(f"{path}_{os.path.getmtime(path)}".encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"size_{cache_key}.json")

        # 检查缓存
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    # 缓存有效期1小时
                    if time.time() - cache_data.get('timestamp', 0) < 3600:
                        return cache_data.get('size', 0)
            except:
                pass

        # 计算大小
        size = self._calculate_dir_size(path)

        # 保存到缓存
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'size': size, 'timestamp': time.time()}, f)
        except:
            pass

        return size

    def _calculate_dir_size(self, path: str) -> float:
        """计算目录实际大小"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            logger.warning(f"计算目录大小失败 {path}: {e}")
        return round(total_size / (1024 * 1024), 2)

    def get(self, key: str, default=None):
        """获取缓存"""
        cache_file = os.path.join(self.cache_dir, f"{hashlib.md5(key.encode()).hexdigest()}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if time.time() - data.get('timestamp', 0) < 3600:  # 1小时有效期
                        return data.get('value', default)
            except:
                pass
        return default

    def set(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存"""
        cache_file = os.path.join(self.cache_dir, f"{hashlib.md5(key.encode()).hexdigest()}.json")
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'value': value, 'timestamp': time.time()}, f)
        except:
            pass

# 全局缓存管理器
cache = CacheManager()

# ============================================
# GitHub API客户端（支持重试和延迟）
# ============================================
class GitHubClient:
    """GitHub API客户端"""

    def __init__(self, token: str = None):
        if not HAS_AIOHTTP:
            raise ImportError("aiohttp未安装，请使用GitHubClientSync或安装: pip install aiohttp")
        self.token = token or GITHUB_TOKEN
        self.headers = {'Accept': 'application/vnd.github.v3+json'}
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'
        self.session = None
        self._last_request_time = 0

    async def _request(self, url: str, method: str = 'GET', **kwargs) -> Optional[dict]:
        """发送HTTP请求（带重试和延迟）"""
        # 请求延迟
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            await asyncio.sleep(REQUEST_DELAY - elapsed)

        # 重试机制
        for attempt in range(MAX_RETRIES):
            try:
                if not self.session:
                    self.session = aiohttp.ClientSession(headers=self.headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT))

                async with self.session.request(method, url, **kwargs) as response:
                    self._last_request_time = time.time()

                    if response.status == 200:
                        return await response.json()
                    elif response.status == 403:
                        # API限流
                        logger.warning("GitHub API限流，等待...")
                        await asyncio.sleep(60)
                        continue
                    else:
                        logger.warning(f"GitHub API请求失败: {response.status}")
                        return None

            except asyncio.TimeoutError:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
            except Exception as e:
                logger.warning(f"请求异常 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)

        return None

    async def get_repo_info(self, owner: str, repo: str) -> Optional[dict]:
        """获取仓库信息"""
        url = f"https://api.github.com/repos/{owner}/{repo}"
        return await self._request(url)

    async def get_latest_commit(self, owner: str, repo: str) -> Optional[dict]:
        """获取最新提交"""
        url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
        items = await self._request(url)
        if items and len(items) > 0:
            return {
                'sha': items[0]['sha'][:7],
                'date': items[0]['commit']['committer']['date'],
                'message': items[0]['commit']['message'].split('\n')[0]
            }
        return None

    async def search_repos(self, query: str) -> List[dict]:
        """搜索仓库"""
        encoded_query = quote(query)
        url = f"https://api.github.com/search/repositories?q={encoded_query}&per_page=5&sort=stars&order=desc"
        result = await self._request(url)
        return result.get('items', []) if result else []

    async def close(self):
        """关闭session"""
        if self.session:
            await self.session.close()

# ============================================
# 同步GitHub客户端（保持兼容）
# ============================================
class GitHubClientSync:
    """同步GitHub API客户端（兼容旧代码）"""

    def __init__(self, token: str = None):
        self.token = token or GITHUB_TOKEN
        self.headers = {'Accept': 'application/vnd.github.v3+json'}
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'
        self._last_request_time = 0

    def _request_with_retry(self, url: str) -> Optional[dict]:
        """带重试的请求"""
        import requests

        # 请求延迟
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)
                self._last_request_time = time.time()

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403:
                    logger.warning("GitHub API限流，等待...")
                    time.sleep(60)
                    continue
                else:
                    return None

            except requests.Timeout:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)

        return None

    def get_repo_info(self, github_url: str) -> Optional[dict]:
        """获取仓库信息"""
        match = re.search(r'github\.com/([^/]+)/([^/]+?)(\.git)?$', github_url)
        if not match:
            return None

        owner = match.group(1)
        repo = match.group(2).replace('.git', '')

        repo_url = f"https://api.github.com/repos/{owner}/{repo}"
        commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"

        try:
            repo_data = self._request_with_retry(repo_url)
            if not repo_data:
                return None

            commits_data = self._request_with_retry(commits_url)
            latest_commit = None
            if commits_data and len(commits_data) > 0:
                latest_commit = {
                    'sha': commits_data[0]['sha'][:7],
                    'date': commits_data[0]['commit']['committer']['date'],
                    'message': commits_data[0]['commit']['message'].split('\n')[0]
                }

            return {
                'stars': repo_data.get('stargazers_count', 0),
                'updated_at': repo_data.get('updated_at'),
                'pushed_at': repo_data.get('pushed_at'),
                'latest_commit': latest_commit,
                'homepage': repo_data.get('homepage'),
                'description': repo_data.get('description'),
                'archived': repo_data.get('archived', False)
            }
        except Exception as e:
            logger.error(f"获取仓库信息失败 {github_url}: {e}")
            return None

# ============================================
# 元数据解析器（支持YAML和Markdown）
# ============================================
class MetadataParser:
    """元数据解析器"""

    @staticmethod
    def parse_skill_file(skill_file: str) -> dict:
        """解析SKILL文件（支持YAML和Markdown）"""
        with open(skill_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 尝试YAML格式
        if content.strip().startswith('---'):
            try:
                import yaml
                yaml_content = content.split('---')[1]
                metadata = yaml.safe_load(yaml_content)
                if metadata and isinstance(metadata, dict):
                    return {
                        'name': metadata.get('name', ''),
                        'version': metadata.get('version', ''),
                        'description': metadata.get('description', ''),
                        'triggers': metadata.get('triggers', metadata.get('trigger', '')),
                    }
            except:
                pass

        # 回退到Markdown解析
        return {
            'name': MetadataParser._extract_name(content),
            'description': MetadataParser._extract_description(content),
            'triggers': MetadataParser._extract_triggers(content),
        }

    @staticmethod
    def _extract_name(content: str) -> str:
        """提取名称"""
        # 尝试YAML frontmatter
        match = re.search(r'name:\s*["\']?([^"\']+)["\']?', content, re.IGNORECASE)
        if match:
            return match.group(1)
        # 尝试标题
        match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_description(content: str) -> str:
        """提取描述"""
        # 尝试Description字段
        match = re.search(r'Description:\s*(.+?)[\n\r]+(?:[\n\r]+|#)', content, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # 获取前200个字符
        lines = content.split('\n')
        desc_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                desc_lines.append(stripped)
                if len(' '.join(desc_lines)) > 200:
                    break

        description = ' '.join(desc_lines[:3])
        if len(description) > 200:
            description = description[:200] + '...'
        return description

    @staticmethod
    def _extract_triggers(content: str) -> str:
        """提取触发词"""
        patterns = [
            r'Trigger:\s*(.+?)[\n\r]+',
            r'触发[词词]+[:：]\s*(.+?)[\n\r]+',
            r'When to use:\s*(.+?)[\n\r]+',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

# ============================================
# 分类器
# ============================================
class SkillClassifier:
    """Skill分类器"""

    def __init__(self):
        self.category_rules = ConfigManager.load_category_rules()
        self.emoji_map = {
            "开发工作流": "⚙️",
            "文档写作": "✍️",
            "设计创意": "🎨",
            "项目管理": "📊",
            "数据处理": "🔧",
            "监控分析": "📈",
            "AI助手": "🤖",
            "其他": "📦"
        }
        self.source_map = {
            "anthropics/anthropic-skills": "🏢 Anthropic官方",
            "cursor-shadowsong": "👤 cursor-shadowsong",
            "wechat-skills": "📱 微信生态",
            "obsidian-skills": "📝 Obsidian社区",
            "microsoft/markitdown": "🔗 Microsoft",
        }

    def classify(self, description: str) -> str:
        """根据描述分类Skill"""
        desc_lower = description.lower() if description else ""

        # 按优先级排序（先匹配较长关键词）
        for category, keywords in sorted(self.category_rules.items(), key=lambda x: -len(x[0])):
            for keyword in sorted(keywords, key=len, reverse=True):
                if keyword in desc_lower:
                    return category

        return "其他"

    def get_source(self, github_url: str) -> str:
        """获取来源标识"""
        if not github_url:
            return "❓ 未知"

        for pattern, source in self.source_map.items():
            if pattern in github_url:
                return source

        return "🔗 社区贡献"

    def get_emoji(self, category: str) -> str:
        """获取类别emoji"""
        return self.emoji_map.get(category, "📌")

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
# 主要功能类
# ============================================
class SkillCollector:
    """Skill收集器"""

    def __init__(self):
        self.classifier = SkillClassifier()
        self.cache = CacheManager()

    def collect_skills(self) -> List[SkillInfo]:
        """扫描并收集所有Skill信息"""
        logger.info("开始扫描Skills目录...")

        all_skills = {}
        skill_files = glob.glob(os.path.join(SKILLS_BASE_PATH, '**/SKILL.md'), recursive=True)

        logger.info(f"找到 {len(skill_files)} 个SKILL.md文件")

        for skill_file_path in skill_files:
            # 提取skill名称
            path_parts = skill_file_path.replace('\\', '/').split('/')
            skill_name = ""

            for i, part in enumerate(path_parts):
                if part == 'skills' and i < len(path_parts) - 1:
                    skill_name = path_parts[i + 1]
                    break

            if not skill_name:
                skill_name = os.path.basename(os.path.dirname(skill_file_path))

            # 跳过重复
            if skill_name in all_skills:
                continue

            # 解析元数据
            try:
                metadata = MetadataParser.parse_skill_file(skill_file_path)
            except Exception as e:
                logger.warning(f"解析元数据失败 {skill_file_path}: {e}")
                metadata = {}

            # 获取目录信息
            skill_dir = os.path.dirname(skill_file_path)

            # 获取时间信息
            try:
                install_time = datetime.fromtimestamp(os.path.getctime(skill_dir)).isoformat()
                modified_time = datetime.fromtimestamp(os.path.getmtime(skill_dir)).isoformat()
            except Exception:
                install_time = ""
                modified_time = ""

            # 获取大小（使用缓存）
            size_mb = self.cache.get_dir_size(skill_dir)

            # 创建SkillInfo对象
            skill_info = SkillInfo(
                name=skill_name,
                path=skill_dir,
                trigger_words=metadata.get('triggers', ''),
                description=metadata.get('description', ''),
                size_mb=size_mb,
                install_date=install_time,
                last_modified=modified_time,
                has_trigger_words=bool(metadata.get('triggers'))
            )

            # 分类和来源
            skill_info.category = self.classifier.classify(skill_info.description)

            all_skills[skill_name] = skill_info

        skills_list = sorted(all_skills.values(), key=lambda x: x.name.lower())
        logger.info(f"成功收集 {len(skills_list)} 个独立的Skill")

        return skills_list

    def fetch_github_urls(self, skills: List[SkillInfo]) -> Tuple[List[SkillInfo], List[SkillInfo]]:
        """获取GitHub地址"""
        logger.info("开始关联GitHub地址...")

        user_map = ConfigManager.load_github_map()
        updated_count = 0
        skills_without_github = []

        for skill in skills:
            if skill.github_url:
                continue

            # 优先级：用户自定义 > README提取 > 已知映射
            new_url = None

            if skill.name in user_map:
                new_url = user_map[skill.name]
            else:
                # 从README提取
                readme_url = self._find_readme_github(skill.path)
                if readme_url:
                    new_url = readme_url
                # 使用已知映射
                elif skill.name in KNOWN_GITHUB_MAP:
                    new_url = KNOWN_GITHUB_MAP[skill.name]

            if new_url:
                skill.github_url = new_url
                skill.source = self.classifier.get_source(new_url)
                updated_count += 1
                logger.info(f"  [+] {skill.name}: {new_url}")
            else:
                skills_without_github.append(skill)

        logger.info(f"成功关联 {updated_count} 个Skills的GitHub地址")
        logger.info(f"仍有 {len(skills_without_github)} 个Skills没有GitHub地址")

        return skills, skills_without_github

    def _find_readme_github(self, skill_dir: str) -> str:
        """在skill目录中查找README并提取GitHub URL"""
        readme_path = os.path.join(skill_dir, 'README.md')
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return extract_github_url(f.read())
            except:
                pass

        # 检查父目录
        parent_dir = os.path.dirname(skill_dir)
        if parent_dir and parent_dir != skill_dir:
            readme_path = os.path.join(parent_dir, 'README.md')
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                        return extract_github_url(f.read())
                except:
                    pass

        return ""

# ============================================
# 版本检查器（支持异步并发）
# ============================================
class VersionChecker:
    """版本检查器"""

    def __init__(self):
        self.github_client_sync = GitHubClientSync()

    def check_versions(self, skills: List[SkillInfo]) -> List[dict]:
        """检查版本更新（同步版本）"""
        logger.info("开始检查版本更新...")

        results = []

        for i, skill in enumerate(skills, 1):
            name = skill.name
            github_url = skill.github_url

            print(f"[{i}/{len(skills)}] {name}...", end=' ')

            # 获取GitHub信息
            github_info = None
            if github_url and 'github.com' in github_url:
                github_info = self.github_client_sync.get_repo_info(github_url)

            # 检查本地版本
            local_version = self._check_local_version(skill.path)

            # 计算更新优先级
            update_info = self._calculate_update_priority(github_info, local_version)

            results.append({
                'name': name,
                'github_url': github_url,
                'github_info': github_info,
                'local_version': local_version,
                'update_info': update_info
            })

            if update_info['available']:
                print(f"可更新 ({update_info['priority']}优先级)")
            elif github_info:
                print(f"已是最新")
            else:
                print(f"无GitHub地址")

        return results

    def _check_local_version(self, skill_path: str) -> dict:
        """检查本地Skill的版本信息"""
        import subprocess

        version_info = {
            'has_git': False,
            'branch': None,
            'commit': None,
            'commit_date': None,
            'dirty': False
        }

        try:
            current_path = skill_path
            while current_path:
                git_dir = os.path.join(current_path, '.git')
                if os.path.exists(git_dir):
                    version_info['has_git'] = True

                    # 获取当前分支
                    try:
                        result = subprocess.run(
                            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                            cwd=current_path, capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            version_info['branch'] = result.stdout.strip()
                    except:
                        pass

                    # 获取当前commit
                    try:
                        result = subprocess.run(
                            ['git', 'rev-parse', 'HEAD'],
                            cwd=current_path, capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            version_info['commit'] = result.stdout.strip()[:7]
                    except:
                        pass

                    # 获取commit日期
                    try:
                        result = subprocess.run(
                            ['git', 'log', '-1', '--format=%ci'],
                            cwd=current_path, capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            version_info['commit_date'] = result.stdout.strip()
                    except:
                        pass

                    # 检查是否有未提交的更改
                    try:
                        result = subprocess.run(
                            ['git', 'status', '--porcelain'],
                            cwd=current_path, capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            version_info['dirty'] = True
                    except:
                        pass
                    break

                parent = os.path.dirname(current_path)
                if parent == current_path:
                    break
                current_path = parent

        except Exception as e:
            pass

        return version_info

    def _calculate_update_priority(self, github_info: dict, local_version: dict) -> dict:
        """计算更新优先级"""
        update_available = False
        update_priority = "无"
        update_reason = []

        if github_info and local_version['has_git'] and github_info.get('latest_commit'):
            if local_version['commit'] != github_info['latest_commit']['sha']:
                update_available = True

                if github_info['latest_commit']['date'] and local_version['commit_date']:
                    try:
                        remote_date = datetime.fromisoformat(github_info['latest_commit']['date'].replace('Z', '+00:00'))
                        local_date = datetime.fromisoformat(local_version['commit_date'])
                        days_behind = (remote_date - local_date).days

                        if days_behind > 180:
                            update_priority = "高"
                            update_reason.append(f"落后{days_behind}天")
                        elif days_behind > 30:
                            update_priority = "中"
                            update_reason.append(f"落后{days_behind}天")
                        else:
                            update_priority = "低"
                            update_reason.append(f"落后{days_behind}天")
                    except:
                        update_priority = "低"
                        update_reason.append("有新版本")

        if github_info and github_info.get('archived'):
            update_reason.append("仓库已归档")

        return {
            'available': update_available,
            'priority': update_priority,
            'reason': update_reason
        }

# ============================================
# GitHub搜索器
# ============================================
class GitHubSearcher:
    """GitHub搜索器"""

    def __init__(self):
        self.github_client_sync = GitHubClientSync()

    def search_skill(self, skill_name: str) -> List[dict]:
        """搜索Skill仓库"""
        logger.info(f"搜索GitHub仓库: {skill_name}")

        try:
            query = f'{skill_name} language:python OR language:typescript OR language:javascript in:name,description,readme'

            # 使用同步requests
            import requests
            encoded_query = quote(query)
            search_url = f'https://api.github.com/search/repositories?q={encoded_query}&per_page=5&sort=stars&order=desc'

            headers = {'Accept': 'application/vnd.github.v3+json'}
            if GITHUB_TOKEN:
                headers['Authorization'] = f'token {GITHUB_TOKEN}'

            response = requests.get(search_url, headers=headers, timeout=REQUEST_DELAY)

            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    return data['items']
        except Exception as e:
            logger.error(f"GitHub搜索失败 {skill_name}: {e}")

        return []

# ============================================
# 报告生成器
# ============================================
class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        self.classifier = SkillClassifier()
        self.version = "2.0.0"

    def generate(self, skills: List[SkillInfo], version_results: List[dict], skills_without_github: List[SkillInfo]) -> str:
        """生成综合报告"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        reports_dir = os.path.join(script_dir, '..', 'reports')
        os.makedirs(reports_dir, exist_ok=True)

        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        # 文件名
        report_filename = f"skills溯源检查报告_v{self.version}_{today}.md"
        report_latest_filename = f"skills溯源检查报告_v{self.version}_{today}_最新.md"

        # 生成报告内容
        md_content = self._generate_markdown(skills, version_results, skills_without_github, today, time_str)

        # 保存报告
        report_path = os.path.join(reports_dir, report_filename)
        report_latest_path = os.path.join(reports_dir, report_latest_filename)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        with open(report_latest_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(f"报告已生成: {report_path}")

        return report_path

    def _generate_markdown(self, skills: List[SkillInfo], version_results: List[dict],
                          skills_without_github: List[SkillInfo], today: str, time_str: str) -> str:
        """生成Markdown报告"""
        md = []

        # 标题
        md.append("# 🎯 Skills 溯源检查报告\n")
        md.append(f"> 📅 **更新时间**: {today} {time_str}\n")
        md.append(f"> 🔢 **版本**: v{self.version}\n")
        md.append("---\n\n")

        # 核心指标
        total = len(skills)
        total_size = sum(s.size_mb for s in skills)
        with_github = sum(1 for s in skills if s.github_url)
        updates_available = sum(1 for r in version_results if r['update_info']['available'])
        high_priority = sum(1 for r in version_results if r['update_info']['priority'] == '高')
        medium_priority = sum(1 for r in version_results if r['update_info']['priority'] == '中')

        md.append("## 📊 核心指标\n\n")
        md.append("| 🎯 指标 | 📈 数值 | 📝 说明 |\n")
        md.append("|--------|--------|--------|\n")
        md.append(f"| **总Skill数** | **{total}** 个 | 全部已安装的技能 |\n")
        md.append(f"| **总占用空间** | **{format_size(total_size)}** | 磁盘占用 |\n")
        md.append(f"| **GitHub来源** | **{with_github}** 个 ({with_github/total*100:.0f}%) | 有明确来源 |\n")
        md.append(f"| **可更新版本** | **{updates_available}** 个 | 有新版本可用 |\n")
        md.append(f"|   - 高优先级 | {high_priority} 个 | 建议立即更新 |\n")
        md.append(f"|   - 中优先级 | {medium_priority} 个 | 可选更新 |\n")

        latest_install = max((s.install_date for s in skills if s.install_date), default=None)
        if latest_install:
            md.append(f"| **最新安装** | **{format_age(latest_install)}** | 最近一次更新 |\n")
        md.append("\n---\n\n")

        # 可视化分析
        md.append("## 📈 可视化分析\n\n")

        # 类别分布
        categories = defaultdict(int)
        for skill in skills:
            categories[skill.category] += 1

        md.append("### 📂 Skill类别分布\n\n")
        max_cat = max(categories.values()) if categories else 1
        bar_width = 40

        for cat in sorted(categories.keys(), key=lambda x: categories[x], reverse=True):
            count = categories[cat]
            pct = count / total * 100
            emoji = self.classifier.get_emoji(cat)
            filled = int((count / max_cat) * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            md.append(f"{emoji} {cat:12} │{bar}│ {pct:.1f}% ({count}个)\n")

        md.append("\n")

        # 空间占用TOP10
        md.append("### 💾 空间占用 TOP 10\n\n")
        top_size = sorted(skills, key=lambda x: x.size_mb, reverse=True)[:10]
        max_size = top_size[0].size_mb if top_size else 1

        for i, skill in enumerate(top_size, 1):
            name = skill.name[:15]
            size = skill.size_mb
            bar_length = int((size / max_size) * bar_width)
            bar = "█" * bar_length + "░" * (bar_width - bar_length)
            md.append(f"{name:15} │{bar}│ {format_size(size)}\n")

        md.append("\n")

        # 来源分布
        sources = defaultdict(int)
        for skill in skills:
            sources[skill.source] = sources.get(skill.source, 0) + 1

        md.append("### 🏪 Skill来源分布\n\n")
        max_source = max(sources.values()) if sources else 1

        for source in sorted(sources.keys(), key=lambda x: sources[x], reverse=True):
            count = sources[source]
            bar_length = int((count / max_source) * bar_width)
            bar = "█" * bar_length + "░" * (bar_width - bar_length)
            md.append(f"{source:20} │{bar}│ {count}个\n")

        md.append("\n")

        # 最近安装时间线
        md.append("### 🕒 最近安装时间线\n\n")
        sorted_by_install = sorted(skills, key=lambda x: x.install_date or '', reverse=True)[:10]

        for i, skill in enumerate(sorted_by_install, 1):
            emoji = self.classifier.get_emoji(skill.category)
            age = format_age(skill.install_date)
            md.append(f"{i:2}. {emoji} **{skill.name}** - `{age}`\n")

        md.append("\n---\n\n")

        # 缺少GitHub地址的Skills
        if skills_without_github:
            md.append("## ⚠️ 缺少 GitHub 地址的 Skills\n\n")
            md.append(f"以下 {len(skills_without_github)} 个 Skills 没有 GitHub 地址：\n\n")
            for skill in skills_without_github:
                md.append(f"- **{skill.name}**\n")
                md.append(f"  - 描述: {skill.description[:80]}...\n")
                md.append(f"  - 路径: `{skill.path}`\n")
            md.append("\n---\n\n")

        # 可更新的Skills
        if updates_available > 0:
            md.append("## 🔄 可更新的 Skills\n\n")
            updates = [r for r in version_results if r['update_info']['available']]
            priority_order = {'高': 0, '中': 1, '低': 2}
            updates = sorted(updates, key=lambda x: priority_order.get(x['update_info']['priority'], 3))

            for r in updates:
                name = r['name']
                priority = r['update_info']['priority']
                priority_emoji = {'高': '🔴', '中': '🟡', '低': '🟢'}.get(priority, '⚪')
                reason = r['update_info']['reason'][0] if r['update_info']['reason'] else ''
                md.append(f"- {priority_emoji} **{name}** - {priority}优先级 ({reason})\n")
            md.append("\n---\n\n")

        # Skill清单
        md.append("## 📋 Skill清单\n\n")

        by_category = defaultdict(list)
        for skill in skills:
            by_category[skill.category].append(skill)

        for category in sorted(by_category.keys()):
            cat_skills = sorted(by_category[category], key=lambda x: x.name.lower())
            emoji = self.classifier.get_emoji(category)

            md.append(f"\n### {emoji} {category} ({len(cat_skills)}个)\n\n")
            md.append("| Skill名称 | 大小 | 来源 | 安装时间 |\n")
            md.append("|-----------|------|------|----------|\n")

            for skill in cat_skills:
                name = skill.name
                size = format_size(skill.size_mb)
                age = format_age(skill.install_date)

                if skill.github_url and skill.github_url not in ["https://github.com/user-attachments/assets", "https://github.com/anthropic.com/anthropic-skills"]:
                    name = f"[{name}]({skill.github_url})"

                md.append(f"| **{name}** | {size} | {skill.source} | {age} |\n")

        md.append("\n---\n\n")

        # 使用说明
        md.append("## 💡 使用说明\n\n")
        md.append("### 📁 配置文件\n\n")
        md.append(f"- **分类规则**: `{os.path.relpath(CATEGORY_RULES_PATH)}`\n")
        md.append(f"- **GitHub映射**: `{os.path.relpath(USER_GITHUB_MAP_PATH)}`\n")
        md.append(f"- **缓存目录**: `{os.path.relpath(CACHE_DIR)}`\n")
        md.append(f"- **日志目录**: `{os.path.relpath(os.path.join(CACHE_DIR, '..', 'logs'))}`\n\n")

        md.append("---\n\n")
        md.append(f"*📅 报告生成: {today} {time_str}:00* | **Skill-Match v{self.version}**\n")

        return ''.join(md)

# ============================================
# 主函数
# ============================================
def main():
    """主执行函数"""
    print("\n" + "=" * 60)
    print("       Skill-Match 数据收集工具 v2.0")
    print(f"       优化版 | {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 60 + "\n")

    # 初始化组件
    collector = SkillCollector()
    checker = VersionChecker()
    reporter = ReportGenerator()

    try:
        # 执行流程
        skills = collector.collect_skills()
        skills, skills_without_github = collector.fetch_github_urls(skills)
        version_results = checker.check_versions(skills)

        # 保存数据
        script_dir = os.path.dirname(os.path.abspath(__file__))
        skills_data_path = os.path.join(script_dir, 'skills_data.json')

        with open(skills_data_path, 'w', encoding='utf-8') as f:
            json.dump([s.to_dict() for s in skills], f, ensure_ascii=False, indent=2)

        logger.info(f"数据已保存: {skills_data_path}")

        # 生成报告
        print("\n生成溯源检查报告...")
        report_path = reporter.generate(skills, version_results, skills_without_github)

        # 统计信息
        total = len(skills)
        with_github = sum(1 for s in skills if s.github_url)
        updates_available = sum(1 for r in version_results if r['update_info']['available'])

        print("\n" + "=" * 60)
        print("数据收集完成！统计信息:")
        print("=" * 60)
        print(f"  总Skill数:     {total}")
        print(f"  有GitHub地址:  {with_github} ({with_github/total*100:.1f}%)")
        print(f"  可更新版本:    {updates_available}")
        print("=" * 60)

    except Exception as e:
        logger.error(f"执行失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n下一步:")
    print("  1. 查看生成的报告")
    print("  2. 根据需要编辑配置文件")
    print("  3. 运行其他子技能处理收集的数据")

if __name__ == '__main__':
    main()
