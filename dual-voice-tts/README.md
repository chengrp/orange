# Dual Voice TTS - 双音色对话语音生成器

基于微软 Edge TTS 的双音色对话语音生成工具，支持多角色对话、7种预设风格、飞书发送。

## ✨ 特性

- 🎙️ **双音色对话** - 男女声自动切换，生成自然流畅的对话音频
- 🎨 **7种预设风格** - 日常/播客/新闻/儿童/甜美/优雅/温柔
- 💬 **飞书发送** - 一键发送语音消息到飞书
- 🆓 **完全免费** - 基于微软 Edge TTS，无需 API Key
- 📦 **开箱即用** - Python API 和 CLI 两种调用方式

## 🚀 快速开始

### 安装依赖

```bash
# 安装 edge-tts
pipx install edge-tts

# 或使用 pip
pip install edge-tts
```

确保系统已安装 `ffmpeg`：
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### 克隆仓库

```bash
git clone https://github.com/openclaw/dual-voice-tts.git
cd dual-voice-tts
```

### 基本使用

**命令行方式：**
```bash
echo '女：你好，我是晓晓。
男：你好，我是云健。
女：今天天气真不错啊。
男：是啊，阳光明媚的，适合出去走走。' | python3 scripts/generate.py --preset daily --send-feishu
```

**Python API：**
```python
from scripts.generate import DialogueGenerator

gen = DialogueGenerator(preset="daily")
audio_path = gen.generate([
    {"speaker": "female", "text": "你好，我是晓晓。"},
    {"speaker": "male", "text": "你好，我是云健。"},
])
```

## 🎨 预设风格

| 预设名 | 女声 | 男声 | 适用场景 |
|-------|------|------|---------|
| `daily` | 晓晓 | 云健 | 日常对话（默认） |
| `podcast` | 晓涵 | 云枫 | 播客/访谈 |
| `news` | 晓晓 | 云扬 | 新闻播报 |
| `kids` | 晓睿 | 云夏 | 儿童内容 |
| `sweet` | 晓梦 | 云希 | 甜美少女 |
| `elegant` | 晓墨 | 云枫 | 成熟优雅 |
| `gentle` | 晓辰 | 云健 | 温柔知性 |

## 🎤 音色列表

### 女声

| 音色代号 | 名称 | 特点 |
|---------|------|------|
| `zh-CN-XiaoxiaoNeural` | 晓晓 | 标准、自然 |
| `zh-CN-XiaoyiNeural` | 晓艺 | 亲切、活泼 |
| `zh-CN-XiaochenNeural` | 晓辰 | 温柔、知性 |
| `zh-CN-XiaohanNeural` | 晓涵 | 活泼、甜美 |
| `zh-CN-XiaomengNeural` | 晓梦 | 少女感 |
| `zh-CN-XiaomoNeural` | 晓墨 | 成熟、优雅 |
| `zh-CN-XiaoruiNeural` | 晓睿 | 儿童音 |

### 男声

| 音色代号 | 名称 | 特点 |
|---------|------|------|
| `zh-CN-YunjianNeural` | 云健 | 标准、稳重 |
| `zh-CN-YunxiNeural` | 云希 | 阳光、年轻 |
| `zh-CN-YunfengNeural` | 云枫 | 沉稳、中年 |
| `zh-CN-YunyangNeural` | 云扬 | 正式、播报 |
| `zh-CN-YunxiaNeural` | 云夏 | 儿童音 |

**在线试听**：https://speech.microsoft.com/portal/voicegallery

## ⚙️ 配置

编辑 `config.json` 配置飞书凭据：

```json
{
  "default_preset": "daily",
  "output_dir": "~/.openclaw/workspace/output/audio",
  "feishu": {
    "app_id": "your_app_id",
    "app_secret": "your_app_secret",
    "default_receive_id": "ou_xxx",
    "receive_id_type": "open_id"
  }
}
```

## 📝 对话格式

```
女：这是女声说的话
男：这是男声说的话
旁白：这是旁白内容
```

支持的角色标记：
- `女` / `女声` / `F` → 女声
- `男` / `男声` / `M` → 男声
- `旁白` / `N` → 旁白（使用男声）

## 🔗 飞书发送

配置好飞书凭据后，使用 `--send-feishu` 参数发送：

```bash
python3 scripts/generate.py --preset podcast --send-feishu < dialogue.txt
```

## 📋 依赖

- Python 3.10+
- edge-tts
- ffmpeg

## 📄 许可证

MIT License

## 🙏 致谢

- 微软 Edge TTS 提供免费的语音合成服务
- OpenClaw 项目

## 📊 费用说明

| TTS 服务 | 费用 | API Key |
|---------|------|---------|
| **Edge TTS（本工具）** | 免费，每月 50 万字符 | 不需要 |
| OpenAI TTS | $15/100万字符 | 需要 |
| ElevenLabs | 有免费额度，超出付费 | 需要 |

Edge TTS 是微软 Edge 浏览器内置的语音服务，完全免费，无需注册任何账号。
