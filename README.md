# orange

<div align="center">

**Personal Portfolio, Sharing AI Skills and Tools**

**个人作品库，共享 AI 技能和工具**

[🇺🇸 English](README.md) | [🇨🇳 中文](README.zh.md)

</div>

---

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
echo 'Female: Hello, I'"'"'m Xiaoxiao.
Male: Hello, I'"'"'m Yunjian.' | python dual-voice-tts/scripts/generate.py --preset daily
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
