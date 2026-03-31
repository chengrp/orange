#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB to Markdown 转换器 V6 - 精确版
修复：
1. 使用 HTML 标题标签作为主要标题来源
2. 只识别明确的中文子节标题（一、二、三、等）
3. 不识别普通数字列表作为标题（避免过度匹配）
"""
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re
from pathlib import Path
import sys

def is_subtitle(text):
    """判断是否是副标题（以——开头）"""
    stripped = text.strip()
    return stripped.startswith('——') or stripped.startswith('---') or stripped.startswith('—')

def html_to_markdown_v6(soup):
    """V6: 直接使用 HTML 标题标签"""
    md_lines = []

    for element in soup.find_all(True):
        tag = element.name

        if tag in ('script', 'style', 'meta', 'link'):
            continue

        # 处理标题标签
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            level = int(tag[1])
            prefix = '#' * level
            text = element.get_text(strip=True)

            if not text:
                continue

            # 检查是否是副标题
            if is_subtitle(text):
                md_lines.append("")
                md_lines.append(f"**{text}**")
                md_lines.append("")
            else:
                md_lines.append("")
                md_lines.append(f"{prefix} {text}")
                md_lines.append("")

        # 段落处理
        elif tag == 'p':
            text = element.get_text(strip=True)
            if text:
                md_lines.append("")
                md_lines.append(text)
                md_lines.append("")

    # 合并内容
    content = '\n'.join(md_lines)

    # 清理多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content

def post_process_chinese_sections(content):
    """
    后处理：只识别明确的中文章节标题

    只匹配："一、文本" 或 "（一）文本" 这样的格式
    不匹配普通的数字列表
    """
    lines = content.split('\n')
    result = []

    # 中文数字
    chinese_nums = '一二三四五六七八九十百千'
    # 只匹配"中文数字、"开头的行
    section_pattern = re.compile(r'^([' + chinese_nums + r']+、)\s*(.+)$')

    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append('')
            continue

        # 跳过已经是标题的行
        if stripped.startswith('#'):
            result.append(stripped)
            continue

        # 只检查明确的中文章节标题
        match = section_pattern.match(stripped)
        if match:
            result.append(f"### {stripped}")
            continue

        # 其他行保持不变
        result.append(stripped)

    return '\n'.join(result)

def cleanup_final_markdown(content):
    """最终清理：移除标题中的粗体标记"""
    lines = content.split('\n')
    result = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append('')
            continue

        # 移除标题行中的所有粗体标记
        if re.match(r'^#+\s', stripped):
            clean_title = stripped.replace('**', '')
            result.append(clean_title)
        else:
            result.append(stripped)

    return '\n'.join(result)

def epub_to_markdown_v6(epub_path, md_path):
    """V6: EPUB 转 Markdown - 精确版"""
    print(f"[INFO] Processing: {epub_path}")

    try:
        book = epub.read_epub(epub_path)

        # 获取元数据
        title = "Unknown Title"
        author = "Unknown Author"
        try:
            if book.get_metadata('DC', 'title'):
                title = book.get_metadata('DC', 'title')[0][0]
            if book.get_metadata('DC', 'creator'):
                author = book.get_metadata('DC', 'creator')[0][0]
        except:
            pass

        print(f"   Title: {title}")
        print(f"   Author: {author}")

        # 收集内容
        md_content = []

        # 添加文档头部
        md_content.append(f"# {title}")
        md_content.append("")
        md_content.append(f"**Author**: {author}")
        md_content.append("")
        md_content.append("---")
        md_content.append("")

        # 获取所有文档
        doc_items = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                doc_items.append(item)

        print(f"   Found {len(doc_items)} document files")

        # 按顺序处理
        for i, item in enumerate(doc_items):
            soup = BeautifulSoup(item.get_content(), 'html.parser')

            # 移除不需要的元素
            for unwanted in soup(['script', 'style', 'meta', 'link']):
                unwanted.decompose()

            # 转换为 Markdown
            chapter_md = html_to_markdown_v6(soup)

            if chapter_md.strip():
                md_content.append(chapter_md)

            if (i + 1) % 10 == 0:
                print(f"   Progress: {i + 1}/{len(doc_items)}")

        # 合并
        full_md = '\n'.join(md_content)

        # 后处理：识别中文子节标题
        full_md = post_process_chinese_sections(full_md)

        # 最终清理
        full_md = cleanup_final_markdown(full_md)

        # 再次清理多余空行
        full_md = re.sub(r'\n{4,}', '\n\n\n', full_md)

        # 写入文件
        Path(md_path).write_text(full_md, encoding='utf-8')

        print(f"[OK] Conversion complete: {md_path}")
        print(f"[STAT] Character count: {len(full_md):,}")

        return True

    except Exception as e:
        print(f"[ERROR] Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python epub_to_md_v6.py <epub_file> [output.md]")
        sys.exit(1)

    epub_path = sys.argv[1]

    if len(sys.argv) >= 3:
        md_path = sys.argv[2]
    else:
        epub_path_obj = Path(epub_path)
        md_path = epub_path_obj.parent / (epub_path_obj.stem + ".md")

    success = epub_to_markdown_v6(epub_path, md_path)
    sys.exit(0 if success else 1)
