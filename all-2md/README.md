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

All-2-MD is a comprehensive document conversion skill for Claude Code that leverages Microsoft's MarkItDown tool to convert various document formats to Markdown. It covers **18 detailed handling scenarios** across **8 file formats**, ensuring **content preservation** as the core principle.

### 中文

All-2-MD 是 Claude Code 的综合文档转换技能，基于微软 MarkItDown 工具，支持将各种文档格式转换为 Markdown。覆盖 **8 种文件格式** 的 **18 种精细化处理场景**，以**内容不丢失**为核心原则。

---

## ✨ Key Features / 核心特性

### English

| Feature | Description |
|---------|-------------|
| 🎯 **18 Scenarios** | Detailed handling strategies for different document types |
| 💎 **Content Preservation** | Never discard content without user confirmation |
| 🔍 **OCR Support** | Extract text from scanned PDFs and images |
| 📊 **Table Preservation** | Convert complex tables to Markdown format |
| 🎵 **Audio Transcription** | Speech-to-text for audio files |
| 📦 **Batch Processing** | Recursively process ZIP archives |

### 中文

| 特性 | 描述 |
|------|------|
| 🎯 **18 种场景** | 针对不同文档类型的精细化处理策略 |
| 💎 **内容不丢失** | 未经用户确认绝不丢弃任何内容 |
| 🔍 **OCR 支持** | 从扫描 PDF 和图片中提取文字 |
| 📊 **表格保留** | 将复杂表格转换为 Markdown 格式 |
| 🎵 **音频转写** | 音频文件语音转文字 |
| 📦 **批量处理** | 递归处理 ZIP 压缩包 |

---

## 📁 Supported Formats / 支持格式

### English

| Format | Extensions | Scenarios |
|--------|-----------|-----------|
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

- **文档迁移**: 将旧文档转换为 Markdown 用于文档站点
- **内容归档**: 将各种格式归档为 Markdown 便于长期保存
- **研究处理**: 从研究论文、报告和演示文稿中提取内容
- **数据提取**: 从 PDF 和 Office 文档中提取文字和表格
- **音频转写**: 将会议录音和讲座转换为文字
- **批量转换**: 处理 ZIP 压缩包中的多个文件

#### ⚠️ 不太适合

- **实时转换**: 未针对实时处理进行优化
- **复杂布局**: 高度格式化的文档可能需要人工调整
- **手写文字**: OCR 准确度因手写质量而异
- **动画内容**: 动画和交互元素无法保留

---

## 🚀 Installation / 安装

### English

#### Prerequisites

- Python 3.8 or higher
- pip package manager

#### Quick Install

```bash
pip install markitdown
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
pip install markitdown
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

#### Method 1: Command Line

```bash
markitdown document.pdf -o output.md
```

#### Method 2: Python Module

```bash
python -m markitdown document.pdf
```

#### Method 3: Bundled Script

```bash
python scripts/convert.py document.pdf output.md
```

### 中文

#### 方式一：命令行

```bash
markitdown document.pdf -o output.md
```

#### 方式二：Python 模块

```bash
python -m markitdown document.pdf
```

#### 方式三：辅助脚本

```bash
python scripts/convert.py document.pdf output.md
```

---

## ⚡ Best Practices / 最佳实践

### English

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

#### For Audio

1. **Use clear, noise-free recordings** - Best transcription results
2. **Single speaker works best** - Multiple speakers may reduce accuracy
3. **Review important content** - Always verify transcriptions of critical material
4. **Consider audio quality** - Background noise affects results

#### For Batch Processing

1. **Test single file first** - Verify results before batch conversion
2. **Process in batches for large sets** - Better progress tracking
3. **Check output completeness** - Ensure all files were processed
4. **Maintain directory structure** - Easier to locate converted files

### 中文

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

#### 音频

1. **使用清晰无噪音录音** - 最佳转写效果
2. **单说话人效果最好** - 多说话人可能降低准确度
3. **审查重要内容** - 重要材料应验证转写结果
4. **注意音频质量** - 背景噪音影响结果

#### 批量处理

1. **先测试单个文件** - 批量转换前验证效果
2. **大批量分批处理** - 更好的进度跟踪
3. **检查输出完整性** - 确保所有文件都已处理
4. **保持目录结构** - 更容易找到转换后的文件

---

## ⚠️ Important Notes / 注意事项

### English

#### OCR Quality

- OCR accuracy depends on **image quality** and **text clarity**
- **Handwritten text** has varying recognition rates
- **Complex layouts** may require manual adjustment
- Always **review important documents** after conversion

#### Format Limitations

- **Dynamic content** (formulas, animations) cannot be fully preserved
- **Complex formatting** may be approximated
- **Audio transcription** quality varies with recording conditions
- **Very large files** may require extended processing time

#### Content Preservation

- The skill follows a **content preservation principle**
- Content is **never discarded** without explicit confirmation
- **Visual content** (images, charts) is embedded when text extraction is insufficient
- **Uncertain cases** prompt for user confirmation

### 中文

#### OCR 质量

- OCR 准确度取决于**图片质量**和**文字清晰度**
- **手写文字**识别率有所变化
- **复杂布局**可能需要人工调整
- 重要文档转换后务必**审查**

#### 格式限制

- **动态内容**（公式、动画）无法完全保留
- **复杂格式**可能被近似处理
- **音频转写**质量因录音条件而异
- **超大文件**可能需要较长处理时间

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

### 中文

- 微软公司的 **MarkItDown** 项目
- MarkItDown 项目的所有开源贡献者

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

</div>
