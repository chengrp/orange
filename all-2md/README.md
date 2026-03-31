# All-2-MD Skill / 全格式文档转换技能

<div align="center">

**A Claude Code Skill for converting various document formats to Markdown**

**基于微软 MarkItDown 的全格式文档转换 Claude Code 技能**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MarkItDown](https://img.shields.io/badge/MarkItDown-0.0.2-green.svg)](https://github.com/microsoft/markitdown)

</div>

---

## ⚠️ Important Notice / 重要提示

**This skill is a wrapper and documentation for MarkItDown by Microsoft. MarkItDown is copyrighted by Microsoft Corporation and licensed under the MIT License.**

**本技能是对微软 MarkItDown 工具的封装和文档说明。MarkItDown 版权归微软公司所有，采用 MIT 许可证。**

---

## 📖 What is All-2-MD? / 什么是 All-2-MD？

### English

All-2-MD is a comprehensive document conversion skill for Claude Code that leverages Microsoft's MarkItDown tool to convert various document formats to Markdown. It covers **18 detailed handling scenarios** across **9 file formats**, ensuring **content preservation** as the core principle. **NEW**: Enhanced EPUB support with optimized Markdown output for Chinese documents.

### 中文

All-2-MD 是 Claude Code 的综合文档转换技能，基于微软 MarkItDown 工具，支持将各种文档格式转换为 Markdown。覆盖 **9 种文件格式** 的 **18 种精细化处理场景**，以**内容不丢失**为核心原则。**新增**：增强的 EPUB 支持，针对中文文档优化 Markdown 输出格式。

---

## ✨ Key Features / 核心特性

### English

| Feature | Description |
|---------|-------------|
| 🎯 **18 Scenarios** | Detailed handling strategies for different document types |
| 📚 **EPUB Enhanced** | Optimized for Chinese books with smart chapter recognition |
| 💎 **Content Preservation** | Never discard content without user confirmation |
| 🔍 **OCR Support** | Extract text from scanned PDFs and images |
| 📊 **Table Preservation** | Convert complex tables to Markdown format |
| 🎵 **Audio Transcription** | Speech-to-text for audio files |
| 📦 **Batch Processing** | Recursively process ZIP archives |
| 🎨 **Markdown Optimization** | Clean headers, proper hierarchy, Chinese subtitle support |

### 中文

| 特性 | 描述 |
|------|------|
| 🎯 **18 种场景** | 针对不同文档类型的精细化处理策略 |
| 📚 **EPUB 增强** | 针对中文图书优化，智能章节识别 |
| 💎 **内容不丢失** | 未经用户确认绝不丢弃任何内容 |
| 🔍 **OCR 支持** | 从扫描 PDF 和图片中提取文字 |
| 📊 **表格保留** | 将复杂表格转换为 Markdown 格式 |
| 🎵 **音频转写** | 音频文件语音转文字 |
| 📦 **批量处理** | 递归处理 ZIP 压缩包 |
| 🎨 **Markdown 优化** | 清理标题格式、正确层级、中文副标题支持 |

---

## 📁 Supported Formats / 支持格式

### English

| Format | Extensions | Scenarios |
|--------|-----------|-----------|
| **EPUB** | `.epub` | E-books, Chinese text optimization |
| **PDF** | `.pdf` | Text-based, Scanned, Images, Photo-only, Mixed |
| **Word** | `.docx` | Normal, Complex with images |
| **PowerPoint** | `.pptx` | Text-heavy, Visual slides |
| **Excel** | `.xlsx`, `.xls` | Data tables, Formulas |
| **HTML** | `.html`, `.htm` | Simple, Complex structure |
| **Images** | `.jpg`, `.png`, `.gif`, `.bmp` | Text-containing, Photos, Diagrams |
| **Audio** | `.mp3`, `.wav`, `.m4a`, `.ogg` | Clear speech, Noisy audio |
| **ZIP** | `.zip` | Mixed files, Large archives |

### 中文

| 格式 | 扩展名 | 场景 |
|------|--------|------|
| **EPUB** | `.epub` | 电子书、中文文本优化 |
| **PDF** | `.pdf` | 文本表格、扫描件、图文、纯图片、混合 |
| **Word** | `.docx` | 普通文档、复杂文档含图 |
| **PowerPoint** | `.pptx` | 文本型、图形化幻灯片 |
| **Excel** | `.xlsx`, `.xls` | 数据表格、公式计算 |
| **HTML** | `.html`, `.htm` | 结构清晰、复杂布局 |
| **图片** | `.jpg`, `.png`, `.gif`, `.bmp` | 含文字、纯图片、图表 |
| **音频** | `.mp3`, `.wav`, `.m4a`, `.ogg` | 清晰语音、质量较差 |
| **ZIP** | `.zip` | 混合文件、大型压缩包 |

---

## 🎯 Use Cases / 适用场景

### English

#### ✅ Perfect For

- **E-book Conversion**: Convert EPUB e-books to Markdown with Chinese text optimization
- **Document Migration**: Convert legacy documents to Markdown for documentation sites
- **Content Archiving**: Archive various formats in Markdown for long-term preservation
- **Research Processing**: Extract content from research papers, reports, and presentations
- **Data Extraction**: Pull text and tables from PDFs and Office documents
- **Audio Transcription**: Convert meeting recordings and lectures to text
- **Batch Conversion**: Process multiple files in ZIP archives

#### ⚠️ Not Recommended For

- **Real-time Conversion**: Not optimized for real-time processing
- **Complex Layouts**: May require manual adjustment for highly formatted documents
- **Handwritten Text**: OCR accuracy varies with handwriting quality
- **Animated Content**: Animations and interactive elements are not preserved

### 中文

#### ✅ 非常适合

- **电子书转换**：将 EPUB 电子书转换为 Markdown，针对中文文本优化
- **文档迁移**：将旧文档转换为 Markdown 用于文档站点
- **内容归档**：将各种格式归档为 Markdown 便于长期保存
- **研究处理**：从研究论文、报告和演示文稿中提取内容
- **数据提取**：从 PDF 和 Office 文档中提取文字和表格
- **音频转写**：将会议录音和讲座转换为文字
- **批量转换**：处理 ZIP 压缩包中的多个文件

#### ⚠️ 不太适合

- **实时转换**：未针对实时处理进行优化
- **复杂布局**：高度格式化的文档可能需要人工调整
- **手写文字**：OCR 准确度因手写质量而异
- **动画内容**：动画和交互元素无法保留

---

## 🚀 Installation / 安装

### English

#### Prerequisites

- Python 3.8 or higher
- pip package manager

#### Quick Install

```bash
pip install markitdown ebooklib beautifulsoup4 lxml
```

#### Install from Requirements

```bash
pip install -r requirements.txt
```

#### Verify Installation

```bash
# Test command line tool
markitdown --help

# Or test Python module
python -c "from markitdown import MarkItDown; print('OK')"
```

### 中文

#### 前置要求

- Python 3.8 或更高版本
- pip 包管理器

#### 快速安装

```bash
pip install markitdown ebooklib beautifulsoup4 lxml
```

#### 从依赖文件安装

```bash
pip install -r requirements.txt
```

#### 验证安装

```bash
# 测试命令行工具
markitdown --help

# 或测试 Python 模块
python -c "from markitdown import MarkItDown; print('OK')"
```

---

## 💡 Usage / 使用方法

### English

#### Method 1: Command Line (MarkItDown)

```bash
# Convert PDF
markitdown document.pdf -o output.md

# Convert EPUB
markitdown book.epub -o book.md

# Convert Word
markitdown report.docx -o report.md
```

#### Method 2: Python Module

```bash
python -m markitdown document.pdf
```

#### Method 3: EPUB with Enhanced Processing

```bash
# Use enhanced EPUB converter for Chinese books
python scripts/epub_to_md.py book.epub book.md

# Features:
# - Smart chapter recognition (一、二、三、etc.)
# - Clean header formatting
# - Proper hierarchy preservation
# - Subtitle handling (——)
```

#### Method 4: General Conversion Script

```bash
python scripts/convert.py document.pdf output.md
```

### 中文

#### 方式一：命令行（MarkItDown）

```bash
# 转换 PDF
markitdown document.pdf -o output.md

# 转换 EPUB
markitdown book.epub -o book.md

# 转换 Word
markitdown report.docx -o report.md
```

#### 方式二：Python 模块

```bash
python -m markitdown document.pdf
```

#### 方式三：EPUB 增强处理

```bash
# 使用增强的 EPUB 转换器处理中文图书
python scripts/epub_to_md.py book.epub book.md

# 特性：
# - 智能章节识别（一、二、三、等）
# - 清理标题格式
# - 保持正确的层级结构
# - 副标题处理（——）
```

#### 方式四：通用转换脚本

```bash
python scripts/convert.py document.pdf output.md
```

---

## 📚 EPUB Processing Details / EPUB 处理详解

### English

#### Enhanced Features for EPUB

The enhanced EPUB converter includes:

1. **Smart Chinese Chapter Recognition**
   - Automatically identifies chapter headers (一、二、三、etc.)
   - Preserves HTML heading tags (h1-h6)
   - Handles subtitles (——) properly

2. **Markdown Optimization**
   - Removes bold markers from headers
   - Cleans up excessive line breaks
   - Maintains proper document hierarchy

3. **Metadata Preservation**
   - Extracts title and author from EPUB
   - Creates well-structured document header

4. **Content Processing**
   - Processes all document files in order
   - Shows progress for large files
   - Outputs character count statistics

#### Usage Example

```bash
python scripts/epub_to_md.py input.epub output.md

# Output:
# [INFO] Processing: input.epub
#    Title: 书名
#    Author: 作者
#    Found 25 document files
#    Progress: 10/25
#    Progress: 20/25
# [OK] Conversion complete: output.md
# [STAT] Character count: 123,456
```

### 中文

#### EPUB 增强功能

增强的 EPUB 转换器包含：

1. **智能中文章节识别**
   - 自动识别章节标题（一、二、三、等）
   - 保留 HTML 标题标签（h1-h6）
   - 正确处理副标题（——）

2. **Markdown 优化**
   - 移除标题中的粗体标记
   - 清理多余的空行
   - 保持正确的文档层级

3. **元数据保留**
   - 从 EPUB 提取书名和作者
   - 创建结构良好的文档头部

4. **内容处理**
   - 按顺序处理所有文档文件
   - 显示大文件处理进度
   - 输出字符数统计

#### 使用示例

```bash
python scripts/epub_to_md.py input.epub output.md

# 输出：
# [INFO] Processing: input.epub
#    Title: 书名
#    Author: 作者
#    Found 25 document files
#    Progress: 10/25
#    Progress: 20/25
# [OK] Conversion complete: output.md
# [STAT] Character count: 123,456
```

---

## ⚡ Best Practices / 最佳实践

### English

#### For EPUB Files

1. **Use enhanced converter for Chinese books** - Better chapter recognition
2. **Check output hierarchy** - Verify headers are properly formatted
3. **Review character encoding** - Ensure UTF-8 for Chinese characters
4. **Test conversion first** - Convert a chapter before full book

#### For PDF Documents

1. **Use native PDFs when possible** - Better text extraction than scanned versions
2. **Ensure high resolution for scans** - Improves OCR accuracy
3. **Check complex tables manually** - May need formatting adjustments
4. **Verify OCR output** - Important documents should be reviewed

#### For Images

1. **Use high-resolution images** - Minimum 300 DPI recommended
2. **Ensure text is clear and readable** - Avoid blurry or distorted images
3. **Straighten skewed images** - Improves OCR accuracy
4. **Provide context for photos** - Helps with proper categorization

### 中文

#### EPUB 文件

1. **中文图书使用增强转换器** - 更好的章节识别效果
2. **检查输出层级** - 验证标题格式正确
3. **检查字符编码** - 确保中文字符使用 UTF-8
4. **先测试转换** - 转换完整本书前先测试一章

#### PDF 文档

1. **优先使用原生 PDF** - 比扫描版本有更好的文字提取效果
2. **确保扫描件高分辨率** - 提高 OCR 准确度
3. **人工检查复杂表格** - 可能需要格式调整
4. **验证 OCR 输出** - 重要文档应人工审核

#### 图片

1. **使用高分辨率图片** - 建议最低 300 DPI
2. **确保文字清晰可读** - 避免模糊或扭曲的图片
3. **扶正倾斜图片** - 提高 OCR 准确度
4. **为照片提供上下文** - 有助于正确分类

---

## ⚠️ Important Notes / 注意事项

### English

#### EPUB Processing

- **Chinese chapter detection** works best with traditional formats (一、二、三、)
- **Complex layouts** may require manual adjustment after conversion
- **Character encoding** is always UTF-8 for proper Chinese display
- **Large EPUB files** may take time to process

#### OCR Quality

- OCR accuracy depends on **image quality** and **text clarity**
- **Handwritten text** has varying recognition rates
- **Complex layouts** may require manual adjustment
- Always **review important documents** after conversion

#### Content Preservation

- The skill follows a **content preservation principle**
- Content is **never discarded** without explicit confirmation
- **Visual content** (images, charts) is embedded when text extraction is insufficient
- **Uncertain cases** prompt for user confirmation

### 中文

#### EPUB 处理

- **中文章节检测**对传统格式效果最好（一、二、三、）
- **复杂布局**转换后可能需要人工调整
- **字符编码**始终使用 UTF-8 以正确显示中文
- **大型 EPUB 文件**处理可能需要时间

#### OCR 质量

- OCR 准确度取决于**图片质量**和**文字清晰度**
- **手写文字**识别率有所变化
- **复杂布局**可能需要人工调整
- 重要文档转换后务必**审查**

#### 内容保留

- 技能遵循**内容不丢失原则**
- 未经明确确认**绝不丢弃内容**
- 文字提取不足时**嵌入视觉内容**（图片、图表）
- **不确定情况**会提示用户确认

---

## 📚 Documentation / 文档

### English

- **[SKILL.md](SKILL.md)** - Core skill documentation and usage guide
- **[FEATURES.md](references/FEATURES.md)** - Complete feature documentation with 18 scenarios
- **[INSTALLATION.md](references/INSTALLATION.md)** - Detailed installation and troubleshooting guide

### 中文

- **[SKILL.md](SKILL.md)** - 核心技能文档和使用指南
- **[FEATURES.md](references/FEATURES.md)** - 完整功能文档，包含 18 种场景
- **[INSTALLATION.md](references/INSTALLATION.md)** - 详细安装和故障排除指南

---

## 🔗 Links / 链接

### English

- [MarkItDown GitHub Repository](https://github.com/microsoft/markitdown)
- [MarkItDown Documentation](https://github.com/microsoft/markitdown/blob/main/README.md)
- [MarkItDown License](https://github.com/microsoft/markitdown/blob/main/LICENSE)

### 中文

- [MarkItDown GitHub 仓库](https://github.com/microsoft/markitdown)
- [MarkItDown 文档](https://github.com/microsoft/markitdown/blob/main/README.md)
- [MarkItDown 许可证](https://github.com/microsoft/markitdown/blob/main/LICENSE)

---

## 📜 License / 许可证

### English

This skill is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

MarkItDown is copyrighted by **Microsoft Corporation** and licensed under the MIT License.

### 中文

本技能采用 **MIT 许可证**。详见 [LICENSE](LICENSE)。

MarkItDown 版权归 **微软公司** 所有，采用 MIT 许可证。

---

## 🙏 Acknowledgments / 致谢

### English

- **MarkItDown** by Microsoft Corporation
- All open-source contributors to the MarkItDown project
- **ebooklib** for EPUB processing
- **Beautiful Soup** for HTML parsing

### 中文

- 微软公司的 **MarkItDown** 项目
- MarkItDown 项目的所有开源贡献者
- **ebooklib** 用于 EPUB 处理
- **Beautiful Soup** 用于 HTML 解析

---

## 🤝 Contributing / 贡献

### English

Contributions are welcome! Please feel free to submit issues or pull requests.

### 中文

欢迎贡献！请随时提交问题或拉取请求。

---

## 📮 Contact / 联系

### English

For questions or feedback, please open an issue on GitHub.

### 中文

如有问题或反馈，请在 GitHub 上提交 issue。

---

<div align="center">

**Built with ❤️ using Microsoft MarkItDown**

**使用微软 MarkItDown 构建 ❤️**

**Enhanced with EPUB support for Chinese books**

**增强 EPUB 支持，专为中文图书优化**

</div>
