#!/usr/bin/env python3
"""
PDF to Markdown Converter
基于微软 MarkItDown 工具的文档转换助手

使用方法:
    python convert.py <文件路径> [输出文件]

示例:
    python convert.py document.pdf
    python convert.py document.pdf output.md
    python convert.py "C:/Documents/report.docx"
"""

import sys
import os
from pathlib import Path
from markitdown import MarkItDown


def convert_to_markdown(input_path: str, output_path: str = None) -> str:
    """
    将文档转换为 Markdown

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径（可选）

    Returns:
        Markdown 内容
    """
    # 检查文件是否存在
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"文件不存在: {input_path}")

    # 转换文件
    md = MarkItDown()
    result = md.convert(input_path)

    # 获取 Markdown 内容
    markdown_content = result.text_content

    # 如果指定了输出文件，保存内容
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(markdown_content, encoding='utf-8')
        print(f"✓ 已保存到: {output_path}")

    return markdown_content


def main():
    if len(sys.argv) < 2:
        print("使用方法: python convert.py <输入文件> [输出文件]")
        print("\n示例:")
        print("  python convert.py document.pdf")
        print("  python convert.py document.pdf output.md")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        print(f"正在转换: {input_file}")
        content = convert_to_markdown(input_file, output_file)

        if not output_file:
            print("\n" + "="*50)
            print("转换结果:")
            print("="*50)
            print(content)
            print("="*50)

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
