#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地 Skills GitHub 匹配评估工具 (增强版)

新增功能：
1. 子目录 skill 可参照父目录配置
2. 用户自己的未发布 skills 直接标注"自定义skill，未发布"
3. 自动检测并提示继承父目录配置
"""

import os
import sys
import json
import re
import glob
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# 导入修复版的相关类
sys.path.insert(0, os.path.dirname(__file__))
from skill_match_v2_fixed import (
    ConfigManager,
    MatchHistoryManager,
    RepoQualityAssessor,
    extract_github_url,
    SIMILARITY_THRESHOLDS,
    CONFIDENCE_LEVEL,
    CACHE_DIR,
    CONFIG_DIR,
    USER_GITHUB_MAP_PATH,
    SKILLS_BASE_PATH,
)

# ============================================
# 日志配置
# ============================================
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================
# 数据类定义
# ============================================
@dataclass
class SkillMatchInfo:
    """Skill 匹配信息"""
    name: str
    path: str
    has_github: bool
    github_url: str
    match_source: str  # user_config / inherited / readme / none
    confidence: float
    quality: str
    stars: int
    forks: int
    description: str
    needs_review: bool
    warnings: List[str]
    suggestions: List[str]
    parent_skill: Optional[str] = None  # 父目录 skill 名称
    inherited_from: Optional[str] = None  # 继承自哪个 skill

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================
# 子目录 skill 继承处理器
# ============================================
class SubdirSkillInheritor:
    """子目录 skill 继承处理器"""

    def __init__(self, user_map: Dict[str, str]):
        self.user_map = user_map

    def get_parent_skill_name(self, skill_path: str) -> Optional[str]:
        """获取父目录 skill 名称"""
        # 检查路径中是否包含 skills/skills/ 模式
        parts = skill_path.replace('\\', '/').split('/')

        # 查找第二个 skills 目录的父级目录名
        for i, part in enumerate(parts):
            if part == 'skills' and i + 1 < len(parts):
                # 找到了第一个 skills 目录
                # 检查是否还有第二个 skills 目录
                for j in range(i + 1, len(parts)):
                    if parts[j] == 'skills' and j + 1 < len(parts):
                        # 找到了第二个 skills 目录，其父目录就是父 skill
                        if j > 0:
                            return parts[j - 1]
                break

        return None

    def get_parent_github_url(self, parent_skill_name: str) -> Optional[str]:
        """获取父 skill 的 GitHub URL"""
        if parent_skill_name in self.user_map:
            return self.user_map[parent_skill_name]
        return None

    def can_inherit(self, skill_name: str, skill_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        检查是否可以继承父目录配置

        返回: (是否可继承, 父skill名称, GitHub URL)
        """
        parent_skill = self.get_parent_skill_name(skill_path)

        if not parent_skill:
            return False, None, None

        # 如果自己已经有配置，不需要继承
        if skill_name in self.user_map:
            return False, None, None

        parent_url = self.get_parent_github_url(parent_skill)

        if not parent_url:
            return False, parent_skill, None

        # 只继承有效的 GitHub URL，不继承"自定义skill，未发布"
        if parent_url.startswith("自定义skill") or not parent_url.startswith("https://"):
            return False, parent_skill, None

        return True, parent_skill, parent_url

    def suggest_inheritance(self, skills: List[Tuple[str, str]]) -> List[Dict]:
        """分析所有需要继承的子目录 skills"""
        suggestions = []

        for skill_name, skill_path in skills:
            can_inherit, parent_skill, parent_url = self.can_inherit(skill_name, skill_path)

            if can_inherit:
                suggestions.append({
                    'name': skill_name,
                    'path': skill_path,
                    'parent': parent_skill,
                    'github_url': parent_url
                })

        return suggestions


# ============================================
# 匹配来源评估器
# ============================================
class MatchSourceEvaluator:
    """匹配来源评估器"""

    def __init__(self):
        self.user_map = ConfigManager.load_github_map()
        self.inheritor = SubdirSkillInheritor(self.user_map)
        self.quality_assessor = RepoQualityAssessor()

    def get_github_url_from_readme(self, skill_path: str) -> Optional[str]:
        """从 README 提取 GitHub URL"""
        readme_path = os.path.join(skill_path, 'README.md')
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                    url = extract_github_url(f.read())
                    if url and url not in ["https://github.com/user-attachments/assets"]:
                        return url
            except:
                pass
        return None

    def get_repo_info(self, github_url: str) -> Tuple[int, int, str]:
        """获取仓库信息"""
        if not github_url or not github_url.startswith("https://"):
            return 0, 0, ""

        try:
            import requests
            match = re.search(r'github\.com/([^/]+)/([^/]+?)(\.git)?$', github_url)
            if not match:
                return 0, 0, ""

            owner = match.group(1)
            repo = match.group(2).replace('.git', '')

            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {'Accept': 'application/vnd.github.v3+json'}
            token = os.environ.get('GITHUB_TOKEN', '')
            if token:
                headers['Authorization'] = f'token {token}'

            response = requests.get(api_url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return (
                    data.get('stargazers_count', 0),
                    data.get('forks_count', 0),
                    data.get('description', '') or ""
                )
        except:
            pass

        return 0, 0, ""

    def evaluate_skill(self, skill_name: str, skill_path: str) -> SkillMatchInfo:
        """评估单个 skill 的匹配情况"""

        warnings = []
        suggestions = []
        match_source = "none"
        github_url = ""
        confidence = 0.0
        quality = "unknown"
        needs_review = False
        parent_skill = None
        inherited_from = None

        # 1. 检查用户配置
        if skill_name in self.user_map:
            github_url = self.user_map[skill_name]

            # 判断是否为自定义 skill
            if github_url.startswith("自定义skill"):
                match_source = "user_config"
                confidence = 1.0
                needs_review = False
                suggestions.append("✅ 用户自己的 skill，未发布")
            elif github_url.startswith("https://"):
                match_source = "user_config"
                confidence = 1.0
                needs_review = False
                suggestions.append("✅ 用户手动配置")
            else:
                match_source = "user_config"
                confidence = 1.0
                needs_review = False

        # 2. 检查是否可以继承父目录配置
        elif not github_url:
            can_inherit, p_skill, p_url = self.inheritor.can_inherit(skill_name, skill_path)

            if can_inherit:
                github_url = p_url
                match_source = "inherited"
                confidence = 0.9
                parent_skill = p_skill
                inherited_from = p_skill
                suggestions.append(f"📎 继承自父目录 skill: {p_skill}")

        # 3. 从 README 提取
        elif not github_url:
            readme_url = self.get_github_url_from_readme(skill_path)
            if readme_url:
                github_url = readme_url
                match_source = "readme"
                confidence = 0.95
                suggestions.append("✅ 从 README.md 提取")

        # 获取仓库信息
        if github_url and github_url.startswith("https://"):
            stars, forks, description = self.get_repo_info(github_url)

            # 评估质量
            repo_info = {
                'stargazers_count': stars,
                'forks_count': forks,
                'description': description,
                'language': None,
                'size': 100,
                'archived': False,
                'updated_at': datetime.now().isoformat()
            }
            quality, quality_score, quality_warnings = self.quality_assessor.assess_quality(repo_info)
            warnings.extend(quality_warnings)
        else:
            stars, forks, description = 0, 0, ""

        return SkillMatchInfo(
            name=skill_name,
            path=skill_path,
            has_github=bool(github_url and not github_url.startswith("自定义skill")),
            github_url=github_url,
            match_source=match_source,
            confidence=confidence,
            quality=quality,
            stars=stars,
            forks=forks,
            description=description,
            needs_review=needs_review,
            warnings=warnings,
            suggestions=suggestions,
            parent_skill=parent_skill,
            inherited_from=inherited_from
        )


# ============================================
# 扫描本地 Skills
# ============================================
def scan_local_skills() -> List[Tuple[str, str]]:
    """扫描本地所有 skills"""
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

    return sorted(all_skills.items(), key=lambda x: x[0].lower())


# ============================================
# 生成评估报告
# ============================================
def generate_evaluation_report(skills: List[Tuple[str, str]]) -> List[SkillMatchInfo]:
    """生成评估报告"""
    evaluator = MatchSourceEvaluator()
    results = []

    print("\n" + "=" * 80)
    print(" " * 15 + "本地 Skills GitHub 匹配评估报告 (增强版)")
    print("=" * 80)
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"置信度级别: {CONFIDENCE_LEVEL}")
    print("=" * 80 + "\n")

    # 先分析可继承的子目录 skills
    inheritance_suggestions = evaluator.inheritor.suggest_inheritance(skills)

    if inheritance_suggestions:
        print("=" * 80)
        print("🔗 检测到可继承父目录配置的子目录 Skills")
        print("=" * 80)
        print(f"\n找到 {len(inheritance_suggestions)} 个子目录 skills 可以继承父目录配置:\n")

        for item in inheritance_suggestions:
            print(f"  📎 {item['name']}")
            print(f"     路径: {item['path']}")
            print(f"     父目录: {item['parent']}")
            print(f"     继承地址: {item['github_url']}")
            print()

        print("=" * 80)
        print("💡 是否自动应用这些继承配置？")
        print("=" * 80)
        print("  这些子目录 skills 将自动使用父目录的 GitHub 地址")
        print("  如果同意，请在 user_github_map.json 中添加对应配置\n")

    # 评估所有 skills
    for skill_name, skill_path in skills:
        match_info = evaluator.evaluate_skill(skill_name, skill_path)
        results.append(match_info)

    return results, inheritance_suggestions


# ============================================
# 打印报告
# ============================================
def print_report(results: List[SkillMatchInfo], inheritance_suggestions: List[Dict]):
    """打印评估报告"""

    # 统计
    total = len(results)
    has_github = sum(1 for r in results if r.has_github)
    custom_skills = sum(1 for r in results if r.github_url.startswith("自定义skill"))
    inherited = sum(1 for r in results if r.match_source == "inherited")
    by_source = {}
    for r in results:
        by_source[r.match_source] = by_source.get(r.match_source, 0) + 1

    # 打印统计
    print("📊 统计概览")
    print("-" * 80)
    print(f"  总 Skill 数:     {total}")
    print(f"  有 GitHub 地址:  {has_github} ({has_github/total*100:.1f}%)")
    print(f"  自定义未发布:    {custom_skills}")
    print(f"  继承父目录:      {inherited}")
    print()
    print("📋 匹配来源分布:")
    for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
        labels = {
            "user_config": "用户配置",
            "inherited": "继承父目录",
            "readme": "README提取",
            "none": "未匹配"
        }
        print(f"  {labels.get(source, source):20} {count:3} 个")
    print()
    print("=" * 80 + "\n")

    # 按匹配来源分组打印
    grouped = {}
    for r in results:
        if r.match_source not in grouped:
            grouped[r.match_source] = []
        grouped[r.match_source].append(r)

    # 定义显示顺序
    order = ["user_config", "inherited", "readme", "none"]
    labels = {
        "user_config": "✅ 用户配置 (user_config)",
        "inherited": "🔗 继承父目录 (inherited)",
        "readme": "✅ README 提取 (readme)",
        "none": "❌ 未匹配 (none)"
    }

    for source in order:
        if source not in grouped:
            continue

        print("=" * 80)
        print(labels.get(source, source))
        print("=" * 80 + "\n")

        for info in grouped[source]:
            # 打印 skill 信息
            if info.github_url.startswith("自定义skill"):
                print(f"🏠 **{info.name}**")
            else:
                print(f"✅ **{info.name}**")
            print(f"   路径: `{info.path}`")

            if info.github_url:
                if info.github_url.startswith("自定义skill"):
                    print(f"   GitHub: {info.github_url}")
                elif info.github_url.startswith("https://"):
                    print(f"   GitHub: [{info.github_url}]({info.github_url})")
                else:
                    print(f"   GitHub: {info.github_url}")

                print(f"   匹配来源: {info.match_source}")
                print(f"   可信度: {info.confidence:.2f} | 质量: {info.quality} | Stars: {info.stars}")

                if info.inherited_from:
                    print(f"   📎 继承自: {info.inherited_from}")

                if info.description:
                    desc = info.description[:80] + "..." if len(info.description) > 80 else info.description
                    print(f"   描述: {desc}")

                # 打印建议
                if info.suggestions:
                    print(f"   说明:")
                    for s in info.suggestions:
                        print(f"     {s}")

                # 打印警告
                if info.warnings:
                    print(f"   警告:")
                    for w in info.warnings:
                        print(f"     {w}")

            else:
                print(f"   GitHub: 未找到")
                print(f"   说明: 此 skill 没有找到对应的 GitHub 仓库")
                print(f"   建议:")
                print(f"     1. 如果是已发布的 skill，请手动添加到 user_github_map.json")
                print(f"     2. 如果是自己的 skill (未发布)，请添加: \"自定义skill，未发布\"")

            print()

    print("=" * 80)
    print("报告结束")
    print("=" * 80)

    # 生成继承配置建议
    if inheritance_suggestions:
        print("\n" + "=" * 80)
        print("💡 继承配置建议")
        print("=" * 80)
        print("\n请在 user_github_map.json 中添加以下配置:\n")
        print("{")
        for item in inheritance_suggestions:
            print(f'  "{item["name"]}": "{item["github_url"]}",')
        print("}")
        print()

    # 保存报告
    save_report(results, by_source, inheritance_suggestions)


def save_report(results: List[SkillMatchInfo], by_source: Dict[str, int], inheritance_suggestions: List[Dict]):
    """保存报告到文件"""
    report_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    os.makedirs(report_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = os.path.join(report_dir, f'skills_match_evaluation_{timestamp}.json')

    report_data = {
        'generated_at': datetime.now().isoformat(),
        'config': {
            'confidence_level': CONFIDENCE_LEVEL
        },
        'statistics': {
            'total': len(results),
            'has_github': sum(1 for r in results if r.has_github),
            'custom_skills': sum(1 for r in results if r.github_url.startswith("自定义skill")),
            'inherited': sum(1 for r in results if r.match_source == "inherited"),
            'by_source': by_source
        },
        'inheritance_suggestions': inheritance_suggestions,
        'skills': [r.to_dict() for r in results]
    }

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"\n📄 报告已保存到: {report_file}")


# ============================================
# 主函数
# ============================================
def main():
    """主函数"""
    print("\n🔍 开始扫描本地 Skills...\n")

    skills = scan_local_skills()
    print(f"找到 {len(skills)} 个 Skills\n")

    results, inheritance_suggestions = generate_evaluation_report(skills)
    print_report(results, inheritance_suggestions)

    print("\n" + "=" * 80)
    print("💡 后续操作建议")
    print("=" * 80)
    print()
    print("1. 查看上述报告，确认所有 Skills 的配置")
    print()
    print("2. 对于子目录 skills，可以继承父目录配置:")
    print(f"   文件位置: {USER_GITHUB_MAP_PATH}")
    print()
    print("3. 对于自己的 skill (未发布)，使用: \"自定义skill，未发布\"")
    print()
    print("4. 修改后重新运行此脚本验证")
    print()


if __name__ == '__main__':
    main()
