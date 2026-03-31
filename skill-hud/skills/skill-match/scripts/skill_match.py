#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill-Match 数据收集核心脚本

功能：
1. 扫描本地技能目录，提取元数据
2. 关联GitHub仓库地址
3. 检查版本更新
4. 评估更新优先级
5. 提示用户补充缺失的GitHub地址
6. 生成skills溯源检查报告
"""

import os
import sys
import json
import re
import glob
import time
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

# ============================================
# 日志系统
# ============================================
import logging

logger = logging.getLogger(__name__)

# ============================================
# 配置
# ============================================
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
SKILLS_BASE_PATH = os.path.expanduser("~/.claude/skills")

# 性能优化配置
REQUEST_DELAY = 1.0  # API请求间隔（秒）
MAX_RETRIES = 3  # 最大重试次数
REQUEST_TIMEOUT = 10  # 请求超时（秒）

# 缓存配置
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache')
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
USER_GITHUB_MAP_PATH = os.path.join(CONFIG_DIR, 'user_github_map.json')
CATEGORY_RULES_PATH = os.path.join(CONFIG_DIR, 'category_rules.json')

# 创建必要目录
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

# 配置日志系统
log_file = os.path.join(LOG_DIR, f'skill_match_{datetime.now().strftime("%Y%m%d")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# 已知的GitHub地址映射
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

    @staticmethod
    def get_dir_size(path: str) -> float:
        """获取目录大小（带缓存）"""
        import hashlib
        cache_key = hashlib.md5(f"{path}_{os.path.getmtime(path)}".encode()).hexdigest()
        cache_file = os.path.join(CACHE_DIR, f"size_{cache_key}.json")

        # 检查缓存
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if time.time() - data.get('timestamp', 0) < 3600:  # 1小时有效期
                        return data.get('size', 0)
            except:
                pass

        # 计算大小
        size = CacheManager._calculate_dir_size(path)

        # 保存到缓存
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'size': size, 'timestamp': time.time()}, f)
        except:
            pass

        return size

    @staticmethod
    def _calculate_dir_size(path: str) -> float:
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

# 全局缓存实例
_cache = CacheManager()

# 用户自定义GitHub地址配置文件路径（保持兼容）
USER_GITHUB_MAP_PATH_OLD = os.path.join(os.path.dirname(__file__), 'user_github_map.json')


# ============================================
# 工具函数
# ============================================
def get_dir_size(path):
    """获取目录大小（MB）- 使用缓存优化"""
    return _cache.get_dir_size(path)

def load_category_rules():
    """加载自定义分类规则"""
    default_rules = {
        "开发工作流": ["code", "git", "debug", "test", "deploy", "commit", "review", "branch", "implementation", "verification"],
        "文档写作": ["writing", "article", "blog", "document", "prd", "prompt", "wechat", "content", "author"],
        "设计创意": ["design", "ui", "ux", "art", "image", "canvas", "ppt", "presentation"],
        "项目管理": ["plan", "task", "brainstorm", "requirement", "solution", "workflow"],
        "数据处理": ["json", "markdown", "obsidian", "base", "file"]
    }

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

# 全局分类规则（延迟加载）
_category_rules = None

def get_category_rules():
    """获取分类规则（懒加载）"""
    global _category_rules
    if _category_rules is None:
        _category_rules = load_category_rules()
    return _category_rules


def extract_github_url(content):
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


def extract_trigger_words(content):
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


def extract_description(content):
    """提取描述"""
    # 尝试匹配Description字段
    desc_match = re.search(r'Description:\s*(.+?)[\n\r]+(?:[\n\r]+|#)', content, re.IGNORECASE)
    if desc_match:
        return desc_match.group(1).strip()

    # 如果没有找到，获取前200个字符
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


def find_readme_with_github(skill_dir):
    """在skill目录或父目录中查找README并提取GitHub URL"""
    # 先检查当前目录
    readme_path = os.path.join(skill_dir, 'README.md')
    if os.path.exists(readme_path):
        try:
            with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                url = extract_github_url(content)
                if url:
                    return url
        except Exception:
            pass

    # 检查父目录
    parent_dir = os.path.dirname(skill_dir)
    if parent_dir and parent_dir != skill_dir:
        readme_path = os.path.join(parent_dir, 'README.md')
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    return extract_github_url(content)
            except Exception:
                pass

    return ""


def load_user_github_map():
    """加载用户自定义GitHub地址映射"""
    if os.path.exists(USER_GITHUB_MAP_PATH):
        try:
            with open(USER_GITHUB_MAP_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_github_repo_info(github_url):
    """获取GitHub仓库信息（带重试机制）"""
    if not github_url or 'github.com' not in github_url:
        return None

    # 提取owner/repo
    match = re.search(r'github\.com/([^/]+)/([^/]+?)(\.git)?$', github_url)
    if not match:
        return None

    owner = match.group(1)
    repo = match.group(2).replace('.git', '')

    # 重试机制
    for attempt in range(MAX_RETRIES):
        try:
            # 获取仓库信息
            headers = {'Accept': 'application/vnd.github.v3+json'}
            if GITHUB_TOKEN:
                headers['Authorization'] = f'token {GITHUB_TOKEN}'

            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = requests.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                repo_data = response.json()

                # 获取最新commit
                commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
                commits_response = requests.get(commits_url, headers=headers, timeout=REQUEST_TIMEOUT)

                latest_commit = None
                if commits_response.status_code == 200:
                    commits = commits_response.json()
                    if commits:
                        latest_commit = {
                            'sha': commits[0]['sha'][:7],
                            'date': commits[0]['commit']['committer']['date'],
                            'message': commits[0]['commit']['message'].split('\n')[0]
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
            elif response.status_code == 403:
                # API限流，等待后重试
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"GitHub API限流，等待60秒后重试...")
                    time.sleep(60)
                    continue
            else:
                return None

        except requests.Timeout:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{MAX_RETRIES})")
                time.sleep(2 ** attempt)  # 指数退避
                continue
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"请求异常 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
                time.sleep(2 ** attempt)
                continue

    logger.error(f"获取仓库信息失败 {github_url}")
    return None


def check_local_version(skill_path):
    """检查本地Skill的版本信息"""
    version_info = {
        'has_git': False,
        'branch': None,
        'commit': None,
        'commit_date': None,
        'dirty': False
    }

    import subprocess

    try:
        # 向上查找git仓库
        current_path = skill_path
        while current_path:
            git_dir = os.path.join(current_path, '.git')
            if os.path.exists(git_dir):
                version_info['has_git'] = True

                # 获取当前分支
                try:
                    result = subprocess.run(
                        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                        cwd=current_path,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        version_info['branch'] = result.stdout.strip()
                except:
                    pass

                # 获取当前commit
                try:
                    result = subprocess.run(
                        ['git', 'rev-parse', 'HEAD'],
                        cwd=current_path,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        version_info['commit'] = result.stdout.strip()[:7]
                except:
                    pass

                # 获取commit日期
                try:
                    result = subprocess.run(
                        ['git', 'log', '-1', '--format=%ci'],
                        cwd=current_path,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        version_info['commit_date'] = result.stdout.strip()
                except:
                    pass

                # 检查是否有未提交的更改
                try:
                    result = subprocess.run(
                        ['git', 'status', '--porcelain'],
                        cwd=current_path,
                        capture_output=True,
                        text=True,
                        timeout=5
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


def calculate_update_priority(github_info, local_version):
    """计算更新优先级"""
    update_available = False
    update_priority = "无"
    update_reason = []

    if github_info and local_version['has_git'] and github_info.get('latest_commit'):
        if local_version['commit'] != github_info['latest_commit']['sha']:
            update_available = True

            # 计算差异天数
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

    # 检查仓库是否已归档
    if github_info and github_info.get('archived'):
        update_reason.append("仓库已归档")

    return {
        'available': update_available,
        'priority': update_priority,
        'reason': update_reason
    }


# ============================================
# 主要功能
# ============================================
def collect_skills():
    """第一步：扫描并收集所有Skill信息"""
    print("=" * 60)
    print("步骤 1/4: 扫描本地Skills目录")
    print("=" * 60)

    all_skills = {}
    skill_files = []

    # 递归查找所有SKILL.md文件
    pattern = os.path.join(SKILLS_BASE_PATH, '**/SKILL.md')
    skill_files = glob.glob(pattern, recursive=True)

    print(f"找到 {len(skill_files)} 个SKILL.md文件\n")

    for skill_file_path in skill_files:
        # 提取skill名称
        path_parts = skill_file_path.replace('\\', '/').split('/')
        skill_name = ""

        # 查找包含skills目录的下一级目录
        for i, part in enumerate(path_parts):
            if part == 'skills' and i < len(path_parts) - 1:
                skill_name = path_parts[i + 1]
                break

        # 如果找不到，使用目录名
        if not skill_name:
            skill_name = os.path.basename(os.path.dirname(skill_file_path))

        # 跳过重复
        if skill_name in all_skills:
            continue

        # 读取SKILL.md内容
        try:
            with open(skill_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            content = ""

        # 获取目录信息
        skill_dir = os.path.dirname(skill_file_path)

        # 获取时间信息
        try:
            install_time = datetime.fromtimestamp(os.path.getctime(skill_dir)).isoformat()
            modified_time = datetime.fromtimestamp(os.path.getmtime(skill_dir)).isoformat()
        except Exception:
            install_time = ""
            modified_time = ""

        # 获取大小
        size_mb = get_dir_size(skill_dir)

        all_skills[skill_name] = {
            'name': skill_name,
            'path': skill_dir,
            'trigger_words': extract_trigger_words(content),
            'description': extract_description(content),
            'size_mb': size_mb,
            'install_date': install_time,
            'last_modified': modified_time,
            'github_url': "",
            'has_trigger_words': bool(extract_trigger_words(content))
        }

    # 转换为列表并排序
    skills_list = sorted(all_skills.values(), key=lambda x: x['name'].lower())

    print(f"成功收集 {len(skills_list)} 个独立的Skill\n")
    return skills_list


def fetch_github_urls(skills):
    """第二步：获取GitHub地址"""
    print("=" * 60)
    print("步骤 2/4: 关联GitHub仓库地址")
    print("=" * 60)

    # 加载用户自定义映射
    user_map = load_user_github_map()

    updated_count = 0
    skills_without_github = []

    for skill in skills:
        skill_name = skill['name']
        github_url = skill.get('github_url', '')

        # 如果已经有GitHub URL，跳过
        if github_url and not github_url.startswith('https://github.com/user-attachments'):
            continue

        # 优先级：用户自定义 > README提取 > 已知映射
        new_url = None

        # 1. 检查用户自定义映射
        if skill_name in user_map:
            new_url = user_map[skill_name]
        # 2. 从README提取
        else:
            readme_url = find_readme_with_github(skill['path'])
            if readme_url:
                new_url = readme_url
            # 3. 使用已知映射
            elif skill_name in KNOWN_GITHUB_MAP:
                new_url = KNOWN_GITHUB_MAP[skill_name]

        if new_url:
            skill['github_url'] = new_url
            updated_count += 1
            print(f"  [+] {skill_name}: {new_url}")
        else:
            skills_without_github.append(skill)

    print(f"\n成功关联 {updated_count} 个Skills的GitHub地址")
    print(f"仍有 {len(skills_without_github)} 个Skills没有GitHub地址\n")

    return skills, skills_without_github


def check_version_updates(skills):
    """第三步：检查版本更新"""
    print("=" * 60)
    print("步骤 3/4: 检查版本更新")
    print("=" * 60)

    results = []

    for i, skill in enumerate(skills, 1):
        name = skill['name']
        github_url = skill.get('github_url', '')
        skill_path = skill.get('path', '')

        print(f"[{i}/{len(skills)}] {name}...", end=' ')

        # 获取GitHub信息
        github_info = None
        if github_url and 'github.com' in github_url:
            github_info = get_github_repo_info(github_url)

        # 检查本地版本
        local_version = check_local_version(skill_path)

        # 计算更新优先级
        update_info = calculate_update_priority(github_info, local_version)

        results.append({
            'name': name,
            'github_url': github_url,
            'github_info': github_info,
            'local_version': local_version,
            'update_info': update_info
        })

        # 输出简短状态
        if update_info['available']:
            print(f"可更新 ({update_info['priority']}优先级)")
        elif github_info:
            print(f"已是最新")
        else:
            print(f"无GitHub地址")

    print()
    return results


def search_github_for_skill(skill_name):
    """在GitHub上搜索Skill仓库"""
    try:
        headers = {'Accept': 'application/vnd.github.v3+json'}
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'

        # 使用skill名称作为搜索关键词
        query = quote(f'{skill_name} language:python OR language:typescript OR language:javascript in:name,description,readme')
        search_url = f'https://api.github.com/search/repositories?q={query}&per_page=5&sort=stars&order=desc'

        response = requests.get(search_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('items'):
                return data['items']
    except Exception as e:
        print(f"  [搜索错误] {skill_name}: {e}")

    return []


def prompt_missing_github(skills, skills_without_github):
    """第四步：提示用户补充缺失的GitHub地址"""
    if not skills_without_github:
        print("\n所有Skills都已有GitHub地址！")
        return {}

    print("=" * 60)
    print("步骤 4/4: 补充缺失的GitHub地址")
    print("=" * 60)
    print(f"\n以下 {len(skills_without_github)} 个Skills没有GitHub地址：\n")

    print("+- 已知GitHub映射 --------------------------------------+")
    print("| 你可以编辑以下文件来添加自定义GitHub地址映射:        |")
    print(f"| {USER_GITHUB_MAP_PATH}                           |")
    print("|                                                      |")
    print("| 格式示例:                                            |")
    print("| {                                                  |")
    print('|   "my-skill": "https://github.com/user/my-skill"    |')
    print("| }                                                  |")
    print("+-----------------------------------------------------+\n")

    print("缺少GitHub地址的Skills:")
    print("-" * 60)

    for skill in skills_without_github:
        print(f"  * {skill['name']}")
        print(f"    描述: {skill['description'][:60]}...")
        print(f"    路径: {skill['path']}")
        print()

    print("-" * 60)

    # 询问是否要在GitHub上搜索
    print("\n" + "=" * 60)
    print("🔍 是否在GitHub上搜索这些Skills的仓库地址？")
    print("=" * 60)
    print("  [Y] 是 - 自动搜索并补充地址")
    print("  [N] 否 - 跳过，手动添加")
    print("=" * 60)

    try:
        # 检测是否为自动模式（非终端输入）
        if not sys.stdin.isatty():
            choice = 'N'  # 自动模式：跳过
            print("\n[自动模式] 已跳过GitHub搜索")
        else:
            choice = input("\n请选择 (Y/N，默认N): ").strip().upper()
        if choice == 'Y' or choice == 'YES':
            print("\n开始在GitHub上搜索...")
            print("-" * 60)

            # 加载或创建用户映射
            user_map = load_user_github_map()

            for skill in skills_without_github:
                skill_name = skill['name']
                print(f"\n搜索: {skill_name}...")

                results = search_github_for_skill(skill_name)

                if results:
                    print(f"  找到 {len(results)} 个可能的结果:")
                    for i, repo in enumerate(results[:3], 1):
                        print(f"    [{i}] {repo['full_name']}")
                        print(f"        ⭐ {repo['stargazers_count']} stars")
                        print(f"        📝 {repo.get('description', 'No description')[:60]}...")
                        print(f"        🔗 {repo['html_url']}")

                    # 选择第一个（star最多）
                    selected = results[0]
                    url = selected['html_url']
                    user_map[skill_name] = url

                    # 更新skill数据
                    skill['github_url'] = url
                    print(f"  ✅ 已自动选择: {url}")
                else:
                    print(f"  ❌ 未找到匹配的仓库")

            # 保存更新后的映射
            if user_map:
                with open(USER_GITHUB_MAP_PATH, 'w', encoding='utf-8') as f:
                    json.dump(user_map, f, ensure_ascii=False, indent=2)
                print(f"\n[OK] 已更新 {USER_GITHUB_MAP_PATH}")

                # 统计更新数量
                updated_count = len([s for s in skills_without_github if s.get('github_url')])
                print(f"[OK] 成功补充 {updated_count} 个Skills的GitHub地址")

                # 返回更新后的列表
                skills_without_github = [s for s in skills_without_github if not s.get('github_url')]
            else:
                print("\n[INFO] 没有找到可匹配的仓库")
        else:
            print("\n已跳过自动搜索")
    except (EOFError, KeyboardInterrupt):
        print("\n\n已取消")
    except Exception as e:
        print(f"\n[错误] {e}")

    print("\n提示: 你可以")
    print("  1. 手动编辑 user_github_map.json 添加地址")
    print("  2. 在Skill的README.md中添加GitHub链接")
    print("  3. 重新运行本脚本以更新")

    # 生成模板配置文件（只针对仍然缺失的）
    template = {}
    for skill in skills_without_github:
        if not skill.get('github_url'):
            template[skill['name']] = "https://github.com/YOUR_USERNAME/YOUR_REPO"

    if template:
        template_path = os.path.join(os.path.dirname(__file__), 'user_github_map.template.json')
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

        print(f"\n已生成模板文件: {template_path}")
        print("你可以编辑此文件并重命名为 user_github_map.json\n")

    return template


def save_results(skills, version_results):
    """保存结果到JSON文件"""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 保存基础Skills数据
    skills_data_path = os.path.join(script_dir, 'skills_data.json')
    with open(skills_data_path, 'w', encoding='utf-8') as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)
    print(f"[OK] 基础数据已保存: {skills_data_path}")

    # 保存版本更新数据
    update_data_path = os.path.join(script_dir, 'skills_version_check.json')
    with open(update_data_path, 'w', encoding='utf-8') as f:
        json.dump(version_results, f, ensure_ascii=False, indent=2)
    print(f"[OK] 版本数据已保存: {update_data_path}")

    # 统计信息
    total = len(skills)
    with_github = sum(1 for s in skills if s.get('github_url'))
    updates_available = sum(1 for r in version_results if r['update_info']['available'])
    high_priority = sum(1 for r in version_results if r['update_info']['priority'] == '高')
    medium_priority = sum(1 for r in version_results if r['update_info']['priority'] == '中')

    print("\n" + "=" * 60)
    print("数据收集完成！统计信息:")
    print("=" * 60)
    print(f"  总Skill数:     {total}")
    print(f"  有GitHub地址:  {with_github} ({with_github/total*100:.1f}%)")
    print(f"  可更新版本:    {updates_available}")
    print(f"    - 高优先级:  {high_priority}")
    print(f"    - 中优先级:  {medium_priority}")
    print("=" * 60)


def generate_report(skills, version_results, skills_without_github):
    """生成skills溯源检查报告"""
    # 报告输出到 skill-match/reports/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(script_dir, '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    # 版本和日期
    version = "2.0.0"
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    # 报告文件名（必须包含版本号和日期）
    report_filename = f"skills溯源检查报告_v{version}_{today}.md"
    report_latest_filename = f"skills溯源检查报告_v{version}_{today}_最新.md"
    report_path = os.path.join(reports_dir, report_filename)
    report_latest_path = os.path.join(reports_dir, report_latest_filename)

    # 统计数据
    total = len(skills)
    total_size = sum(s['size_mb'] for s in skills)
    with_github = sum(1 for s in skills if s.get('github_url'))
    updates_available = sum(1 for r in version_results if r['update_info']['available'])
    high_priority = sum(1 for r in version_results if r['update_info']['priority'] == '高')
    medium_priority = sum(1 for r in version_results if r['update_info']['priority'] == '中')

    # 工具函数
    def format_size(mb):
        if mb < 0.01:
            return "很小"
        elif mb < 1:
            return f"{mb*1024:.0f}KB"
        elif mb < 1024:
            return f"{mb:.1f}MB"
        else:
            return f"{mb/1024:.1f}GB"

    def format_age(iso_date):
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

    def get_category_from_description(description):
        """根据描述获取分类（使用可配置规则）"""
        desc_lower = description.lower() if description else ""
        categories = get_category_rules()
        for category, keywords in categories.items():
            if any(keyword in desc_lower for keyword in keywords):
                return category
        return "其他"

    def get_source_from_github(url):
        if not url:
            return "❓ 未知"
        if "anthropics/anthropic-skills" in url:
            return "🏢 Anthropic官方"
        elif "cursor-shadowsong" in url:
            return "👤 cursor-shadowsong"
        elif "wechat-skills" in url:
            return "📱 微信生态"
        elif "obsidian-skills" in url:
            return "📝 Obsidian社区"
        elif "microsoft/markitdown" in url:
            return "🔗 Microsoft"
        else:
            return "🔗 社区贡献"

    # 生成报告内容
    md = []
    md.append("# 🎯 Skills 溯源检查报告\n")
    md.append(f"> 📅 **更新时间**: {today} {time_str}\n")
    md.append("---\n\n")

    # 核心指标（更丰富的表格）
    md.append("## 📊 核心指标\n\n")
    md.append("| 🎯 指标 | 📈 数值 | 📝 说明 |\n")
    md.append("|--------|--------|--------|\n")
    md.append(f"| **总Skill数** | **{total}** 个 | 全部已安装的技能 |\n")
    md.append(f"| **总占用空间** | **{format_size(total_size)}** | 磁盘占用 |\n")
    md.append(f"| **GitHub来源** | **{with_github}** 个 ({with_github/total*100:.0f}%) | 有明确来源 |\n")
    md.append(f"| **可更新版本** | **{updates_available}** 个 | 有新版本可用 |\n")
    md.append(f"|   - 高优先级 | {high_priority} 个 | 建议立即更新 |\n")
    md.append(f"|   - 中优先级 | {medium_priority} 个 | 可选更新 |\n")

    # 计算最新安装时间
    latest_install = max((s['install_date'] for s in skills if s['install_date']), default=None)
    if latest_install:
        md.append(f"| **最新安装** | **{format_age(latest_install)}** | 最近一次更新 |\n")
    md.append("\n---\n\n")

    # 可视化分析
    md.append("## 📈 可视化分析\n\n")

    # 类别分布
    categories = {}
    for skill in skills:
        cat = get_category_from_description(skill['description'])
        categories[cat] = categories.get(cat, 0) + 1

    cat_emoji = {"开发工作流": "⚙️", "文档写作": "✍️", "设计创意": "🎨", "项目管理": "📊", "数据处理": "🔧", "其他": "📦"}

    md.append("### 📂 Skill类别分布\n\n")
    max_cat = max(categories.values()) if categories else 1
    bar_width = 40

    for cat in sorted(categories.keys(), key=lambda x: categories[x], reverse=True):
        count = categories[cat]
        pct = count / total * 100
        emoji = cat_emoji.get(cat, "📌")
        filled = int((count / max_cat) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        md.append(f"{emoji} {cat:12} │{bar}│ {pct:.1f}% ({count}个)\n")

    md.append("\n")

    # 空间占用TOP10
    md.append("### 💾 空间占用 TOP 10\n\n")
    top_size = sorted(skills, key=lambda x: x['size_mb'], reverse=True)[:10]
    max_size = top_size[0]['size_mb'] if top_size else 1

    for i, skill in enumerate(top_size, 1):
        name = skill['name'][:15]
        size = skill['size_mb']
        bar_length = int((size / max_size) * bar_width)
        bar = "█" * bar_length + "░" * (bar_width - bar_length)
        md.append(f"{name:15} │{bar}│ {format_size(size)}\n")

    md.append("\n")

    # 来源分布
    sources = {}
    for skill in skills:
        source = get_source_from_github(skill.get('github_url', ''))
        sources[source] = sources.get(source, 0) + 1

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
    sorted_by_install = sorted(skills, key=lambda x: x['install_date'] or '', reverse=True)[:10]

    for i, skill in enumerate(sorted_by_install, 1):
        cat = get_category_from_description(skill['description'])
        emoji = cat_emoji.get(cat, "📌")
        age = format_age(skill['install_date'])
        md.append(f"{i:2}. {emoji} **{skill['name']}** - `{age}`\n")

    md.append("\n---\n\n")

    # 缺少GitHub地址的Skills
    if skills_without_github:
        md.append("## ⚠️ 缺少 GitHub 地址的 Skills\n\n")
        md.append(f"以下 {len(skills_without_github)} 个 Skills 没有 GitHub 地址：\n\n")
        for skill in skills_without_github:
            md.append(f"- **{skill['name']}**\n")
            md.append(f"  - 描述: {skill['description'][:80]}...\n")
            md.append(f"  - 路径: `{skill['path']}`\n")
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

    # Skill清单（按类别分组）
    md.append("## 📋 Skill清单\n\n")

    by_category = {}
    for skill in skills:
        cat = get_category_from_description(skill['description'])
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(skill)

    for category in sorted(by_category.keys()):
        cat_skills = sorted(by_category[category], key=lambda x: x['name'].lower())
        emoji = cat_emoji.get(category, "📌")

        md.append(f"\n### {emoji} {category} ({len(cat_skills)}个)\n\n")
        md.append("| Skill名称 | 大小 | 来源 | 安装时间 |\n")
        md.append("|-----------|------|------|----------|\n")

        for skill in cat_skills:
            name = skill['name']
            size = format_size(skill['size_mb'])
            source = get_source_from_github(skill.get('github_url', ''))
            age = format_age(skill['install_date'])

            # 如果有GitHub链接，添加可点击链接
            if skill.get('github_url') and skill['github_url'] not in ["https://github.com/user-attachments/assets", "https://github.com/anthropics/anthropic-skills"]:
                name = f"[{name}]({skill['github_url']})"

            md.append(f"| **{name}** | {size} | {source} | {age} |\n")

    md.append("\n---\n\n")

    # 使用说明
    md.append("## 💡 如何补充 GitHub 地址\n\n")
    md.append("### 方法1: 编辑配置文件\n\n")
    md.append(f"编辑 `user_github_map.json` 文件：\n\n")
    md.append("```json\n")
    md.append("{\n")
    md.append('  "your-skill-name": "https://github.com/username/repo"\n')
    md.append("}\n")
    md.append("```\n\n")
    md.append("### 方法2: 在 README.md 中添加\n\n")
    md.append("在 Skill 的 README.md 中添加 GitHub 链接，脚本会自动提取。\n\n")

    md.append("---\n\n")
    md.append(f"*📅 报告生成: {today} {time_str}:00* | **Skill-Match v{version}**\n")

    # 保存报告
    report_content = ''.join(md)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    with open(report_latest_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"[OK] 报告已生成: {report_path}")
    return report_path


# ============================================
# 主函数
# ============================================
def main():
    """主执行函数"""
    print("\n" + "=" * 60)
    print("       Skill-Match 数据收集工具")
    print("       优化版 v2.0 | " + datetime.now().strftime("%Y-%m-%d"))
    print("=" * 60)
    print("       优化：缓存 | 重试 | 日志 | 可配置分类规则")
    print("=" * 60 + "\n")

    # 执行四步流程
    skills = collect_skills()
    skills, skills_without_github = fetch_github_urls(skills)
    version_results = check_version_updates(skills)
    prompt_missing_github(skills, skills_without_github)

    # 保存结果
    save_results(skills, version_results)

    # 生成报告
    print("\n生成溯源检查报告...")
    generate_report(skills, version_results, skills_without_github)

    print("\n数据收集完成！")
    print("\n下一步:")
    print("  1. 如需补充GitHub地址，请编辑 user_github_map.json")
    print("  2. 运行其他子技能处理收集的数据")


if __name__ == '__main__':
    main()
