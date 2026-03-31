#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill-Health 技能健康度评估工具

功能：
1. 生成驾驶舱报告（图表、空间、占比、应用周期）
2. 扫描评估每个Skill的健康度
3. 验证Skill规范合规性
4. 提供自动重构清理功能
"""

import os
import sys
import json
import re
import glob
import shutil
from datetime import datetime
from collections import Counter
from pathlib import Path

# 设置 Windows 控制台 UTF-8 输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ============================================
# 配置
# ============================================
SKILL_FILE_MAX_LINES = 500  # SKILL.md 最大行数
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_BASE_PATH = os.path.expanduser("~/.claude/skills")

# ============================================
# 工具函数
# ============================================
def format_size(mb):
    """格式化大小显示"""
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


def get_emoji_for_category(category):
    """获取类别对应的emoji"""
    emoji_map = {
        "开发工作流": "⚙️",
        "文档写作": "✍️",
        "设计创意": "🎨",
        "项目管理": "📊",
        "数据处理": "🔧",
        "其他": "📦"
    }
    return emoji_map.get(category, "📌")


def extract_category_from_frontmatter(skill_path):
    """从 SKILL.md 的 frontmatter 中提取 category 字段"""
    skill_file = os.path.join(skill_path, 'SKILL.md')
    if not os.path.exists(skill_file):
        return None

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 查找 frontmatter 中的 category 字段
        # 支持: category: 和 category: 两种格式
        category_pattern = r'^category:\s*[\'"]?([^\'"\n]+)[\'"]?'
        match = re.search(category_pattern, content, re.MULTILINE)
        if match:
            return match.group(1).strip()
    except Exception:
        pass

    return None


def get_category_from_description(description, skill_path=None):
    """
    获取 Skill 类别
    优先级: frontmatter category > 关键词推断
    """
    # 1. 首先尝试从 frontmatter 读取
    if skill_path:
        frontmatter_category = extract_category_from_frontmatter(skill_path)
        if frontmatter_category:
            return frontmatter_category

    # 2. 使用关键词推断作为后备
    desc_lower = description.lower() if description else ""

    categories = {
        "开发工作流": ["code", "git", "debug", "test", "deploy", "commit", "review", "branch", "implementation", "verification"],
        "文档写作": ["writing", "article", "blog", "document", "prd", "prompt", "wechat", "content", "author", "思维"],
        "设计创意": ["design", "ui", "ux", "art", "image", "canvas", "ppt", "presentation"],
        "项目管理": ["plan", "task", "brainstorm", "requirement", "solution", "workflow", "需求"],
        "数据处理": ["json", "markdown", "obsidian", "base", "file"]
    }

    for category, keywords in categories.items():
        if any(keyword in desc_lower for keyword in keywords):
            return category

    return "其他"


def get_source_from_github(url):
    """根据GitHub地址判断来源"""
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
    elif "obra/superpowers" in url:
        return "🦸 superpowers"
    elif "ModelScope" in url:
        return "🎨 ModelScope"
    else:
        return "🔗 社区贡献"


def create_ascii_bar_chart(data, title, width=50):
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

        bar_length = int((value / max_val) * width)
        bar = "█" * bar_length + "░" * (width - bar_length)
        total = sum(item[1] for item in data)
        percentage = (value / total) * 100 if total > 0 else 0

        info = f" {extra}" if extra else ""
        lines.append(f"{label:15} │{bar}│ {value}{info}")

    return "\n".join(lines) + "\n"


def create_ascii_pie(data, title):
    """创建ASCII饼图（简化版）"""
    if not data:
        return f"\n### {title}\n暂无数据\n"

    total = sum(item[1] for item in data)
    lines = [f"\n### {title}\n"]

    for label, value in data:
        percentage = (value / total) * 100
        bar = "●" * int(percentage / 5) + "○" * (20 - int(percentage / 5))
        lines.append(f"{label:12} │{bar}│ {percentage:.1f}% ({value}个)")

    return "\n".join(lines) + "\n"


# ============================================
# 健康度检查函数
# ============================================
def check_skill_file_length(skill_path, skill_name):
    """检查SKILL.md文件长度"""
    skill_file = os.path.join(skill_path, 'SKILL.md')

    if not os.path.exists(skill_file):
        return {
            'status': 'error',
            'issue': 'SKILL.md文件不存在',
            'line_count': 0,
            'exceeds_limit': False
        }

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            line_count = len(lines)

        exceeds_limit = line_count > SKILL_FILE_MAX_LINES

        return {
            'status': 'ok' if not exceeds_limit else 'warning',
            'issue': None if not exceeds_limit else f'文件过长({line_count}行，超过{SKILL_FILE_MAX_LINES}行限制)',
            'line_count': line_count,
            'exceeds_limit': exceeds_limit
        }
    except Exception as e:
        return {
            'status': 'error',
            'issue': f'读取文件失败: {str(e)}',
            'line_count': 0,
            'exceeds_limit': False
        }


def check_skill_directory_structure(skill_path, skill_name):
    """检查Skill目录结构是否符合规范"""
    issues = []

    # 必需文件
    required_files = ['SKILL.md']
    for file in required_files:
        file_path = os.path.join(skill_path, file)
        if not os.path.exists(file_path):
            issues.append(f'缺少必需文件: {file}')

    # 推荐文件
    recommended_files = ['README.md']
    missing_recommended = []
    for file in recommended_files:
        file_path = os.path.join(skill_path, file)
        if not os.path.exists(file_path):
            missing_recommended.append(file)

    # 检查scripts目录
    scripts_dir = os.path.join(skill_path, 'scripts')
    has_scripts = os.path.exists(scripts_dir)

    # 检查references目录
    refs_dir = os.path.join(skill_path, 'references')
    has_refs = os.path.exists(refs_dir)

    # 检查是否有不必要的文件
    unnecessary_files = []
    unnecessary_patterns = ['.pyc', '__pycache__', '.DS_Store', 'Thumbs.db']
    for root, dirs, files in os.walk(skill_path):
        for file in files:
            for pattern in unnecessary_patterns:
                if pattern in file:
                    unnecessary_files.append(os.path.join(root, file))

    return {
        'status': 'ok' if not issues else 'warning',
        'issues': issues,
        'missing_recommended': missing_recommended,
        'has_scripts': has_scripts,
        'has_references': has_refs,
        'unnecessary_files': unnecessary_files
    }


def check_skill_metadata_consistency(skill_path, skill_name):
    """检查SKILL.md中的元数据一致性"""
    skill_file = os.path.join(skill_path, 'SKILL.md')

    if not os.path.exists(skill_file):
        return {'status': 'error', 'issues': ['SKILL.md文件不存在']}

    issues = []
    warnings = []

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查必需的frontmatter字段
        required_fields = ['name:', 'description:', 'version:']
        missing_fields = []
        for field in required_fields:
            if field not in content:
                missing_fields.append(field)

        if missing_fields:
            issues.append(f'缺少frontmatter字段: {", ".join(missing_fields)}')

        # 检查触发词
        has_trigger = 'trigger:' in content.lower() or '触发' in content or 'when to use' in content.lower()
        if not has_trigger:
            warnings.append('没有明确的触发词说明')

        # 检查使用场景
        has_use_case = 'use case' in content.lower() or '使用场景' in content or 'when to use' in content.lower()
        if not has_use_case:
            warnings.append('缺少使用场景说明')

        # 检查是否有说明部分
        has_description_section = '##' in content or '说明' in content or 'Description' in content
        if not has_description_section:
            warnings.append('缺少详细说明部分')

    except Exception as e:
        issues.append(f'解析文件失败: {str(e)}')

    return {
        'status': 'error' if issues else ('warning' if warnings else 'ok'),
        'issues': issues,
        'warnings': warnings
    }


def check_skill_triggers_completeness(skill_path, skill_name):
    """检查触发词完整性 - 第一阶段核心检查"""
    skill_file = os.path.join(skill_path, 'SKILL.md')

    if not os.path.exists(skill_file):
        return {'status': 'error', 'issues': ['SKILL.md文件不存在'], 'has_triggers': False}

    issues = []
    warnings = []

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查 frontmatter 中的 triggers 字段
        has_triggers_field = 'triggers:' in content or 'trigger:' in content

        # 提取 frontmatter 中的 triggers
        triggers_list = []
        if has_triggers_field:
            # 匹配 triggers: 或 trigger: 后面的数组
            trigger_pattern = r'(?:triggers|trigger):\s*\[(.*?)\]'
            match = re.search(trigger_pattern, content, re.DOTALL)
            if match:
                triggers_content = match.group(1)
                # 提取引号中的触发词
                trigger_items = re.findall(r'["\']([^"\']+)["\']', triggers_content)
                triggers_list = [t.strip() for t in trigger_items if t.strip()]

        # 检查是否有有效的触发词
        if not triggers_list:
            if has_triggers_field:
                warnings.append('triggers 字段存在但格式不正确或为空')
            else:
                issues.append('缺少 triggers 字段')

        # 检查触发词数量（建议至少2个）
        if len(triggers_list) < 2:
            warnings.append(f'触发词数量不足（当前{len(triggers_list)}个，建议至少2个）')

        return {
            'status': 'error' if issues else ('warning' if warnings else 'ok'),
            'issues': issues,
            'warnings': warnings,
            'has_triggers': has_triggers_field,
            'triggers_count': len(triggers_list),
            'triggers_list': triggers_list
        }
    except Exception as e:
        return {'status': 'error', 'issues': [f'解析失败: {str(e)}'], 'has_triggers': False, 'triggers_count': 0, 'triggers_list': []}


def check_version_compliance(skill_path, skill_name):
    """检查版本号是否符合语义化版本规范 - 第一阶段核心检查"""
    skill_file = os.path.join(skill_path, 'SKILL.md')

    if not os.path.exists(skill_file):
        return {'status': 'error', 'issues': ['SKILL.md文件不存在'], 'is_compliant': False}

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取 version 字段
        version_pattern = r'^version:\s*["\']?(\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?)["\']?'
        match = re.search(version_pattern, content, re.MULTILINE)

        if not match:
            return {'status': 'error', 'issues': ['未找到符合语义化版本的 version 字段'], 'is_compliant': False, 'version': None}

        version = match.group(1)

        return {
            'status': 'ok',
            'issues': [],
            'is_compliant': True,
            'version': version
        }
    except Exception as e:
        return {'status': 'error', 'issues': [f'解析失败: {str(e)}'], 'is_compliant': False, 'version': None}


def check_skill_examples(skill_path):
    """检查是否包含使用示例 - 第二阶段质量检查"""
    skill_file = os.path.join(skill_path, 'SKILL.md')

    if not os.path.exists(skill_file):
        return {'status': 'error', 'has_examples': False, 'example_count': 0}

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查 markdown 代码块（使用示例通常在代码块中）
        code_blocks = re.findall(r'```[\w]*\n.*?```', content, re.DOTALL)
        example_count = len(code_blocks)

        # 检查是否有"示例"、"example"等关键词
        has_example_keywords = re.search(r'(?:示例|example|Example|EXAMPLE)', content, re.IGNORECASE)

        if example_count > 0:
            return {
                'status': 'ok',
                'has_examples': True,
                'example_count': example_count,
                'has_example_keywords': bool(has_example_keywords)
            }
        elif has_example_keywords:
            return {
                'status': 'warning',
                'has_examples': False,
                'example_count': 0,
                'warnings': ['提到了示例但没有代码块']
            }
        else:
            return {
                'status': 'warning',
                'has_examples': False,
                'example_count': 0,
                'warnings': ['缺少使用示例']
            }
    except Exception as e:
        return {'status': 'error', 'has_examples': False, 'example_count': 0, 'issues': [f'检查失败: {str(e)}']}


def check_python_scripts_standard(skill_path):
    """检查 Python 脚本规范性 - 第二阶段质量检查"""
    scripts_dir = os.path.join(skill_path, 'scripts')

    if not os.path.exists(scripts_dir):
        return {'status': 'ok', 'has_scripts': False, 'scripts_checked': 0, 'issues': [], 'warnings': []}

    issues = []
    warnings = []
    scripts_checked = 0
    scripts_with_main = 0
    scripts_with_docstring = 0
    scripts_with_shebang = 0

    for root, dirs, files in os.walk(scripts_dir):
        for file in files:
            if file.endswith('.py'):
                scripts_checked += 1
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')

                    # 检查是否有 if __name__ == '__main__'
                    if "__name__" in content and '__main__' in content:
                        scripts_with_main += 1
                    else:
                        warnings.append(f'{file}: 缺少 if __name__ == "__main__"')

                    # 检查是否有模块级 docstring
                    has_docstring = False
                    if lines:
                        first_line = lines[0].strip() if lines else ''
                        second_line = lines[1].strip() if len(lines) > 1 else ''
                        if first_line.startswith('"""') or first_line.startswith("'''"):
                            has_docstring = True
                        elif second_line.startswith('"""') or second_line.startswith("'''"):
                            has_docstring = True

                    if has_docstring:
                        scripts_with_docstring += 1
                    else:
                        warnings.append(f'{file}: 缺少模块级 docstring')

                    # 检查是否有 shebang
                    if lines and lines[0].startswith('#!'):
                        scripts_with_shebang += 1
                    elif file.endswith('.py') and not any(line.startswith('#!') for line in lines[:3]):
                        warnings.append(f'{file}: 缺少 shebang (#!/usr/bin/env python3)')

                except Exception as e:
                    issues.append(f'{file}: 检查失败 - {str(e)}')

    return {
        'status': 'error' if issues else ('warning' if warnings else 'ok'),
        'has_scripts': scripts_checked > 0,
        'scripts_checked': scripts_checked,
        'scripts_with_main': scripts_with_main,
        'scripts_with_docstring': scripts_with_docstring,
        'scripts_with_shebang': scripts_with_shebang,
        'issues': issues,
        'warnings': warnings
    }


def check_mcp_dependencies(skill_path):
    """检查 MCP 依赖 - 第一阶段核心检查"""
    skill_file = os.path.join(skill_path, 'SKILL.md')

    if not os.path.exists(skill_file):
        return {'status': 'error', 'has_mcp_deps': False, 'issues': ['SKILL.md文件不存在']}

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否有 MCP 相关声明
        mcp_patterns = [
            r'mcp\s*:',
            r'requires\s*:\s*\[.*?mcp',
            r'dependencies?\s*:',
            r'uses?\s*:\s*\[.*?mcp'
        ]

        has_mcp_mention = any(re.search(pattern, content, re.IGNORECASE | re.DOTALL) for pattern in mcp_patterns)

        if not has_mcp_mention:
            return {
                'status': 'ok',
                'has_mcp_deps': False,
                'mcp_servers': [],
                'notes': '无 MCP 依赖'
            }

        # 尝试提取 MCP server 名称
        mcp_servers = []
        mcp_server_pattern = r'["\']([a-zA-Z0-9_-]+)["\'].*?mcp'
        matches = re.findall(mcp_server_pattern, content, re.IGNORECASE)
        mcp_servers = list(set(matches))  # 去重

        return {
            'status': 'ok',
            'has_mcp_deps': True,
            'mcp_servers': mcp_servers,
            'notes': f'发现 {len(mcp_servers)} 个 MCP server 引用'
        }
    except Exception as e:
        return {'status': 'error', 'has_mcp_deps': False, 'issues': [f'检查失败: {str(e)}']}


def check_security_issues(skill_path, enable_deep_check=False):
    """
    基础安全检查 - 第二阶段质量检查
    enable_deep_check: 是否启用深度检查（可能影响性能）
    """
    issues = []
    warnings = []
    security_risks = []

    for root, dirs, files in os.walk(skill_path):
        # 跳过某些目录
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules']]

        for file in files:
            file_path = os.path.join(root, file)

            try:
                # 只检查文本文件
                if not file.endswith(('.md', '.py', '.txt', '.json', '.yaml', '.yml', '.sh', '.bash')):
                    continue

                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 1. 检查硬编码的敏感信息（基础检查）
                sensitive_patterns = [
                    (r'api[_-]?key\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']', '疑似硬编码 API Key'),
                    (r'password\s*[:=]\s*["\']([^"\']{8,})["\']', '疑似硬编码密码'),
                    (r'token\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']', '疑似硬编码 Token'),
                    (r'secret[_-]?key\s*[:=]\s*["\']([^"\']{16,})["\']', '疑似硬编码 Secret Key'),
                ]

                for pattern, desc in sensitive_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        security_risks.append({
                            'file': file_path,
                            'type': desc,
                            'count': len(matches),
                            'severity': 'high'
                        })

                # 2. 检查危险函数（深度检查）
                if enable_deep_check and file.endswith('.py'):
                    dangerous_patterns = [
                        (r'\beval\s*\(', '使用 eval() 函数（代码注入风险）'),
                        (r'\bexec\s*\(', '使用 exec() 函数（代码注入风险）'),
                        (r'\bsubprocess\.call\s*\([^,)]*\+[^,)]*\)', 'shell 命令拼接（注入风险）'),
                        (r'\bos\.system\s*\([^,)]*\+[^,)]*\)', 'os.system 命令拼接（注入风险）'),
                    ]

                    for pattern, desc in dangerous_patterns:
                        if re.search(pattern, content):
                            security_risks.append({
                                'file': file_path,
                                'type': desc,
                                'severity': 'medium'
                            })

            except Exception as e:
                warnings.append(f'{file_path}: 安全检查失败 - {str(e)}')

    if security_risks:
        high_risks = [r for r in security_risks if r.get('severity') == 'high']
        if high_risks:
            issues.append(f'发现 {len(high_risks)} 个高风险安全问题')

    return {
        'status': 'error' if issues else ('warning' if warnings or security_risks else 'ok'),
        'issues': issues,
        'warnings': warnings,
        'security_risks': security_risks,
        'high_risk_count': len([r for r in security_risks if r.get('severity') == 'high']),
        'medium_risk_count': len([r for r in security_risks if r.get('severity') == 'medium'])
    }


def calculate_skill_health_score(skill_data, file_check, structure_check, metadata_check,
                                triggers_check=None, version_check=None, examples_check=None,
                                python_check=None, security_check=None):
    """
    计算综合健康度评分 - 方案1：平衡区分型

    核心原则：
    - 基础分80分，保证基本水平
    - 奖励项最高+20分，鼓励最佳实践
    - 扣分项最高-20分，体现问题区分度
    - 评分范围：60-100分（特殊情况0分）

    评分范围：
    - 基础分: 80分
    - 最高分: 100分（+20分奖励）
    - 最低分: 0分（严重问题）或 60分（多项扣分）
    """
    score = 80  # 基础分
    score_deductions = []
    score_bonuses = []
    security_veto = False

    # ========== 严重问题（大额扣分） ==========

    # 安全性检查（一票否决）
    if security_check and security_check.get('high_risk_count', 0) > 0:
        security_veto = True
        score_deductions.append(f'🚨 安全风险: 发现 {security_check["high_risk_count"]} 个高风险问题（一票否决）')

    # SKILL.md 几乎为空
    if file_check['line_count'] < 50 and file_check['line_count'] > 0:
        deduction = 40
        score -= deduction
        score_deductions.append(f'SKILL.md内容过少: -{deduction}')

    # 缺少必需文件（SKILL.md）
    if structure_check['issues']:
        deduction = 100  # 直接0分
        score -= deduction
        score_deductions.append(f'缺少必需文件(SKILL.md): -{deduction}')

    # ========== 轻微问题（小额扣分，固定值，不累加） ==========

    # 文件过长
    if file_check['exceeds_limit']:
        deduction = 5
        score -= deduction
        score_deductions.append(f'文件过长: -{deduction}')

    # 元数据问题（固定扣分，不按数量累加）
    if metadata_check['issues']:
        deduction = 5
        score -= deduction
        score_deductions.append(f'元数据不完整: -{deduction}')
    elif metadata_check['warnings']:
        deduction = 1
        score -= deduction
        score_deductions.append(f'元数据警告: -{deduction}')

    # 缺少 scripts 目录
    if not structure_check.get('has_scripts'):
        deduction = 3
        score -= deduction
        score_deductions.append(f'缺少scripts目录: -{deduction}')

    # 缺少使用示例
    if examples_check and not examples_check.get('has_examples'):
        deduction = 3
        score -= deduction
        score_deductions.append(f'缺少使用示例: -{deduction}')

    # 有不必要文件
    if structure_check.get('unnecessary_files'):
        deduction = 3
        score -= deduction
        score_deductions.append(f'有不必要文件: -{deduction}')

    # Python 脚本规范问题
    if python_check and python_check.get('warnings'):
        deduction = min(3, len(python_check['warnings']))
        score -= deduction
        score_deductions.append(f'Python脚本规范: -{deduction}')

    # ==================== 奖励项（加分，最高+20） ====================

    # 有完整 triggers（最重要，触发机制）
    if triggers_check and triggers_check.get('triggers_count', 0) >= 2:
        bonus = 5
        score += bonus
        score_bonuses.append(f'有完整triggers: +{bonus}')

    # 版本号规范（语义化版本）
    if version_check and version_check.get('is_compliant'):
        bonus = 2
        score += bonus
        score_bonuses.append(f'版本号规范: +{bonus}')

    # 有 scripts 且规范（高质量实现）
    if structure_check.get('has_scripts') and python_check:
        if not python_check.get('warnings'):
            bonus = 5
            score += bonus
            score_bonuses.append(f'scripts规范完善: +{bonus}')

    # 有 README（额外文档）
    if not structure_check.get('missing_recommended'):
        bonus = 3
        score += bonus
        score_bonuses.append(f'有README文档: +{bonus}')

    # 有 references 目录（参考资料）
    if structure_check.get('has_references'):
        bonus = 3
        score += bonus
        score_bonuses.append(f'有references目录: +{bonus}')

    # 有使用示例
    if examples_check and examples_check.get('has_examples'):
        bonus = 4
        score += bonus
        score_bonuses.append(f'有使用示例: +{bonus}')

    # 确保分数在 0-100 范围内
    score = max(0, min(100, int(score)))

    # 评级标准（调整后）
    if security_veto:
        grade = '不合格'
        emoji = '🚨'
    elif score >= 90:
        grade = '优秀'
        emoji = '🏆'
    elif score >= 80:
        grade = '良好'
        emoji = '👍'
    elif score >= 70:
        grade = '及格'
        emoji = '😐'
    else:
        grade = '需改进'
        emoji = '⚠️'

    return {
        'score': score,
        'grade': grade,
        'emoji': emoji,
        'deductions': score_deductions,
        'bonuses': score_bonuses,
        'security_veto': security_veto
    }


# ============================================
# 自动重构功能（增强版：支持备份、日志、回滚）
# ============================================
def create_backup(skill_path, skill_name):
    """创建备份"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(SCRIPT_DIR, '..', 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    backup_name = f"{skill_name}_{timestamp}"
    backup_path = os.path.join(backup_dir, backup_name)

    try:
        if os.path.exists(skill_path):
            shutil.copytree(skill_path, backup_path)
            print(f"[备份] 已创建备份: {backup_path}")
            return backup_path
    except Exception as e:
        print(f"[警告] 备份失败: {e}")
    return None


def restore_backup(backup_path, target_path):
    """从备份恢复"""
    try:
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        shutil.copytree(backup_path, target_path)
        print(f"[恢复] 已从备份恢复: {backup_path} -> {target_path}")
        return True
    except Exception as e:
        print(f"[错误] 恢复失败: {e}")
    return False


def cleanup_unnecessary_files(skill_path, unnecessary_files, refactor_log):
    """清理不必要文件（带日志记录）"""
    removed = []
    for file_path in unnecessary_files:
        try:
            # 备份文件内容（如果是小文件）
            backup_content = None
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    if len(content) < 10240:  # 只备份小于10KB的文件
                        backup_content = content
                except:
                    pass

            if os.path.isfile(file_path):
                os.remove(file_path)
                removed.append(file_path)
                refactor_log['removed_files'].append({
                    'path': file_path,
                    'backup': backup_content
                })
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                removed.append(file_path)
                refactor_log['removed_dirs'].append(file_path)
        except Exception as e:
            refactor_log['errors'].append(f"清理失败: {file_path} - {e}")
            print(f"  清理失败: {file_path} - {e}")
    return removed


def create_missing_files(skill_path, skill_name, missing_files, refactor_log):
    """创建缺失的推荐文件（带日志记录）"""
    created = []

    if 'README.md' in missing_files:
        readme_path = os.path.join(skill_path, 'README.md')
        if not os.path.exists(readme_path):
            content = f"""# {skill_name}

> 自动生成的README文件

## 说明

请在此文件中添加Skill的详细说明。

## 使用方法

TODO: 添加使用方法

## 配置

TODO: 添加配置说明

## 作者

TODO: 添加作者信息
"""
            try:
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                created.append(readme_path)
                refactor_log['created_files'].append(readme_path)
            except Exception as e:
                refactor_log['errors'].append(f"创建README.md失败: {e}")
                print(f"  创建README.md失败: {e}")

    return created


def refactor_skill_structure(skill_path, skill_name, health_report, backup_path=None):
    """
    重构Skill目录结构（增强版）

    Args:
        skill_path: Skill目录路径
        skill_name: Skill名称
        health_report: 健康检查报告
        backup_path: 备份路径（如果提供，支持回滚）

    Returns:
        dict: 包含操作日志和回滚信息
    """
    print(f"\n[重构] {skill_name}")
    print("-" * 60)

    # 初始化重构日志
    refactor_log = {
        'skill_name': skill_name,
        'timestamp': datetime.now().isoformat(),
        'backup_path': backup_path,
        'removed_files': [],
        'removed_dirs': [],
        'created_files': [],
        'created_dirs': [],
        'errors': []
    }

    actions_taken = []

    # 1. 清理不必要文件
    if health_report['structure_check']['unnecessary_files']:
        print("清理不必要的文件:")
        removed = cleanup_unnecessary_files(skill_path, health_report['structure_check']['unnecessary_files'], refactor_log)
        actions_taken.append(f'清理了{len(removed)}个不必要文件')
        for f in removed:
            print(f"  - {f}")

    # 2. 创建推荐文件
    if health_report['structure_check']['missing_recommended']:
        print("\n创建推荐文件:")
        created = create_missing_files(skill_path, skill_name, health_report['structure_check']['missing_recommended'], refactor_log)
        actions_taken.append(f'创建了{len(created)}个推荐文件')
        for f in created:
            print(f"  + {f}")

    # 3. 创建标准目录结构
    for dir_name in ['scripts', 'references']:
        dir_path = os.path.join(skill_path, dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            actions_taken.append(f'创建了{dir_name}目录')
            refactor_log['created_dirs'].append(dir_path)
            print(f"  + {dir_path}/")

    # 保存重构日志
    log_dir = os.path.join(SCRIPT_DIR, '..', 'refactor_logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{skill_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(refactor_log, f, ensure_ascii=False, indent=2)

    print(f"\n重构完成! 共执行{len(actions_taken)}项操作")
    print(f"[日志] 已保存重构日志: {log_file}")
    if backup_path:
        print(f"[备份] 备份位置: {backup_path}")
        print(f"[提示] 如需回滚，使用日志文件或备份目录")

    return {
        'actions': actions_taken,
        'log_file': log_file,
        'backup_path': backup_path,
        'refactor_log': refactor_log
    }


def rollback_refactor(log_file, backup_path=None):
    """
    回滚重构操作

    Args:
        log_file: 重构日志文件路径
        backup_path: 备份路径（优先使用备份恢复）
    """
    print(f"\n[回滚] 开始回滚操作...")
    print("-" * 60)

    # 优先使用备份恢复
    if backup_path and os.path.exists(backup_path):
        # 从备份路径提取 skill_name
        skill_name = os.path.basename(backup_path).split('_')[0]
        target_path = os.path.join(SKILLS_BASE_PATH, skill_name)

        if restore_backup(backup_path, target_path):
            print(f"[成功] 已从备份完整恢复")
            return True
        else:
            print(f"[失败] 备份恢复失败，尝试使用日志回滚")

    # 使用日志回滚
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)

        skill_name = log_data['skill_name']
        target_path = os.path.join(SKILLS_BASE_PATH, skill_name)

        # 删除创建的文件和目录
        for file_path in log_data.get('created_files', []):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"  - {file_path}")
            except Exception as e:
                print(f"  删除失败: {file_path} - {e}")

        for dir_path in log_data.get('created_dirs', []):
            try:
                if os.path.exists(dir_path) and not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    print(f"  - {dir_path}/")
            except Exception as e:
                print(f"  删除失败: {dir_path} - {e}")

        # 恢复删除的文件
        for file_info in log_data.get('removed_files', []):
            file_path = file_info['path']
            backup_content = file_info.get('backup')
            if backup_content:
                try:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb') as f:
                        f.write(backup_content)
                    print(f"  + {file_path}")
                except Exception as e:
                    print(f"  恢复失败: {file_path} - {e}")

        print(f"[完成] 日志回滚完成")
        return True
    except Exception as e:
        print(f"[错误] 日志回滚失败: {e}")
        return False


# ============================================
# 主要功能
# ============================================
def load_skills_data():
    """加载Skills数据 - 统一从 skill-match 获取"""
    # 从 skill-match 获取数据
    # SCRIPT_DIR 是 skill-health/scripts，需要向上两级到技能根目录
    skills_root = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
    skill_match_path = os.path.join(skills_root, 'skill-match', 'scripts', 'skills_data.json')

    if os.path.exists(skill_match_path):
        data_path = skill_match_path
        print("[INFO] 使用 skill-match 生成的数据")
    else:
        # 回退到本地数据（兼容性考虑）
        data_path = os.path.join(SCRIPT_DIR, 'skills_data.json')
        if not os.path.exists(data_path):
            print(f"[ERROR] 找不到数据文件")
            print(f"  期望路径: {skill_match_path}")
            print("请先运行 skill-match 收集数据")
            return None
        print("[INFO] 使用本地 skills_data.json（建议使用 skill-match 统一管理）")

    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_health_checks(skills, enable_security_deep_check=False):
    """
    运行健康度检查（增强版）

    Args:
        skills: Skills 数据列表
        enable_security_deep_check: 是否启用安全性深度检查（可能影响性能）
    """
    print("\n" + "=" * 60)
    print("步骤 1/2: 运行健康度检查")
    print("=" * 60)

    # 展示所有检查项
    print("\n[检查项清单]")
    print("  [第一阶段：核心规范]")
    print("    + 触发词完整性检查 (triggers)")
    print("    + 版本号规范检查 (语义化版本)")
    print("    + MCP 依赖检查")
    print("  [第二阶段：质量提升]")
    print("    + 使用示例检查 (代码块)")
    print("    + Python 脚本规范检查")
    print("    + 安全性基础检查")
    print()

    # 安全性深度检查性能提醒
    if enable_security_deep_check:
        print("[!] 已启用安全性深度检查，可能影响性能...")
    else:
        print("[提示] 使用 --deep-security 启用安全性深度检查")

    health_results = []
    issues_summary = {'error': 0, 'warning': 0, 'ok': 0}

    for i, skill in enumerate(skills, 1):
        name = skill['name']
        path = skill['path']

        print(f"[{i}/{len(skills)}] 检查 {name}...", end=' ', flush=True)

        # ========== 执行各项检查 ==========
        # 基础检查
        file_check = check_skill_file_length(path, name)
        structure_check = check_skill_directory_structure(path, name)
        metadata_check = check_skill_metadata_consistency(path, name)

        # 第一阶段：核心规范检查
        triggers_check = check_skill_triggers_completeness(path, name)
        version_check = check_version_compliance(path, name)
        mcp_check = check_mcp_dependencies(path)

        # 第二阶段：质量提升检查
        examples_check = check_skill_examples(path)
        python_check = check_python_scripts_standard(path)
        security_check = check_security_issues(path, enable_deep_check=enable_security_deep_check)

        # 计算健康度评分（传入所有检查结果）
        health_score = calculate_skill_health_score(
            skill, file_check, structure_check, metadata_check,
            triggers_check=triggers_check,
            version_check=version_check,
            examples_check=examples_check,
            python_check=python_check,
            security_check=security_check
        )

        # 统计状态
        overall_status = 'ok'
        critical_checks = [file_check, structure_check, metadata_check, triggers_check,
                          version_check, mcp_check, examples_check, python_check, security_check]

        if any(c.get('status') == 'error' for c in critical_checks) or health_score.get('security_veto'):
            overall_status = 'error'
            issues_summary['error'] += 1
        elif any(c.get('status') == 'warning' for c in critical_checks) or health_score['score'] < 75:
            overall_status = 'warning'
            issues_summary['warning'] += 1
        else:
            issues_summary['ok'] += 1

        result = {
            'name': name,
            'path': path,
            'health_score': health_score,
            'file_check': file_check,
            'structure_check': structure_check,
            'metadata_check': metadata_check,
            'triggers_check': triggers_check,
            'version_check': version_check,
            'mcp_check': mcp_check,
            'examples_check': examples_check,
            'python_check': python_check,
            'security_check': security_check,
            'overall_status': overall_status
        }

        health_results.append(result)

        # 输出简短状态
        status_symbol = {'ok': '[OK]', 'warning': '[!]', 'error': '[X]'}
        grade_symbol = {'优秀': '[A+]', '良好': '[A]', '及格': '[C]', '需改进': '[D]', '不合格': '[🚨]'}
        print(f"{status_symbol[overall_status]} {grade_symbol.get(health_score['grade'], '[?]')} {health_score['score']}分")

    print(f"\n检查完成: [OK]{issues_summary['ok']} [!]{issues_summary['warning']} [X]{issues_summary['error']}")

    return health_results


def generate_health_report(skills, health_results):
    """生成健康度报告（驾驶舱风格）"""
    print("\n" + "=" * 60)
    print("步骤 2/2: 生成健康度报告")
    print("=" * 60)

    md = []

    # 标题
    md.append("# 🏥 Claude Code Skills 健康度驾驶舱\n")
    md.append(f"> 📅 **报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    md.append("---\n")

    # ========== 核心指标总览 ==========
    total = len(health_results)
    excellent = sum(1 for r in health_results if r['health_score']['grade'] == '优秀')
    good = sum(1 for r in health_results if r['health_score']['grade'] == '良好')
    pass_grade = sum(1 for r in health_results if r['health_score']['grade'] == '及格')
    need_improvement = sum(1 for r in health_results if r['health_score']['grade'] == '需改进')
    failed = sum(1 for r in health_results if r['health_score']['grade'] == '不合格')

    avg_score = sum(r['health_score']['score'] for r in health_results) / total if total > 0 else 0
    has_security_issues = sum(1 for r in health_results if r['security_check'].get('high_risk_count', 0) > 0)

    # 统计安全问题总数（用于显示详细数据）
    total_security_issues = 0
    for r in health_results:
        total_security_issues += r['security_check'].get('high_risk_count', 0)

    md.append("## 📊 核心指标\n\n")
    md.append("| 🎯 指标 | 📈 数值 | 📝 说明 |\n")
    md.append("|--------|--------|--------|\n")
    md.append(f"| **总Skill数** | **{total}** 个 | 全部已安装的技能 |\n")
    md.append(f"| **平均健康分** | **{avg_score:.1f}** 分 | 所有Skill的平均得分 |\n")
    md.append(f"| **优秀率** | **{excellent/total*100:.1f}%** | 获得90分以上的比例 |\n")
    md.append(f"| **安全问题** | **{has_security_issues}**个Skill/{total_security_issues}个问题 | 高风险安全问题统计 |\n")
    md.append(f"| **需要改进** | **{need_improvement + failed}** 个 | 健康度低于70分的Skill |\n")
    md.append("\n---\n")

    # ========== 🚨 高安全问题专项表格 ==========
    security_issues_list = []
    for r in health_results:
        sc = r.get('security_check', {})
        high_risks = sc.get('security_risks', [])
        for risk in high_risks:
            if risk.get('severity') == 'high':
                security_issues_list.append({
                    'skill': r['name'],
                    'type': risk.get('type', '未知'),
                    'file': os.path.basename(risk.get('file', '')),
                    'count': risk.get('count', 1)
                })

    if security_issues_list:
        md.append("## 🚨 高安全问题清单\n\n")
        md.append(f"> ⚠️ **发现 {len(security_issues_list)} 个高风险安全问题，请立即处理！**\n\n")
        md.append("| Skill | 问题类型 | 文件 | 数量 |\n")
        md.append("|-------|----------|------|------|\n")
        for issue in security_issues_list[:20]:  # 最多显示20个
            md.append(f"| **{issue['skill']}** | {issue['type']} | `{issue['file']}` | {issue['count']} |\n")
        if len(security_issues_list) > 20:
            md.append(f"| ... | 还有 {len(security_issues_list) - 20} 个问题 | | |\n")
        md.append("\n---\n")

    # ========== 健康度等级分布 ==========
    md.append("## 📈 可视化分析\n\n")
    md.append("### 🏆 健康度等级分布\n\n")

    grade_distribution = [
        ("🏆 优秀", excellent, excellent),
        ("👍 良好", good, good),
        ("😐 及格", pass_grade, pass_grade),
        ("⚠️ 需改进", need_improvement, need_improvement),
        ("🚨 不合格", failed, failed)
    ]

    max_grade = max(item[1] for item in grade_distribution) if grade_distribution else 1
    if max_grade == 0:
        max_grade = 1

    for label, value, _ in grade_distribution:
        if value > 0:
            bar_length = int((value / max_grade) * 50)
            bar = "█" * bar_length + "░" * (50 - bar_length)
            percentage = (value / total) * 100 if total > 0 else 0
            md.append(f"{label:12} │{bar}│ {value} ({percentage:.1f}%)\n")

    md.append("\n")

    # ========== 问题类别统计 ==========
    md.append("### ⚠️ 问题类别 TOP 10\n\n")

    # 统计各类问题数量
    issue_categories = {
        "🎯 触发词缺失": 0,
        "🏷️ 版本号不规范": 0,
        "📖 缺少使用示例": 0,
        "🐍 Python脚本不规范": 0,
        "📁 缺少scripts目录": 0,
        "📚 缺少references目录": 0,
        "📄 SKILL.md过短": 0,
        "📝 缺少README": 0,
        "🗑️ 有不必要文件": 0,
        "🔒 高安全问题": 0,
        "⚠️ 中安全问题": 0
    }

    for r in health_results:
        if r.get('triggers_check', {}).get('issues'):
            issue_categories["🎯 触发词缺失"] += 1
        if not r.get('version_check', {}).get('is_compliant'):
            issue_categories["🏷️ 版本号不规范"] += 1
        if not r.get('examples_check', {}).get('has_examples'):
            issue_categories["📖 缺少使用示例"] += 1
        if r.get('python_check', {}).get('warnings'):
            issue_categories["🐍 Python脚本不规范"] += 1
        if not r.get('structure_check', {}).get('has_scripts'):
            issue_categories["📁 缺少scripts目录"] += 1
        if not r.get('structure_check', {}).get('has_references'):
            issue_categories["📚 缺少references目录"] += 1
        if r.get('file_check', {}).get('exceeds_limit'):
            issue_categories["📄 SKILL.md过短"] += 1
        if r.get('structure_check', {}).get('missing_recommended'):
            issue_categories["📝 缺少README"] += 1
        if r.get('structure_check', {}).get('unnecessary_files'):
            issue_categories["🗑️ 有不必要文件"] += 1
        if r.get('security_check', {}).get('high_risk_count', 0) > 0:
            issue_categories["🔒 高安全问题"] += 1
        if r.get('security_check', {}).get('medium_risk_count', 0) > 0:
            issue_categories["⚠️ 中安全问题"] += 1

    # 按问题数量排序，取Top 10
    sorted_issues = sorted(issue_categories.items(), key=lambda x: x[1], reverse=True)[:10]
    max_issue = max(item[1] for item in sorted_issues) if sorted_issues else 1
    if max_issue == 0:
        max_issue = 1

    for category, count in sorted_issues:
        if count > 0:
            bar_length = int((count / max_issue) * 50)
            bar = "█" * bar_length + "░" * (50 - bar_length)
            percentage = (count / total) * 100 if total > 0 else 0
            md.append(f"{category:15} │{bar}│ {count} ({percentage:.1f}%)\n")

    md.append("\n")

    # ========== 问题 Skill TOP 10 ==========
    md.append("### 🔻 健康度最低 TOP 10\n\n")

    sorted_by_score = sorted(health_results, key=lambda x: x['health_score']['score'])[:10]
    for i, result in enumerate(sorted_by_score, 1):
        name = result['name']
        score = result['health_score']['score']
        grade = result['health_score']['grade']
        emoji = result['health_score']['emoji']

        bar_length = int(score / 2)
        bar = "█" * bar_length + "░" * (50 - bar_length)
        md.append(f"{i:2}. {emoji} {name[:20]:20} │{bar}│ {score}分\n")

    md.append("\n")

    # ========== 扣分原因分布 ==========
    md.append("### 💔 主要扣分原因分布\n\n")

    deduction_reasons = {}
    for r in health_results:
        for deduction in r['health_score'].get('deductions', []):
            # 提取扣分原因类型
            reason_type = deduction.split(':')[0].replace('🚨 ', '').replace('- ', '').strip()
            deduction_reasons[reason_type] = deduction_reasons.get(reason_type, 0) + 1

    sorted_deductions = sorted(deduction_reasons.items(), key=lambda x: x[1], reverse=True)[:10]
    max_deduction = max(item[1] for item in sorted_deductions) if sorted_deductions else 1
    if max_deduction == 0:
        max_deduction = 1

    for reason, count in sorted_deductions:
        if count > 0:
            bar_length = int((count / max_deduction) * 50)
            bar = "█" * bar_length + "░" * (50 - bar_length)
            percentage = (count / total) * 100 if total > 0 else 0
            md.append(f"{reason:20} │{bar}│ {count} ({percentage:.1f}%)\n")

    md.append("\n---\n")

    # ========== 健康度等级统计表 ==========
    md.append("## 📋 健康度等级统计\n\n")
    md.append("| 等级 | 数量 | 占比 | 评分范围 |\n")
    md.append("|------|------|------|----------|\n")
    md.append(f"| 🏆 优秀 | {excellent} | {excellent/total*100:.1f}% | 90-100分 |\n")
    md.append(f"| 👍 良好 | {good} | {good/total*100:.1f}% | 75-89分 |\n")
    md.append(f"| 😐 及格 | {pass_grade} | {pass_grade/total*100:.1f}% | 60-74分 |\n")
    md.append(f"| ⚠️ 需改进 | {need_improvement} | {need_improvement/total*100:.1f}% | 0-59分 |\n")
    if failed > 0:
        md.append(f"| 🚨 不合格 | {failed} | {failed/total*100:.1f}% | 安全问题 |\n")
    md.append("\n---\n")

    # 需要改进的Skills
    need_refactor = [r for r in health_results if r['overall_status'] != 'ok']
    if need_refactor:
        md.append("## ⚠️ 需要关注的 Skills\n\n")
        md.append(f"以下 {len(need_refactor)} 个Skills存在健康问题:\n\n")

        for result in sorted(need_refactor, key=lambda x: x['health_score']['score']):
            name = result['name']
            score = result['health_score']['score']
            grade = result['health_score']['grade']
            emoji = result['health_score']['emoji']

            md.append(f"### {emoji} {name} - {score}分 ({grade})\n\n")

            # 奖励项（新增）
            if result['health_score'].get('bonuses'):
                md.append("**✨ 加分项**:\n")
                for bonus in result['health_score']['bonuses']:
                    md.append(f"- + {bonus}\n")
                md.append("\n")

            # 扣分原因
            if result['health_score']['deductions']:
                md.append("**扣分原因**:\n")
                for deduction in result['health_score']['deductions']:
                    md.append(f"- {deduction}\n")
                md.append("\n")

            # 具体问题
            issues = []
            if result['file_check']['issue']:
                issues.append(f"文件: {result['file_check']['issue']}")
            if result['structure_check']['issues']:
                issues.extend([f"结构: {i}" for i in result['structure_check']['issues']])
            if result['metadata_check']['issues']:
                issues.extend([f"元数据: {i}" for i in result['metadata_check']['issues']])

            if issues:
                md.append("**问题详情**:\n")
                for issue in issues:
                    md.append(f"- {issue}\n")
                md.append("\n")

            md.append("---\n")

    # 详细健康度报告
    md.append("## 📋 详细健康度报告\n\n")

    for result in sorted(health_results, key=lambda x: x['health_score']['score'], reverse=True):
        name = result['name']
        score = result['health_score']['score']
        grade = result['health_score']['grade']
        emoji = result['health_score']['emoji']

        md.append(f"### {emoji} {name} - {score}分 ({grade})\n\n")

        # === 第一阶段：核心规范 ===
        md.append("#### 【第一阶段：核心规范】\n\n")

        # 触发词检查
        md.append("**🎯 触发词检查**:\n")
        if 'triggers_check' in result:
            tc = result['triggers_check']
            if tc.get('has_triggers') and tc.get('triggers_count', 0) > 0:
                md.append(f"- ✅ 有 {tc['triggers_count']} 个触发词\n")
                if tc.get('triggers_list'):
                    md.append(f"  触发词: `{', '.join(tc['triggers_list'][:5])}`{'...' if len(tc['triggers_list']) > 5 else ''}\n")
            else:
                md.append("- ⚠️ 缺少触发词或格式不正确\n")
            if tc.get('warnings'):
                for w in tc.get('warnings', []):
                    md.append(f"- ⚠️ {w}\n")
        else:
            md.append("- ℹ️ 未检查\n")
        md.append("\n")

        # 版本号检查
        md.append("**🏷️ 版本号检查**:\n")
        if 'version_check' in result:
            vc = result['version_check']
            if vc.get('is_compliant'):
                md.append(f"- ✅ 版本号符合规范: `{vc.get('version')}`\n")
            else:
                md.append("- ⚠️ 版本号不符合语义化版本规范\n")
        else:
            md.append("- ℹ️ 未检查\n")
        md.append("\n")

        # MCP 依赖检查
        md.append("**🔗 MCP 依赖检查**:\n")
        if 'mcp_check' in result:
            mc = result['mcp_check']
            if mc.get('has_mcp_deps'):
                md.append(f"- ℹ️ {mc.get('notes', '有 MCP 依赖')}\n")
                if mc.get('mcp_servers'):
                    md.append(f"  MCP Servers: `{', '.join(mc['mcp_servers'])}`\n")
            else:
                md.append("- ✅ 无 MCP 依赖\n")
        else:
            md.append("- ℹ️ 未检查\n")
        md.append("\n")

        # === 第二阶段：质量提升 ===
        md.append("#### 【第二阶段：质量提升】\n\n")

        # 使用示例检查
        md.append("**📖 使用示例检查**:\n")
        if 'examples_check' in result:
            ec = result['examples_check']
            if ec.get('has_examples'):
                md.append(f"- ✅ 包含 {ec.get('example_count', 0)} 个代码块示例\n")
            else:
                md.append("- ⚠️ 缺少使用示例\n")
            if ec.get('warnings'):
                for w in ec.get('warnings', []):
                    md.append(f"- ⚠️ {w}\n")
        else:
            md.append("- ℹ️ 未检查\n")
        md.append("\n")

        # Python 脚本规范检查
        md.append("**🐍 Python 脚本规范**:\n")
        if 'python_check' in result:
            pc = result['python_check']
            if pc.get('has_scripts'):
                md.append(f"- ℹ️ 检查了 {pc.get('scripts_checked', 0)} 个脚本\n")
                if pc.get('scripts_with_main', 0) > 0:
                    md.append(f"  ✅ 有 `if __name__ == '__main__'`: {pc['scripts_with_main']}/{pc['scripts_checked']}\n")
                if pc.get('scripts_with_docstring', 0) > 0:
                    md.append(f"  ✅ 有 docstring: {pc['scripts_with_docstring']}/{pc['scripts_checked']}\n")
                if pc.get('warnings'):
                    md.append("- ⚠️ 警告:\n")
                    for w in pc.get('warnings', [])[:3]:
                        md.append(f"  - {w}\n")
                    if len(pc.get('warnings', [])) > 3:
                        md.append(f"  - ... 还有 {len(pc['warnings']) - 3} 个警告\n")
            else:
                md.append("- ℹ️ 无 Python 脚本\n")
        else:
            md.append("- ℹ️ 未检查\n")
        md.append("\n")

        # 安全性检查
        md.append("**🔒 安全性检查**:\n")
        if 'security_check' in result:
            sc = result['security_check']
            high_risk = sc.get('high_risk_count', 0)
            medium_risk = sc.get('medium_risk_count', 0)

            if high_risk > 0:
                md.append(f"- 🚨 **高风险**: {high_risk} 个问题\n")
                for risk in sc.get('security_risks', [])[:3]:
                    if risk.get('severity') == 'high':
                        md.append(f"  - {risk.get('type', '未知风险')} ({os.path.basename(risk.get('file', ''))})\n")
            elif medium_risk > 0:
                md.append(f"- ⚠️ **中风险**: {medium_risk} 个问题\n")
            else:
                md.append("- ✅ 未发现安全问题\n")
        else:
            md.append("- ℹ️ 未检查\n")
        md.append("\n")

        # === 基础检查 ===
        md.append("#### 【基础检查】\n\n")

        # 文件检查
        md.append("**📄 文件检查**:\n")
        md.append(f"- 行数: {result['file_check']['line_count']}\n")
        if result['file_check'].get('issue'):
            md.append(f"- ⚠️ {result['file_check']['issue']}\n")
        else:
            md.append(f"- ✅ 文件长度正常\n")
        md.append("\n")

        # 结构检查
        md.append("**📁 结构检查**:\n")
        if result['structure_check']['has_scripts']:
            md.append("- ✅ 有 scripts 目录\n")
        else:
            md.append("- ⚠️ 缺少 scripts 目录\n")

        if result['structure_check']['has_references']:
            md.append("- ✅ 有 references 目录\n")
        else:
            md.append("- ⚠️ 缺少 references 目录\n")

        if result['structure_check']['unnecessary_files']:
            md.append(f"- ⚠️ 发现 {len(result['structure_check']['unnecessary_files'])} 个不必要文件\n")
        md.append("\n")

        # 元数据检查
        md.append("**📝 元数据检查**:\n")
        if result['metadata_check'].get('warnings'):
            for warning in result['metadata_check']['warnings']:
                md.append(f"- ⚠️ {warning}\n")
        else:
            md.append("- ✅ 元数据完整\n")

        md.append("\n---\n")

    # 保存报告
    reports_dir = os.path.join(SCRIPT_DIR, '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    version = "2.0.0"  # 更新版本号，反映新增的检查项
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f'SKILLS_健康度_v{version}_{date_str}.md'
    output_path = os.path.join(reports_dir, filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(md)

    # 同时生成默认名称
    default_path = os.path.join(reports_dir, 'SKILLS_健康度_最新.md')
    with open(default_path, 'w', encoding='utf-8') as f:
        f.writelines(md)

    print(f"[OK] 健康度报告已生成: {output_path}")
    return output_path


def prompt_refactor(health_results):
    """提示用户是否需要重构"""
    # 找出需要重构的Skills
    need_refactor = [r for r in health_results if r['overall_status'] != 'ok']

    if not need_refactor:
        print("\n[SUCCESS] 所有Skills健康度良好，无需重构!")
        return []

    print("\n" + "=" * 60)
    print("发现需要重构的Skills")
    print("=" * 60)
    print(f"\n以下 {len(need_refactor)} 个Skills存在健康问题:\n")

    for i, result in enumerate(need_refactor[:10], 1):  # 最多显示10个
        name = result['name']
        score = result['health_score']['score']
        grade = result['health_score']['grade']
        print(f"{i}. [{grade}] {name} - {score}分")

    if len(need_refactor) > 10:
        print(f"\n... 还有 {len(need_refactor) - 10} 个Skills")

    print("\n" + "-" * 60)
    print("\n重构操作包括:")
    print("  1. 自动备份（支持回滚）")
    print("  2. 清理不必要文件 (.pyc, __pycache__, .DS_Store等)")
    print("  3. 创建推荐文件 (README.md等)")
    print("  4. 创建标准目录结构 (scripts/, references/)")
    print("  5. 生成重构日志（记录所有操作）")

    print("\n是否要执行重构? (y/n): ", end='')
    # 检测是否为自动模式（非终端输入）
    if not sys.stdin.isatty():
        response = 'n'  # 自动模式：跳过
        print("\n[自动模式] 已跳过重构操作")
    else:
        try:
            response = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            response = 'n'

    if response.lower() == 'y':
        refactored = []
        for result in need_refactor:
            try:
                # 创建备份
                backup_path = create_backup(result['path'], result['name'])
                # 执行重构
                actions = refactor_skill_structure(result['path'], result['name'], result, backup_path)
                refactored.append({
                    'name': result['name'],
                    'actions': actions,
                    'backup_path': backup_path
                })
            except Exception as e:
                print(f"\n[ERROR] 重构 {result['name']} 失败: {e}")

        print(f"\n[OK] 成功重构 {len(refactored)} 个Skills")
        if refactored:
            print("\n[提示] 备份和日志已保存，如需回滚请使用:")
            print("  python skill_health.py --rollback <log_file>")
        return refactored
    else:
        print("\n已跳过重构操作")
        print("\n提示: 你可以手动重构，或使用以下命令交互式执行:")
        print("  python -m skill_health.interactive_refactor")
        return []


# ============================================
# 主函数
# ============================================
def main():
    """主执行函数（支持命令行参数）"""
    import sys

    # 解析命令行参数
    enable_deep_security = '--deep-security' in sys.argv or '-d' in sys.argv
    show_help = '--help' in sys.argv or '-h' in sys.argv

    print("\n" + "=" * 60)
    print("       Skill-Health 健康度评估工具 v2.0")
    print("=" * 60 + "\n")

    if show_help:
        print("用法: python skill_health.py [选项]")
        print("\n选项:")
        print("  -d, --deep-security    启用安全性深度检查（可能影响性能）")
        print("  -h, --help             显示此帮助信息")
        print("\n检查项:")
        print("  【第一阶段：核心规范】")
        print("    - 触发词完整性检查 (triggers)")
        print("    - 版本号规范检查 (语义化版本)")
        print("    - MCP 依赖检查")
        print("  【第二阶段：质量提升】")
        print("    - 使用示例检查 (代码块)")
        print("    - Python 脚本规范检查")
        print("    - 安全性基础检查")
        print("    - 安全性深度检查 (需要 --deep-security)")
        return

    # 安全性深度检查性能提醒
    if enable_deep_security:
        print("\n" + "=" * 60)
        print("⚠️  安全性深度检查已启用")
        print("=" * 60)
        print("\n深度安全检查将分析以下内容:")
        print("  • 危险函数使用 (eval, exec, shell注入)")
        print("  • 硬编码敏感信息 (API Key, 密码, Token)")
        print("\n这可能会增加 10-30% 的执行时间，是否继续? (y/n): ", end='')
        try:
            # 检测是否为自动模式
            if not sys.stdin.isatty():
                response = 'n'  # 自动模式：跳过
                print("\n[自动模式] 已跳过深度安全检查")
                enable_deep_security = False
            else:
                response = input().strip().lower()
                if response != 'y':
                    print("已取消深度安全检查，使用基础安全检查...")
                    enable_deep_security = False
        except (EOFError, KeyboardInterrupt):
            print("\n已取消深度安全检查，使用基础安全检查...")
            enable_deep_security = False
        print()

    # 加载数据
    skills = load_skills_data()
    if not skills:
        return

    print("[INFO] 驾驶舱报告请参考 skill-match 的溯源检查报告")
    print("[INFO] 本工具专注于健康度评估和问题分析\n")

    # 执行健康度检查（传入深度安全检查参数）
    health_results = run_health_checks(skills, enable_security_deep_check=enable_deep_security)
    health_path = generate_health_report(skills, health_results)

    # 保存健康度数据
    health_data_path = os.path.join(SCRIPT_DIR, 'skills_health_data.json')
    with open(health_data_path, 'w', encoding='utf-8') as f:
        json.dump(health_results, f, ensure_ascii=False, indent=2)
    print(f"[OK] 健康度数据已保存: {health_data_path}")

    # 提示重构
    prompt_refactor(health_results)

    print("\n" + "=" * 60)
    print("健康度评估完成!")
    print("=" * 60)
    print(f"\n生成的报告:")
    print(f"  - {health_path}")
    print(f"\n下一步:")
    print(f"  1. 查看 skill-match 的溯源检查报告了解概况")
    print(f"  2. 查看健康度报告了解问题详情")
    print(f"  3. 根据建议手动或自动重构")


if __name__ == '__main__':
    main()
