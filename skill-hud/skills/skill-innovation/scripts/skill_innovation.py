#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill-Innovation 技能创新指导工具 v3.0

功能：
1. 自动所有权检测（author字段、Git历史、文件差异分析）
2. 智能类别推断（基于triggers、代码结构分析）
3. 创新价值评分算法（独特性、实用性、完整性、活跃度）
4. 精准魔改推荐（基于代码分析、已有功能检测）
5. 整合 skill-health 数据
6. 使用数据分析增强
7. Git 命令性能优化（缓存机制）
8. 详细日志记录系统
"""

import os
import sys
import json
import re
import glob
import hashlib
import time
import logging
import argparse
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path

# 设置 Windows 控制台 UTF-8 输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置日志系统
def setup_logging(verbose=False):
    """设置日志系统"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='[%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(__name__)

logger = logging.getLogger(__name__)

# ============================================
# 配置
# ============================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_BASE_PATH = os.path.expanduser("~/.claude/skills")
CACHE_DIR = os.path.join(SCRIPT_DIR, '.cache')
CACHE_EXPIRY_SECONDS = 3600  # 缓存1小时

# 文件忽略模式 - 用于所有权检测时过滤非代码文件
IGNORED_PATTERNS = [
    '.env', '.git', '.idea', '.vscode', '__pycache__',
    'config.json', 'ownership_config.json', 'skills_data.json',
    '.DS_Store', 'thumbs.db', '*.pyc', '*.pyo',
    '.claude/', '.spec-workflow/', 'node_modules/',
    '*.log', '*.tmp', '*.bak', '*.swp'
]

# 缓存相关的全局变量
_cache_enabled = True
_verbose_mode = False

# Claude Code 官方内置技能白名单 v2.4
# 这些技能是 Claude Code 官方提供的，但可能不在 anthropics/skills 仓库的 upstream/main 中
CLAUDE_CODE_OFFICIAL_SKILLS = {
    # 官方开发工作流技能
    'brainstorming', 'executing-plans', 'finishing-a-development-branch',
    'systematic-debugging', 'test-driven-development', 'verification-before-completion',
    'receiving-code-review', 'requesting-code-review', 'subagent-driven-development',
    # 官方 Git 工作流技能
    'using-git-worktrees', 'using-superpowers',
    # 官方写作技能
    'writing-plans', 'writing-skills',
    # 官方其他技能
    'dispatching-parallel-agents', 'json-canvas', 'n8n-skills',
    'obsidian-bases', 'obsidian-markdown', 'planning-with-files',
    'req-change-workflow', 'webapp-testing',
    # Anthropic 官方技能仓库中的技能
    'anthropic-skills', 'obsidian-skills', 'superpowers',
}

# 当前用户名（用于原创检测）- 优先使用 Git 配置
def get_current_git_user():
    """获取当前 Git 配置的用户名"""
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'config', '--global', 'user.name'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    # 降级到系统用户名
    return os.path.basename(os.path.expanduser("~"))

CURRENT_USER = get_current_git_user()

# ============================================
# 工具函数
# ============================================
def format_size(mb):
    """格式化大小"""
    if mb < 0.01:
        return "很小"
    elif mb < 1:
        return f"{mb*1024:.0f}KB"
    elif mb < 1024:
        return f"{mb:.1f}MB"
    else:
        return f"{mb/1024:.1f}GB"


def format_age(iso_date):
    """计算友好的时间显示"""
    if not iso_date:
        return "未知"
    try:
        dt = datetime.fromisoformat(iso_date)
        delta = datetime.now() - dt
        days = delta.days
        if days == 0:
            hours = delta.seconds // 3600
            return f"今天" if hours < 12 else f"{hours}小时前"
        elif days == 1:
            return "昨天"
        elif days < 7:
            return f"{days}天前"
        elif days < 30:
            weeks = days // 7
            return f"{weeks}周前"
        elif days < 90:
            months = days // 30
            return f"{months}月前"
        else:
            return dt.strftime("%Y-%m-%d")
    except Exception:
        return "未知"


def calculate_file_hash(file_path):
    """计算文件的哈希值，用于检测修改"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None


# ============================================
# 缓存管理模块
# ============================================
def get_cache_path(skill_name):
    """获取缓存文件路径"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f'git_{skill_name}.json')


def is_cache_valid(cache_path):
    """检查缓存是否有效"""
    if not os.path.exists(cache_path):
        return False
    cache_age = time.time() - os.path.getmtime(cache_path)
    return cache_age < CACHE_EXPIRY_SECONDS


def load_from_cache(skill_name):
    """从缓存加载 Git 信息"""
    if not _cache_enabled:
        return None

    cache_path = get_cache_path(skill_name)
    if is_cache_valid(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"从缓存加载: {skill_name}")
                return data
        except Exception as e:
            logger.warning(f"缓存读取失败 {skill_name}: {e}")
    return None


def save_to_cache(skill_name, data):
    """保存 Git 信息到缓存"""
    if not _cache_enabled:
        return

    try:
        cache_path = get_cache_path(skill_name)
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"缓存已保存: {skill_name}")
    except Exception as e:
        logger.warning(f"缓存保存失败 {skill_name}: {e}")


def clear_cache():
    """清空所有缓存"""
    if os.path.exists(CACHE_DIR):
        for file in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, file)
            try:
                os.remove(file_path)
            except:
                pass
        logger.info("缓存已清空")


def create_ascii_bar_chart(data, title, width=40):
    """创建ASCII条形图"""
    if not data:
        return f"\n### {title}\n暂无数据\n"

    max_val = max(item[1] for item in data) if data else 1
    if max_val == 0:
        max_val = 1

    lines = [f"\n### {title}\n"]
    for item in data:
        label = item[0]
        value = item[1]
        extra = item[2] if len(item) > 2 else ""

        bar_length = int((value / max_val) * width) if max_val > 0 else 0
        bar = "█" * bar_length + "░" * (width - bar_length)

        info = f" {extra}" if extra else ""
        lines.append(f"{label:15} │{bar}│ {value}{info}")

    return "\n".join(lines) + "\n"


# ============================================
# 数据加载模块
# ============================================
def load_skills_data():
    """加载Skills数据 - 统一从 skill-match 获取"""
    skills_root = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
    skill_match_path = os.path.join(skills_root, 'skill-match', 'scripts', 'skills_data.json')

    if os.path.exists(skill_match_path):
        data_path = skill_match_path
        print("[INFO] 使用 skill-match 生成的数据")
    else:
        data_path = os.path.join(SCRIPT_DIR, 'skills_data.json')
        if not os.path.exists(data_path):
            print(f"[ERROR] 找不到数据文件: {data_path}")
            print("请先运行 skill-match 收集数据")
            return None
        print("[INFO] 使用本地 skills_data.json")

    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_health_data():
    """加载 skill-health 生成的健康度数据"""
    skills_root = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
    health_data_path = os.path.join(skills_root, 'skill-health', 'scripts', 'skills_health_data.json')

    if os.path.exists(health_data_path):
        print("[INFO] 已加载 skill-health 数据")
        with open(health_data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        print("[INFO] 未找到 skill-health 数据，部分功能将受限")
        return None


def load_usage_data():
    """加载使用频率数据"""
    usage_path = os.path.join(SCRIPT_DIR, 'skills_usage_estimated.json')

    if os.path.exists(usage_path):
        with open(usage_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_ownership_config():
    """加载所有权配置（手动配置优先，自动检测为补充）"""
    config_path = os.path.join(SCRIPT_DIR, 'ownership_config.json')

    default_config = {
        "原创": [],
        "魔改": {},
        "说明": "手动配置技能所有权（可选，系统会自动检测）",
        "auto_detection": {
            "enabled": True,
            "users": [CURRENT_USER],
            "user_aliases": [],
            "说明": {
                "enabled": "是否启用自动检测",
                "users": "你的用户名列表（用于识别你的仓库）",
                "user_aliases": "用户别名/昵称列表（用于识别你的仓库）"
            }
        },
        "示例配置": {
            "说明": "取消注释以下内容来手动配置技能",
            "原创示例": ["原创技能名称"],
            "魔改示例": {
                "魔改技能名称": {
                    "based_on": "原始作者/原始仓库名",
                    "modifications": [
                        "修改内容1",
                        "修改内容2"
                    ],
                    "custom_percentage": 30
                }
            }
        }
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 兼容旧配置：添加默认 users 如果不存在
            if 'auto_detection' not in config:
                config['auto_detection'] = default_config['auto_detection']
            elif 'users' not in config['auto_detection']:
                config['auto_detection']['users'] = [CURRENT_USER]
            if 'user_aliases' not in config['auto_detection']:
                config['auto_detection']['user_aliases'] = []

            # 确保有基本字段
            if '原创' not in config:
                config['原创'] = []
            if '魔改' not in config:
                config['魔改'] = {}

            logger.debug(f"已加载配置文件: {config_path}")
            return config
        except json.JSONDecodeError as e:
            logger.warning(f"配置文件格式错误，使用默认配置: {e}")
            return default_config
        except Exception as e:
            logger.warning(f"配置文件加载失败，使用默认配置: {e}")
            return default_config

    # 创建默认配置文件
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        logger.info(f"已创建默认配置文件: {config_path}")
    except Exception as e:
        logger.warning(f"配置文件创建失败: {e}")

    return default_config


def is_user_author(author, config):
    """
    检查 author 是否匹配当前用户

    支持的匹配方式:
    1. 完全匹配 users 列表
    2. 包含匹配 user_aliases 列表
    3. 包含系统用户名 (CURRENT_USER)
    """
    if not author:
        return False

    author_lower = author.lower()

    # 获取配置的用户列表
    users = config.get('auto_detection', {}).get('users', [CURRENT_USER])
    aliases = config.get('auto_detection', {}).get('user_aliases', [])

    # 检查 users 列表 (完全匹配或包含)
    for user in users:
        if user.lower() in author_lower or author_lower in user.lower():
            return True

    # 检查 aliases 列表 (包含匹配)
    for alias in aliases:
        if alias.lower() in author_lower:
            return True

    # 检查系统用户名
    if CURRENT_USER.lower() in author_lower:
        return True

    return False


# ============================================
# 自动所有权检测模块
# ============================================
def extract_skill_metadata(skill_path):
    """从 SKILL.md 提取元数据"""
    skill_file = os.path.join(skill_path, 'SKILL.md')

    if not os.path.exists(skill_file):
        return None

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        metadata = {}

        # 提取 frontmatter 中的字段
        patterns = {
            'name': r'^name:\s*[\'"]?([^\'"\n]+)[\'"]?',
            'version': r'^version:\s*[\'"]?([^\'"\n]+)[\'"]?',
            'author': r'^author:\s*[\'"]?([^\'"\n]+)[\'"]?',
            'category': r'^category:\s*[\'"]?([^\'"\n]+)[\'"]?',
            'triggers': r'(?:triggers|trigger):\s*\[(.*?)\]',
            'based_on': r'(?:based-on|forked-from|based_on):\s*[\'"]?([^\'"\n]+)[\'"]?'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
            if match:
                value = match.group(1).strip()
                if key == 'triggers':
                    # 提取数组内容
                    value = [t.strip().strip('\'"') for t in value.split(',') if t.strip()]
                metadata[key] = value

        return metadata
    except Exception as e:
        return None


def detect_git_modifications(skill_path, use_cache=True):
    """
    通过 Git 检测修改情况（优化版 v2.2 - 血统分析）

    优化点：
    1. 添加缓存支持
    2. 合并 Git 命令减少 subprocess 调用
    3. 改进文件过滤规则
    4. 新增: 检查 upstream 远程仓库（fork 模式）
    5. 新增: 支持 Git worktree 检测（.git 是文件而非目录）

    返回完整的 Git 信息用于血统判定
    """
    skill_name = os.path.basename(skill_path)

    # 尝试从缓存加载
    if use_cache:
        cached_data = load_from_cache(skill_name)
        if cached_data:
            return cached_data

    # v2.2 改进: 使用 git rev-parse 检查是否为 Git 仓库
    # 这样可以支持 worktree（.git 是文件）的情况
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            cwd=skill_path,
            capture_output=True,
            text=True,
            timeout=5
        )
        has_git = result.returncode == 0
    except:
        has_git = False

    if not has_git:
        return {
            'is_repo': False,
            'has_git': False,
            'remote_url': None,
            'upstream_url': None,
            'is_dirty': False,
            'commits_ahead': 0,
            'commits_behind': 0,
            'commits_count': 0,
            'last_commit_date': None
        }

    try:
        import subprocess

        # ========== 优化: 合并 Git 命令调用 ==========
        # 使用 git status -sb --porcelain 一次性获取状态
        # v2.2 改进: 只检查当前技能目录的修改状态
        status_result = {"returncode": 1, "stdout": ""}
        try:
            status_result = subprocess.run(
                ['git', 'status', '-sb', '--porcelain', skill_path],  # 只检查当前目录
                cwd=skill_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if status_result.returncode != 0:
                logger.warning(f"Git status 失败: {skill_name}")
        except subprocess.TimeoutExpired:
            logger.warning(f"Git 命令超时: {skill_name}")
        except Exception as e:
            logger.debug(f"Git status 异常 {skill_name}: {e}")

        # 解析状态输出
        status_lines = status_result.stdout.split('\n') if status_result.returncode == 0 else []

        # 提取分支状态（第一行：## branch... [ahead N] [behind M]）
        branch_line = status_lines[0] if status_lines else ""
        commits_ahead = 0
        commits_behind = 0
        ahead_match = re.search(r'ahead (\d+)', branch_line)
        behind_match = re.search(r'behind (\d+)', branch_line)
        if ahead_match:
            commits_ahead = int(ahead_match.group(1))
        if behind_match:
            commits_behind = int(behind_match.group(1))

        # 检查工作区状态（过滤忽略的文件）
        is_dirty = False
        modified_files = [line.strip() for line in status_lines[1:] if line.strip()]

        if modified_files:
            # 优化: 更完善的文件过滤
            non_config_changes = []
            for f in modified_files:
                # 检查是否匹配任何忽略模式
                is_ignored = any(
                    pattern in f or f.endswith(pattern)
                    for pattern in IGNORED_PATTERNS
                )
                if not is_ignored:
                    non_config_changes.append(f)
            is_dirty = len(non_config_changes) > 0
            if _verbose_mode and non_config_changes:
                logger.debug(f"{skill_name} 修改文件: {non_config_changes[:3]}...")

        # 获取远程地址 - 同时检查 origin 和 upstream
        remote_url = None
        upstream_url = None  # 新增: 用于 fork 模式检测
        try:
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=skill_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                remote_url = result.stdout.strip()
        except Exception as e:
            logger.debug(f"获取 origin URL 失败 {skill_name}: {e}")

        # 新增: 检查 upstream 远程仓库
        try:
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.upstream.url'],
                cwd=skill_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                upstream_url = result.stdout.strip()
                if _verbose_mode:
                    logger.debug(f"{skill_name} 发现 upstream: {upstream_url}")
        except Exception as e:
            logger.debug(f"获取 upstream URL 失败 {skill_name}: {e}")

        # 获取提交信息（合并 log 命令）
        commits_count = 0
        last_commit_date = None
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%ci|%H'],
                cwd=skill_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                last_commit_date = result.stdout.strip()
        except Exception as e:
            logger.debug(f"获取提交信息失败 {skill_name}: {e}")

        # 获取提交数量
        try:
            result = subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD'],
                cwd=skill_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                commits_count = int(result.stdout.strip())
        except Exception as e:
            logger.debug(f"获取提交数量失败 {skill_name}: {e}")

        git_info = {
            'is_repo': True,
            'has_git': True,
            'remote_url': remote_url,
            'upstream_url': upstream_url,  # 新增
            'is_dirty': is_dirty,
            'commits_ahead': commits_ahead,
            'commits_behind': commits_behind,
            'commits_count': commits_count,
            'last_commit_date': last_commit_date
        }

        # 保存到缓存
        save_to_cache(skill_name, git_info)

        return git_info

    except Exception as e:
        logger.error(f"Git 分析异常 {skill_name}: {e}")
        return {
            'is_repo': False,
            'has_git': False,
            'remote_url': None,
            'upstream_url': None,  # 新增
            'is_dirty': False,
            'commits_ahead': 0,
            'commits_behind': 0,
            'commits_count': 0,
            'last_commit_date': None
        }


def analyze_skill_structure(skill_path):
    """
    分析 Skill 的代码结构

    返回详细的代码分析数据，用于动态计算自定义度
    """
    structure = {
        'has_scripts': False,
        'has_references': False,
        'has_readme': False,
        'python_files': 0,
        'total_files': 0,
        'has_custom_logic': False,
        # 新增：代码行数统计
        'total_code_lines': 0,
        'total_comment_lines': 0,
        'total_blank_lines': 0,
        'max_file_lines': 0,
        'function_count': 0,
        'class_count': 0,
        'has_git': False,
        'custom_file_count': 0
    }

    try:
        # 检查目录结构
        structure['has_scripts'] = os.path.exists(os.path.join(skill_path, 'scripts'))
        structure['has_references'] = os.path.exists(os.path.join(skill_path, 'references'))
        structure['has_readme'] = os.path.exists(os.path.join(skill_path, 'README.md'))
        structure['has_git'] = os.path.exists(os.path.join(skill_path, '.git'))

        # 统计文件和代码行数
        for root, dirs, files in os.walk(skill_path):
            # 跳过隐藏目录和 __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

            for file in files:
                structure['total_files'] += 1
                if file.endswith('.py'):
                    structure['python_files'] += 1

                    # 分析 Python 文件内容
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()

                        code_lines = 0
                        comment_lines = 0
                        blank_lines = 0
                        functions = 0
                        classes = 0

                        for line in lines:
                            stripped = line.strip()
                            if not stripped:
                                blank_lines += 1
                            elif stripped.startswith('#'):
                                comment_lines += 1
                            else:
                                code_lines += 1
                                # 统计函数和类定义
                                if stripped.startswith('def '):
                                    functions += 1
                                elif stripped.startswith('class '):
                                    classes += 1

                        structure['total_code_lines'] += code_lines
                        structure['total_comment_lines'] += comment_lines
                        structure['total_blank_lines'] += blank_lines
                        structure['function_count'] += functions
                        structure['class_count'] += classes
                        structure['max_file_lines'] = max(structure['max_file_lines'], code_lines)

                        # 检测自定义逻辑（有实际代码内容的文件）
                        if code_lines > 30:  # 超过30行代码认为有自定义内容
                            structure['custom_file_count'] += 1

                    except:
                        pass

        # 判断是否有自定义逻辑
        structure['has_custom_logic'] = (
            structure['total_code_lines'] > 50 or
            structure['custom_file_count'] >= 1 or
            structure['function_count'] >= 3
        )

    except Exception as e:
        pass

    return structure


def calculate_custom_percentage(structure, git_info, ownership_config, metadata):
    """
    动态计算自定义度百分比

    计算依据:
    1. 代码行数 (最多 40 分)
    2. 文件修改/自定义文件数 (最多 30 分)
    3. Git 提交活跃度 (最多 20 分)
    4. 元数据完整性 (最多 10 分)
    """
    score = 0

    # 1. 代码行数评分 (40 分)
    code_lines = structure.get('total_code_lines', 0)
    if code_lines >= 500:
        score += 40
    elif code_lines >= 300:
        score += 35
    elif code_lines >= 200:
        score += 30
    elif code_lines >= 100:
        score += 25
    elif code_lines >= 50:
        score += 20
    elif code_lines >= 30:
        score += 15
    elif code_lines > 0:
        score += 10

    # 函数和类加分
    function_count = structure.get('function_count', 0)
    class_count = structure.get('class_count', 0)
    if function_count >= 10 or class_count >= 5:
        score += 5
    elif function_count >= 5 or class_count >= 2:
        score += 3

    # 2. 文件修改评分 (30 分)
    custom_file_count = structure.get('custom_file_count', 0)
    if custom_file_count >= 3:
        score += 30
    elif custom_file_count >= 2:
        score += 25
    elif custom_file_count >= 1:
        score += 20

    # 有 scripts 目录但无自定义文件
    if structure.get('has_scripts') and custom_file_count == 0:
        score += 10

    # 有 README
    if structure.get('has_readme'):
        score += 5

    # 3. Git 提交活跃度 (20 分)
    commits_count = git_info.get('commits_count', 0)
    if commits_count >= 50:
        score += 20
    elif commits_count >= 30:
        score += 18
    elif commits_count >= 20:
        score += 15
    elif commits_count >= 10:
        score += 12
    elif commits_count >= 5:
        score += 8
    elif commits_count >= 1:
        score += 5

    # 4. 元数据完整性 (10 分)
    if metadata:
        if metadata.get('triggers'):
            score += 3
        if metadata.get('version'):
            score += 2
        if metadata.get('category'):
            score += 2
        if metadata.get('description'):
            score += 3

    # 有独立的 Git 仓库额外加分
    if structure.get('has_git') and commits_count >= 10:
        score = min(100, score + 10)

    return min(100, max(0, score))


# ============================================
# 多因子评分系统 v3.0 - 不依赖白名单
# ============================================

def calculate_official_score(skill_path, metadata, structure):
    """
    计算技能的官方特征评分（0-100）

    官方技能特征：
    - 有 triggers 字段（官方技能都有）
    - 描述包含 "Use when"、"Use this tool when"
    - SKILL.md 中有 "Use this tool"、"Invoke this tool"
    - 版本号符合 x.y.z 格式
    - 没有 scripts/ 目录或 scripts/ 为空
    - SKILL.md 行数适中（50-200）
    - 没有 references/ 或其他自定义目录
    - 描述包含 "Available skills" 列表
    - 没有 README.md
    """
    score = 0

    skill_file = os.path.join(skill_path, 'SKILL.md')
    if not os.path.exists(skill_file):
        return score

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()
            content_lower = content.lower()
    except:
        return score

    # 1. triggers 字段检查 (+20分)
    if metadata and metadata.get('triggers'):
        if isinstance(metadata['triggers'], list) and len(metadata['triggers']) >= 2:
            score += 20
        elif isinstance(metadata['triggers'], list) and len(metadata['triggers']) >= 1:
            score += 15

    # 2. 官方用语检查 (+25分)
    official_phrases = [
        ('use when', 8),
        ('use this tool', 7),
        ('invoke this tool', 5),
        ('available skills', 5),
        ('you must use this tool', 10),
        ('never use this tool', 5),
        ('before calling this tool', 5),
        ('always use this tool', 5),
    ]

    for phrase, points in official_phrases:
        if phrase in content_lower:
            score += points

    # 3. 版本号规范检查 (+10分)
    if metadata and metadata.get('version'):
        version = metadata['version']
        # 检查是否为语义化版本（x.y.z 或 vx.y.z）
        if re.match(r'^v?\d+\.\d+\.\d+', str(version)):
            score += 10

    # 4. 目录结构检查 (+25分)
    # 没有 scripts/ 目录或目录为空
    if not structure.get('has_scripts'):
        score += 10
    elif structure.get('scripts_file_count', 0) == 0:
        score += 5

    # 没有复杂目录结构
    if not structure.get('has_references'):
        score += 8
    if not structure.get('has_readme'):
        score += 7

    # 5. 文档长度检查 (+10分)
    # 官方技能 SKILL.md 通常在 50-200 行之间
    skill_lines = content.count('\n')
    if 50 <= skill_lines <= 200:
        score += 10
    elif 30 <= skill_lines < 50 or 200 < skill_lines <= 300:
        score += 5

    # 6. 官方特征标记 (+10分)
    official_markers = [
        'claude code',
        'anthropic',
        'superpowers:',
        'skill tool',
        'task tool',
        'mcp server',
        'use the',
        'instead of',
    ]

    marker_count = sum(1 for marker in official_markers if marker in content_lower)
    if marker_count >= 4:
        score += 10
    elif marker_count >= 2:
        score += 5

    return min(100, score)


def calculate_original_score(skill_path, metadata, structure, git_info=None):
    """
    计算技能的原创特征评分（0-100）

    原创技能特征：
    - 描述包含中文、个性化说明
    - 有复杂的 scripts/ 目录（有 .py 文件）
    - SKILL.md 行数 > 200
    - 有 references/ 或其他自定义目录
    - Git 仓库属于用户（非 anthropics）
    - 有配置文件（如 ownership_config.json）
    - 没有 triggers 字段或触发词很少
    - 有个性化注释和说明
    """
    score = 0

    skill_file = os.path.join(skill_path, 'SKILL.md')
    if not os.path.exists(skill_file):
        return score

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()
            content_lower = content.lower()
    except:
        return score

    # 1. 中文和个性化内容 (+30分)
    # 检查中文字符比例
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
    total_chars = len(content)
    if total_chars > 0:
        chinese_ratio = chinese_chars / total_chars
        if chinese_ratio > 0.15:  # 15%以上是中文
            score += 30
        elif chinese_ratio > 0.05:
            score += 15

    # 2. 复杂 scripts 目录 (+25分)
    if structure.get('has_scripts'):
        scripts_file_count = structure.get('scripts_file_count', 0)
        if scripts_file_count >= 3:
            score += 25
        elif scripts_file_count >= 2:
            score += 18
        elif scripts_file_count >= 1:
            score += 10

    # 3. 自定义目录结构 (+20分)
    if structure.get('has_references'):
        score += 10
    if structure.get('has_readme'):
        score += 5
    if structure.get('has_examples'):
        score += 5

    # 4. 文档长度 (+10分)
    skill_lines = content.count('\n')
    if skill_lines > 300:
        score += 10
    elif skill_lines > 200:
        score += 5

    # 5. Git 仓库特征 (+15分)
    if git_info:
        remote_url = git_info.get('remote_url', '')
        if remote_url:
            # 检查是否为用户自己的仓库（不是 anthropics）
            if 'anthropic' not in remote_url.lower():
                # 检查是否包含用户名
                if CURRENT_USER.lower() in remote_url.lower():
                    score += 15
                else:
                    score += 10

    # 6. 个性化特征检查 (+10分)
    # 检查是否有配置文件
    config_files = ['ownership_config.json', 'config.json', 'settings.json']
    for config_file in config_files:
        if os.path.exists(os.path.join(skill_path, config_file)):
            score += 10
            break

    # 没有 triggers 或触发词很少
    if not metadata or not metadata.get('triggers'):
        score += 5
    elif isinstance(metadata.get('triggers'), list) and len(metadata['triggers']) <= 1:
        score += 3

    # 有个性化说明（如 "作者"、"版权" 等）
    personal_markers = ['作者', 'author', '版权', 'copyright', 'license', '许可']
    if any(marker in content_lower for marker in personal_markers):
        score += 5

    return min(100, score)


def classify_by_score(skill_path, metadata, structure, git_info=None):
    """
    基于多因子评分分类技能

    返回 (type, emoji, label, detection_method, reasons, confidence)
    - type: '原生', '魔改', '原创'
    - confidence: 'high', 'medium', 'low'
    """
    official_score = calculate_official_score(skill_path, metadata, structure)
    original_score = calculate_original_score(skill_path, metadata, structure, git_info)

    # 判定规则
    # 官方分数 >= 60 -> 原生
    # 原创分数 >= 50 -> 原创
    # 两者都不满足 -> 魔改

    if official_score >= 60:
        reasons = [f'官方特征评分: {official_score}/100', f'原创特征评分: {original_score}/100']
        confidence = 'high' if official_score >= 80 else 'medium'
        return '原生', '📦', 'Native', 'score_based_classification', reasons, confidence
    elif original_score >= 50:
        reasons = [f'原创特征评分: {original_score}/100', f'官方特征评分: {official_score}/100']
        confidence = 'high' if original_score >= 70 else 'medium'
        return '原创', '🎨', 'Original', 'score_based_classification', reasons, confidence
    else:
        # 检查是否有 Git 仓库和修改
        if git_info and git_info.get('is_dirty'):
            reasons = [f'工作区有修改', f'官方特征评分: {official_score}/100', f'原创特征评分: {original_score}/100']
            return '魔改', '🔧', 'Modified', 'score_based_classification', reasons, 'low'
        else:
            # 默认为原生（保守策略）
            reasons = [f'默认判定为原生', f'官方特征评分: {official_score}/100', f'原创特征评分: {original_score}/100']
            return '原生', '📦', 'Native', 'score_based_classification', reasons, 'low'


# ============================================
# Genealogy Analysis v2.0 - "有罪推定" 原则
# ============================================

def get_current_user_info():
    """
    Phase 0: Identity Setup
    获取当前 Git 配置的用户名和邮箱
    """
    try:
        import subprocess
        # 获取用户名
        result = subprocess.run(
            ['git', 'config', '--global', 'user.name'],
            capture_output=True, text=True, timeout=5
        )
        user_name = result.stdout.strip() if result.returncode == 0 else ''

        # 获取邮箱
        result = subprocess.run(
            ['git', 'config', '--global', 'user.email'],
            capture_output=True, text=True, timeout=5
        )
        user_email = result.stdout.strip() if result.returncode == 0 else ''

        return user_name, user_email
    except:
        return '', ''


def analyze_skill_genealogy_v2(skill_path):
    """
    Genealogy Analysis v2.0 - "有罪推定" 原则

    除非我们确定是用户创建的，否则认为是 "原生" 或 "魔改"

    返回 (type, emoji, label, detection_method, reasons)
    - type: '原生', '魔改', '原创'
    """
    current_user_name, current_user_email = get_current_user_info()

    # 检查是否有 .git 目录
    has_git = os.path.exists(os.path.join(skill_path, '.git'))

    if has_git:
        # ============================================
        # Phase 1: The "Git" Path
        # ============================================
        return _analyze_git_path(skill_path, current_user_name, current_user_email)
    else:
        # ============================================
        # Phase 2: The "Non-Git" Path (关键修复)
        # ============================================
        return _analyze_non_git_path(skill_path, current_user_name)


def _analyze_git_path(skill_path, current_user_name, current_user_email):
    """
    Phase 1: Git 路径分析
    """
    try:
        import subprocess

        # 获取远程 URL
        result = subprocess.run(
            ['git', 'config', '--get', 'remote.origin.url'],
            cwd=skill_path, capture_output=True, text=True, timeout=5
        )
        remote_url = result.stdout.strip() if result.returncode == 0 else ''

        if not remote_url:
            # 无远程 URL，可能是本地仓库，保守判定为原生
            return '原生', '📦', 'Native', 'genealogy_v2_git_no_remote', ['无远程 URL 的本地仓库']

        # 检查 Remote URL 是否包含当前用户名
        if current_user_name and current_user_name.lower() in remote_url.lower():
            # Remote 包含当前用户名，需要检查是否为 fork
            # 获取第一个 commit 的 email
            result = subprocess.run(
                ['git', 'log', '--reverse', '--format=%ae', 'HEAD'],
                cwd=skill_path, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                first_commit_emails = result.stdout.strip().split('\n')
                if first_commit_emails and first_commit_emails[0]:
                    first_email = first_commit_emails[0].strip().lower()
                    # 比较第一个 commit 的 email
                    if first_email != current_user_email.lower():
                        # 第一个 commit 不是用户，说明是 fork
                        # 检查是否有修改
                        result = subprocess.run(
                            ['git', 'status', '--porcelain'],
                            cwd=skill_path, capture_output=True, text=True, timeout=5
                        )
                        is_dirty = bool(result.stdout.strip())

                        result = subprocess.run(
                            ['git', 'rev-list', '--count', '@{u}..HEAD'],
                            cwd=skill_path, capture_output=True, text=True, timeout=5
                        )
                        commits_ahead = int(result.stdout.strip()) if result.returncode == 0 else 0

                        if is_dirty or commits_ahead > 0:
                            return '魔改', '🔧', 'Modified', 'genealogy_v2_fork_modified', [
                                f'Fork 仓库（首个 commit: {first_email}）',
                                f'当前用户: {current_user_email}',
                                '有本地修改' if is_dirty else f'领先 {commits_ahead} 提交'
                            ]
                        else:
                            return '原生', '📦', 'Native', 'genealogy_v2_fork_vanilla', [
                                f'Fork 仓库但未修改',
                                f'首个 commit: {first_email}'
                            ]

            # 第一个 commit 是用户，确认为原创
            return '原创', '🎨', 'Original', 'genealogy_v2_original', [
                f'Git 仓库属于当前用户 ({current_user_name})',
                '首个 commit 由用户创建'
            ]
        else:
            # Remote 不包含当前用户名，是第三方仓库
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=skill_path, capture_output=True, text=True, timeout=5
            )
            is_dirty = bool(result.stdout.strip())

            result = subprocess.run(
                ['git', 'rev-list', '--count', '@{u}..HEAD'],
                cwd=skill_path, capture_output=True, text=True, timeout=5
            )
            commits_ahead = int(result.stdout.strip()) if result.returncode == 0 else 0

            if is_dirty or commits_ahead > 0:
                return '魔改', '🔧', 'Modified', 'genealogy_v2_third_party_modified', [
                    f'第三方仓库: {remote_url}',
                    '有本地修改' if is_dirty else f'领先 {commits_ahead} 提交'
                ]
            else:
                return '原生', '📦', 'Native', 'genealogy_v2_third_party_vanilla', [
                    f'第三方仓库未修改: {remote_url}'
                ]

    except Exception as e:
        logger.debug(f"Git 路径分析失败 {skill_path}: {e}")
        return '原生', '📦', 'Native', 'genealogy_v2_error', [f'分析失败，默认为原生: {str(e)}']


def _analyze_non_git_path(skill_path, current_user_name):
    """
    Phase 2: 非 Git 路径分析（关键修复）

    应用启发式规则验证是否真的是原创
    """
    reasons = []

    # ============================================
    # Heuristic A: 时间悖论检查
    # ============================================
    main_entry_files = ['index.js', 'index.py', 'main.py', 'SKILL.md']
    time_paradox_detected = False

    for entry_file in main_entry_files:
        file_path = os.path.join(skill_path, entry_file)
        if os.path.exists(file_path):
            try:
                stat_info = os.stat(file_path)
                mtime = stat_info.st_mtime  # 最后修改时间
                # Windows 上 birthtime 可能不存在
                try:
                    birthtime = stat_info.st_birthtime
                except AttributeError:
                    birthtime = stat_info.st_ctime  # 降级到创建时间

                time_diff = mtime - birthtime
                now = time.time()

                # 检查时间悖论：修改时间早于创建时间超过 1 分钟
                if time_diff < -60:  # mtime 比 birthtime 早超过 60 秒
                    time_paradox_detected = True
                    reasons.append(f'时间悖论: 文件 {entry_file} 修改时间早于创建时间')

                    # 检查 mtime 距离现在的时间
                    age_hours = (now - mtime) / 3600
                    if age_hours < 24:
                        return '魔改', '🔧', 'Modified', 'genealogy_v2_time_paradox_recent', [
                            '时间悖论 + 最近修改 (24h内)',
                            '判定为下载后修改的第三方技能'
                        ]
                    else:
                        return '原生', '📦', 'Native', 'genealogy_v2_time_paradox_old', [
                            f'时间悖论 + 远古修改 ({age_hours/24:.1f} 天前)',
                            '判定为下载的第三方技能'
                        ]
            except Exception as e:
                logger.debug(f"时间检查失败 {entry_file}: {e}")

    # ============================================
    # Heuristic B: 元数据嗅探
    # ============================================
    for meta_file in ['package.json', 'pyproject.toml', 'setup.py']:
        meta_path = os.path.join(skill_path, meta_file)
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 检查 author 字段
                author_match = re.search(r'["\']?author["\']?\s*[:=]\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
                if author_match:
                    author = author_match.group(1)
                    if current_user_name and current_user_name.lower() not in author.lower():
                        return '原生', '📦', 'Native', 'genealogy_v2_metadata_mismatch', [
                            f'metadata 作者: {author}',
                            f'当前用户: {current_user_name}',
                            '不匹配，判定为第三方技能'
                        ]
            except:
                pass

    # ============================================
    # Heuristic C: 默认回退
    # ============================================
    # 通过了所有检查，承认是原创
    if not time_paradox_detected:
        reasons.append('未检测到时间悖论')
    reasons.append('metadata 检查通过或不存在')

    return '原创', '🎨', 'Original', 'genealogy_v2_default_original', reasons


def is_official_skill_marker(skill_path):
    """
    检查技能是否包含官方技能标记（Anthropic/superpowers 标记）

    返回 (is_official, confidence)
    - is_official: 是否为官方技能
    - confidence: 置信度 (high/medium/low)

    v2.4 改进：
    1. 检查白名单（Claude Code 官方内置技能）
    2. 检查高置信度标记（只依赖白名单和特定标记）
    3. 移除过于宽泛的中置信度标记（如 "Use when"）
    """
    skill_name = os.path.basename(skill_path)

    # 步骤 1: 检查白名单（最高优先级）
    if skill_name in CLAUDE_CODE_OFFICIAL_SKILLS:
        return True, 'high'

    skill_file = os.path.join(skill_path, 'SKILL.md')
    if not os.path.exists(skill_file):
        return False, 'low'

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read().lower()
    except:
        return False, 'low'

    # 步骤 2: 检查高置信度标记（只有这些特定的标记才算官方技能）
    high_confidence_markers = [
        'superpowers:',
        'use superpowers:',
        'claude code skills',
        'you must use this',
        # 更严格的 "Use when" 模式：必须在 description 中
        # 且前面有特定前缀
    ]

    for marker in high_confidence_markers:
        if marker in content:
            return True, 'high'

    # 不再检查中置信度标记（太宽泛）

    return False, 'low'


def auto_detect_ownership(skill, ownership_config, health_data=None):
    """
    血统分析算法 v3.0 - 自动检测 Skill 的所有权类型

    使用多因子评分系统，不依赖白名单

    判定逻辑：
    1. 官方特征评分 >= 60 → 原生
    2. 原创特征评分 >= 50 → 原创
    3. 其他 → 魔改
    """
    skill_name = skill['name']
    skill_path = skill['path']

    # ============================================
    # 步骤 0: 检查手动配置（优先级最高）
    # ============================================
    original_list = ownership_config.get('原创', [])
    modified_list = ownership_config.get('魔改', {})

    if skill_name in original_list:
        return {
            'type': '原创',
            'emoji': '🎨',
            'label': 'Original',
            'detection_method': 'manual_config',
            'custom_percentage': 100
        }

    if skill_name in modified_list:
        info = modified_list[skill_name]
        return {
            'type': '魔改',
            'emoji': '🔧',
            'label': 'Modified',
            'detection_method': 'manual_config',
            'based_on': info.get('based_on', ''),
            'modifications': info.get('modifications', []),
            'custom_percentage': info.get('custom_percentage', 0)
        }
    # 需要区分：
    # - 独立 Git 仓库：skill_path/.git 存在（目录或文件）
    # - 使用主仓库 Git：skill_path/.git 不存在，但可以访问父仓库

    has_independent_git = False
    git_dir_in_skill = os.path.join(skill_path, '.git')

    if os.path.exists(git_dir_in_skill):
        # .git 存在（可能是目录或 worktree 的 gitfile）
        has_independent_git = True
    else:
        # 尝试用 git rev-parse 检查
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=skill_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            # 如果返回的 git_dir 在 skill_path 内，说明是独立仓库
            if result.returncode == 0:
                git_dir = result.stdout.strip()
                # 转换为绝对路径进行比较
                skill_path_abs = os.path.abspath(skill_path)
                git_dir_abs = os.path.abspath(git_dir) if not os.path.isabs(git_dir) else git_dir

                # 检查 git_dir 是否在 skill_path 内（处理 worktree 情况）
                try:
                    git_dir_parent = os.path.dirname(git_dir_abs)
                    if git_dir_parent == skill_path_abs or git_dir_abs.startswith(skill_path_abs + os.sep):
                        has_independent_git = True
                except:
                    pass
        except:
            pass

    if not has_independent_git:
        # 无独立 Git 仓库 -> 使用多因子评分系统
        structure = analyze_skill_structure(skill_path)
        metadata = extract_skill_metadata(skill_path)

        # v3.0: 使用多因子评分系统（不依赖白名单）
        skill_type, emoji, label, method, reasons, confidence = classify_by_score(
            skill_path, metadata, structure, git_info=None
        )

        # 计算自定义百分比
        custom_percentage = calculate_custom_percentage(
            structure, {'has_git': False}, ownership_config, metadata
        )

        # 如果评分判定为魔改，需要检查实际修改
        if skill_type == '魔改':
            custom_percentage = max(custom_percentage, 20)  # 至少20%
        elif skill_type == '原生':
            custom_percentage = 0

        return {
            'type': skill_type,
            'emoji': emoji,
            'label': label,
            'detection_method': method,
            'detection_reasons': reasons,
            'custom_percentage': custom_percentage,
            'metadata': metadata,
            'git_info': {'is_repo': False, 'has_git': False},
            'structure': structure,
            'confidence': confidence
        }

    # ============================================
    # 步骤 2: 处理 Git 仓库（精准判定逻辑）
    # ============================================
    git_info = detect_git_modifications(skill_path)
    metadata = extract_skill_metadata(skill_path)
    structure = analyze_skill_structure(skill_path)

    detection_reasons = []

    # 2.1 获取远程地址（origin 和 upstream）
    remote_url = git_info.get('remote_url')
    upstream_url = git_info.get('upstream_url')

    # ============================================
    # v3.0 新增: 多因子评分系统辅助判断
    # ============================================
    # 对于有 Git 仓库的技能，先使用评分系统进行预判
    # 如果评分明确指向某个类型，可以加速判断
    score_type, score_emoji, score_label, score_method, score_reasons, score_confidence = classify_by_score(
        skill_path, metadata, structure, git_info
    )

    # 如果评分置信度很高，可以提前返回
    if score_confidence == 'high':
        custom_percentage = calculate_custom_percentage(
            structure, git_info, ownership_config, metadata
        )

        # 对于 Git 仓库，需要检查修改状态
        if score_type == '原生' and not git_info.get('is_dirty', False) and git_info.get('commits_ahead', 0) == 0:
            return {
                'type': score_type,
                'emoji': score_emoji,
                'label': score_label,
                'detection_method': score_method,
                'detection_reasons': score_reasons,
                'custom_percentage': 0,
                'metadata': metadata,
                'git_info': git_info,
                'structure': structure,
                'confidence': score_confidence
            }
        elif score_type == '原创' and (remote_url or '').lower() == git_info.get('remote_url', '').lower():
            # 确认是用户自己的仓库
            return {
                'type': score_type,
                'emoji': score_emoji,
                'label': score_label,
                'detection_method': score_method,
                'detection_reasons': score_reasons,
                'custom_percentage': custom_percentage,
                'metadata': metadata,
                'git_info': git_info,
                'structure': structure,
                'confidence': score_confidence
            }

    if upstream_url:
        # 存在 upstream，说明是 fork 的仓库
        # 检查 upstream 是否为官方仓库
        known_official_repos = [
            'anthropics/skills',
            'anthropics/anthropic-skills',
            'obra/superpowers',
        ]

        is_fork_of_official = any(
            repo in upstream_url.lower()
            for repo in known_official_repos
        )

        if is_fork_of_official:
            # v2.3 改进: 检查技能是否在用户的 origin 中首次创建
            # 通过检查技能目录是否在 origin 仓库的历史中
            try:
                import subprocess
                # 获取技能目录相对于 Git 根目录的路径
                result = subprocess.run(
                    ['git', 'rev-parse', '--show-prefix'],
                    cwd=skill_path,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                skill_relative_path = result.stdout.strip() if result.returncode == 0 else ''

                # 获取 Git 根目录
                result = subprocess.run(
                    ['git', 'rev-parse', '--show-toplevel'],
                    cwd=skill_path,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                git_root = result.stdout.strip() if result.returncode == 0 else ''

                # 检查该技能是否在 upstream 中存在
                skill_in_upstream = False
                if git_root and skill_relative_path:
                    try:
                        # 尝试多个可能的分支名
                        for branch in ['upstream/main', 'upstream/master', 'upstream/HEAD']:
                            result = subprocess.run(
                                ['git', 'ls-tree', branch, skill_relative_path],
                                cwd=git_root,
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if result.returncode == 0 and result.stdout.strip():
                                skill_in_upstream = True
                                break
                    except:
                        pass

                # 判断逻辑：
                # 如果技能不在 upstream 中 -> 原创（无论是否在 origin 中或是否已提交）
                # 如果技能在 upstream 中 -> 检查是否有修改

                if not skill_in_upstream:
                    # 技能不在 upstream 中 -> 原创
                    custom_percentage = calculate_custom_percentage(
                        structure, git_info, ownership_config, metadata
                    )
                    return {
                        'type': '原创',
                        'emoji': '🎨',
                        'label': 'Original',
                        'detection_method': 'genealogy_analysis_origin_only',
                        'detection_reasons': [f'不在 upstream 中，判定为原创'],
                        'custom_percentage': custom_percentage,
                        'metadata': metadata,
                        'git_info': git_info,
                        'structure': structure
                    }

            except Exception as e:
                logger.debug(f"检查技能在 upstream 中的状态失败 {skill_name}: {e}")

            # 默认逻辑：检查是否有实际修改
            is_dirty = git_info.get('is_dirty', False)
            commits_ahead = git_info.get('commits_ahead', 0)

            # 只有确实有修改的才是"魔改"
            if is_dirty or commits_ahead > 0:
                custom_percentage = calculate_custom_percentage(
                    structure, git_info, ownership_config, metadata
                )
                reasons = [f'Fork 自官方仓库: {upstream_url}']
                if is_dirty:
                    reasons.append('工作区有修改')
                if commits_ahead > 0:
                    reasons.append(f'领先 upstream {commits_ahead} 提交')

                return {
                    'type': '魔改',
                    'emoji': '🔧',
                    'label': 'Modified',
                    'detection_method': 'genealogy_analysis_upstream',
                    'detection_reasons': reasons,
                    'custom_percentage': custom_percentage,
                    'based_on': upstream_url,
                    'metadata': metadata,
                    'git_info': git_info,
                    'structure': structure
                }
            else:
                # 没有修改，判定为"原生"
                return {
                    'type': '原生',
                    'emoji': '📦',
                    'label': 'Native',
                    'detection_method': 'genealogy_analysis_upstream',
                    'detection_reasons': [f'Fork 自官方仓库但未修改: {upstream_url}'],
                    'custom_percentage': 0,
                    'metadata': metadata,
                    'git_info': git_info,
                    'structure': structure
                }

    # 2.2 检查所有权 (Ownership)
    # 获取配置的用户列表
    config_users = ownership_config.get('auto_detection', {}).get('users', [CURRENT_USER])
    config_aliases = ownership_config.get('auto_detection', {}).get('user_aliases', [])

    # 检查是否为我的仓库
    is_my_repo = False

    # 情况 A: 无远程 URL（本地仓库）-> ORIGINAL
    if not remote_url:
        is_my_repo = True
        detection_reasons.append('本地仓库（无远程 URL）')

    # 情况 B: 远程 URL 包含当前用户名 -> ORIGINAL
    else:
        remote_lower = remote_url.lower()

        # 检查主用户名
        for user in config_users:
            if user.lower() in remote_lower:
                is_my_repo = True
                detection_reasons.append(f'远程 URL 包含用户名: {user}')
                break

        # 检查别名
        if not is_my_repo:
            for alias in config_aliases:
                if alias.lower() in remote_lower:
                    is_my_repo = True
                    detection_reasons.append(f'远程 URL 包含别名: {alias}')
                    break

        # 检查 Git 配置的用户名
        if not is_my_repo and CURRENT_USER.lower() in remote_lower:
            is_my_repo = True
            detection_reasons.append(f'远程 URL 包含 Git 用户名: {CURRENT_USER}')

    # v2.2 新增: 检查是否为知名第三方仓库
    known_third_party = [
        'obra/superpowers',
        'anthropics/skills',
        'anthropics/anthropic-skills',
        'pleaseprompto/notebooklm',
        'op7418/document-illustrator',
        'xj-bear/nanobanana',
    ]

    is_third_party = any(
        repo in (remote_url or '').lower()
        for repo in known_third_party
    )

    # 如果是第三方仓库（无论是否有 upstream）
    if is_third_party and not is_my_repo:
        is_dirty = git_info.get('is_dirty', False)
        commits_ahead = git_info.get('commits_ahead', 0)

        if is_dirty or commits_ahead > 0:
            custom_percentage = calculate_custom_percentage(
                structure, git_info, ownership_config, metadata
            )
            return {
                'type': '魔改',
                'emoji': '🔧',
                'label': 'Modified',
                'detection_method': 'genealogy_analysis_third_party',
                'detection_reasons': [f'第三方仓库且有修改: {remote_url}'],
                'custom_percentage': custom_percentage,
                'based_on': remote_url,
                'metadata': metadata,
                'git_info': git_info,
                'structure': structure
            }
        else:
            return {
                'type': '原生',
                'emoji': '📦',
                'label': 'Native',
                'detection_method': 'genealogy_analysis_third_party',
                'detection_reasons': [f'第三方仓库未修改: {remote_url}'],
                'custom_percentage': 0,
                'metadata': metadata,
                'git_info': git_info,
                'structure': structure
            }

    # 如果是我的仓库 -> ORIGINAL（原创）
    if is_my_repo and not upstream_url:
        custom_percentage = calculate_custom_percentage(
            structure, git_info, ownership_config, metadata
        )
        return {
            'type': '原创',
            'emoji': '🎨',
            'label': 'Original',
            'detection_method': 'genealogy_analysis',
            'detection_reasons': detection_reasons,
            'custom_percentage': min(100, custom_percentage),
            'metadata': metadata,
            'git_info': git_info,
            'structure': structure
        }

    # 2.3 检查修改状态（针对第三方仓库）
    # 此时仓库属于别人，需要检查是否被修改
    is_dirty = git_info.get('is_dirty', False)
    commits_ahead = git_info.get('commits_ahead', 0)
    commits_behind = git_info.get('commits_behind', 0)

    # 判定逻辑
    is_modified = False

    # 条件 A: 工作区脏了 (git status --porcelain 有输出) -> MODDED
    if is_dirty:
        is_modified = True
        detection_reasons.append('工作区存在未提交的修改')

    # 条件 B: 有本地提交 (ahead) -> MODDED
    if commits_ahead > 0:
        is_modified = True
        detection_reasons.append(f'领先远程 {commits_ahead} 个提交')

    # 如果满足任一修改条件 -> MODDED (魔改)
    if is_modified:
        custom_percentage = calculate_custom_percentage(
            structure, git_info, ownership_config, metadata
        )
        return {
            'type': '魔改',
            'emoji': '🔧',
            'label': 'Modified',
            'detection_method': 'genealogy_analysis',
            'detection_reasons': detection_reasons,
            'custom_percentage': custom_percentage,
            'based_on': remote_url or upstream_url or '第三方仓库',
            'metadata': metadata,
            'git_info': git_info,
            'structure': structure
        }

    # 条件 C: 工作区干净 AND 同步或落后 -> VANILLA (原生)
    detection_reasons.append('工作区干净且与远程同步')
    if commits_behind > 0:
        detection_reasons.append(f'落后远程 {commits_behind} 个提交')

    return {
        'type': '原生',
        'emoji': '📦',
        'label': 'Native',
        'detection_method': 'genealogy_analysis',
        'detection_reasons': detection_reasons,
        'custom_percentage': 0,
        'metadata': metadata,
        'git_info': git_info,
        'structure': structure
    }


# ============================================
# 智能类别推断模块
# ============================================
def get_smart_category(skill, ownership_info, health_data=None):
    """
    智能推断 Skill 类别

    优先级：frontmatter category > triggers 分析 > 描述关键词 > 代码结构
    """
    skill_name = skill['name']
    skill_path = skill['path']
    description = skill.get('description', '')

    # 1. 从 metadata 获取
    metadata = ownership_info.get('metadata', {}) if ownership_info else {}
    if metadata and 'category' in metadata:
        return metadata['category']

    # 2. 从 triggers 分析
    if metadata and 'triggers' in metadata:
        triggers = metadata['triggers']
        if isinstance(triggers, list) and triggers:
            triggers_text = ' '.join(triggers).lower()
            category = infer_category_from_keywords(triggers_text)
            if category != "其他":
                return category

    # 3. 从描述关键词
    category = infer_category_from_keywords(description.lower())
    if category != "其他":
        return category

    # 4. 从代码结构
    structure = ownership_info.get('structure', {})
    if structure.get('has_custom_logic'):
        # 有自定义脚本，根据脚本内容推断
        scripts_dir = os.path.join(skill_path, 'scripts')
        for py_file in glob.glob(os.path.join(scripts_dir, '*.py')):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()

                # 分析导入和关键词
                if 'git' in content or 'commit' in content:
                    return "开发工作流"
                elif 'markdown' in content or 'writing' in content:
                    return "文档写作"
                elif 'image' in content or 'canvas' in content or 'ppt' in content:
                    return "设计创意"
            except:
                pass

    return "其他"


def infer_category_from_keywords(text):
    """
    根据关键词推断类别（优化版 v2.1）

    改进：
    1. 使用加权关键词（核心词权重更高）
    2. 扩展关键词覆盖范围
    3. 支持中文和英文混合匹配
    4. 减少类别间关键词重叠
    5. 添加排除规则避免误判
    """
    # 加权关键词配置：{关键词: 权重}
    # 优化: 减少类别间重叠，添加排除词
    categories = {
        "开发工作流": {
            # 核心关键词（权重3）- 专注于开发流程
            "debug": 4, "debugging": 4, "test-driven": 4, "tdd": 4,
            "systematic-debug": 4, "verification": 4,
            # 重要关键词（权重2）
            "implementation": 3, "code-review": 3, "receiving-review": 3,
            "requesting-review": 3, "finishing-branch": 3, "subagent": 3,
            "workflow": 2, "dev-workflow": 2,
            # 中文关键词
            "调试": 4, "验证": 3, "代码评审": 3,
            # 排除词
            "_exclude": ["git", "version", "github"]  # 归入版本控制
        },
        "版本控制": {
            # 核心关键词（权重3）- 专注于 Git 操作
            "git": 4, "worktree": 4, "branch": 3,
            "github": 3, "gitlab": 3, "repository": 3,
            "commit": 3, "merge": 3, "rebase": 3, "push": 2, "pull": 2,
            # 中文关键词
            "提交": 4, "分支": 3, "合并": 3, "仓库": 2,
            # 排除词（空表示不排除）
            "_exclude": []
        },
        "文档写作": {
            # 核心关键词（权重3）- 专注于写作流程
            "writing": 4, "authoring": 4, "draft": 3,
            "article": 3, "blog": 3, "essay": 3, "publish": 3,
            "prd": 4, "requirement": 3, "thought-mining": 4, "成稿": 4,
            # 重要关键词（权重2）
            "markdown": 2, "document": 2, "writing-plans": 3, "writing-skills": 3,
            "wechat": 3, "x-article": 3,
            # 中文关键词
            "写作": 4, "文章": 3, "文档": 2, "博客": 2, "思维挖掘": 4,
            # 排除词
            "_exclude": ["convert", "transform"]  # 归入数据处理
        },
        "设计创意": {
            # 核心关键词（权重3）- 专注于设计和视觉
            "design": 4, "designer": 4, "ui/ux": 4, "ux": 4, "ui": 4,
            "ppt": 4, "presentation": 4, "slide": 3,
            "illustrator": 4, "illustration": 3, "visual": 3,
            # 中文关键词
            "设计": 4, "创意": 3, "界面": 3, "演示": 4,
            # 排除词
            "_exclude": ["canvas", "json"]  # canvas 归入数据处理
        },
        "项目管理": {
            # 核心关键词（权重3）- 专注于项目管理
            "planning": 4, "brainstorm": 4, "solution": 3,
            "executing": 3, "finishing": 3,
            # 重要关键词（权重2）
            "project": 2, "task": 2, "milestone": 2, "plan": 3,
            # 中文关键词
            "规划": 4, "头脑风暴": 4, "方案": 3,
            # 排除词
            "_exclude": []
        },
        "数据处理": {
            # 核心关键词（权重3）- 专注于数据转换
            "convert": 4, "transform": 4, "parse": 3,
            "json": 4, "yaml": 3, "xml": 2,
            "all-2md": 4, "obsidian": 3, "base": 3,
            # 重要关键词（权重2）
            "file": 2, "export": 2, "import": 2, "format": 2,
            "canvas": 4,  # json-canvas 归入此类
            # 中文关键词
            "转换": 4, "解析": 3, "导出": 3, "导入": 3,
            # 排除词
            "_exclude": ["document", "writing"]  # 文档写作优先
        },
        "AI/LLM": {
            # 核心关键词（权重3）- 专注于 AI 相关
            "ai": 4, "llm": 4, "gpt": 4, "claude": 4,
            "agent": 4, "multi-agent": 4, "subagent": 4,
            "prompt": 3, "inference": 3, "model": 3,
            # 中文关键词
            "智能": 3, "模型": 3, "推理": 3,
            # 排除词
            "_exclude": []
        },
        "测试工具": {
            # 核心关键词（权重3）- 专注于测试
            "test": 4, "testing": 4, "webapp": 4,
            "spec": 3, "specification": 3,
            # 中文关键词
            "测试": 4,
            # 排除词
            "_exclude": []
        },
        "监控分析": {
            # 核心关键词（权重3）- 专注于监控和报告
            "monitor": 4, "health": 4, "sk-monitor": 4,
            "analyze": 3, "report": 3, "dashboard": 3,
            "daily-topic": 4,  # 选题监控
            # 中文关键词
            "监控": 4, "健康": 3, "分析": 3, "报告": 3,
            # 排除词
            "_exclude": []
        }
    }

    # 计算每个类别的加权得分（优化版 - 支持排除规则）
    category_scores = {}
    all_excluded_words = set()

    for category, keywords in categories.items():
        exclude_words = keywords.get('_exclude', [])
        all_excluded_words.update(exclude_words)

        score = 0
        matched_keywords = []
        for keyword, weight in keywords.items():
            if keyword == '_exclude':
                continue
            if keyword.lower() in text.lower():
                score += weight
                matched_keywords.append(keyword)

        if score > 0:
            category_scores[category] = {
                'score': score,
                'matches': matched_keywords,
                'exclude': exclude_words
            }

    # 二次过滤: 检查是否命中排除词
    for category, data in list(category_scores.items()):
        for exclude_word in data['exclude']:
            if exclude_word.lower() in text.lower():
                # 扣除排除词的分数
                penalty = data['matches'].count(exclude_word) * 5
                category_scores[category]['score'] = max(0, data['score'] - penalty)

    if category_scores:
        # 返回得分最高的类别
        best_category = max(category_scores, key=lambda k: category_scores[k]['score'])
        if _verbose_mode and category_scores[best_category]['matches']:
            logger.debug(f"类别推断: {best_category} (匹配: {category_scores[best_category]['matches'][:3]})")
        return best_category

    return "其他"


# ============================================
# 创新价值评分模块
# ============================================


def calculate_enhanced_uniqueness(description, all_skills, skill_name):
    """
    增强的独特性评分算法（优化版 v2.1）

    改进点:
    1. 使用词频统计，稀有词权重更高
    2. 使用加权相似度而非简单词汇计数
    3. 考虑描述长度的归一化
    4. 动态阈值调整
    5. 提前终止优化 - 发现高相似度后提前返回
    6. 批量计算优化
    """
    # 分词和预处理
    words = description.lower().split()

    # 过滤停用词（常见但无意义的词）
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
        'that', 'these', 'those', '的', '了', '是', '在', '和', '与', '或',
        '但是', '然而', '因此', '所以', '如果', '那么', '这个', '那个',
        'for', 'use', 'tool', 'help', 'support', 'enable'
    }

    # 移除停用词和短词
    meaningful_words = [w for w in words if len(w) > 2 and w not in stopwords]

    if not meaningful_words:
        return 50, []  # 无有效信息，给中等分数

    # 计算词频 (TF)
    word_freq = {}
    for word in meaningful_words:
        word_freq[word] = word_freq.get(word, 0) + 1

    # 优化: 批量统计所有技能的词频 (DF)
    doc_freq = defaultdict(int)
    for skill in all_skills:
        if skill['name'] == skill_name:
            continue
        other_desc = skill.get('description', '').lower()
        other_words = set(w for w in other_desc.split() if len(w) > 2)
        for word in other_words:
            doc_freq[word] += 1

    # 计算每个词的 IDF 权重
    import math
    total_docs = len(all_skills) - 1
    word_weights = {}
    for word in word_freq:
        df = doc_freq.get(word, 0)
        # IDF = log(total_docs / df)，罕见词权重更高
        idf = math.log((total_docs + 1) / (df + 1)) + 1
        # TF-IDF: 词频 * IDF
        word_weights[word] = word_freq[word] * idf

    # 计算与其他每个技能的加权相似度
    similarities = []
    word_set = set(meaningful_words)
    total_weight = sum(word_weights.values()) if word_weights else 1

    for skill in all_skills:
        if skill['name'] == skill_name:
            continue

        other_desc = skill.get('description', '').lower()
        other_words = [w for w in other_desc.split() if len(w) > 2 and w not in stopwords]

        if not other_words:
            continue

        # 计算 Jaccard 相似度（基于集合）
        other_set = set(other_words)
        jaccard = len(word_set & other_set) / len(word_set | other_set) if (word_set | other_set) else 0

        # 优化: 提前终止 - 如果 Jaccard 相似度太低，跳过加权计算
        if jaccard < 0.05:
            continue

        # 计算加权相似度
        common_words = word_set & other_set
        weighted_similarity = sum(word_weights.get(w, 0) for w in common_words) / total_weight if total_weight > 0 else 0

        # 综合相似度
        combined_similarity = (jaccard * 0.5 + weighted_similarity * 0.5)

        if combined_similarity > 0.15:  # 阈值降低以捕获更细微的相似性
            similarities.append({
                'name': skill['name'],
                'similarity': combined_similarity,
                'jaccard': jaccard,
                'common_words': list(common_words)[:5]
            })

        # 优化: 提前终止 - 如果发现非常相似的技能，可以提前确定低独特性
        if similarities and similarities[-1]['similarity'] > 0.6:
            break

    # 根据相似度数量和程度计算独特性分数
    if not similarities:
        return 100, []

    # 按相似度排序
    similarities.sort(key=lambda x: x['similarity'], reverse=True)

    # 计算惩罚
    penalty = 0
    for sim in similarities[:5]:  # 只考虑最相似的5个
        if sim['similarity'] > 0.5:
            penalty += 20
        elif sim['similarity'] > 0.4:
            penalty += 15
        elif sim['similarity'] > 0.3:
            penalty += 10
        elif sim['similarity'] > 0.2:
            penalty += 5
        else:
            penalty += 2

    uniqueness_score = max(0, 100 - penalty)

    # 生成相似性报告
    similar_skills = [s['name'] for s in similarities[:3]]
    return uniqueness_score, similar_skills
def calculate_innovation_score(skill, ownership_info, all_skills, health_data=None, usage_data=None):
    """
    计算创新价值评分

    评分维度：
    - 独特性 (30%): 功能是否独特，与现有技能的相似度
    - 实用性 (30%): 是否解决实际问题，描述质量
    - 完整性 (20%): 文档和代码是否完整（基于 health_data）
    - 活跃度 (20%): 是否有更新维护
    """
    skill_name = skill['name']
    description = skill.get('description', '')

    scores = {
        'uniqueness': 0,
        'utility': 0,
        'completeness': 0,
        'activity': 0
    }

    reasons = []

    # ========== 独特性评分 (30%) ==========
    # 使用增强的相似度分析算法
    uniqueness_score, similar_skills = calculate_enhanced_uniqueness(description, all_skills, skill_name)
    scores['uniqueness'] = uniqueness_score
    if similar_skills:
        reasons.append(f"独特性: 发现相似技能 {', '.join(similar_skills[:3])}")

    # ========== 实用性评分 (30%) ==========
    # 基于描述长度、功能点数量、是否有具体使用场景
    utility_score = 0

    # 描述长度（越长通常说明越详细）
    desc_length = len(description)
    if desc_length > 500:
        utility_score += 30
    elif desc_length > 200:
        utility_score += 20
    elif desc_length > 100:
        utility_score += 10

    # 检查使用场景关键词
    usage_keywords = ['use case', '使用场景', 'when to use', 'example', '示例', '场景']
    usage_count = sum(1 for kw in usage_keywords if kw in description.lower())
    utility_score += min(30, usage_count * 10)

    # 检查功能点（是否有明确的动词说明功能）
    action_keywords = ['convert', 'generate', 'create', 'analyze', 'transform', 'extract', '自动', '生成', '转换']
    action_count = sum(1 for kw in action_keywords if kw in description.lower())
    utility_score += min(40, action_count * 10)

    scores['utility'] = min(100, utility_score)

    # ========== 完整性评分 (20%) - 基于 health_data ==========
    completeness_score = 50  # 基础分

    if health_data:
        for health_item in health_data:
            if health_item.get('name') == skill_name:
                health_score_obj = health_item.get('health_score', {})
                health_score = health_score_obj.get('score', 50)

                # 使用健康度评分作为完整性评分
                completeness_score = health_score

                # 加分项
                if health_item.get('triggers_check', {}).get('triggers_count', 0) > 0:
                    completeness_score += 5
                if health_item.get('examples_check', {}).get('has_examples'):
                    completeness_score += 5
                if health_item.get('structure_check', {}).get('has_readme'):
                    completeness_score += 5

                break
    else:
        # 没有 health_data 时做简单检查
        metadata = ownership_info.get('metadata', {})
        if metadata.get('triggers'):
            completeness_score += 10
        if metadata.get('version'):
            completeness_score += 5

    scores['completeness'] = min(100, completeness_score)

    # ========== 活跃度评分 (20%) ==========
    activity_score = 0

    # Git 活跃度
    git_info = ownership_info.get('git_info', {})
    if git_info.get('has_git'):
        commits = git_info.get('commits_count', 0)
        if commits >= 20:
            activity_score += 40
        elif commits >= 10:
            activity_score += 30
        elif commits >= 5:
            activity_score += 20
        elif commits >= 1:
            activity_score += 10

        last_commit = git_info.get('last_commit_date')
        if last_commit:
            try:
                commit_date = datetime.fromisoformat(last_commit.replace(' ', 'T'))
                days_since = (datetime.now() - commit_date).days
                if days_since < 7:
                    activity_score += 30
                elif days_since < 30:
                    activity_score += 20
                elif days_since < 90:
                    activity_score += 10
            except:
                pass

    # 文件修改时间
    last_modified = skill.get('last_modified')
    if last_modified:
        try:
            mod_date = datetime.fromisoformat(last_modified)
            days_since = (datetime.now() - mod_date).days
            if days_since < 7:
                activity_score += 20
            elif days_since < 30:
                activity_score += 15
            elif days_since < 90:
                activity_score += 5
        except:
            pass

    # 使用频率（如果有 usage_data）
    if usage_data and skill_name in usage_data:
        usage = usage_data[skill_name]
        if usage.get('has_recent_activity'):
            activity_score += 10

    scores['activity'] = min(100, activity_score)

    # ========== 计算总分 ==========
    total_score = (
        scores['uniqueness'] * 0.3 +
        scores['utility'] * 0.3 +
        scores['completeness'] * 0.2 +
        scores['activity'] * 0.2
    )

    # 确定评级
    if total_score >= 80:
        grade = 'S'
        grade_desc = '卓越'
    elif total_score >= 70:
        grade = 'A'
        grade_desc = '优秀'
    elif total_score >= 60:
        grade = 'B'
        grade_desc = '良好'
    elif total_score >= 40:
        grade = 'C'
        grade_desc = '及格'
    else:
        grade = 'D'
        grade_desc = '需改进'

    return {
        'total': round(total_score, 1),
        'grade': grade,
        'grade_desc': grade_desc,
        'scores': scores,
        'reasons': reasons
    }


# ============================================
# 精准魔改推荐模块
# ============================================
def analyze_modification_opportunities(skills, ownership_results, health_data=None, usage_data=None):
    """
    分析魔改机会，生成精准推荐

    优先级：
    1. 高创新价值但原生使用的
    2. 活跃使用但功能可增强的
    3. 有健康问题但修复后价值高的
    """
    opportunities = []

    for skill, ownership in zip(skills, ownership_results):
        # 跳过已原创和已魔改的
        if ownership['type'] in ['原创', '魔改']:
            continue

        skill_name = skill['name']
        skill_path = skill['path']

        # 计算创新评分
        innovation = calculate_innovation_score(skill, ownership, skills, health_data, usage_data)

        # 检查活跃度
        is_active = False
        if usage_data and skill_name in usage_data:
            usage = usage_data[skill_name]
            is_active = usage.get('has_recent_activity', False)

        # 检查健康问题
        health_issues = []
        if health_data:
            for h in health_data:
                if h.get('name') == skill_name:
                    if h.get('health_score', {}).get('score', 100) < 75:
                        health_issues = h.get('health_score', {}).get('deductions', [])
                    break

        # 分析可改进点
        metadata = ownership.get('metadata', {})
        structure = ownership.get('structure', {})

        improvement_ideas = []

        # 基于健康度的问题
        if health_issues:
            for issue in health_issues:
                if '触发词' in issue:
                    improvement_ideas.append("添加中文触发词")
                elif '示例' in issue:
                    improvement_ideas.append("补充使用示例")
                elif 'README' in issue:
                    improvement_ideas.append("创建中文README")

        # 基于结构分析
        if not structure.get('has_scripts'):
            improvement_ideas.append("添加自动化脚本")

        if not structure.get('has_readme'):
            improvement_ideas.append("编写使用文档")

        # 基于功能增强
        description = skill.get('description', '').lower()
        if 'convert' in description or '转换' in description:
            improvement_ideas.append("支持更多文件格式")
        if 'image' in description or '图片' in description:
            improvement_ideas.append("添加批量处理功能")
            improvement_ideas.append("优化中文提示词支持")

        # 计算推荐优先级
        priority_score = 0

        # 高创新价值
        if innovation['total'] >= 70:
            priority_score += 30

        # 活跃使用
        if is_active:
            priority_score += 20

        # 有改进空间
        if improvement_ideas:
            priority_score += len(improvement_ideas) * 5

        # Anthropic 官方技能优先推荐
        github_url = skill.get('github_url', '')
        if 'anthropics/anthropic-skills' in github_url:
            priority_score += 15

        opportunities.append({
            'name': skill_name,
            'priority_score': priority_score,
            'innovation_score': innovation,
            'is_active': is_active,
            'health_issues': health_issues,
            'improvement_ideas': list(set(improvement_ideas)),  # 去重
            'category': get_smart_category(skill, ownership, health_data),
            'github_url': github_url,
            'description': skill.get('description', '')[:150]
        })

    # 按优先级排序
    opportunities.sort(key=lambda x: x['priority_score'], reverse=True)

    return opportunities


def generate_modification_recommendations(opportunities, top_n=10):
    """生成精准魔改推荐"""
    recommendations = []

    for opp in opportunities[:top_n]:
        name = opp['name']
        category = opp['category']
        github_url = opp['github_url']
        ideas = opp['improvement_ideas']
        innovation = opp['innovation_score']

        # 估算难度
        difficulty = '简单'
        if len(ideas) >= 4 or innovation['scores']['completeness'] < 60:
            difficulty = '复杂'
        elif len(ideas) >= 2:
            difficulty = '中等'

        # 估算魔改后的自定义度
        estimated_custom = min(40, len(ideas) * 10 + 15)

        recommendations.append({
            'name': name,
            'category': category,
            'github_url': github_url,
            'ideas': ideas,
            'difficulty': difficulty,
            'estimated_custom': estimated_custom,
            'innovation_score': innovation,
            'priority_score': opp['priority_score']
        })

    return recommendations


# ============================================
# 新增功能模块
# ============================================

def generate_skill_combinations(skills, ownership_results):
    """
    🎯 技能组合推荐

    分析可以组合使用的技能，提供工作流优化建议

    返回组合推荐列表
    """
    # 技能组合模式库
    combinations = [
        {
            'name': '完整开发工作流',
            'skills': ['brainstorming', 'executing-plans', 'systematic-debugging', 'test-driven-development'],
            'description': '从头脑风暴到测试的完整开发流程',
            'benefit': '提升开发效率，确保代码质量'
        },
        {
            'name': '代码审查流程',
            'skills': ['requesting-code-review', 'receiving-code-review', 'systematic-debugging'],
            'description': '请求审查 -> 接收反馈 -> 修复问题',
            'benefit': '建立良好的代码审查习惯'
        },
        {
            'name': '文档创作流程',
            'skills': ['writing-plans', 'all-2md', 'prd-doc-writer'],
            'description': '规划 -> 转换 -> 生成专业文档',
            'benefit': '标准化文档输出，提升质量'
        },
        {
            'name': '项目管理组合',
            'skills': ['finishing-a-development-branch', 'verification-before-completion', 'subagent-driven-development'],
            'description': '完成分支 -> 验证 -> 协作开发',
            'benefit': '规范项目收尾流程'
        },
        {
            'name': '需求分析链路',
            'skills': ['req-record', 'solution-creator', 'prd-doc-writer'],
            'description': '需求记录 -> 方案设计 -> 文档输出',
            'benefit': '完整的需求到设计链路'
        },
        {
            'name': '设计创意工具箱',
            'skills': ['brainstorming', 'json-canvas', 'image-assistant'],
            'description': '创意生成 -> 结构化 -> 可视化',
            'benefit': '激发创意，快速原型'
        },
        {
            'name': 'Git 工作流优化',
            'skills': ['using-git-worktrees', 'finishing-a-development-branch', 'verification-before-completion'],
            'description': '分支管理 -> 完成开发 -> 验证',
            'benefit': '高效的 Git 工作流'
        },
        {
            'name': '内容创作套件',
            'skills': ['daily-topic-selector', 'thought-mining', 'wechat-writing'],
            'description': '选题 -> 思维挖掘 -> 写作',
            'benefit': '系统化内容生产流程'
        }
    ]

    # 检查哪些组合的用户已拥有
    available_combinations = []
    skill_names = {s['name'].lower() for s in skills}

    for combo in combinations:
        owned_skills = [s for s in combo['skills'] if s.lower() in skill_names]
        coverage = len(owned_skills) / len(combo['skills'])

        if coverage >= 0.5:  # 至少拥有50%的技能
            available_combinations.append({
                **combo,
                'owned_skills': owned_skills,
                'coverage': coverage,
                'missing_skills': [s for s in combo['skills'] if s.lower() not in skill_names]
            })

    # 按覆盖率排序
    available_combinations.sort(key=lambda x: x['coverage'], reverse=True)

    return available_combinations[:5]  # 返回前5个推荐


def generate_achievements(ownership_results, innovation_scores):
    """
    🏆 成就系统

    基于用户的技能使用情况，计算达成成就

    返回成就列表
    """
    original_count = sum(1 for o in ownership_results if o['type'] == '原创')
    modified_count = sum(1 for o in ownership_results if o['type'] == '魔改')
    native_count = sum(1 for o in ownership_results if o['type'] == '原生')

    avg_innovation = sum(s['total'] for s in innovation_scores) / len(innovation_scores) if innovation_scores else 0
    high_innovation_count = sum(1 for s in innovation_scores if s['total'] >= 70)

    # 成就定义
    achievements = []

    # 原创成就
    if original_count >= 1:
        achievements.append({
            'name': '🌟 创造新手',
            'desc': '创造了第一个原创技能',
            'level': 'bronze',
            'unlocked': True
        })
    if original_count >= 3:
        achievements.append({
            'name': '🎨 创意达人',
            'desc': '创造了3个原创技能',
            'level': 'silver',
            'unlocked': True
        })
    if original_count >= 5:
        achievements.append({
            'name': '👑 创造大师',
            'desc': '创造了5个原创技能',
            'level': 'gold',
            'unlocked': True
        })
    if original_count >= 10:
        achievements.append({
            'name': '💎 传奇创造者',
            'desc': '创造了10个原创技能',
            'level': 'legendary',
            'unlocked': True
        })

    # 魔改成就
    if modified_count >= 1:
        achievements.append({
            'name': '🔧 魔改新手',
            'desc': '魔改了第一个技能',
            'level': 'bronze',
            'unlocked': True
        })
    if modified_count >= 5:
        achievements.append({
            'name': '⚙️ 定制专家',
            'desc': '魔改了5个技能',
            'level': 'silver',
            'unlocked': True
        })
    if modified_count >= 10:
        achievements.append({
            'name': '🛠️ 魔改大师',
            'desc': '魔改了10个技能',
            'level': 'gold',
            'unlocked': True
        })

    # 创新成就
    if high_innovation_count >= 1:
        achievements.append({
            'name': '💡 创新先锋',
            'desc': '拥有1个高价值技能（评分≥70）',
            'level': 'silver',
            'unlocked': True
        })
    if high_innovation_count >= 3:
        achievements.append({
            'name': '🚀 创新领袖',
            'desc': '拥有3个高价值技能（评分≥70）',
            'level': 'gold',
            'unlocked': True
        })
    if avg_innovation >= 60:
        achievements.append({
            'name': '📈 均衡发展',
            'desc': '平均创新评分达到60',
            'level': 'silver',
            'unlocked': True
        })

    # 生态成就
    total = original_count + modified_count + native_count
    if total >= 20:
        achievements.append({
            'name': '📚 技能收藏家',
            'desc': '收集了20个技能',
            'level': 'bronze',
            'unlocked': True
        })
    if total >= 50:
        achievements.append({
            'name': '🏛️ 技能博物馆',
            'desc': '收集了50个技能',
            'level': 'gold',
            'unlocked': True
        })

    # 检查未解锁的成就（展示下一步目标）
    locked_achievements = []

    if original_count == 0:
        locked_achievements.append({
            'name': '🌟 创造新手',
            'desc': '创造你的第一个原创技能',
            'level': 'bronze',
            'unlocked': False,
            'progress': f'当前: {original_count}/1'
        })
    elif original_count < 3:
        locked_achievements.append({
            'name': '🎨 创意达人',
            'desc': '创造3个原创技能',
            'level': 'silver',
            'unlocked': False,
            'progress': f'当前: {original_count}/3'
        })
    elif original_count < 5:
        locked_achievements.append({
            'name': '👑 创造大师',
            'desc': '创造5个原创技能',
            'level': 'gold',
            'unlocked': False,
            'progress': f'当前: {original_count}/5'
        })

    if modified_count == 0 and native_count > 0:
        locked_achievements.append({
            'name': '🔧 魔改新手',
            'desc': '魔改你的第一个技能',
            'level': 'bronze',
            'unlocked': False,
            'progress': '当前: 0/1'
        })
    elif modified_count < 5:
        locked_achievements.append({
            'name': '⚙️ 定制专家',
            'desc': f'魔改5个技能',
            'level': 'silver',
            'unlocked': False,
            'progress': f'当前: {modified_count}/5'
        })

    return {
        'unlocked': achievements,
        'locked': locked_achievements[:3]  # 只显示最近的3个未解锁成就
    }


def generate_skill_fusions(skills, ownership_results, innovation_scores):
    """
    🔄 技能融合推荐

    分析功能相似的技能，推荐可以合并/整合的技能

    返回融合建议列表
    """
    # 技能融合模式库
    fusion_patterns = [
        {
            'name': '文档处理工具集',
            'skills': ['all-2md', 'json-canvas', 'obsidian-markdown', 'writing-plans'],
            'fusion_target': '文档处理工具集',
            'reason': '都处理文档转换和格式化',
            'benefit': '统一文档处理流程，减少工具碎片化'
        },
        {
            'name': '测试工具集合',
            'skills': ['test-driven-development', 'webapp-testing', 'systematic-debugging', 'verification-before-completion'],
            'fusion_target': '测试与验证工具集',
            'reason': '都涉及代码测试和验证',
            'benefit': '建立完整的测试工作流'
        },
        {
            'name': '创意工具集',
            'skills': ['brainstorming', 'json-canvas', 'image-assistant', 'thought-mining'],
            'fusion_target': '创意生成工具集',
            'reason': '都用于创意和思维活动',
            'benefit': '整合创意工作流，提升灵感转化率'
        },
        {
            'name': '代码审查工具链',
            'skills': ['requesting-code-review', 'receiving-code-review', 'verification-before-completion'],
            'fusion_target': '代码审查工具链',
            'reason': '都涉及代码审查和质量控制',
            'benefit': '建立完整的代码审查流程'
        },
        {
            'name': '写作工具集',
            'skills': ['writing-plans', 'writing-skills', 'thought-mining', 'wechat-writing'],
            'fusion_target': '写作助手工具集',
            'reason': '都用于写作和内容创作',
            'benefit': '统一写作流程，提升创作效率'
        },
        {
            'name': '项目管理工具组',
            'skills': ['finishing-a-development-branch', 'executing-plans', 'subagent-driven-development', 'planning-with-files'],
            'fusion_target': '项目管理工具组',
            'reason': '都涉及项目规划和执行',
            'benefit': '统一项目管理方法'
        },
        {
            'name': '监控分析工具集',
            'skills': ['sk-monitor', 'skill-health', 'skill-hud', 'skill-match', 'daily-topic-selector'],
            'fusion_target': '技能管理系统',
            'reason': '都是技能管理和分析工具',
            'benefit': '整合为一个完整的技能管理平台'
        }
    ]

    # 检查哪些融合模式用户已拥有足够的基础
    fusion_recommendations = []
    skill_names = {s['name'].lower() for s in skills}

    for pattern in fusion_patterns:
        owned_skills = [s for s in pattern['skills'] if s.lower() in skill_names]

        if len(owned_skills) >= 3:  # 至少拥有3个相关技能才推荐融合
            fusion_recommendations.append({
                'name': pattern['fusion_target'],
                'source_skills': owned_skills,
                'skill_count': len(owned_skills),
                'reason': pattern['reason'],
                'benefit': pattern['benefit'],
                'complexity': '高' if len(owned_skills) >= 5 else '中'
            })

    # 按技能数量排序（越多越优先）
    fusion_recommendations.sort(key=lambda x: x['skill_count'], reverse=True)

    return fusion_recommendations[:5]  # 返回前5个推荐


# ============================================
# 创新建议生成模块
# ============================================
def generate_innovation_tips(avg_custom_score, original_count, modified_count, native_count, innovation_scores):
    """生成个性化创新建议"""
    tips = []

    # 基于当前状态的建议
    if original_count == 0:
        tips.append({
            'type': '原创建议',
            'priority': '高',
            'title': '创建你的第一个原创Skill',
            'description': '从日常工作中寻找重复性任务，将其自动化为一个Skill',
            'actions': [
                '使用 `/skill-creator` 辅助创建',
                '从简单的需求开始，逐步完善',
                '参考现有Skills的结构'
            ]
        })

    if modified_count == 0 and native_count > 0:
        tips.append({
            'type': '魔改建议',
            'priority': '中',
            'title': '尝试魔改一个常用Skill',
            'description': '选择你常用的原生Skill，添加个人配置和优化',
            'actions': [
                '选择活跃使用的Skill',
                '添加你个人需要的配置',
                '优化交互流程',
                '记录在 ownership_config.json 中'
            ]
        })

    # 基于创新评分的建议
    high_innovation = [s for s in innovation_scores if s['total'] >= 70]
    if len(high_innovation) < 3:
        tips.append({
            'type': '创新建议',
            'priority': '中',
            'title': '发现高价值创新机会',
            'description': '你的 Skills 中有一些高价值的，可以进一步挖掘',
            'actions': [
                '关注创新评分 > 70 的 Skills',
                '考虑将其系列化、组合化',
                '分享到社区获取反馈'
            ]
        })

    # 基于自定义度的建议
    if avg_custom_score < 20:
        tips.append({
            'type': '成长建议',
            'priority': '高',
            'title': '提升自定义度到20%以上',
            'description': '从新手级成长为成长级，开始打造个人生态',
            'actions': [
                '魔改2-3个常用Skills',
                '创建1个原创Skill',
                '建立个人Skill规范'
            ]
        })
    elif avg_custom_score < 40:
        tips.append({
            'type': '进阶建议',
            'priority': '中',
            'title': '向进阶级迈进',
            'description': '从成长级晋升为进阶级，培养个人Skill生态',
            'actions': [
                '将自定义度提升到40%以上',
                '魔改5-10个常用Skills',
                '创建2-3个原创Skills'
            ]
        })
    elif avg_custom_score < 70:
        tips.append({
            'type': '大师之路',
            'priority': '低',
            'title': '向大师级进发',
            'description': '从进阶级晋升为大师级，形成完整生态',
            'actions': [
                '将自定义度提升到70%以上',
                '创建系列化原创Skills',
                '分享到GitHub回馈社区'
            ]
        })

    return tips


# ============================================
# 报告生成模块
# ============================================
def generate_innovation_report(verbose=False, no_cache=False):
    """生成创新指导报告（优化版 v2.1）

    Args:
        verbose: 是否显示详细输出
        no_cache: 是否禁用缓存
    """

    # 设置全局变量
    global _verbose_mode, _cache_enabled
    _verbose_mode = verbose
    _cache_enabled = not no_cache

    if verbose:
        logger.setLevel(logging.DEBUG)

    if no_cache:
        clear_cache()
        logger.info("缓存已禁用，正在重新分析...")
    reports_dir = os.path.join(SCRIPT_DIR, '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")

    # 检查当天已有的报告数量，确定版本号
    existing_reports = []
    for f in os.listdir(reports_dir):
        if f.startswith(f'SKILLS_创新指导_v') and f.endswith(f'_{date_str}.md'):
            try:
                # 去掉日期后缀，提取版本号
                # SKILLS_创新指导_v1.0_2026-01-24.md -> SKILLS_创新指导_v1.0
                without_date = f[:-len(f'_{date_str}.md')]
                # SKILLS_创新指导_v1.0 -> v1.0
                version_str = without_date.split('v')[-1]
                existing_reports.append(version_str)
            except:
                pass

    if existing_reports:
        version_numbers = []
        for v in existing_reports:
            parts = v.split('.')
            try:
                if len(parts) >= 2:
                    major = int(parts[0])
                    minor = int(parts[1])
                    version_numbers.append((major, minor))
            except:
                pass

        if version_numbers:
            latest = max(version_numbers)
            new_major, new_minor = latest
            new_minor += 1
            version = f"{new_major}.{new_minor}"
        else:
            version = "1.0"
    else:
        version = "1.0"

    # ============================================
    # 开始执行分析流程
    # ============================================
    print("\n" + "=" * 60)
    print(f"       Skill-Innovation 创新指导工具 v2.1")
    print(f"       {'[详细模式]' if _verbose_mode else '[标准模式]'}")
    print(f"       {'[缓存禁用]' if not _cache_enabled else '[缓存启用]'}")
    print("=" * 60 + "\n")

    # 加载数据
    print("[步骤 1/4] 加载数据...")
    skills = load_skills_data()
    if not skills:
        return

    ownership_config = load_ownership_config()
    health_data = load_health_data()
    usage_data = load_usage_data()

    print(f"[OK] 已加载 {len(skills)} 个 Skills")
    if health_data:
        print(f"[OK] 已加载健康度数据")
    if usage_data:
        print(f"[OK] 已加载使用数据")

    # 分析所有权
    print("\n[步骤 2/4] 分析所有权...")
    ownership_results = []
    for skill in skills:
        ownership = auto_detect_ownership(skill, ownership_config, health_data)
        ownership_results.append(ownership)

    original_count = sum(1 for o in ownership_results if o['type'] == '原创')
    modified_count = sum(1 for o in ownership_results if o['type'] == '魔改')
    native_count = sum(1 for o in ownership_results if o['type'] == '原生')

    total_custom_score = sum(o.get('custom_percentage', 0) for o in ownership_results)
    avg_custom_score = total_custom_score / len(skills) if skills else 0

    print(f"[OK] 原创: {original_count}, 魔改: {modified_count}, 原生: {native_count}")
    print(f"[OK] 平均自定义度: {avg_custom_score:.1f}%")

    # 计算创新评分
    print("\n[步骤 3/4] 计算创新评分...")
    innovation_scores = []
    for skill, ownership in zip(skills, ownership_results):
        score = calculate_innovation_score(skill, ownership, skills, health_data, usage_data)
        innovation_scores.append(score)

    print(f"[OK] 已完成创新评分")

    # 生成推荐
    print("\n[步骤 4/4] 生成魔改推荐...")
    opportunities = analyze_modification_opportunities(skills, ownership_results, health_data, usage_data)
    recommendations = generate_modification_recommendations(opportunities, top_n=10)

    print(f"[OK] 已生成 {len(recommendations)} 条推荐")

    # 生成报告
    print("\n[生成] 创新指导报告...")
    md = []

    # 标题
    md.append(f"# 🚀 Skills 创新指导报告 v{version}\n")
    md.append(f"> 📅 **报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    md.append(f"> 🔧 **版本**: {version} - 增强版\n")
    md.append("> 💡 **理念**: 支持原创，鼓励魔改，人人都应skill\n")
    md.append(f"> 🆕 **v{version} 新功能**: 自动所有权检测、智能类别推断、创新价值评分\n")
    md.append("---\n")

    # ============================================
    # 🏆 所有权与创新总览
    # ============================================
    md.append("## 🏆 所有权与创新总览\n\n")

    # 所有权分布
    md.append("### 📊 所有权分布\n\n")
    max_count = max(original_count, modified_count, native_count, 1)

    ownership_data = [
        ("🎨 原创", original_count),
        ("🔧 魔改", modified_count),
        ("📦 原生", native_count)
    ]
    md.append(create_ascii_bar_chart(ownership_data, ""))
    md.append("\n")

    # 自定义评分
    md.append("### 🌟 自定义评分\n\n")
    md.append(f"| 指标 | 数值 |\n")
    md.append(f"|------|------|\n")
    md.append(f"| **总Skill数** | {len(skills)} 个 |\n")
    md.append(f"| **平均自定义度** | {avg_custom_score:.1f}% |\n")
    md.append(f"| **完全原创** | {original_count} 个 |\n")
    md.append(f"| **经过魔改** | {modified_count} 个 |\n")
    md.append(f"| **保持原生** | {native_count} 个 |\n")
    md.append("\n")

    # 评分等级
    md.append("**评分等级**: \n")
    if avg_custom_score >= 70:
        md.append("- 🏆 **大师级** (70%+) - 你是Skill创造大师！\n")
    elif avg_custom_score >= 40:
        md.append("- 🔥 **进阶级** (40%+) - 正在培养自己的Skill生态\n")
    elif avg_custom_score >= 20:
        md.append("- 🌱 **成长级** (20%+) - 开始尝试自定义\n")
    else:
        md.append("- 🌿 **新手级** (20%以下) - 大量使用原生Skills\n")
    md.append("\n---\n")

    # ============================================
    # 💡 创新价值排行榜
    # ============================================
    md.append("## 💡 创新价值排行榜\n\n")
    md.append("基于独特性、实用性、完整性、活跃度综合评分\n\n")

    # 排序
    sorted_innovation = sorted(
        zip(skills, innovation_scores),
        key=lambda x: x[1]['total'],
        reverse=True
    )

    md.append("| 排名 | Skill | 类别 | 创新评分 | 独特性 | 实用性 | 完整性 | 活跃度 |\n")
    md.append("|------|-------|------|----------|--------|--------|--------|--------|\n")

    for rank, (skill, innovation) in enumerate(sorted_innovation[:20], 1):
        name = skill['name']
        category = get_smart_category(skill, ownership_results[skills.index(skill)], health_data)
        total = innovation['total']
        grade = innovation['grade']
        scores = innovation['scores']

        md.append(f"| {rank} | **{name}** | {category} | **{total}** ({grade}) | "
                  f"{scores['uniqueness']:.0f} | {scores['utility']:.0f} | "
                  f"{scores['completeness']:.0f} | {scores['activity']:.0f} |\n")

    md.append("\n---\n")

    # ============================================
    # 📋 Skills 按所有权分类
    # ============================================
    md.append("## 📋 Skills 按所有权分类\n\n")

    # 按所有权分组
    by_ownership = {
        'Original': [],
        'Modified': [],
        'Native': []
    }

    for skill, ownership in zip(skills, ownership_results):
        category = get_smart_category(skill, ownership, health_data)
        innovation = innovation_scores[skills.index(skill)]

        by_ownership[ownership['label']].append({
            **skill,
            'ownership': ownership,
            'category': category,
            'innovation': innovation
        })

    # ============================================
    # 💪 创造力激励
    # ============================================
    md.append("### 💪 创造力激励\n\n")

    original_count = len(by_ownership['Original'])
    modified_count = len(by_ownership['Modified'])
    native_count = len(by_ownership['Native'])
    avg_score = sum(o['custom_percentage'] for o in ownership_results) / len(ownership_results) if ownership_results else 0

    if original_count > 0:
        if original_count >= 5:
            md.append(f"🌟 **太棒了！** 你已经创造了 **{original_count}** 个原创 Skills，展现了强大的创造力！\n\n")
        else:
            md.append(f"✨ **很好的开始！** 你已经迈出了创造的第一步（{original_count} 个原创）\n\n")
    else:
        md.append("🌱 **新手阶段** 还没有原创 Skills，不要担心，从魔改开始也是很好的学习方式！\n\n")

    if modified_count > 0:
        md.append(f"🔧 **魔改经验** 你已经魔改了 **{modified_count}** 个 Skills，正在逐步打造个性化工具集\n\n")

    if avg_score < 20:
        md.append("💡 **成长建议**: 尝试魔改一个常用的原生 Skill 以适应你的特定需求\n")
        md.append("   - 选择你常用的 Skill\n")
        md.append("   - 添加你觉得有用的功能\n")
        md.append("   - 记录在 `ownership_config.json` 中\n\n")

    md.append("---\n")

    # 原创Skills
    md.append("### 🎨 原创Skills\n")
    md.append("_完全由你创建的Skills，体现你的创造力和专业领域_\n\n")

    if by_ownership['Original']:
        md.append("| Skill | 类别 | 自定义度 | 创新评分 | 检测方式 |\n")
        md.append("|-------|------|----------|----------|----------|\n")

        for item in by_ownership['Original']:
            name = item['name']
            category = item['category']
            custom = item['ownership']['custom_percentage']
            innovation = item['innovation']['total']
            method = item['ownership']['detection_method']

            md.append(f"| **{name}** | {category} | {custom}% | {innovation} | {method} |\n")
    else:
        md.append("_还没有原创Skills，开始创造吧！_\n")

    md.append("\n")

    # 魔改Skills
    md.append("### 🔧 魔改Skills\n")
    md.append("_基于他人Skills修改，适配你的特定需求_\n\n")

    if by_ownership['Modified']:
        md.append("| Skill | 基于项目 | 修改内容 | 自定义度 | 创新评分 |\n")
        md.append("|-------|----------|----------|----------|----------|\n")

        for item in by_ownership['Modified']:
            name = item['name']
            ownership = item['ownership']
            based_on = ownership.get('based_on', ownership.get('detection_reasons', ['未知'])[0] if ownership.get('detection_reasons') else '未知')
            reasons = ownership.get('detection_reasons', ownership.get('modifications', []))
            custom = ownership['custom_percentage']
            innovation = item['innovation']['total']

            reasons_str = '; '.join(reasons[:2]) if reasons else '未知'
            if len(reasons) > 2:
                reasons_str += f' 等{len(reasons)}项'

            md.append(f"| **{name}** | {based_on} | {reasons_str} | {custom}% | {innovation} |\n")
    else:
        md.append("_还没有魔改Skills，选择一个常用的尝试改进吧！_\n")

    md.append("\n")

    # 原生Skills - 按类别分组展示
    md.append("### 📦 原生Skills\n")
    md.append("_从GitHub等来源直接安装，保持原版_\n\n")

    if by_ownership['Native']:
        # 按类别分组
        native_by_category = {}
        for item in by_ownership['Native']:
            category = item['category']
            if category not in native_by_category:
                native_by_category[category] = []
            native_by_category[category].append(item)

        # 按类别名称排序
        sorted_categories = sorted(native_by_category.keys())

        for category in sorted_categories:
            items = native_by_category[category]
            md.append(f"#### {category} ({len(items)}个)\n\n")

            # 只显示前 10 个，避免列表过长
            display_items = items[:10]
            md.append("| Skill | 创新评分 | 来源 | 建议 |\n")
            md.append("|-------|----------|------|------|\n")

            for item in display_items:
                name = item['name']
                innovation = item['innovation']['total']
                method = item['ownership']['detection_method']

                # 判断来源
                if 'anthropic' in method.lower() or 'anthropic' in name.lower():
                    source = "🏢 Anthropic"
                elif 'third_party' in method.lower() or 'genealogy_analysis' in method.lower():
                    source = "🔗 社区"
                else:
                    source = "📦 官方"

                # 根据评分给出建议
                if innovation >= 60:
                    suggestion = "💡 建议魔改"
                elif innovation >= 50:
                    suggestion = "🔧 可考虑魔改"
                else:
                    suggestion = "保持原生"

                md.append(f"| {name} | {innovation} | {source} | {suggestion} |\n")

            if len(items) > 10:
                remaining = len(items) - 10
                md.append(f"| _...还有 {remaining} 个_ | | | |\n")

            md.append("\n")
    else:
        md.append("_没有原生 Skills_\n")

    md.append("\n---\n")

    # ============================================
    # 🔧 精准魔改推荐（简化版）
    # ============================================
    md.append("## 🔧 精准魔改推荐\n\n")
    md.append("基于创新价值、使用活跃度、健康度分析生成的个性化推荐\n\n")

    if recommendations:
        md.append("| # | Skill | 类别 | 评分 | 优先级 | 改进方向 |\n")
        md.append("|---|-------|------|------|--------|----------|\n")

        for i, rec in enumerate(recommendations[:10], 1):
            name = rec['name']
            category = rec['category']
            score = rec['innovation_score']['total']
            priority = rec['priority_score']
            ideas = rec['ideas'][:2]  # 只取前2个建议

            ideas_str = '; '.join(ideas)
            md.append(f"| {i} | **{name}** | {category} | {score:.0f} | {priority:.0f} | {ideas_str} |\n")

        md.append(f"\n💡 提示：点击上方 Skill 查看详细改进建议和配置示例\n\n")
    else:
        md.append("_暂无推荐（所有Skills已配置或无合适的魔改目标）_\n\n")

    md.append("---\n")

    # ============================================
    # 🎯 技能组合推荐
    # ============================================
    md.append("## 🎯 技能组合推荐\n\n")
    md.append("发现可以协同工作的技能，构建高效工作流\n\n")

    skill_combinations = generate_skill_combinations(skills, ownership_results)

    if skill_combinations:
        for combo in skill_combinations:
            coverage_pct = int(combo['coverage'] * 100)
            md.append(f"### {combo['name']} ({coverage_pct}% 完成)\n\n")
            md.append(f"**描述**: {combo['description']}\n\n")
            md.append(f"**收益**: {combo['benefit']}\n\n")

            md.append("**已拥有技能**:\n")
            for skill in combo['owned_skills']:
                md.append(f"- ✅ {skill}\n")

            if combo['missing_skills']:
                md.append("\n**缺少技能**:\n")
                for skill in combo['missing_skills']:
                    md.append(f"- ❌ {skill}\n")

            md.append("\n")

        md.append(f"💡 提示：完善技能组合可以提升整体工作效率\n\n")
    else:
        md.append("_暂无技能组合推荐\n\n")

    md.append("---\n")

    # ============================================
    # 🏆 成就系统
    # ============================================
    md.append("## 🏆 成就系统\n\n")
    md.append("记录你的技能生态建设里程碑\n\n")

    achievements = generate_achievements(ownership_results, innovation_scores)

    # 已解锁成就
    if achievements['unlocked']:
        md.append("### ✨ 已解锁成就\n\n")

        # 按等级分组
        by_level = {'legendary': [], 'gold': [], 'silver': [], 'bronze': []}
        for ach in achievements['unlocked']:
            by_level[ach['level']].append(ach)

        for level in ['legendary', 'gold', 'silver', 'bronze']:
            if by_level[level]:
                level_emoji = {'legendary': '💎', 'gold': '🥇', 'silver': '🥈', 'bronze': '🥉'}
                md.append(f"**{level_emoji[level]} {level.capitalize()}**\n\n")
                for ach in by_level[level]:
                    md.append(f"- {ach['name']}: {ach['desc']}\n")
                md.append("\n")

    # 未解锁成就（下一步目标）
    if achievements['locked']:
        md.append("### 🎯 下一步目标\n\n")

        for ach in achievements['locked']:
            progress = ach.get('progress', '')
            md.append(f"- **{ach['name']}**: {ach['desc']}")
            if progress:
                md.append(f" ({progress})")
            md.append("\n")

        md.append("\n")

    md.append("---\n")

    # ============================================
    # 🔄 技能融合推荐
    # ============================================
    md.append("## 🔄 技能融合推荐\n\n")
    md.append("发现功能相似的技能，考虑整合以减少工具碎片化\n\n")

    skill_fusions = generate_skill_fusions(skills, ownership_results, innovation_scores)

    if skill_fusions:
        md.append("| 融合目标 | 来源技能 | 复杂度 | 原因 | 收益 |\n")
        md.append("|----------|----------|--------|------|------|\n")

        for fusion in skill_fusions:
            source_skills = ', '.join(fusion['source_skills'][:4])  # 最多显示4个
            if len(fusion['source_skills']) > 4:
                source_skills += f' 等{len(fusion["source_skills"])}个'

            md.append(f"| **{fusion['name']}** | {source_skills} | {fusion['complexity']} | {fusion['reason'][:20]} | {fusion['benefit'][:20]} |\n")

        md.append(f"\n💡 提示：技能融合可以简化工具链，提升工作效率\n\n")
    else:
        md.append("_暂无技能融合推荐（需要更多相关技能）\n\n")

    md.append("---\n")

    # ============================================
    # 💪 创新建议
    # ============================================
    md.append("## 💪 创新指导建议\n\n")

    tips = generate_innovation_tips(avg_custom_score, original_count, modified_count, native_count, innovation_scores)

    for tip in tips:
        priority_emoji = {'高': '🔴', '中': '🟡', '低': '🟢'}
        emoji = priority_emoji.get(tip['priority'], '⚪')

        md.append(f"### {emoji} {tip['title']}\n\n")
        md.append(f"{tip['description']}\n\n")
        md.append("**行动步骤**:\n")
        for action in tip['actions']:
            md.append(f"- {action}\n")
        md.append("\n")

    # ============================================
    # 📖 配置说明
    # ============================================
    md.append("## 📖 配置说明\n\n")

    md.append("### ⚙️ 所有权配置文件\n\n")
    md.append(f"虽然 v{version} 支持自动检测，但你仍然可以通过 `ownership_config.json` 手动配置：\n\n")
    md.append("```json\n")
    md.append("{\n")
    md.append('  "原创": [\n')
    md.append('    "my-awesome-skill",\n')
    md.append('    "another-custom-skill"\n')
    md.append('  ],\n')
    md.append('  "魔改": {\n')
    md.append('    "modified-skill-name": {\n')
    md.append('      "based_on": "original-author/original-skill",\n')
    md.append('      "modifications": [\n')
    md.append('        "添加了中文支持",\n')
    md.append('        "优化了输出格式"\n')
    md.append('      ],\n')
    md.append('      "custom_percentage": 30\n')
    md.append('    }\n')
    md.append('  }\n')
    md.append("}\n")
    md.append("```\n\n")

    md.append("---\n")
    md.append(f"\n*📅 报告生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    md.append("\n*💡 记住：最好的Skill是适合你的Skill！*")
    md.append(f"\n*🔧 v{version} 增强功能：自动检测、智能分析、精准推荐*")

    # 保存报告
    # 注意: reports_dir 和 date_str 已在函数开头定义
    filename = f'SKILLS_创新指导_v{version}_{date_str}.md'
    output_path = os.path.join(reports_dir, filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(md)

    # 同时生成默认名称
    default_path = os.path.join(reports_dir, 'SKILLS_创新指导_最新.md')
    with open(default_path, 'w', encoding='utf-8') as f:
        f.writelines(md)

    print(f"\n[OK] 创新指导报告已生成: {output_path}")
    print(f"\n[统计]")
    print(f"  原创: {original_count} 个")
    print(f"  魔改: {modified_count} 个")
    print(f"  原生: {native_count} 个")
    print(f"  自定义度: {avg_custom_score:.1f}%")

    # 保存数据供后续使用
    data_output = {
        'generated_at': datetime.now().isoformat(),
        'version': version,
        'stats': {
            'total': len(skills),
            'original': original_count,
            'modified': modified_count,
            'native': native_count,
            'avg_custom_percentage': avg_custom_score
        },
        'ownership_results': [
            {
                'name': s['name'],
                'type': o['type'],
                'custom_percentage': o.get('custom_percentage', 0),
                'detection_method': o.get('detection_method', 'unknown')
            }
            for s, o in zip(skills, ownership_results)
        ],
        'innovation_scores': [
            {
                'name': s['name'],
                'score': score['total'],
                'grade': score['grade']
            }
            for s, score in zip(skills, innovation_scores)
        ]
    }

    data_path = os.path.join(SCRIPT_DIR, 'skills_innovation_data.json')
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data_output, f, ensure_ascii=False, indent=2)
    print(f"[OK] 数据已保存: {data_path}")

    print(f"\n下一步:")
    print(f"  1. 查看创新指导报告")
    print(f"  2. 根据精准推荐进行魔改")
    print(f"  3. 记录修改到 ownership_config.json")

    return output_path


def main():
    """主执行函数（优化版 v2.1）"""
    parser = argparse.ArgumentParser(
        description='Skill-Innovation 创新指导工具 v2.1',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python skill_innovation.py              # 默认运行（使用缓存）
  python skill_innovation.py -v           # 详细输出模式
  python skill_innovation.py --no-cache   # 禁用缓存重新分析
  python skill_innovation.py --clear-cache  # 清空缓存后退出
        '''
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='详细输出模式（显示调试信息）'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='禁用缓存，强制重新分析'
    )
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='清空缓存后退出'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='Skill-Innovation v2.1 - 优化版'
    )

    args = parser.parse_args()

    # 设置日志
    global logger
    logger = setup_logging(args.verbose)

    # 处理清空缓存
    if args.clear_cache:
        clear_cache()
        return

    # 生成报告
    generate_innovation_report(
        verbose=args.verbose,
        no_cache=args.no_cache
    )


if __name__ == '__main__':
    main()
