#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill-Innovation v3.0 备份 - 多因子评分系统

备份日期: 2026-01-24
备份原因: 用于与 v2.0 Genealogy Analysis 逻辑对比效果

核心逻辑:
- 不依赖白名单
- 官方特征评分 (triggers, Use when, 版本号等)
- 原创特征评分 (中文内容, 复杂 scripts, 自定义目录等)
- 判定规则: 官方分数 >= 60 → 原生, 原创分数 >= 50 → 原创
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ============================================
# 多因子评分系统 v3.0 - 不依赖白名单
# ============================================

def calculate_official_score_v3(skill_path, metadata, structure):
    """
    计算技能的官方特征评分（0-100）

    官方技能特征：
    - 有 triggers 字段（官方技能都有） +20分
    - 描述包含 "Use when"、"Use this tool when" +25分
    - 版本号符合 x.y.z 格式 +10分
    - 没有 scripts/ 目录或 scripts/ 为空 +10分
    - SKILL.md 行数适中（50-200） +10分
    - 没有 references/ 或其他自定义目录 +15分
    - 描述包含 "Available skills" 列表 +10分
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
        if re.match(r'^v?\d+\.\d+\.\d+', str(version)):
            score += 10

    # 4. 目录结构检查 (+25分)
    if not structure.get('has_scripts'):
        score += 10
    elif structure.get('scripts_file_count', 0) == 0:
        score += 5

    if not structure.get('has_references'):
        score += 8
    if not structure.get('has_readme'):
        score += 7

    # 5. 文档长度检查 (+10分)
    skill_lines = content.count('\n')
    if 50 <= skill_lines <= 200:
        score += 10
    elif 30 <= skill_lines < 50 or 200 < skill_lines <= 300:
        score += 5

    # 6. 官方特征标记 (+10分)
    official_markers = [
        'claude code', 'anthropic', 'superpowers:',
        'skill tool', 'task tool', 'mcp server',
        'use the', 'instead of',
    ]

    marker_count = sum(1 for marker in official_markers if marker in content_lower)
    if marker_count >= 4:
        score += 10
    elif marker_count >= 2:
        score += 5

    return min(100, score)


def calculate_original_score_v3(skill_path, metadata, structure, git_info=None, current_user=None):
    """
    计算技能的原创特征评分（0-100）

    原创技能特征：
    - 描述包含中文、个性化说明 +30分
    - 有复杂的 scripts/ 目录（有 .py 文件） +25分
    - SKILL.md 行数 > 200 +10分
    - 有 references/ 或其他自定义目录 +20分
    - Git 仓库属于用户（非 anthropics） +15分
    - 有配置文件（如 ownership_config.json） +10分
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
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
    total_chars = len(content)
    if total_chars > 0:
        chinese_ratio = chinese_chars / total_chars
        if chinese_ratio > 0.15:
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
        if remote_url and current_user:
            if 'anthropic' not in remote_url.lower():
                if current_user.lower() in remote_url.lower():
                    score += 15
                else:
                    score += 10

    # 6. 个性化特征检查 (+10分)
    config_files = ['ownership_config.json', 'config.json', 'settings.json']
    for config_file in config_files:
        if os.path.exists(os.path.join(skill_path, config_file)):
            score += 10
            break

    if not metadata or not metadata.get('triggers'):
        score += 5
    elif isinstance(metadata.get('triggers'), list) and len(metadata['triggers']) <= 1:
        score += 3

    personal_markers = ['作者', 'author', '版权', 'copyright', 'license', '许可']
    if any(marker in content_lower for marker in personal_markers):
        score += 5

    return min(100, score)


def classify_by_score_v3(skill_path, metadata, structure, git_info=None, current_user=None):
    """
    基于多因子评分分类技能 (v3.0)

    返回 (type, emoji, label, detection_method, reasons, confidence)
    """
    official_score = calculate_official_score_v3(skill_path, metadata, structure)
    original_score = calculate_original_score_v3(skill_path, metadata, structure, git_info, current_user)

    # 判定规则
    # 官方分数 >= 60 -> 原生
    # 原创分数 >= 50 -> 原创
    # 两者都不满足 -> 魔改

    if official_score >= 60:
        reasons = [f'官方特征评分: {official_score}/100', f'原创特征评分: {original_score}/100']
        confidence = 'high' if official_score >= 80 else 'medium'
        return '原生', '📦', 'Native', 'score_based_classification_v3', reasons, confidence, (official_score, original_score)
    elif original_score >= 50:
        reasons = [f'原创特征评分: {original_score}/100', f'官方特征评分: {official_score}/100']
        confidence = 'high' if original_score >= 70 else 'medium'
        return '原创', '🎨', 'Original', 'score_based_classification_v3', reasons, confidence, (official_score, original_score)
    else:
        if git_info and git_info.get('is_dirty'):
            reasons = [f'工作区有修改', f'官方特征评分: {official_score}/100', f'原创特征评分: {original_score}/100']
            return '魔改', '🔧', 'Modified', 'score_based_classification_v3', reasons, 'low', (official_score, original_score)
        else:
            reasons = [f'默认判定为原生', f'官方特征评分: {official_score}/100', f'原创特征评分: {original_score}/100']
            return '原生', '📦', 'Native', 'score_based_classification_v3', reasons, 'low', (official_score, original_score)


# 导出函数列表
__all__ = [
    'calculate_official_score_v3',
    'calculate_original_score_v3',
    'classify_by_score_v3',
]
