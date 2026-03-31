#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地 Skills GitHub 匹配评估工具

功能：
1. 扫描本地所有已安装的 skills
2. 检查每个 skill 的 GitHub 地址来源
3. 生成详细评估报告
4. 标识需要手动确认的匹配
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
    SkipListManager,
    MatchHistoryManager,
    FixedGitHubSearcher,
    SimilarityCalculator,
    RepoQualityAssessor,
    KNOWN_GITHUB_MAP,
    extract_github_url,
    CONFIDENCE_LEVEL,
    AUTO_CONFIRM,
    SIMILARITY_THRESHOLDS,
    CACHE_DIR,
    CONFIG_DIR,
    USER_GITHUB_MAP_PATH,
    SKIP_LIST_PATH,
    SKILLS_BASE_PATH,
)

# ============================================
# 日志配置
# ============================================
logging.basicConfig(
    level=logging.WARNING,  # 只显示警告和错误
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
    match_source: str  # user_config / known_map / readme / auto_search / none
    confidence: float  # 可信度 0-1
    quality: str  # high/medium/low/unknown
    stars: int
    forks: int
    description: str
    needs_review: bool  # 是否需要人工审核
    warnings: List[str]
    suggestions: List[str]

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================
# 匹配来源评估器
# ============================================
class MatchSourceEvaluator:
    """匹配来源评估器"""

    def __init__(self):
        self.user_map = ConfigManager.load_github_map()
        self.skip_manager = SkipListManager()
        self.searcher = FixedGitHubSearcher()
        self.quality_assessor = RepoQualityAssessor()

    def get_github_url_from_readme(self, skill_path: str) -> Optional[str]:
        """从 README 提取 GitHub URL"""
        # 检查当前目录
        readme_path = os.path.join(skill_path, 'README.md')
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                    url = extract_github_url(f.read())
                    if url:
                        return url
            except:
                pass

        # 检查父目录
        parent_dir = os.path.dirname(skill_path)
        if parent_dir and parent_dir != skill_path:
            readme_path = os.path.join(parent_dir, 'README.md')
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                        return extract_github_url(f.read())
                except:
                    pass

        return None

    def get_repo_info(self, github_url: str) -> Tuple[int, int, str]:
        """获取仓库信息（stars, forks, description）"""
        if not github_url or 'github.com' not in github_url:
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
        needs_review = True
        stars = 0
        forks = 0
        description = ""

        # 检查是否在跳过列表
        if self.skip_manager.is_skipped(skill_name):
            return SkillMatchInfo(
                name=skill_name,
                path=skill_path,
                has_github=False,
                github_url="",
                match_source="skipped",
                confidence=1.0,
                quality="skipped",
                stars=0,
                forks=0,
                description="用户手动跳过",
                needs_review=False,
                warnings=[],
                suggestions=["此 skill 已在跳过列表中，不会自动匹配"]
            )

        # 1. 检查用户配置（最可信）
        if skill_name in self.user_map:
            github_url = self.user_map[skill_name]
            match_source = "user_config"
            confidence = 1.0
            needs_review = False
            suggestions.append("✅ 用户手动配置，可信度最高")

        # 2. 从 README 提取
        elif not github_url:
            readme_url = self.get_github_url_from_readme(skill_path)
            if readme_url:
                github_url = readme_url
                match_source = "readme"
                confidence = 0.95
                needs_review = False
                suggestions.append("✅ 从 README.md 提取，可信度高")

        # 3. 检查已知映射
        elif not github_url and skill_name in KNOWN_GITHUB_MAP:
            github_url = KNOWN_GITHUB_MAP[skill_name]
            match_source = "known_map"
            confidence = 0.9
            suggestions.append("✅ 预定义映射，可信度较高")

        # 4. 自动搜索
        elif not github_url:
            match_result = self.searcher.search_and_match(skill_name)
            if match_result:
                github_url = match_result.github_url
                match_source = "auto_search"
                confidence = match_result.confidence
                quality = match_result.quality_level
                warnings = match_result.warnings

                if match_result.needs_confirmation:
                    needs_review = True
                    warnings.append("⚠️ 自动匹配，需要人工确认")
                    suggestions.append(f"相似度: {match_result.similarity:.2f}")
                    suggestions.append(f"可信度: {match_result.confidence:.2f}")
                else:
                    needs_review = False
                    suggestions.append(f"✅ 自动匹配且通过验证 (可信度: {match_result.confidence:.2f})")

        # 获取仓库信息
        if github_url and github_url not in ["https://github.com/user-attachments/assets"]:
            stars, forks, description = self.get_repo_info(github_url)

            # 评估质量
            if quality == "unknown":
                repo_info = {
                    'stargazers_count': stars,
                    'forks_count': forks,
                    'description': description,
                    'language': None,  # 暂不获取
                    'size': 100,  # 默认值
                    'archived': False,
                    'updated_at': datetime.now().isoformat()
                }
                quality, quality_score, quality_warnings = self.quality_assessor.assess_quality(repo_info)
                warnings.extend(quality_warnings)

            # 低质量警告
            if match_source == "auto_search" and stars == 0 and quality == "low":
                needs_review = True
                if not any("低质量" in w for w in warnings):
                    warnings.append("⚠️ 仓库质量低 (0 stars)")

        return SkillMatchInfo(
            name=skill_name,
            path=skill_path,
            has_github=bool(github_url),
            github_url=github_url,
            match_source=match_source,
            confidence=confidence,
            quality=quality,
            stars=stars,
            forks=forks,
            description=description,
            needs_review=needs_review,
            warnings=warnings,
            suggestions=suggestions
        )


# ============================================
# 扫描本地 Skills
# ============================================
def scan_local_skills() -> List[Tuple[str, str]]:
    """扫描本地所有 skills"""
    skill_files = glob.glob(os.path.join(SKILLS_BASE_PATH, '**/SKILL.md'), recursive=True)

    all_skills = {}
    for skill_file_path in skill_files:
        # 提取 skill 名称
        path_parts = skill_file_path.replace('\\', '/').split('/')
        skill_name = ""

        for i, part in enumerate(path_parts):
            if part == 'skills' and i < len(path_parts) - 1:
                skill_name = path_parts[i + 1]
                break

        if not skill_name:
            skill_name = os.path.basename(os.path.dirname(skill_file_path))

        # 跳过重复
        if skill_name not in all_skills:
            skill_dir = os.path.dirname(skill_file_path)
            all_skills[skill_name] = skill_dir

    return sorted(all_skills.items(), key=lambda x: x[0].lower())


# ============================================
# 生成评估报告
# ============================================
def generate_evaluation_report(skills: List[Tuple[str, str]]) -> List[SkillMatchInfo]:
    """生成评估报告"""
    evaluator = MatchSourceEvaluator()
    results = []

    print("\n" + "=" * 80)
    print(" " * 20 + "本地 Skills GitHub 匹配评估报告")
    print("=" * 80)
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"置信度级别: {CONFIDENCE_LEVEL} | 自动确认: {AUTO_CONFIRM}")
    print("=" * 80 + "\n")

    for skill_name, skill_path in skills:
        match_info = evaluator.evaluate_skill(skill_name, skill_path)
        results.append(match_info)

    return results


# ============================================
# 打印报告
# ============================================
def print_report(results: List[SkillMatchInfo]):
    """打印评估报告"""

    # 统计
    total = len(results)
    has_github = sum(1 for r in results if r.has_github)
    needs_review = sum(1 for r in results if r.needs_review)
    by_source = {}
    for r in results:
        by_source[r.match_source] = by_source.get(r.match_source, 0) + 1

    # 打印统计
    print("📊 统计概览")
    print("-" * 80)
    print(f"  总 Skill 数:     {total}")
    print(f"  有 GitHub 地址:  {has_github} ({has_github/total*100:.1f}%)")
    print(f"  需要人工审核:    {needs_review}")
    print()
    print("📋 匹配来源分布:")
    for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {source:20} {count:3} 个")
    print()
    print("=" * 80 + "\n")

    # 按匹配来源分组打印
    grouped = {}
    for r in results:
        if r.match_source not in grouped:
            grouped[r.match_source] = []
        grouped[r.match_source].append(r)

    # 定义显示顺序
    order = ["user_config", "readme", "known_map", "auto_search", "none", "skipped"]
    labels = {
        "user_config": "✅ 用户手动配置 (user_config)",
        "readme": "✅ README 提取 (readme)",
        "known_map": "✓ 预定义映射 (known_map)",
        "auto_search": "🔍 自动搜索 (auto_search)",
        "none": "❌ 未匹配 (none)",
        "skipped": "⏭️  已跳过 (skipped)"
    }

    for source in order:
        if source not in grouped:
            continue

        print("=" * 80)
        print(labels.get(source, source))
        print("=" * 80 + "\n")

        for info in grouped[source]:
            # 打印 skill 信息
            status_icon = "⚠️" if info.needs_review else "✅"
            print(f"{status_icon} **{info.name}**")
            print(f"   路径: `{info.path}`")

            if info.has_github:
                print(f"   GitHub: [{info.github_url}]({info.github_url})")
                print(f"   匹配来源: {info.match_source}")
                print(f"   可信度: {info.confidence:.2f} | 质量: {info.quality} | Stars: {info.stars}")

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

                # 需要审核
                if info.needs_review:
                    print()
                    print(f"   ⚠️  **需要人工确认**")
                    print(f"   如果确认此匹配正确，请添加到 user_github_map.json:")
                    print(f'   ```json')
                    print(f'   "{info.name}": "{info.github_url}"')
                    print(f'   ```')

                    # 如果是低质量匹配，建议跳过
                    if info.quality == "low" or info.stars == 0:
                        print()
                        print(f"   如果这是你自己的 skill (未发布)，建议跳过:")
                        print(f'   ```json')
                        print(f'   "{info.name}": {{')
                        print(f'     "reason": "用户自己的 skill，尚未发布到 GitHub",')
                        print(f'     "added_at": "{datetime.now().isoformat()}"')
                        print(f'   }}')
                        print(f'   ```')

            else:
                print(f"   GitHub: 未找到")
                print(f"   说明: 此 skill 没有找到对应的 GitHub 仓库")
                print(f"   建议:")
                print(f"     1. 如果是已发布的 skill，请手动添加 GitHub 地址到 user_github_map.json")
                print(f"     2. 如果是自己的 skill (未发布)，请添加到 skip_list.json")

            print()

    print("=" * 80)
    print("报告结束")
    print("=" * 80)

    # 保存报告到文件
    save_report(results, by_source)


def save_report(results: List[SkillMatchInfo], by_source: Dict[str, int]):
    """保存报告到 JSON 文件"""
    report_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    os.makedirs(report_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = os.path.join(report_dir, f'skills_match_evaluation_{timestamp}.json')

    report_data = {
        'generated_at': datetime.now().isoformat(),
        'config': {
            'confidence_level': CONFIDENCE_LEVEL,
            'auto_confirm': AUTO_CONFIRM
        },
        'statistics': {
            'total': len(results),
            'has_github': sum(1 for r in results if r.has_github),
            'needs_review': sum(1 for r in results if r.needs_review),
            'by_source': by_source
        },
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

    # 扫描本地 skills
    skills = scan_local_skills()
    print(f"找到 {len(skills)} 个 Skills\n")

    # 生成评估报告
    results = generate_evaluation_report(skills)

    # 打印报告
    print_report(results)

    # 打印后续操作建议
    print("\n" + "=" * 80)
    print("💡 后续操作建议")
    print("=" * 80)
    print()
    print("1. 查看上述报告，确认所有标记为 [⚠️ 需要人工确认] 的 Skills")
    print()
    print("2. 对于正确的匹配，添加到 user_github_map.json:")
    print(f"   文件位置: {USER_GITHUB_MAP_PATH}")
    print('   格式: {"skill-name": "https://github.com/user/repo"}')
    print()
    print("3. 对于自己的 skill (未发布)，添加到 skip_list.json:")
    print(f"   文件位置: {SKIP_LIST_PATH}")
    print('   格式: {"skill-name": {"reason": "...", "added_at": "..."}}')
    print()
    print("4. 修改后重新运行此脚本验证")
    print()


if __name__ == '__main__':
    main()
