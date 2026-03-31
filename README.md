# orange

<div align="center">

**个人作品库，共享 AI 技能和工具**

**Personal Portfolio, Sharing AI Skills and Tools**

[English](#english) | [中文](#中文)

</div>

---

<a name="中文"></a>

# 🇨🇳 中文

## 📦 Skills

| Skill | 描述 | 状态 |
|-------|------|------|
| [all-2md](./all-2md) | 全格式文档转换，支持 PDF/DOCX/PPTX/EPUB/图片/音频等 9 种格式，针对中文图书优化 | ✅ 可用 |
| [dual-voice-tts](./dual-voice-tts) | 双音色对话语音生成器，基于 Edge TTS，7种预设风格 | ✅ 可用 |
| [skill-hud](./skill-hud) | OpenClaw Skill 可视化仪表盘，实时监控所有技能状态 | ✅ 可用 |
| [info-graphic](./info-graphic) | 高密度信息图生成，支持 8 种视觉风格 | ✅ 可用 |

## 🔧 环境要求

### 通用要求
- Python 3.8+
- Node.js 18+ (部分技能)
- ffmpeg（用于音频处理）

## 🚀 快速开始

### all-2md - 全格式文档转换

```bash
# 安装依赖
pip install markitdown ebooklib beautifulsoup4 lxml

# 转换 PDF
markitdown document.pdf -o output.md

# 转换 EPUB（增强支持，针对中文图书优化）
python all-2md/scripts/epub_to_md.py book.epub book.md
```

### dual-voice-tts - 双音色对话语音生成

```bash
# 安装依赖
pip install edge-tts

# macOS/Linux
brew install ffmpeg  # 或 sudo apt install ffmpeg

# 生成对话音频
echo '女：你好，我是晓晓。
男：你好，我是云健。' | python dual-voice-tts/scripts/generate.py --preset daily
```

### skill-hud - 技能仪表板

```bash
# 前置要求
# 1. Claude Code 已安装并配置
# 2. Python 3.8+

# 运行仪表板
python skill-hud/scripts/hud_dashboard.py
```

### info-graphic - 高密度信息图生成

```bash
# 安装依赖
pip install google-generativeai

# 配置 API Key（获取地址：https://ai.google.dev/）
export ALL_IMAGE_GOOGLE_API_KEY="your_api_key_here"  # Linux/Mac
$env:ALL_IMAGE_GOOGLE_API_KEY="your_api_key_here"    # Windows PowerShell
```

## 📖 技能文档

每个技能目录都包含完整的文档：
- `SKILL.md` - 核心技能文档
- `README.md` - 项目概述
- `references/` - 参考资料和详细指南

## 📄 许可证

所有技能均采用 MIT 许可证。

## 🔗 相关链接

- [OpenClaw](https://github.com/openclaw/openclaw) - AI 助手框架
- [ClawHub](https://clawhub.com) - 技能市场
- [MarkItDown](https://github.com/microsoft/markitdown) - 微软文档转换工具

---

<a name="english"></a>

# 🇺🇸 English

## 📦 Skills

| Skill | Description | Status |
|-------|-------------|--------|
| [all-2md](./all-2md) | Universal document conversion, supports 9 formats including PDF/DOCX/PPTX/EPUB/images/audio, optimized for Chinese books | ✅ Available |
| [dual-voice-tts](./dual-voice-tts) | Dual-voice dialogue TTS generator, based on Edge TTS, 7 preset styles | ✅ Available |
| [skill-hud](./skill-hud) | OpenClaw Skill visual dashboard, real-time monitoring of all skills | ✅ Available |
| [info-graphic](./info-graphic) | High-density infographic generation, supports 8 visual styles | ✅ Available |

## 🔧 Requirements

### Common Requirements
- Python 3.8+
- Node.js 18+ (some skills)
- ffmpeg (for audio processing)

## 🚀 Quick Start

### all-2md - Universal Document Converter

```bash
# Install dependencies
pip install markitdown ebooklib beautifulsoup4 lxml

# Convert PDF
markitdown document.pdf -o output.md

# Convert EPUB (enhanced support, optimized for Chinese books)
python all-2md/scripts/epub_to_md.py book.epub book.md
```

### dual-voice-tts - Dual-Voice Dialogue TTS

```bash
# Install dependencies
pip install edge-tts

# macOS/Linux
brew install ffmpeg  # or sudo apt install ffmpeg

# Generate dialogue audio
echo 'Female: Hello, I'm Xiaoxiao.
Male: Hello, I'm Yunjian.' | python dual-voice-tts/scripts/generate.py --preset daily
```

### skill-hud - Skills Dashboard

```bash
# Prerequisites
# 1. Claude Code installed and configured
# 2. Python 3.8+

# Run dashboard
python skill-hud/scripts/hud_dashboard.py
```

### info-graphic - High-Density Infographic Generator

```bash
# Install dependencies
pip install google-generativeai

# Configure API Key (get from: https://ai.google.dev/)
export ALL_IMAGE_GOOGLE_API_KEY="your_api_key_here"  # Linux/Mac
$env:ALL_IMAGE_GOOGLE_API_KEY="your_api_key_here"    # Windows PowerShell
```

## 📖 Documentation

Each skill directory contains complete documentation:
- `SKILL.md` - Core skill documentation
- `README.md` - Project overview
- `references/` - Reference materials and detailed guides

## 📄 License

All skills are licensed under the MIT License.

## 🔗 Related Links

- [OpenClaw](https://github.com/openclaw/openclaw) - AI assistant framework
- [ClawHub](https://clawhub.com) - Skills marketplace
- [MarkItDown](https://github.com/microsoft/markitdown) - Microsoft document conversion tool

---

<div align="center">

**Built with ❤️ by the community**

**社区共建 ❤️**

</div>
