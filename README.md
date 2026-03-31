# orange

个人作品库，共享 AI 技能和工具。

## 📦 Skills

| Skill | 描述 | 状态 |
|-------|------|------|
| [all-2md](./all-2md) | 全格式文档转换，基于微软 MarkItDown，支持 PDF/DOCX/PPTX/图片/音频等 8 种格式 | ✅ 可用 |
| [dual-voice-tts](./dual-voice-tts) | 双音色对话语音生成器，基于 Edge TTS，7种预设风格 | ✅ 可用 |
| [skill-hud](./skill-hud) | OpenClaw Skill 可视化仪表盘，实时监控所有技能状态 | ✅ 可用 |
| [info-graphic](./info-graphic) | 高密度信息图生成，支持 8 种视觉风格 | ✅ 可用 |

## 🔧 环境要求

### 通用要求
- Python 3.10+
- Node.js 18+ (部分技能)
- ffmpeg（用于音频处理）

### all-2md 专用
- Python 3.8+
- pip install markitdown

## 📄 许可证

所有技能均采用 MIT 许可证。

## 🔗 相关链接

- [OpenClaw](https://github.com/openclaw/openclaw) - AI 助手框架
- [ClawHub](https://clawhub.com) - 技能市场
- [MarkItDown](https://github.com/microsoft/markitdown) - 微软文档转换工具

## 📖 技能文档

每个技能目录都包含完整的文档：
- `SKILL.md` - 核心技能文档
- `README.md` - 项目概述
- `references/` - 参考资料和详细指南

## 🚀 快速开始

### 安装 all-2md

```bash
pip install markitdown
```

### 使用示例

```bash
# 转换 PDF
markitdown document.pdf -o output.md

# 转换 Word
markitdown report.docx -o report.md

# 使用辅助脚本
python all-2md/scripts/convert.py document.pdf output.md
```

详见各技能目录中的 README 文件。
