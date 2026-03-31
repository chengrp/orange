---
name: dual-voice-tts
description: 双音色对话语音生成器，支持多角色对话、7种预设风格、飞书发送。基于微软 Edge TTS（免费、无需 Key）。
metadata:
  openclaw:
    emoji: "🎙️"
    requires:
      bins: ["ffmpeg", "python3"]
      packages: ["edge-tts"]
---

# 双音色对话 TTS

## 功能特点

- ✅ **多角色对话**：支持任意数量的角色和音色
- ✅ **7种预设风格**：日常对话、播客、新闻、儿童、甜美、优雅、温柔
- ✅ **完全免费**：基于微软 Edge TTS，无需 API Key
- ✅ **飞书发送**：直接发送语音消息到飞书

## 快速使用

### 方式1：简单对话

```
/dual-voice-tts
女：你好，今天天气真不错。
男：是啊，我们一起去公园吧。
女：好啊，我想带本书去那儿看。
男：那我带点水果和饮料。
```

### 方式2：指定预设

```
/dual-voice-tts --preset podcast
主持人：欢迎来到我们的节目，今天聊聊 AI 的发展。
嘉宾：AI 确实发展很快，特别是大语言模型领域。
```

### 方式3：发送到飞书

```
/dual-voice-tts --send-feishu
女：小互，你的任务完成了。
男：好的，我马上来检查。
```

## 预设风格

| 预设名 | 女声 | 男声 | 适用场景 |
|-------|------|------|---------|
| `daily` | 晓晓 | 云健 | 日常对话（默认） |
| `podcast` | 晓涵 | 云枫 | 播客/访谈 |
| `news` | 晓晓 | 云扬 | 新闻播报 |
| `kids` | 晓睿 | 云夏 | 儿童内容 |
| `sweet` | 晓梦 | 云希 | 甜美少女 |
| `elegant` | 晓墨 | 云枫 | 成熟优雅 |
| `gentle` | 晓辰 | 云健 | 温柔知性 |

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--preset` | 预设风格 | `daily` |
| `--output` | 输出文件路径 | 自动生成 |
| `--send-feishu` | 发送到飞书 | 否 |
| `--female-voice` | 自定义女声 | 预设值 |
| `--male-voice` | 自定义男声 | 预设值 |

## 对话格式

```
角色标记：文本内容
```

**角色标记**：
- `女` / `女声` / `F` → 使用女声音色
- `男` / `男声` / `M` → 使用男声音色
- `旁白` / `N` → 使用男声（新闻风格）

## 完整音色列表

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

## Python API

```python
from dual_voice_tts import DialogueGenerator

# 使用预设
gen = DialogueGenerator(preset="podcast")
audio_path = gen.generate([
    {"speaker": "female", "text": "你好"},
    {"speaker": "male", "text": "你好啊"},
])

# 自定义音色
gen = DialogueGenerator(
    female_voice="zh-CN-XiaoyiNeural",
    male_voice="zh-CN-YunxiNeural"
)

# 发送到飞书
gen.generate_and_send(dialogue, receive_id="ou_xxx")
```

## 依赖

- `edge-tts`：微软 Edge TTS（免费）
- `ffmpeg`：音频处理

安装：
```bash
pipx install edge-tts
```
