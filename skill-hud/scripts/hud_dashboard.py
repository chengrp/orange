#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill-HUD 综合仪表板报告生成工具

功能：
1. 整合三个子技能的数据（fetchget/health/innovation）
2. 生成综合仪表板报告
3. 简明扼要、详略得当地展示所有关键信息
4. 丰富的图表和可视化样式
"""

import os
import sys
import json
from datetime import datetime
from collections import defaultdict

import subprocess

# ============================================
# 配置
# ============================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION = "1.0.0"

# Skills 基础目录 - 自动检测
# 新结构：子技能在 skill-hud/skills/ 目录下
_POSSIBLE_SKILLS_BASE = [
    os.path.join(os.path.dirname(SCRIPT_DIR), 'skills'),  # skill-hud/skills (新结构)
    os.path.dirname(SCRIPT_DIR),  # skill-hud 的父目录
    os.path.expanduser('~/.claude/skills'),
    'C:\\Users\\RyanCh\\.claude\\skills',
]
SKILLS_BASE_DIR = None
for path in _POSSIBLE_SKILLS_BASE:
    if os.path.exists(os.path.join(path, 'skill-match')):
        SKILLS_BASE_DIR = path
        break

if SKILLS_BASE_DIR is None:
    # 如果都找不到，使用默认路径（skill-hud/skills）
    SKILLS_BASE_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'skills')

# ============================================
# 工具函数
# ============================================
def format_size(mb):
    """格式化大小，统一显示格式"""
    if mb < 0.001:
        return f"{mb*1024*1024:.0f}B"
    elif mb < 1:
        return f"{mb*1024:.1f}KB"
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
            return "今天"
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
    except:
        return "未知"


def get_category_from_description(description):
    """根据描述推断Skill类别"""
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
        return "🏢 Anthropic"
    elif "cursor-shadowsong" in url:
        return "👤 cursor"
    elif "wechat-skills" in url:
        return "📱 微信"
    elif "obsidian-skills" in url:
        return "📝 Obsidian"
    else:
        return "🔗 社区"


def create_progress_bar(percentage, width=30):
    """创建进度条（增强版 - 支持颜色级别）"""
    filled = int(percentage / 100 * width)
    # 根据百分比选择不同字符
    if percentage >= 75:
        bar_char = "█"
    elif percentage >= 50:
        bar_char = "▓"
    elif percentage >= 25:
        bar_char = "▒"
    else:
        bar_char = "░"
    bar = bar_char * filled + "░" * (width - filled)
    return f"{bar} {percentage:.1f}%"


def create_badge(text, color="blue"):
    """创建徽章样式"""
    colors = {
        "green": "🟢",
        "blue": "🔵",
        "red": "🔴",
        "yellow": "🟡",
        "purple": "🟣",
        "orange": "🟠"
    }
    icon = colors.get(color, "⚪")
    return f"`{icon} {text}`"


def create_ascii_chart(data, title, max_width=50, style="bar"):
    """创建ASCII图表（增强版 - 支持多种样式）"""
    if not data:
        return f"\n### {title}\n暂无数据\n"

    lines = [f"\n### {title}\n"]
    max_val = max(item[1] for item in data) if data else 1
    if max_val == 0:
        max_val = 1

    for label, value in data:
        pct = value / max_val if max_val > 0 else 0
        bar_length = int(pct * max_width)

        if style == "block":
            # 块状样式
            bar = "█" * bar_length + "░" * (max_width - bar_length)
            lines.append(f"{label:15} │{bar}│ {value}")
        elif style == "dot":
            # 点状样式
            bar = "●" * bar_length + "○" * (max_width - bar_length)
            lines.append(f"{label:15} │{bar}│ {value}")
        elif style == "gradient":
            # 渐变样式
            gradient_chars = "█▓▒░"
            full_blocks = bar_length // 4
            partial = bar_length % 4
            bar = "█" * full_blocks
            if partial > 0:
                bar += gradient_chars[4-partial]
            bar += "░" * (max_width - bar_length)
            lines.append(f"{label:15} │{bar}│ {value}")
        else:
            bar = "█" * bar_length + "░" * (max_width - bar_length)
            lines.append(f"{label:15} │{bar}│ {value}")

    return "\n".join(lines) + "\n"


def create_metric_card(title, value, description, icon="📊", color="blue"):
    """创建指标卡片样式"""
    color_icons = {
        "green": "💚",
        "blue": "💙",
        "red": "❤️",
        "yellow": "💛",
        "purple": "💜"
    }
    return f"""
### {icon} {title}

| 指标 | 数值 |
|------|------|
| **{title}** | **{value}** |
| 说明 | {description} |
"""


def create_health_badge(score, grade):
    """创建健康度徽章"""
    grade_icons = {
        "优秀": ("🏆", "green"),
        "良好": ("👍", "blue"),
        "及格": ("😐", "yellow"),
        "需改进": ("⚠️", "red")
    }
    icon, color = grade_icons.get(grade, ("❓", "gray"))
    return f"{icon} **{grade}** ({score}分)"


def create_ownership_badge(ownership_type, custom_pct=0):
    """创建所有权徽章"""
    badges = {
        "原创": "🎨",
        "魔改": "🔧",
        "原生": "📦"
    }
    icon = badges.get(ownership_type, "❓")
    if ownership_type == "原创":
        return f"{icon} **原创** (100%自定义)"
    elif ownership_type == "魔改":
        return f"{icon} **魔改** ({custom_pct}%自定义)"
    else:
        return f"{icon} **原生** (0%自定义)"


def create_info_box(title, content, box_type="info"):
    """创建信息框"""
    box_types = {
        "info": "ℹ️",
        "warning": "⚠️",
        "success": "✅",
        "error": "❌",
        "tip": "💡"
    }
    icon = box_types.get(box_type, "📌")
    return f"""
> {icon} **{title}**
>
> {content}
"""


def create_sparkline(values, width=20, min_val=None, max_val=None):
    """创建迷你图（Sparkline）"""
    if not values:
        return "▁▁▁▁▁▁▁▁▁▁"

    if min_val is None:
        min_val = min(values)
    if max_val is None:
        max_val = max(values)

    if max_val == min_val:
        return "▂" * width

    range_val = max_val - min_val
    spark_chars = "▁▂▃▄▅▆▇█"

    result = []
    for v in values:
        normalized = (v - min_val) / range_val if range_val > 0 else 0.5
        char_idx = int(normalized * (len(spark_chars) - 1))
        result.append(spark_chars[char_idx])

    return "".join(result)


# ============================================
# 数据加载
# ============================================
def load_all_data():
    """加载所有子技能的数据"""
    data = {
        'skills': None,
        'version_check': None,
        'health_data': None,
        'ownership_config': None
    }

    # 1. 加载基础Skills数据 - 尝试多个可能的路径
    skills_paths = [
        os.path.join(SKILLS_BASE_DIR, 'skill-match', 'scripts', 'skills_data.json'),
        os.path.join(SKILLS_BASE_DIR, 'skill-fetchget', 'scripts', 'skills_data.json'),
        os.path.join(SCRIPT_DIR, 'skills_data.json'),
    ]

    for skills_path in skills_paths:
        if os.path.exists(skills_path):
            with open(skills_path, 'r', encoding='utf-8') as f:
                data['skills'] = json.load(f)
            print(f"[INFO] 已加载基础Skills数据 (来源: {os.path.basename(os.path.dirname(skills_path))})")
            break
    else:
        print("[WARN] 未找到基础Skills数据")

    # 2. 加载版本检查数据
    version_paths = [
        os.path.join(SKILLS_BASE_DIR, 'skill-fetchget', 'scripts', 'skills_version_check.json'),
        os.path.join(SKILLS_BASE_DIR, 'skill-match', 'scripts', 'skills_version_check.json'),
        os.path.join(SCRIPT_DIR, 'skills_version_check.json'),
    ]

    for version_path in version_paths:
        if os.path.exists(version_path):
            with open(version_path, 'r', encoding='utf-8') as f:
                data['version_check'] = json.load(f)
            print("[INFO] 已加载版本检查数据")
            break
    else:
        print("[WARN] 未找到版本检查数据")

    # 3. 加载健康度数据
    health_paths = [
        os.path.join(SKILLS_BASE_DIR, 'skill-health', 'scripts', 'skills_health_data.json'),
        os.path.join(SCRIPT_DIR, 'skills_health_data.json'),
    ]

    for health_path in health_paths:
        if os.path.exists(health_path):
            with open(health_path, 'r', encoding='utf-8') as f:
                data['health_data'] = json.load(f)
            print("[INFO] 已加载健康度数据")
            break
    else:
        print("[WARN] 未找到健康度数据")

    # 4. 加载所有权配置
    # 注意：skills_innovation_data.json 是实际生成的数据，ownership_config.json 是模板
    ownership_paths = [
        os.path.join(SKILLS_BASE_DIR, 'skill-innovation', 'scripts', 'skills_innovation_data.json'),
        os.path.join(SKILLS_BASE_DIR, 'skill-innovation', 'scripts', 'ownership_config.json'),
        os.path.join(SCRIPT_DIR, 'skills_innovation_data.json'),
        os.path.join(SCRIPT_DIR, 'ownership_config.json'),
    ]

    for ownership_path in ownership_paths:
        if os.path.exists(ownership_path):
            with open(ownership_path, 'r', encoding='utf-8') as f:
                data['ownership_config'] = json.load(f)
            print(f"[INFO] 已加载所有权配置 (来源: {os.path.basename(ownership_path)})")
            break
    else:
        print("[WARN] 未找到所有权配置")

    return data


def check_data_source_status(data):
    """检查数据来源状态（API限流/缓存使用）"""
    data_source_info = {
        'issues': [],
        'warnings': [],
        'is_fresh': True
    }

    import glob
    import time

    # 检查 skill-match 的数据来源状态
    # 尝试从 evaluation JSON 文件中读取
    try:
        match_reports_dir = os.path.join(SKILLS_BASE_DIR, 'skill-match', 'reports')
        if not os.path.exists(match_reports_dir):
            match_reports_dir = os.path.join(SKILLS_BASE_DIR, 'skill-match', 'scripts', 'reports')

        eval_files = glob.glob(os.path.join(match_reports_dir, 'skills_evaluation_v3_*.json'))
        if eval_files:
            latest_eval = sorted(eval_files, key=os.path.getmtime, reverse=True)[0]
            with open(latest_eval, 'r', encoding='utf-8') as f:
                eval_data = json.load(f)
                data_source = eval_data.get('data_source', {})

                if data_source.get('rate_limit_hit'):
                    data_source_info['issues'].append('GitHub API 限流')
                    data_source_info['is_fresh'] = False
                if data_source.get('used_cache'):
                    data_source_info['warnings'].append('部分数据来自缓存')
                    data_source_info['is_fresh'] = False
    except Exception as e:
        pass  # 静默失败，不阻塞主流程

    # 检查数据文件的时间戳（超过24小时视为可能过期）
    now = time.time()
    day_in_seconds = 24 * 60 * 60

    # 检查 skills_data.json 的时间
    skills_data_paths = [
        os.path.join(SKILLS_BASE_DIR, 'skill-match', 'scripts', 'skills_data.json'),
        os.path.join(SKILLS_BASE_DIR, 'skill-match', 'scripts', 'reports', 'skills_data.json'),
    ]

    skills_data_path = None
    for path in skills_data_paths:
        if os.path.exists(path):
            skills_data_path = path
            break

    if skills_data_path:
        file_age = now - os.path.getmtime(skills_data_path)
        if file_age > day_in_seconds:
            hours_old = int(file_age / 3600)
            data_source_info['warnings'].append(f'基础数据已 {hours_old} 小时未更新')
            data_source_info['is_fresh'] = False
    else:
        data_source_info['warnings'].append('未找到基础数据文件')

    return data_source_info


# ============================================
# 综合仪表板生成
# ============================================
def generate_hud_dashboard():
    """生成综合仪表板报告"""
    print("\n" + "=" * 60)
    print("       Skill-HUD 综合仪表板")
    print("=" * 60 + "\n")

    # 加载所有数据
    data = load_all_data()
    skills = data['skills']

    if not skills:
        print("[ERROR] 没有Skills数据，请先运行 skill-fetchget")
        return

    # 检查数据来源状态
    data_source_status = check_data_source_status(data)

    md = []

    # ============================================
    # 🎯 仪表板标题
    # ============================================
    md.append("# 🎯 Claude Code Skills 综合仪表板\n")
    md.append(f"> 📅 **报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    md.append(f"> 🔢 **版本**: {VERSION}\n")
    md.append("> 💡 **整合**: 数据收集 + 健康评估 + 创新指导\n")

    # 数据来源状态警告
    if data_source_status['issues'] or data_source_status['warnings']:
        md.append("\n---\n")
        md.append("## ⚠️ 数据来源说明\n\n")

        if data_source_status['issues']:
            md.append("**当前数据状态：**\n")
            for issue in data_source_status['issues']:
                md.append(f"- ⚠️ {issue}\n")
            md.append("\n")

        if data_source_status['warnings']:
            md.append("**提示：**\n")
            for warning in data_source_status['warnings']:
                md.append(f"- 💡 {warning}\n")
            md.append("\n")

        md.append("**建议：**\n")
        md.append("- 设置 `GITHUB_TOKEN` 环境变量以提高 API 限额\n")
        md.append("- 或稍后重新运行获取最新数据\n")
        md.append("\n")

        # 在标题行添加数据状态标记
        data_status_badge = " ⚠️ **[数据可能非最新]**"
    else:
        data_status_badge = ""

    if data_status_badge:
        # 修改标题行添加状态标记
        md.append("\n---\n")

    # ============================================
    # 📂 相关子报告（显著位置）
    # ============================================
    md.append("## 📂 相关子报告\n\n")
    md.append("> 💡 **提示**: 本报告是综合概览，以下是各子技能的详细报告\n\n")

    # 计算相对路径到子报告
    hud_reports_dir = os.path.join(SCRIPT_DIR, '..', 'reports')
    skills_base = os.path.join(os.path.dirname(SCRIPT_DIR), 'skills')

    md.append("| 子报告 | 说明 | 链接 |\n")
    md.append("|--------|------|------|\n")

    # skill-match 报告
    match_report = os.path.join(skills_base, 'skill-match', 'reports')
    if os.path.exists(match_report):
        md.append("| **📊 数据收集报告** | GitHub关联、版本检查、空间分析 | `../skills/skill-match/reports/` |\n")
    else:
        md.append("| **📊 数据收集报告** | GitHub关联、版本检查、空间分析 | _（未生成）_ |\n")

    # skill-health 报告
    health_report = os.path.join(skills_base, 'skill-health', 'reports')
    if os.path.exists(health_report):
        md.append("| **🏥 健康度报告** | 文件检查、结构验证、问题分析 | `../skills/skill-health/reports/` |\n")
    else:
        md.append("| **🏥 健康度报告** | 文件检查、结构验证、问题分析 | _（未生成）_ |\n")

    # skill-innovation 报告
    innovation_report = os.path.join(skills_base, 'skill-innovation', 'reports')
    if os.path.exists(innovation_report):
        md.append("| **🎨 创新指导报告** | 所有权分析、自定义度、魔改推荐 | `../skills/skill-innovation/reports/` |\n")
    else:
        md.append("| **🎨 创新指导报告** | 所有权分析、自定义度、魔改推荐 | _（未生成）_ |\n")

    md.append("\n---\n")

    # ============================================
    # 📊 核心指标卡片
    # ============================================
    md.append("## 📊 核心指标一览\n\n")

    total_skills = len(skills)
    total_size = sum(s['size_mb'] for s in skills)
    with_github = sum(1 for s in skills if s.get('github_url'))

    # 计算健康度统计
    health_stats = {'优秀': 0, '良好': 0, '及格': 0, '需改进': 0}
    if data['health_data']:
        for h in data['health_data']:
            grade = h['health_score']['grade']
            health_stats[grade] = health_stats.get(grade, 0) + 1

    # 计算所有权统计 - 支持两种数据格式
    ownership_stats = {'Original': 0, 'Modified': 0, 'Native': 0}
    custom_score = 0

    if data['ownership_config']:
        # 检查数据格式类型
        if 'ownership_results' in data['ownership_config']:
            # skill-innovation v2.0 格式
            for item in data['ownership_config']['ownership_results']:
                item_type = item.get('type', '原生')
                if item_type == '原创':
                    ownership_stats['Original'] += 1
                    custom_score += item.get('custom_percentage', 100)
                elif item_type == '魔改':
                    ownership_stats['Modified'] += 1
                    custom_score += item.get('custom_percentage', 0)
                else:
                    ownership_stats['Native'] += 1
        else:
            # 旧格式: {"原创": [...], "魔改": {...}}
            original_list = data['ownership_config'].get('原创', [])
            modified_list = data['ownership_config'].get('魔改', {})

            for skill in skills:
                name = skill['name']
                if name in original_list:
                    ownership_stats['Original'] += 1
                    custom_score += 100
                elif name in modified_list:
                    ownership_stats['Modified'] += 1
                    custom_score += modified_list[name].get('custom_percentage', 0)
                else:
                    ownership_stats['Native'] += 1

    avg_custom = custom_score / total_skills if total_skills else 0

    # 指标卡片
    md.append("### 📈 快速概览\n\n")
    md.append("| 🎯 指标 | 📊 数值 | 📝 说明 |\n")
    md.append("|--------|--------|--------|\n")
    md.append(f"| **总Skill数** | **{total_skills}** 个 | 已安装的Skills |\n")
    md.append(f"| **总占用空间** | **{format_size(total_size)}** | 磁盘占用 |\n")

    # GitHub覆盖指标 - 根据数据来源状态添加标注
    github_note = ""
    if not data_source_status['is_fresh'] and ('GitHub API 限流' in data_source_status['issues'] or '缓存' in str(data_source_status['warnings'])):
        github_note = " ⚠️"
    md.append(f"| **GitHub覆盖** | **{with_github}** ({with_github/total_skills*100:.0f}%){github_note} | 有明确来源 |\n")

    md.append(f"| **平均自定义度** | **{avg_custom:.1f}%** | 创造力水平 |\n")

    # 健康度等级
    if avg_custom >= 70:
        custom_level = "🏆 大师级"
    elif avg_custom >= 40:
        custom_level = "🔥 进阶级"
    elif avg_custom >= 20:
        custom_level = "🌱 成长级"
    else:
        custom_level = "🌿 新手级"

    md.append(f"| **创造力等级** | **{custom_level}** | 自定义水平 |\n")

    # 健康度概览 - 检查是否有健康度数据
    if data['health_data'] and sum(health_stats.values()) > 0:
        healthy_count = health_stats.get('优秀', 0) + health_stats.get('良好', 0)
        md.append(f"| **健康率** | **{healthy_count}/{total_skills}** ({healthy_count/total_skills*100:.0f}%) | 健康/良好Skills |\n")
    else:
        md.append(f"| **健康率** | **-** | 未运行健康度检查 |\n")

    md.append("\n---\n")

    # ============================================
    # 📈 可视化分析（增强版）
    # ============================================
    md.append("## 📈 可视化分析\n\n")

    # 类别分布 - 使用渐变样式
    categories = defaultdict(int)
    for skill in skills:
        cat = get_category_from_description(skill['description'])
        categories[cat] += 1

    cat_emoji = {"开发工作流": "⚙️", "文档写作": "✍️", "设计创意": "🎨", "项目管理": "📊", "数据处理": "🔧", "其他": "📦"}

    md.append("### 📂 类别分布\n\n")
    max_cat = max(categories.values()) if categories else 1
    for cat in sorted(categories.keys(), key=lambda x: categories[x], reverse=True):
        count = categories[cat]
        pct = count / total_skills * 100
        emoji = cat_emoji.get(cat, "📌")
        bar_length = int((count / max_cat) * 40)
        # 使用渐变字符
        gradient_chars = "█▓▒░"
        full_blocks = bar_length // 4
        partial = bar_length % 4
        bar = "█" * full_blocks
        if partial > 0:
            bar += gradient_chars[4-partial]
        bar += "░" * (40 - bar_length)
        md.append(f"{emoji} **{cat:12}** │{bar}│ **{count}** ({pct:.1f}%)\n")

    # 添加迷你图
    cat_values = [categories[cat] for cat in sorted(categories.keys(), key=lambda x: categories[x], reverse=True)]
    md.append(f"\n**趋势**: {create_sparkline(cat_values, width=15)}\n\n")

    # 空间占用TOP10 - 增强版
    md.append("### 💾 空间占用 TOP 10\n\n")
    top_size = sorted(skills, key=lambda x: x['size_mb'], reverse=True)[:10]
    max_size = top_size[0]['size_mb'] if top_size else 1

    md.append("| 排名 | Skill名称 | 大占用 | 可视化 | 占比 |\n")
    md.append("|------|----------|--------|--------|------|\n")

    for i, skill in enumerate(top_size, 1):
        name = skill['name'][:20]
        size = skill['size_mb']
        size_pct = (size / total_size * 100) if total_size > 0 else 0
        bar_length = int((size / max_size) * 25)

        # 根据大小使用不同颜色
        if size > 10:
            color_bar = "🔴" + "█" * bar_length
        elif size > 5:
            color_bar = "🟡" + "█" * bar_length
        else:
            color_bar = "🟢" + "█" * bar_length

        md.append(f"| **{i:2}** | **{name}** | {format_size(size)} | {color_bar[:25]} | {size_pct:.1f}% |\n")

    md.append(f"\n**总占用**: {format_size(total_size)} | **平均占用**: {format_size(total_size/total_skills)}\n\n")

    # 来源分布 - 增强版
    sources = defaultdict(int)
    for skill in skills:
        source = get_source_from_github(skill.get('github_url', ''))
        sources[source] += 1

    md.append("### 🏪 来源分布\n\n")
    max_source = max(sources.values()) if sources else 1

    md.append("| 来源 | 数量 | 占比 | 可视化 |\n")
    md.append("|------|------|------|--------|\n")

    for source in sorted(sources.keys(), key=lambda x: sources[x], reverse=True):
        count = sources[source]
        pct = count / total_skills * 100
        bar_length = int((count / max_source) * 30)
        bar = "█" * bar_length + "░" * (30 - bar_length)
        md.append(f"| **{source}** | **{count}** | {pct:.1f}% │{bar}│\n")

    md.append("\n---\n")

    # ============================================
    # 🏥 健康度分析（增强版）
    # ============================================
    md.append("## 🏥 健康度分析\n\n")

    # 检查是否真的有健康度数据（通过检查总和是否大于0）
    has_health_data = data['health_data'] and sum(health_stats.values()) > 0

    if has_health_data:
        total_health = sum(health_stats.values())

        md.append("### 📊 健康度分布\n\n")
        md.append("| 等级 | 徽章 | 数量 | 占比 | 可视化 | 评分 |\n")
        md.append("|------|------|------|------|--------|------|\n")

        grades_data = [
            ("优秀", "🏆", health_stats['优秀'], "green", "90-100"),
            ("良好", "👍", health_stats['良好'], "blue", "75-89"),
            ("及格", "😐", health_stats['及格'], "yellow", "60-74"),
            ("需改进", "⚠️", health_stats['需改进'], "red", "0-59")
        ]

        for grade, icon, count, color, score_range in grades_data:
            pct = count / total_health * 100
            bar_length = int(pct / 100 * 30)
            bar = "█" * bar_length + "░" * (30 - bar_length)
            md.append(f"| {grade} | {icon} | **{count}** | {pct:.1f}% │{bar}│ {score_range}分 |\n")

        md.append("\n")

        # 健康度进度条（增强版）
        md.append("### 🎯 整体健康度\n\n")
        healthy_pct = (health_stats['优秀'] + health_stats['良好']) / total_health * 100

        # 添加健康度评级
        if healthy_pct >= 80:
            health_grade = "🏆 优秀"
        elif healthy_pct >= 60:
            health_grade = "👍 良好"
        elif healthy_pct >= 40:
            health_grade = "😐 及格"
        else:
            health_grade = "⚠️ 需改进"

        md.append(f"**健康率**: {health_grade} {create_progress_bar(healthy_pct)}\n\n")

        # 添加健康度趋势迷你图
        health_values = [health_stats['优秀'], health_stats['良好'], health_stats['及格'], health_stats['需改进']]
        md.append(f"**分布**: {create_sparkline(health_values, width=20)} (优秀→需改进)\n\n")
    else:
        md.append("> ⚠️ **未运行健康度检查**\n\n")
        md.append("_请运行以下命令获取健康度数据：_\n\n")
        md.append("```bash\n")
        md.append("cd skill-health/scripts && python skill_health.py\n")
        md.append("```\n\n")

    # 需要关注的Skills
    if has_health_data:
        need_attention = [h for h in data['health_data'] if h['overall_status'] != 'ok']

        if need_attention:
            md.append("### ⚠️ 需要关注的 Skills\n\n")
            md.append(f"以下 {len(need_attention)} 个Skills存在健康问题：\n\n")

            # 按评分排序，显示最需要关注的前10个
            sorted_issues = sorted(need_attention, key=lambda x: x['health_score']['score'])[:10]

            for i, h in enumerate(sorted_issues, 1):
                name = h['name']
                score = h['health_score']['score']
                grade = h['health_score']['grade']

                # 收集所有问题
                issue_list = []

                # 文件检查问题
                if h['file_check'].get('issue'):
                    issue_list.append(h['file_check']['issue'])
                if h['file_check'].get('exceeds_limit'):
                    issue_list.append(f"文件过长({h['file_check']['line_count']}行)")

                # 结构检查问题
                if h['structure_check'].get('issues'):
                    issue_list.extend(h['structure_check']['issues'])
                if h['structure_check'].get('missing_recommended'):
                    missing = h['structure_check']['missing_recommended']
                    if missing:
                        issue_list.append(f"缺少推荐文件: {', '.join(missing)}")

                # 元数据检查问题
                if h.get('metadata_check', {}).get('issues'):
                    issue_list.extend(h['metadata_check']['issues'][:2])

                # 触发器检查问题
                if h.get('triggers_check', {}).get('issues'):
                    issue_list.extend(h['triggers_check']['issues'][:2])

                # 扣分原因
                if h['health_score'].get('deductions'):
                    issue_list.extend(h['health_score']['deductions'][:2])

                # 如果还没有问题，显示默认信息
                if not issue_list:
                    issue_list.append("需要进一步检查")

                issues = '; '.join(issue_list[:3])
                if len(issue_list) > 3:
                    issues += ' 等'

                md.append(f"{i:2}. **{name}** - {score}分 ({grade})\n")
                md.append(f"    _问题: {issues}_\n")
        else:
            md.append("### ✅ 健康状况良好\n\n")
            md.append("_所有Skills健康度良好，无需关注_\n")

        md.append("\n")

    md.append("---\n")

    # ============================================
    # 🎨 创新力分析（增强版）
    # ============================================
    md.append("## 🎨 创新力分析\n\n")

    # 检查是否真的有所有权配置数据
    has_ownership_data = data['ownership_config'] is not None

    if has_ownership_data:
        total_own = sum(ownership_stats.values())

        md.append("### 📊 所有权分布\n\n")
        md.append("| 类型 | 图标 | 数量 | 占比 | 可视化 |\n")
        md.append("|------|------|------|------|--------|\n")

        # 所有权条形图
        max_own = max(ownership_stats.values()) if ownership_stats else 1

        own_data = [
            ('Original', '🎨', '原创', 'pink'),
            ('Modified', '🔧', '魔改', 'purple'),
            ('Native', '📦', '原生', 'gray')
        ]

        for label, icon, name, color in own_data:
            count = ownership_stats[label]
            pct = count / total_own * 100
            bar_length = int((count / max_own) * 30)
            bar = "█" * bar_length + "░" * (30 - bar_length)
            md.append(f"| {name} | {icon} | **{count}** | {pct:.1f}% │{bar}│\n")

        md.append("\n")

        # 自定义度评分（增强版）
        md.append("### 🌟 自定义度评分\n\n")
        md.append(f"| 指标 | 数值 | 可视化 | 等级 |\n")
        md.append(f"|------|------|--------|------|\n")

        # 完全原创
        original_pct = (ownership_stats['Original'] / total_own * 100) if total_own > 0 else 0
        bar_length = int(original_pct / 100 * 20)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        md.append(f"| **完全原创** | {ownership_stats['Original']} 个 │{bar}│ 🏆 大师 |\n")

        # 经过魔改
        modified_pct = (ownership_stats['Modified'] / total_own * 100) if total_own > 0 else 0
        bar_length = int(modified_pct / 100 * 20)
        bar = "▓" * bar_length + "░" * (20 - bar_length)
        md.append(f"| **经过魔改** | {ownership_stats['Modified']} 个 │{bar}│ 🔧 进阶 |\n")

        # 保持原生
        native_pct = (ownership_stats['Native'] / total_own * 100) if total_own > 0 else 0
        bar_length = int(native_pct / 100 * 20)
        bar = "░" * 20
        md.append(f"| **保持原生** | {ownership_stats['Native']} 个 │{bar}│ 🌿 基础 |\n")

        md.append(f"| **平均自定义度** | **{avg_custom:.1f}%** │{create_progress_bar(avg_custom, width=15)}│ |\n")

        md.append("\n")

        # 创造力等级（增强版）
        md.append("### 🏆 创造力等级\n\n")

        # 根据自定义度给评级
        if avg_custom >= 70:
            md.append(create_info_box(
                "🏆 大师级 (70%+)",
                "你是Skill创造大师！拥有大量原创内容，建立了自己的Skill生态系统。",
                "success"
            ))
        elif avg_custom >= 40:
            md.append(create_info_box(
                "🔥 进阶级 (40-70%)",
                "正在培养自己的Skill生态，有一定数量的魔改和原创内容。",
                "info"
            ))
        elif avg_custom >= 20:
            md.append(create_info_box(
                "🌱 成长级 (20-40%)",
                "开始尝试自定义，探索Skill的魔改和创作。",
                "tip"
            ))
        else:
            md.append(create_info_box(
                "🌿 新手级 (0-20%)",
                "大量使用原生Skills，建议尝试魔改常用Skills或创建原创内容。",
                "warning"
            ))

        # 添加自定义度趋势
        custom_values = [ownership_stats['Original'] * 100, ownership_stats['Modified'] * 50, ownership_stats['Native'] * 0]
        md.append(f"\n**创新趋势**: {create_sparkline(custom_values, width=25)} (原创→魔改→原生)\n\n")
        md.append(f"| **完全原创** | {ownership_stats['Original']} 个 (100%自定义) |\n")
        md.append(f"| **经过魔改** | {ownership_stats['Modified']} 个 (1-99%自定义) |\n")
        md.append(f"| **保持原生** | {ownership_stats['Native']} 个 (0%自定义) |\n")
        md.append(f"| **平均自定义度** | **{avg_custom:.1f}%** |\n")
        md.append("\n")

        # 评分等级
        md.append("**创造力等级**: ")
        if avg_custom >= 70:
            md.append("🏆 **大师级** (70%+) - 你是Skill创造大师！\n")
        elif avg_custom >= 40:
            md.append("🔥 **进阶级** (40-70%) - 正在培养自己的Skill生态\n")
        elif avg_custom >= 20:
            md.append("🌱 **成长级** (20-40%) - 开始尝试自定义\n")
        else:
            md.append("🌿 **新手级** (0-20%) - 大量使用原生Skills\n")

        md.append("\n")
    else:
        md.append("> ⚠️ **未配置所有权信息**\n\n")
        md.append("_请运行以下命令配置所有权：_\n\n")
        md.append("```bash\n")
        md.append("cd skill-innovation/scripts && python skill_innovation.py\n")
        md.append("```\n\n")

    md.append("---\n")

    # ============================================
    # 🔄 版本更新状态
    # ============================================
    md.append("## 🔄 版本更新状态\n\n")

    if data['version_check'] and len(data['version_check']) > 0:
        updates_available = sum(1 for v in data['version_check'] if v.get('update_info', {}).get('available', False))
        high_priority = sum(1 for v in data['version_check'] if v.get('update_info', {}).get('priority') == '高')
        medium_priority = sum(1 for v in data['version_check'] if v.get('update_info', {}).get('priority') == '中')

        md.append("### 📊 更新统计\n\n")
        md.append(f"| 状态 | 数量 |\n")
        md.append(f"|------|------|\n")
        md.append(f"| ✅ 已是最新 | {len(data['version_check']) - updates_available} 个 |\n")
        md.append(f"| 🔄 可更新 | {updates_available} 个 |\n")
        md.append(f"|   - 🔴 高优先级 | {high_priority} 个 |\n")
        md.append(f"|   - 🟡 中优先级 | {medium_priority} 个 |\n")
        md.append("\n")

        # 需要更新的Skills
        if updates_available > 0:
            md.append("### ⚠️ 建议更新的 Skills\n\n")

            updates = [v for v in data['version_check'] if v.get('update_info', {}).get('available', False)]

            # 排序：按优先级（高>中>低），然后按原始顺序
            priority_order = {'高': 0, '中': 1, '低': 2}
            updates = sorted(updates, key=lambda x: priority_order.get(x.get('update_info', {}).get('priority', '低'), 3))

            for v in updates[:10]:
                name = v['name']
                priority = v.get('update_info', {}).get('priority', '低')
                priority_emoji = {'高': '🔴', '中': '🟡', '低': '🟢'}.get(priority, '⚪')
                reasons = v.get('update_info', {}).get('reason', [])
                reason_str = reasons[0] if reasons else ''

                md.append(f"- {priority_emoji} **{name}** - {priority}优先级 ({reason_str})\n")

            if len(updates) > 10:
                md.append(f"\n_... 还有 {len(updates) - 10} 个Skills可更新_\n")

        else:
            md.append("### ✅ 所有Skills都是最新版本\n\n")
    else:
        md.append("> ⚠️ **未运行版本检查**\n\n")
        md.append("_版本检查功能暂未实现，请关注后续更新_\n\n")

    md.append("---\n")

    # ============================================
    # 💡 快速建议
    # ============================================
    md.append("## 💡 快速建议\n\n")

    suggestions = []

    # 基于数据完整性的建议
    missing_checks = []
    if not data['health_data'] or sum(health_stats.values()) == 0:
        missing_checks.append('健康度检查')
    if not data['ownership_config']:
        missing_checks.append('创新力分析')

    if missing_checks:
        suggestions.append({
            'type': '数据完整性',
            'priority': '中',
            'text': f'缺少 {", ".join(missing_checks)} 数据，建议运行相应子技能获取完整信息'
        })

    # 基于健康度的建议
    has_health_data = data['health_data'] and sum(health_stats.values()) > 0
    if has_health_data:
        needs_improvement = health_stats.get('需改进', 0)
        pass_count = health_stats.get('及格', 0)
        if needs_improvement > 0:
            suggestions.append({
                'type': '健康度',
                'priority': '高' if needs_improvement > 3 else '中',
                'text': f'有 {needs_improvement} 个Skills健康度需改进（{pass_count}个及格），建议查看详情'
            })

    # 基于自定义度的建议
    if avg_custom < 20:
        suggestions.append({
            'type': '创新',
            'priority': '中',
            'text': f'自定义度仅 {avg_custom:.1f}%，建议尝试魔改常用Skills或创建原创Skill'
        })

    # 空间占用建议
    large_skills = [s for s in skills if s['size_mb'] > 10]
    if len(large_skills) > 0:
        total_large = sum(s['size_mb'] for s in large_skills)
        suggestions.append({
            'type': '空间',
            'priority': '低',
            'text': f'有 {len(large_skills)} 个Skills占用超过10MB（共 {format_size(total_large)}），可考虑清理不常用的大型技能'
        })

    # GitHub覆盖率建议
    github_coverage = with_github / total_skills * 100 if total_skills > 0 else 0
    if github_coverage < 100:
        missing_github = total_skills - with_github
        suggestions.append({
            'type': '来源',
            'priority': '低',
            'text': f'有 {missing_github} 个Skills缺少GitHub来源（覆盖率 {github_coverage:.0f}%），建议补充来源信息'
        })

    # 添加通用建议
    suggestions.append({
        'type': '定期',
        'priority': '低',
        'text': '建议每周运行一次完整分析，保持Skills在最佳状态'
    })

    # 按优先级排序建议
    priority_order = {'高': 0, '中': 1, '低': 2}
    suggestions.sort(key=lambda x: priority_order.get(x['priority'], 3))

    if suggestions:
        # 按优先级分组显示
        high_priority = [s for s in suggestions if s['priority'] == '高']
        medium_priority = [s for s in suggestions if s['priority'] == '中']
        low_priority = [s for s in suggestions if s['priority'] == '低']

        # 高优先级建议
        if high_priority:
            md.append("### 🔴 高优先级\n\n")
            for sugg in high_priority:
                md.append(create_info_box(sugg['type'], sugg['text'], "error"))

        # 中优先级建议
        if medium_priority:
            md.append("### 🟡 中优先级\n\n")
            for sugg in medium_priority:
                md.append(create_info_box(sugg['type'], sugg['text'], "warning"))

        # 低优先级建议
        if low_priority:
            md.append("### 🟢 低优先级\n\n")
            for sugg in low_priority:
                md.append(create_info_box(sugg['type'], sugg['text'], "tip"))

    md.append("\n---\n")

    # ============================================
    # 📖 使用说明
    # ============================================
    md.append("## 📖 使用说明\n\n")

    md.append("### 🔄 更新报告\n\n")
    md.append("```bash\n# 运行所有子技能（从 skill-hud 目录）\n")
    md.append("cd skills/skill-match/scripts && python skill_match.py\n")
    md.append("cd ../../skill-health/scripts && python skill_health.py\n")
    md.append("cd ../../skill-innovation/scripts && python skill_innovation.py\n")
    md.append("\n# 生成综合仪表板\n")
    md.append("cd ../../../scripts && python hud_dashboard.py\n")
    md.append("```\n\n")

    md.append("### 📂 报告文件\n\n")
    md.append("| 报告 | 文件 | 说明 |\n")
    md.append("|------|------|------|\n")
    md.append("| 综合仪表板 | `SKILLS_综合分析_最新.md` | 本报告（主入口） |\n")
    md.append("| 驾驶舱报告 | `SKILLS_驾驶舱_最新.md` | 可视化概览（skill-health） |\n")
    md.append("| 健康度报告 | `SKILLS_健康度_最新.md` | 健康详情（skill-health） |\n")
    md.append("| 创新指导 | `SKILLS_创新指导_最新.md` | 所有权与创新（skill-innovation） |\n")
    md.append("\n")

    md.append("---\n")
    md.append(f"\n*📅 报告生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    md.append("\n*💡 提示: 这是一个综合仪表板，整合了所有子技能的数据*")

    # 保存报告
    reports_dir = os.path.join(SCRIPT_DIR, '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")

    # 检查同一天的现有报告，自动递增版本号
    import re
    existing_files = []
    for f in os.listdir(reports_dir):
        if f.startswith(f'SKILLS_综合分析_v') and f.endswith(f'_{date_str}.md'):
            match = re.search(r'_v(\d+)\.(\d+)\.(\d+)_', f)
            if match:
                major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
                existing_files.append((major, minor, patch, f))

    # 确定版本号
    if existing_files:
        # 按版本号排序，取最新的，然后递增minor版本
        existing_files.sort(reverse=True)
        major, minor, patch = existing_files[0][:3]
        new_version = f"{major}.{minor + 1}.0"
        print(f"[INFO] 检测到同日报告，版本号自动递增: v{major}.{minor}.{patch} -> v{new_version}")
    else:
        new_version = VERSION

    filename = f'SKILLS_综合分析_v{new_version}_{date_str}.md'
    output_path = os.path.join(reports_dir, filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(md)

    # 同时生成默认名称
    default_path = os.path.join(reports_dir, 'SKILLS_综合分析_最新.md')
    with open(default_path, 'w', encoding='utf-8') as f:
        f.writelines(md)

    print(f"[OK] 综合仪表板已生成: {output_path}")
    print(f"[STAT] 总Skills: {total_skills}")
    # 计算健康率用于统计显示
    if data['health_data'] and sum(health_stats.values()) > 0:
        healthy_count = health_stats.get('优秀', 0) + health_stats.get('良好', 0)
        print(f"[STAT] 健康率: {(healthy_count/total_skills*100):.1f}%")
    else:
        print(f"[STAT] 健康率: - (未运行)")
    print(f"[STAT] 自定义度: {avg_custom:.1f}%")
    print(f"\n下一步:")
    print(f"  1. 查看综合仪表板了解全貌")
    print(f"  2. 根据建议优化Skills")
    print(f"  3. 定期运行保持更新")

    return output_path


def run_subskill_match():
    """运行 skill-match 数据收集"""
    print("\n" + "=" * 60)
    print("[1/4] 运行 Skill-Match 数据收集...")
    print("=" * 60)
    try:
        # 优先使用支持 data_source 的 v3 版本
        script_path_v3 = os.path.join(SKILLS_BASE_DIR, 'skill-match', 'scripts', 'skill_match_v3_optimized.py')
        script_path = os.path.join(SKILLS_BASE_DIR, 'skill-match', 'scripts', 'skill_match.py')

        # 检查 v3 版本是否存在
        if os.path.exists(script_path_v3):
            script_path = script_path_v3
            print("[INFO] 使用 skill_match_v3_optimized.py (支持 API 限流检测)")
        else:
            print("[INFO] 使用 skill_match.py")

        # stdin 自动检测已在子技能中实现，无需手动输入
        result = subprocess.run([sys.executable, script_path],
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace')  # 处理编码错误
        # 安全地打印输出（处理 Windows GBK 编码问题）
        try:
            print(result.stdout)
        except UnicodeEncodeError:
            print("[输出包含特殊字符，已省略详细信息]")
        if result.returncode != 0:
            try:
                print(result.stderr)
            except UnicodeEncodeError:
                print("[错误输出包含特殊字符]")
            return False
        return True
    except Exception as e:
        print(f"[错误] Skill-Match 运行失败: {e}")
        return False


def run_subskill_health():
    """运行 skill-health 健康度检查"""
    print("\n" + "=" * 60)
    print("[2/4] 运行 Skill-Health 健康度检查...")
    print("=" * 60)
    try:
        script_path = os.path.join(SKILLS_BASE_DIR, 'skill-health', 'scripts', 'skill_health.py')
        # stdin 自动检测已在子技能中实现，无需手动输入
        result = subprocess.run([sys.executable, script_path],
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace')  # 处理编码错误
        # 安全地打印输出（处理 Windows GBK 编码问题）
        try:
            print(result.stdout)
        except UnicodeEncodeError:
            print("[输出包含特殊字符，已省略详细信息]")
        if result.returncode != 0:
            try:
                print(result.stderr)
            except UnicodeEncodeError:
                print("[错误输出包含特殊字符]")
            return False
        return True
    except Exception as e:
        print(f"[错误] Skill-Health 运行失败: {e}")
        return False


def run_subskill_innovation():
    """运行 skill-innovation 创新指导"""
    print("\n" + "=" * 60)
    print("[3/4] 运行 Skill-Innovation 创新指导...")
    print("=" * 60)
    try:
        script_path = os.path.join(SKILLS_BASE_DIR, 'skill-innovation', 'scripts', 'skill_innovation.py')
        result = subprocess.run([sys.executable, script_path],
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace')  # 处理编码错误
        # 安全地打印输出（处理 Windows GBK 编码问题）
        try:
            print(result.stdout)
        except UnicodeEncodeError:
            print("[输出包含特殊字符，已省略详细信息]")
        if result.returncode != 0:
            try:
                print(result.stderr)
            except UnicodeEncodeError:
                print("[错误输出包含特殊字符]")
            return False
        return True
    except Exception as e:
        print(f"[错误] Skill-Innovation 运行失败: {e}")
        return False


def main():
    """主执行函数"""
    print("\n" + "=" * 60)
    print("       Skill-HUD 综合仪表板")
    print("       整合所有子技能数据")
    print("=" * 60)

    # 依次运行子技能
    results = {
        'match': run_subskill_match(),
        'health': run_subskill_health(),
        'innovation': run_subskill_innovation()
    }

    # 生成综合仪表板
    print("\n" + "=" * 60)
    print("[4/4] 生成综合仪表板报告...")
    print("=" * 60)

    try:
        report_path = generate_hud_dashboard()
        print(f"\n[OK] 综合仪表板已生成: {report_path}")

        # 显示运行结果摘要
        print("\n" + "=" * 60)
        print("运行结果摘要:")
        print("=" * 60)
        print(f"  Skill-Match:      {'[OK] 成功' if results['match'] else '[X] 失败'}")
        print(f"  Skill-Health:     {'[OK] 成功' if results['health'] else '[X] 失败'}")
        print(f"  Skill-Innovation: {'[OK] 成功' if results['innovation'] else '[X] 失败'}")
        print(f"  Skill-HUD:        [OK] 成功")
        print("=" * 60)

    except Exception as e:
        print(f"[错误] 综合仪表板生成失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
