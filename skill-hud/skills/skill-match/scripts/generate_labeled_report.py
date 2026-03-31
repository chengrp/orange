#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skills GitHub 匹配评估报告 (生成 Markdown 格式报告)

基于现有配置文件生成带标注的报告：
1. 高质量仓库 (Stars > 1000) 用 ⭐ 标注
2. 重度使用 skills 用 🔥 标注
3. 用户行为数据分析（最常用skill）
4. 可视化图表（ASCII字符绘制）
5. 保存为 Markdown 文件
"""

import os
import sys
import json
import glob
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

# Windows 编码修复
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

# ============================================
# 配置
# ============================================
SKILLS_BASE_PATH = os.path.expanduser("~/.claude/skills")
CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'config')
REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')
USER_GITHUB_MAP_PATH = os.path.join(CONFIG_DIR, 'user_github_map.json')
HIGH_QUALITY_STARS = 1000
HEAVY_USE_DAYS = 30
HEAVY_USE_SIZE_MB = 1.0

# Skill 类别映射
SKILL_CATEGORIES = {
    # 开发工作流
    "executing-plans": "开发工作流",
    "finishing-a-development-branch": "开发工作流",
    "receiving-code-review": "开发工作流",
    "requesting-code-review": "开发工作流",
    "subagent-driven-development": "开发工作流",
    "systematic-debugging": "开发工作流",
    "test-driven-development": "开发工作流",
    "using-git-worktrees": "开发工作流",
    "verification-before-completion": "开发工作流",
    "writing-plans": "开发工作流",
    "writing-skills": "开发工作流",
    "webapp-testing": "开发工作流",
    "skill-creator": "开发工作流",

    # 设计创意
    "brainstorming": "设计创意",
    "image-assistant": "设计创意",
    "json-canvas": "设计创意",
    "mcp-builder": "设计创意",
    "ms-image": "设计创意",
    "n8n-skills": "设计创意",
    "obsidian-skills": "设计创意",
    "ppt-generator": "设计创意",
    "pptx": "设计创意",
    "superpowers": "设计创意",
    "ui-ux-pro-max-skill": "设计创意",
    "using-superpowers": "设计创意",

    # 文档写作
    "all-2md": "文档写作",
    "baoyu-skills": "文档写作",
    "document-illustrator": "文档写作",
    "Document-illustrator-skill": "文档写作",
    "prd-doc-writer": "文档写作",
    "prompt-copilot": "文档写作",
    "wechat-item": "文档写作",
    "wechat-writing": "文档写作",
    "x-article-publisher": "文档写作",

    # 项目管理
    "dispatching-parallel-agents": "项目管理",
    "planning-with-files": "项目管理",
    "req-change-workflow": "项目管理",
    "solution-creator": "项目管理",

    # 监控分析
    "sk-monitor": "监控分析",
    "skill-hud": "监控分析",

    # AI助手
    "notebooklm": "AI助手",
    "anthropic-skills": "AI助手",

    # 数据处理
    "obsidian-bases": "数据处理",
    "obsidian-markdown": "数据处理",
}

# ============================================
# 数据类定义
# ============================================
@dataclass
class SkillInfo:
    name: str
    path: str
    github_url: str
    source: str
    size_mb: float
    last_modified: str
    days_since_modified: int
    usage_frequency: str
    stars: int
    is_high_quality: bool = False
    is_custom: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================
# 工具函数
# ============================================
def get_dir_size(path: str) -> float:
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
    if mb < 0.01:
        return "很小"
    elif mb < 1:
        return f"{mb*1024:.0f}KB"
    elif mb < 1024:
        return f"{mb:.1f}MB"
    else:
        return f"{mb/1024:.1f}GB"


def format_age(days: int) -> str:
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
        return f"{days}天前"


def draw_bar_chart(value: int, max_value: int, width: int = 50) -> str:
    """绘制 ASCII 条形图"""
    if max_value == 0:
        return "░" * width
    filled = int((value / max_value) * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def get_skill_owner(github_url: str) -> str:
    """从 GitHub URL 获取作者/组织"""
    if not github_url or not github_url.startswith("https://"):
        return "❓ 未知"

    match = github_url.split("github.com/")
    if len(match) < 2:
        return "❓ 未知"

    owner = match[1].split("/")[0]

    # 映射常见作者/组织
    owner_map = {
        "anthropics": "🏢 Anthropic官方",
        "microsoft": "🔗 Microsoft",
        "obsidian-skills": "📝 Obsidian社区",
        "JimLiu": "✍️ 宝玉",
        "obra": "✨ 作者obra",
        "op7418": "🔗 社区贡献",
        "OthmanAdi": "🔗 社区贡献",
        "nextlevelbuilder": "🔗 社区贡献",
        "cursor-shadowsong": "👤 cursor-shadowsong",
        "System-Engineering-Prompt-Copilot": "🔗 社区贡献",
        "thought-mining": "🔗 社区贡献",
        "YaoYS2024": "🔗 社区贡献",
        "Nick-Armstrong": "🔗 社区贡献",
        "Claude-Code-Skills": "🔗 社区贡献",
        "dingfeihu2023": "🔗 社区贡献",
    }

    return owner_map.get(owner, f"🔗 社区贡献")


def get_skill_category(skill_name: str) -> str:
    """获取 Skill 类别"""
    return SKILL_CATEGORIES.get(skill_name, "📦 其他")


# ============================================
# 主函数
# ============================================
def main():
    print("\n" + "=" * 80)
    print(" " * 15 + "Skills GitHub 匹配评估报告")
    print("=" * 80)
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")

    # 加载用户配置
    user_map = {}
    if os.path.exists(USER_GITHUB_MAP_PATH):
        with open(USER_GITHUB_MAP_PATH, 'r', encoding='utf-8') as f:
            user_map = json.load(f)

    # 扫描 skills
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
            all_skills[skill_name] = os.path.dirname(skill_file_path)

    # 已知的高质量仓库 stars 数据
    known_stars = {
        "https://github.com/microsoft/markitdown": 85700,
        "https://github.com/JimLiu/baoyu-skills": 2401,
        "https://github.com/anthropics/claude-code": 60307,
        "https://github.com/OthmanAdi/planning-with-files": 11153,
        "https://github.com/op7418/NanoBanana-PPT-Skills": 942,
        "https://github.com/obra/superpowers": 35271,
        "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill": 22329,
        "https://github.com/yt-dlp/yt-dlp": 143911,
        "https://github.com/Nick-Armstrong/awesomeAgentskills": 500,
    }

    # 分析每个 skill
    skills_list = []
    for skill_name, skill_path in sorted(all_skills.items(), key=lambda x: x[0].lower()):
        # 获取基本信息
        try:
            modified_time = datetime.fromtimestamp(os.path.getmtime(skill_path))
            days_since = (datetime.now() - modified_time).days
            modified_iso = modified_time.isoformat()
        except:
            days_since = 999
            modified_iso = ""

        size_mb = get_dir_size(skill_path)

        # 使用频率
        if days_since < HEAVY_USE_DAYS and size_mb > HEAVY_USE_SIZE_MB:
            usage_freq = "heavy"
        elif days_since < HEAVY_USE_DAYS:
            usage_freq = "medium"
        elif days_since < 90:
            usage_freq = "low"
        else:
            usage_freq = "unknown"

        # GitHub 信息
        github_url = user_map.get(skill_name, "")
        source = "none"
        stars = 0
        is_custom = False
        is_high_quality = False

        if github_url:
            if github_url.startswith("自定义"):
                source = "custom"
                is_custom = True
            elif github_url.startswith("https://"):
                source = "user_config"
                stars = known_stars.get(github_url, 0)
                is_high_quality = stars >= HIGH_QUALITY_STARS
            else:
                source = "config"

        skills_list.append(SkillInfo(
            name=skill_name,
            path=skill_path,
            github_url=github_url,
            source=source,
            size_mb=size_mb,
            last_modified=modified_iso,
            days_since_modified=days_since,
            usage_frequency=usage_freq,
            stars=stars,
            is_high_quality=is_high_quality,
            is_custom=is_custom
        ))

    # 统计
    total = len(skills_list)
    has_github = sum(1 for s in skills_list if s.github_url and not s.is_custom)
    custom_skills = sum(1 for s in skills_list if s.is_custom)
    high_quality = sum(1 for s in skills_list if s.is_high_quality)
    heavy_use = sum(1 for s in skills_list if s.usage_frequency == "heavy")
    total_size = sum(s.size_mb for s in skills_list)

    # 打印统计到控制台
    print("📊 统计概览")
    print("-" * 80)
    print(f"  总 Skill 数:        {total}")
    print(f"  总占用空间:         {format_size(total_size)}")
    print(f"  有 GitHub 地址:     {has_github} ({has_github/total*100:.1f}%)")
    print(f"  🏠 自定义未发布:     {custom_skills}")
    print(f"  ⭐ 高质量仓库:      {high_quality} (>{HIGH_QUALITY_STARS} stars)")
    print(f"  🔥 重度使用:        {heavy_use} (最近{HEAVY_USE_DAYS}天修改 + >{HEAVY_USE_SIZE_MB}MB)")
    print()

    # 生成 Markdown 报告
    report_lines = []

    # 报告头部
    now = datetime.now()
    report_lines.append("# 🎯 Skills 溯源检查报告")
    report_lines.append(f"> 📅 **更新时间**: {now.strftime('%Y-%m-%d %H:%M')}")
    report_lines.append("---")
    report_lines.append("")

    # 核心指标
    report_lines.append("## 📊 核心指标")
    report_lines.append("")
    report_lines.append("| 🎯 指标 | 📈 数值 | 📝 说明 |")
    report_lines.append("|--------|--------|--------|")
    report_lines.append(f"| **总Skill数** | **{total}** 个 | 全部已安装的技能 |")
    report_lines.append(f"| **总占用空间** | **{format_size(total_size)}** | 磁盘占用 |")
    report_lines.append(f"| **GitHub来源** | **{has_github}** 个 ({has_github/total*100:.0f}%) | 有明确来源 |")
    report_lines.append(f"| **🏠 自定义未发布** | **{custom_skills}** 个 | 用户自己的 skill |")
    report_lines.append(f"| **⭐ 高质量仓库** | **{high_quality}** 个 | Stars > {HIGH_QUALITY_STARS} |")
    report_lines.append(f"| **🔥 重度使用** | **{heavy_use}** 个 | 最近{HEAVY_USE_DAYS}天修改 |")
    report_lines.append("")

    # 数据来源说明
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 📌 数据来源说明")
    report_lines.append("")

    # 检查是否有数据源问题（检查最近的评估报告）
    data_source_note = []
    try:
        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        latest_eval = sorted(glob.glob(os.path.join(reports_dir, 'skills_evaluation_v3_*.json')),
                           key=os.path.getmtime, reverse=True)
        if latest_eval:
            with open(latest_eval[0], 'r', encoding='utf-8') as f:
                eval_data = json.load(f)
                data_source_info = eval_data.get('data_source', {})
                if data_source_info.get('used_cache'):
                    data_source_note.append("⚠️ 部分数据来自缓存（非最新）")
                if data_source_info.get('rate_limit_hit'):
                    data_source_note.append("⚠️ 遇到了 GitHub API 限流")
    except:
        pass

    if data_source_note:
        report_lines.append("**当前数据状态：**")
        for note in data_source_note:
            report_lines.append(f"- {note}")
        report_lines.append("")
        report_lines.append("**建议：**")
        report_lines.append("- 设置 `GITHUB_TOKEN` 环境变量以提高 API 限额")
        report_lines.append("- 或稍后重新运行获取最新数据")
        report_lines.append("")
    else:
        report_lines.append("✅ 数据来源：GitHub API 实时获取")
        report_lines.append("")

    # 可视化分析
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 📈 可视化分析")
    report_lines.append("")

    # 空间占用 TOP 10
    report_lines.append("### 💾 空间占用 TOP 10")
    report_lines.append("")
    top_by_size = sorted(skills_list, key=lambda x: x.size_mb, reverse=True)[:10]
    max_size = top_by_size[0].size_mb
    for skill in top_by_size:
        name = skill.name[:15].ljust(15)
        bar = draw_bar_chart(skill.size_mb, max_size)

        icons = []
        if skill.usage_frequency == "heavy":
            icons.append("🔥")
        if skill.is_high_quality:
            icons.append("⭐")
        icon_prefix = "".join(icons) + " " if icons else ""

        report_lines.append(f"{icon_prefix}{name} │{bar}│ {format_size(skill.size_mb)}")
    report_lines.append("")

    # Skill 类别分布
    category_stats = defaultdict(int)
    for skill in skills_list:
        category = get_skill_category(skill.name)
        category_stats[category] += 1

    report_lines.append("### 📂 Skill类别分布")
    report_lines.append("")
    max_category = max(category_stats.values())
    for category, count in sorted(category_stats.items(), key=lambda x: -x[1]):
        percentage = count / total * 100
        bar = draw_bar_chart(count, max_category)
        report_lines.append(f"{category.ljust(20)} │{bar}│ {percentage:.1f}% ({count}个)")
    report_lines.append("")

    # GitHub 来源分布
    report_lines.append("### 🏪 Skill来源分布")
    report_lines.append("")
    owner_stats = defaultdict(int)
    for skill in skills_list:
        if skill.github_url and not skill.is_custom:
            owner = get_skill_owner(skill.github_url)
            owner_stats[owner] += 1
        elif skill.is_custom:
            owner_stats["👤 自定义未发布"] += 1
        else:
            owner_stats["❓ 未知"] += 1

    max_owner = max(owner_stats.values())
    for owner, count in sorted(owner_stats.items(), key=lambda x: -x[1]):
        bar = draw_bar_chart(count, max_owner)
        report_lines.append(f"{owner.ljust(20)} │{bar}│ {count}个")
    report_lines.append("")

    # 高质量仓库图表
    high_quality_skills = [s for s in skills_list if s.is_high_quality]
    if high_quality_skills:
        report_lines.append("### ⭐ 高质量Skill仓库")
        report_lines.append("")
        report_lines.append(f"*Stars > {HIGH_QUALITY_STARS}*")
        report_lines.append("")

        max_stars = max(s.stars for s in high_quality_skills)
        for skill in sorted(high_quality_skills, key=lambda x: x.stars, reverse=True):
            name = skill.name[:15].ljust(15)
            bar = draw_bar_chart(skill.stars, max_stars)

            icons = []
            if skill.usage_frequency == "heavy":
                icons.append("🔥")
            icon_prefix = "".join(icons) + " " if icons else ""

            report_lines.append(f"{icon_prefix}{name} │{bar}│ {skill.stars:,} stars")
        report_lines.append("")

    # 高质量仓库详细列表
    if high_quality_skills:
        report_lines.append("---")
        report_lines.append("")
        report_lines.append("## ⭐ 高质量仓库详情")
        report_lines.append("")
        report_lines.append(f"以下 {len(high_quality_skills)} 个仓库 Stars > {HIGH_QUALITY_STARS}:")
        report_lines.append("")

        for skill in sorted(high_quality_skills, key=lambda x: x.stars, reverse=True):
            icons = []
            if skill.usage_frequency == "heavy":
                icons.append("🔥")
            icon_prefix = " ".join(icons) + " " if icons else ""

            report_lines.append(f"- {icon_prefix}**[{skill.name}]({skill.github_url})**")
            report_lines.append(f"  - ⭐ Stars: {skill.stars:,}")
            report_lines.append(f"  - 💾 大小: {format_size(skill.size_mb)}")
            report_lines.append(f"  - 🕒 最近修改: {format_age(skill.days_since_modified)}")
            report_lines.append("")

    # 重度使用的 Skills - 已删除
    # 重度使用标注保留在可视化图表中

    # 未配置的 Skills
    report_lines.append("---")
    report_lines.append("")
    unmatched_skills = [s for s in skills_list if not s.github_url]
    if unmatched_skills:
        report_lines.append("## ⚠️ 未配置 GitHub 地址的 Skills")
        report_lines.append("")
        report_lines.append(f"以下 {len(unmatched_skills)} 个 Skills 没有 GitHub 地址:")
        report_lines.append("")

        for skill in unmatched_skills:
            report_lines.append(f"- **{skill.name}**")
            report_lines.append(f"  - 路径: `{skill.path}`")
            report_lines.append("")

    # 完整 Skill 清单（按类别分组）
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 📋 Skill清单")
    report_lines.append("")

    # 按类别分组
    category_groups = defaultdict(list)
    for skill in skills_list:
        category = get_skill_category(skill.name)
        category_groups[category].append(skill)

    for category in sorted(category_groups.keys()):
        skills = category_groups[category]
        report_lines.append(f"### {category} ({len(skills)}个)")
        report_lines.append("")
        report_lines.append("| Skill名称 | 大小 | 来源 | 最近修改 |")
        report_lines.append("|-----------|------|------|----------|")

        # 按使用频率排序
        sort_order = {"heavy": 0, "medium": 1, "low": 2, "unknown": 3}
        sorted_skills = sorted(skills, key=lambda x: (sort_order.get(x.usage_frequency, 3), x.name.lower()))

        for skill in sorted_skills:
            icons = []
            if skill.usage_frequency == "heavy":
                icons.append("🔥")
            if skill.is_high_quality:
                icons.append("⭐")
            if skill.is_custom:
                icons.append("🏠")
            icon_prefix = "".join(icons)

            name = f"{icon_prefix} **{skill.name}**" if icon_prefix else f"**{skill.name}**"

            if skill.github_url and skill.github_url.startswith("https://"):
                name = f"{icon_prefix} **[{skill.name}]({skill.github_url})**" if icon_prefix else f"**[{skill.name}]({skill.github_url})**"

            size = format_size(skill.size_mb)

            if skill.is_custom:
                source = "🏠 自定义"
            elif skill.github_url:
                source = get_skill_owner(skill.github_url)
            else:
                source = "❓ 未知"

            age = format_age(skill.days_since_modified)

            report_lines.append(f"| {name} | {size} | {source} | {age} |")

        report_lines.append("")

    # 报告尾部
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 💡 如何补充 GitHub 地址")
    report_lines.append("")
    report_lines.append("### 方法1: 编辑配置文件")
    report_lines.append("")
    report_lines.append(f'编辑 `{USER_GITHUB_MAP_PATH}` 文件：')
    report_lines.append("")
    report_lines.append("```json")
    report_lines.append('{')
    report_lines.append('  "your-skill-name": "https://github.com/username/repo"')
    report_lines.append('}')
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("### 方法2: 标记自定义 skill")
    report_lines.append("")
    report_lines.append("如果是自己的 skill（未发布），使用:")
    report_lines.append("")
    report_lines.append("```json")
    report_lines.append('{')
    report_lines.append('  "your-skill-name": "自定义skill，未发布"')
    report_lines.append('}')
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append(f"*📅 报告生成: {now.strftime('%Y-%m-%d %H:%M:%S')}* | **Skill-Match v2.0.0**")

    # 保存报告 - 版本号 + 日期（当日更新时递增 minor 版本号）
    os.makedirs(REPORTS_DIR, exist_ok=True)

    date_str = now.strftime('%Y-%m-%d')
    # 查找当日的所有报告（使用 os.listdir 避免中文编码问题）
    try:
        all_reports = []
        for filename in os.listdir(REPORTS_DIR):
            if filename.startswith('skills溯源检查报告_v') and f'_{date_str}' in filename and filename.endswith('.md'):
                all_reports.append(os.path.join(REPORTS_DIR, filename))
    except Exception:
        all_reports = []

    # 过滤出符合新格式的报告（排除 _最新.md 和 _数字.md）
    existing_reports = []
    for report in all_reports:
        filename = os.path.basename(report)
        # 严格匹配：必须以 _{date_str}.md 结尾，不能有额外后缀
        if filename.endswith(f"_{date_str}.md") and not filename.endswith(f"_{date_str}_最新.md") and not re.search(rf"_{date_str}_\d+\.md$", filename):
            existing_reports.append(report)

    # 提取现有报告的版本号，找到最大的 minor 版本
    max_minor = 0
    for report in existing_reports:
        # 从文件名提取版本号，格式: skills溯源检查报告_v{major}.{minor}.{patch}_{date}.md
        filename = os.path.basename(report)
        try:
            version_part = filename.split("_v")[1].split(f"_{date_str}")[0]
            parts = version_part.split(".")
            if len(parts) >= 2 and parts[0] == "2":
                minor = int(parts[1])
                if minor > max_minor:
                    max_minor = minor
        except:
            pass

    # 递增 minor 版本号
    next_minor = max_minor + 1
    report_file = os.path.join(REPORTS_DIR, f"skills溯源检查报告_v2.{next_minor}.0_{date_str}.md")

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    print("=" * 80)
    print(f"✅ 报告已生成: {report_file}")
    print("=" * 80)

    # 同时打印到控制台
    print("\n" + "=" * 80)
    print("⭐ 高质量仓库")
    print("=" * 80)
    for skill in sorted(high_quality_skills, key=lambda x: x.stars, reverse=True):
        heavy_icon = "🔥 " if skill.usage_frequency == "heavy" else ""
        print(f"  {heavy_icon}**{skill.name}** - {skill.stars:,} stars")
    print()


if __name__ == '__main__':
    main()
