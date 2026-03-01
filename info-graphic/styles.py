#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信息图风格定义模块
定义 6 种高密度信息图风格
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass


def detect_language(text: str) -> str:
    """
    检测文本的主要语言

    Returns:
        "zh" = 中文, "en" = 英文, "mixed" = 中英混合
    """
    # 统计中文字符数
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 统计英文字符数
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    total = chinese_chars + english_chars

    if total == 0:
        return "en"

    chinese_ratio = chinese_chars / total
    english_ratio = english_chars / total

    if chinese_ratio > 0.3:
        return "zh"
    elif english_ratio > 0.7:
        return "en"
    else:
        return "mixed"


@dataclass
class InfographicStyle:
    """信息图风格定义"""
    name: str                          # 风格名称
    name_en: str                       # 英文名称
    description: str                   # 风格描述
    background: str                    # 背景色
    base_colors: List[str]             # 主色调
    accent_colors: List[str]           # 强调色
    layout_style: str                  # 布局风格描述
    typography: str                    # 字体风格
    visual_elements: str               # 视觉元素风格
    avoid: List[str]                   # 避免的元素
    keywords: List[str]                # 风格关键词


# 6 种信息图风格定义
INFOGRAPHIC_STYLES: Dict[str, InfographicStyle] = {

    "1": InfographicStyle(
        name="坐标蓝图·波普实验室",
        name_en="Blueprint Pop Lab",
        description="实验室精密手册感 + 波普实验风格，技术图纸与荧光色的碰撞",
        background="#F2F2F2 (Professional grayish-white with blueprint grid texture)",
        base_colors=["#B8D8BE (Muted Teal/Sage Green)"],
        accent_colors=["#E91E63 (Vibrant Fluorescent Pink)", "#FFF200 (Vivid Lemon Yellow)", "#2D2926 (Ultra-fine Charcoal Brown)"],
        layout_style="""
        - INFORMATION AS COORDINATES: 每个模块都有坐标标签 (e.g., A-01, B-05, C-12)
        - HIGH DENSITY: 每张图 6-7 个模块，最小化边距
        - VISUAL CONTRAST: 超大粗体标题 vs 极小技术注释
        - LAB MANUAL AESTHETIC: 显微细节 + 宏观数据的混合
        """,
        typography="""
        - Headers: Bold Brutalist Chinese characters, high impact
        - Body: Professional sans-serif or crisp handwritten technical print
        - Numbers: Large, highlighted with Yellow or Blue
        """,
        visual_elements="""
        - TECHNICAL DIAGRAMS: 爆炸图、剖面图、建筑骨架线
        - COORDINATE SYSTEMS: 精确标尺 (0.5mm, 1.8mm, 45°)
        - DATA BLOCKS: "Marker-over-Print" 效果，色块与文字略微错位
        - SYMBOLS: 十字准星、数学符号 (Σ, Δ, ∞)、方向箭头
        - 每个角落包含元数据：条形码、时间戳、技术参数
        """,
        avoid=[
            "NO cute/cartoonish doodles",
            "NO soft pastels or generic textures",
            "NO empty white space",
            "NO flat vector stock icons"
        ],
        keywords=["technical", "blueprint", "laboratory", "coordinates", "precision", "industrial design"]
    ),

    "2": InfographicStyle(
        name="莫兰迪效果",
        name_en="Morandi Effect",
        description="小红书爆款内容策划专家，擅长将复杂专业知识转化为超高信息密度+手绘手账风格的小红书干货内容",
        background="#F5F5DC (Beige) or #FFF8E7 (Warm cream) with paper texture",
        base_colors=["#D8BFD8 (Muted Purple)", "#B0C4DE (Light Steel Blue)", "#F5DEB3 (Wheat)"],
        accent_colors=["#DDA0DD (Plum)", "#87CEEB (Sky Blue)", "#F0E68C (Khaki)"],
        layout_style="""
        - HIGH DENSITY: 每张图必须包含 6-7 个子主题模块
        - 数据说话: 每个模块包含具体数字/品牌/参数
        - 手绘手账风格，亲和力强
        - 宁可信息丰富，不可内容空洞
        """,
        typography="""
        - Headers: Handwritten style, warm and friendly
        - Body: Clear handwritten or rounded sans-serif
        - Numbers: Highlighted with soft colors
        """,
        visual_elements="""
        - HAND-DRAWN ELEMENTS: 手绘图标和装饰
        - DOODLES: 角落有装饰性涂鸦
        - HIGHLIGHTING: 荧光笔高亮标记
        - PAPER TEXTURE: 纸张纹理感
        - SOFT COLORS: 莫兰迪色系，低饱和度
        """,
        avoid=[
            "NO harsh neon colors",
            "NO sterile digital look",
            "NO rigid grids",
            "NO flat vector stock icons"
        ],
        keywords=["xiaohongshu", "morandi", "hand-drawn", "high-density", "data-driven", "warm"]
    ),

    "3": InfographicStyle(
        name="复古波普网格",
        name_en="Retro Pop Grid",
        description="70年代复古波普艺术风格，粗描边平涂色彩，网格布局，秩序感强",
        background="#FFFFFF (Pure white) or #FFFACD (Lemon chiffon)",
        base_colors=["#FFD700 (Gold)", "#FF6B6B (Coral Red)", "#4ECDC4 (Turquoise)"],
        accent_colors=["#45B7D1 (Sky Blue)", "#96CEB4 (Sage)", "#FFEAA7 (Cream)"],
        layout_style="""
        - SWISS GRID: 严格的网格布局，方形/矩形格子
        - MODULE DISTRIBUTION: 信息模块化分配到不同格子中
        - HIGH DENSITY: 每张图 6-7 个模块
        - 秩序感强，视觉层次清晰
        """,
        typography="""
        - Headers: Bold sans-serif, high contrast
        - Body: Clean sans-serif, excellent readability
        - Numbers: Large, emphasized with color
        """,
        visual_elements="""
        - BOLD OUTLINES: 粗描边，清晰边界
        - FLAT COLORS: 平涂色彩，无渐变
        - GEOMETRIC SHAPES: 几何图形装饰
        - RETRO POP ART: 70年代波普艺术风格
        - ICONS: 简约图标，统一风格
        """,
        avoid=[
            "NO gradient effects",
            "NO complex shadows",
            "NO organic irregular shapes",
            "NO photographic elements"
        ],
        keywords=["retro", "pop-art", "grid", "bold-outlines", "flat-colors", "70s", "order"]
    ),

    "4": InfographicStyle(
        name="文件夹风格",
        name_en="Stationery Folder Style",
        description="文具美学风格，3D剪贴板、文件夹、索引标签，精致3D效果",
        background="#F5F5DC (Beige/Cream) or #FAF9F6 (Off-white)",
        base_colors=["#0047AB (Klein Blue)", "#FF8C00 (Dark Orange)", "#696969 (Dim Gray)"],
        accent_colors=["#FFD700 (Gold)", "#708090 (Slate Gray)", "#DEB887 (Burlywood)"],
        layout_style="""
        - 3D CLIPBOARD: 垂直剪贴板布局
        - LAYERED FOLDERS: 分层文件夹效果
        - INDEX TABS: 侧边索引标签
        - HIGH DENSITY: 每张图 6-7 个模块
        """,
        typography="""
        - Headers: Bold sans-serif, professional
        - Body: Clean sans-serif, organized
        - Numbers: Large, clear emphasis
        """,
        visual_elements="""
        - 3D STYLING: 3D 渲染效果
        - CLIPBOARDS: 剪贴板容器
        - FOLDERS: 文件夹样式
        - INDEX TABS: 索引标签装饰
        - MOUSE CURSOR: 3D 鼠标光标元素
        - NOTIFICATION ICONS: 通知图标装饰
        """,
        avoid=[
            "NO flat 2D design",
            "NO messy layouts",
            "NO inconsistent styling",
            "NO cartoonish elements"
        ],
        keywords=["stationery", "3D", "clipboard", "folders", "index-tabs", "organized", "planner"]
    ),

    "5": InfographicStyle(
        name="打印热敏纸风",
        name_en="Receipt Ticket Aesthetic",
        description="收据/票务美学，现代拟物设计，穿孔边缘，3D 渲染",
        background="#FFFFFF (Pure white) or #F9F9F9 (Light gray)",
        base_colors=["#000000 (Pure black)", "#333333 (Dark gray)"],
        accent_colors=["#00AEEF (Cyan)", "#FFD100 (Mustard Yellow)", "#FF6B35 (Vibrant Orange)"],
        layout_style="""
        - RECEIPT FORMAT: 收据式纵向布局
        - PERFORATED EDGES: 穿孔边缘效果
        - SEQUENTIAL: 顺序排列，清晰层次
        - HIGH DENSITY: 每张图 6-7 个模块
        """,
        typography="""
        - Headers: Monospace or pixel font (retro digital)
        - Body: Clean sans-serif, high readability
        - Numbers: Large, emphasized
        - English: Small subtitles below main headings
        """,
        visual_elements="""
        - 3D ICONS: 3D/Claymorphism 渲染图标
        - HAND-DRAWN DETAILS: 手绘风格高亮标记
        - PERFORATIONS: 穿孔边缘
        - TICKET/RECEIPT: 票据/收据样式
        - CHECKBOXES: 手绘风格复选框
        """,
        avoid=[
            "NO photographic backgrounds",
            "NO inconsistent icon styles",
            "NO messy layouts",
            "NO low contrast text"
        ],
        keywords=["receipt", "ticket", "3D-icons", "perforated", "sequential", "claymorphism", "modern-skeuomorphism"]
    ),

    "6": InfographicStyle(
        name="复古手帐风",
        name_en="Retro Journal Style",
        description="现代收据美学，3D图标+手绘细节，双语分层，复古手帐风格",
        background="#00AEEF (Cyan) or #FFD100 (Mustard Yellow) - Vibrant solid color block framing",
        base_colors=["#F9F9F9 (Off-white/light gray) - paper core", "#2C2C2C (Dark charcoal)"],
        accent_colors=["#E74C3C (Red marker)", "#3498DB (Blue pen)", "#F1C40F (Yellow highlighter)"],
        layout_style="""
        - HIGH-CONTRAST FRAMING: 鲜艳色块框定中心内容区
        - NEUTRAL CORE: 米白/浅灰核心区域，模拟纸张
        - SEQUENTIAL STRUCTURE: 收据格式组织密集信息
        - BILINGUAL LAYERING: 中文主标题 + 小号英文副标题
        - HIGH DENSITY: 每张图 6-7 个模块
        """,
        typography="""
        - Headers: Retro digital/pixel fonts or bold modern sans-serif
        - Body: Smaller lighter sans-serif, excellent readability
        - English: Small subtitles below main headings
        - Numbers: Large emphasis
        """,
        visual_elements="""
        - 3D/CLAYMORPHISM ICONS: 平滑3D渲染图标 (books, cameras, ID cards)
        - HAND-DRAWN DETAILS: 手绘风格复选框、高亮标记
        - PERFORATED EDGES: 穿孔边缘
        - MODERN SKEUOMORPHISM: 现代拟物设计
        - PAPER TEXTURE: 纸张纹理核心区
        """,
        avoid=[
            "NO flat digital styling",
            "NO low contrast",
            "NO messy organization",
            "NO inconsistent visual language"
        ],
        keywords=["modern-receipt", "ticket", "3D-icons", "hand-drawn", "perforated", "bilingual", "high-density"]
    )
}


def get_style_list() -> List[str]:
    """获取所有风格名称列表"""
    return [style.name for style in INFOGRAPHIC_STYLES.values()]


def get_style_by_id(style_id: str) -> InfographicStyle:
    """通过ID获取风格"""
    return INFOGRAPHIC_STYLES.get(style_id, INFOGRAPHIC_STYLES["1"])


def display_styles():
    """展示所有可选风格"""
    print("=" * 60)
    print("高密度信息图 - 风格选择")
    print("=" * 60)
    print()

    for style_id, style in INFOGRAPHIC_STYLES.items():
        print(f"[{style_id}] {style.name} ({style.name_en})")
        print(f"    {style.description}")
        print(f"    关键词: {', '.join(style.keywords)}")
        print()

    print("=" * 60)


def generate_infographic_prompt(
    topic: str,
    modules: List[str],
    style_id: str = "1",
    ratio: str = "3:4",
    quality: str = "4k",
    preserve_language: bool = True
) -> str:
    """
    生成信息图 Prompt，支持语言保持

    Args:
        topic: 信息图主题
        modules: 内容模块列表（6-7个）
        style_id: 风格ID (1-6)
        ratio: 宽高比
        quality: 质量
        preserve_language: 是否保持原始语言（默认True，自动检测并保持）

    Returns:
        完整的生图 Prompt
    """
    style = get_style_by_id(style_id)

    # 检测语言
    detected_lang = detect_language(topic + " ".join(modules))

    # 语言保持指令
    lang_instruction = ""
    if preserve_language:
        if detected_lang == "zh":
            lang_instruction = """
CRITICAL LANGUAGE REQUIREMENT:
- ALL content text MUST be in CHINESE (中文)
- DO NOT translate any Chinese content to English
- Keep all titles, labels, and content in original Chinese
- Numbers and symbols can remain as-is
- This is a non-negotiable requirement
"""
        elif detected_lang == "en":
            lang_instruction = """
CRITICAL LANGUAGE REQUIREMENT:
- ALL content text MUST be in ENGLISH
- Maintain all English text as provided
- Do not add translations in other languages
"""
        else:  # mixed
            lang_instruction = """
CRITICAL LANGUAGE REQUIREMENT:
- Preserve the ORIGINAL language of each content piece
- Chinese content stays in Chinese
- English content stays in English
- DO NOT translate or change languages
"""

    # 构建模块内容
    modules_text = ""
    for i, module in enumerate(modules, 1):
        modules_text += f"- Module {i:02d}: {module}\n"

    # 组装完整 Prompt
    prompt = f"""Create a high-density infographic in {style.name_en} style.

=== CONTENT (6-7 modules) ===
TITLE: {topic}

{modules_text}

=== STYLE SPECIFICATIONS ===
Background: {style.background}
Base Colors: {', '.join(style.base_colors)}
Accent Colors: {', '.join(style.accent_colors)}

Layout Style:
{style.layout_style}

Typography:
{style.typography}

Visual Elements:
{style.visual_elements}

Style Keywords: {', '.join(style.keywords)}

Avoid:
{chr(10).join('- ' + item for item in style.avoid)}

=== OUTPUT SPECIFICATIONS ===
- Aspect Ratio: {ratio}
- Quality: {quality}
- High information density with 6-7 modules
- No empty white space
{lang_instruction}
"""

    return prompt


def format_prompt_for_file(
    topic: str,
    modules: List[str],
    style_id: str = "1",
    ratio: str = "3:4",
    quality: str = "4k"
) -> str:
    """
    生成用于保存到文件的格式化 Prompt（带分隔线和说明）

    Returns:
        格式化的 Prompt 文本
    """
    style = get_style_by_id(style_id)
    detected_lang = detect_language(topic + " ".join(modules))

    lang_note = ""
    if detected_lang == "zh":
        lang_note = "【语言保持】中文内容不会翻译为英文"
    elif detected_lang == "en":
        lang_note = "【语言保持】英文内容不会翻译为其他语言"
    else:
        lang_note = "【语言保持】保持原始中英文混合，不做翻译"

    prompt = f"""{'=' * 80}
信息图生成 Prompt - {style.name}
{'=' * 80}

【风格】{style.name} ({style.name_en})
【尺寸】{ratio} 竖版
【质量】{quality}
{lang_note}

{'=' * 80}
色彩规范
{'=' * 80}
- 背景色: {style.background}
- 基础色: {', '.join(style.base_colors)}
- 强调色: {', '.join(style.accent_colors)}

{'=' * 80}
布局要求 - 高密度 6-7 模块
{'=' * 80}

┌─────────────────────────────────────────────────────────────────┐
│  [主标题] {topic}
├─────────────────────────────────────────────────────────────────┤
"""

    # 添加模块内容
    for i, module in enumerate(modules, 1):
        prompt += f"│  [{i:02d}] {module}\n"

    prompt += f"""└─────────────────────────────────────────────────────────────────┘

{'=' * 80}
视觉元素要求
{'=' * 80}

【整体风格】
{style.layout_style}

【视觉元素】
{style.visual_elements}

【排版】
{style.typography}

【色彩应用】
- 模块背景使用基础色: {style.base_colors[0] if style.base_colors else 'N/A'}
- 强调内容使用强调色
- 保持高对比度

{'=' * 80}
语言保持要求（CRITICAL）
{'=' * 80}
"""

    if detected_lang == "zh":
        prompt += """✅ 保持中文：所有内容文字必须保持中文，不得翻译为英文
✅ 原文呈现：标题、标签、内容全部使用原始中文
✅ 符号数字：数字和符号保持原样
❌ 禁止翻译：不要将任何中文内容翻译成英文
"""
    elif detected_lang == "en":
        prompt += """✅ Keep English: All content must remain in English
✅ Original text: Keep all titles, labels, and content in English
✅ No translation: Do not translate to other languages
"""
    else:
        prompt += """✅ Preserve original language: Keep each piece in its original language
✅ Chinese stays Chinese, English stays English
✅ No translation: Do not translate or change languages
"""

    prompt += f"""
{'=' * 80}
避免事项
{'=' * 80}
"""

    for item in style.avoid:
        prompt += f"❌ {item}\n"

    prompt += f"""
{'=' * 80}
质量检查
{'=' * 80}
✓ 6-7个模块完整呈现
✓ 高密度信息无空白
✓ 色彩符合风格规范
✓ 语言保持原文不变
{'=' * 80}
"""

    return prompt


if __name__ == "__main__":
    display_styles()
