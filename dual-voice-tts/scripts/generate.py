#!/usr/bin/env python3
"""
双音色对话 TTS 生成器
支持多角色对话、预设风格、飞书发送
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import argparse
from pathlib import Path
from typing import List, Dict, Optional

# 配置路径
SKILL_DIR = Path(__file__).parent.parent
CONFIG_FILE = SKILL_DIR / "config.json"
PRESETS_DIR = SKILL_DIR / "presets"


def load_config() -> dict:
    """加载配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def load_preset(preset_name: str) -> dict:
    """加载预设"""
    preset_file = PRESETS_DIR / f"{preset_name}.json"
    if preset_file.exists():
        with open(preset_file) as f:
            return json.load(f)
    raise ValueError(f"预设 '{preset_name}' 不存在")


def parse_dialogue(text: str) -> List[Dict[str, str]]:
    """
    解析对话文本
    支持格式：
    - 女：你好
    - 男：你好
    - 旁白：今天天气不错
    - F: Hello
    - M: Hello
    """
    dialogue = []
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 匹配格式：角色：文本 或 角色: 文本
        match = re.match(r'^([女男旁白FMN]+)[：:]\s*(.+)$', line)
        if match:
            speaker_raw = match.group(1)
            text = match.group(2)
            
            # 标准化角色标记
            if speaker_raw in ['女', '女声', 'F', 'f']:
                speaker = 'female'
            elif speaker_raw in ['男', '男声', 'M', 'm']:
                speaker = 'male'
            elif speaker_raw in ['旁白', 'N', 'n']:
                speaker = 'narrator'
            else:
                speaker = 'female'  # 默认女声
            
            dialogue.append({
                'speaker': speaker,
                'text': text
            })
    
    return dialogue


async def generate_audio_segment(text: str, voice: str, output_path: str):
    """生成单个音频片段"""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def merge_audio_segments(segment_files: List[str], output_path: str):
    """合并多个音频片段"""
    # 创建临时文件列表
    list_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    for f in segment_files:
        list_file.write(f"file '{f}'\n")
    list_file.close()
    
    # ffmpeg 合并
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', list_file.name,
        '-c:a', 'libopus', '-b:a', '32k',
        output_path
    ], capture_output=True, check=True)
    
    os.unlink(list_file.name)


def get_audio_duration(file_path: str) -> int:
    """获取音频时长（秒）"""
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
        capture_output=True, text=True
    )
    return int(float(result.stdout.strip()))


def send_to_feishu(audio_path: str, config: dict, receive_id: str = None) -> dict:
    """发送语音到飞书"""
    import requests
    
    app_id = config.get('feishu', {}).get('app_id')
    app_secret = config.get('feishu', {}).get('app_secret')
    receive_id = receive_id or config.get('feishu', {}).get('default_receive_id')
    receive_id_type = config.get('feishu', {}).get('receive_id_type', 'open_id')
    
    # 获取 token
    token_resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret}
    )
    token = token_resp.json()["tenant_access_token"]
    
    # 获取时长
    duration = get_audio_duration(audio_path)
    
    # 上传文件
    with open(audio_path, 'rb') as f:
        upload_resp = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("voice.opus", f, "audio/opus")},
            data={"file_type": "opus", "file_name": "voice.opus", "duration": duration}
        )
    
    file_key = upload_resp.json()["data"]["file_key"]
    
    # 发送消息
    send_resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages",
        headers={"Authorization": f"Bearer {token}"},
        params={"receive_id_type": receive_id_type},
        json={
            "receive_id": receive_id,
            "msg_type": "audio",
            "content": json.dumps({"file_key": file_key})
        }
    )
    
    return send_resp.json()


class DialogueGenerator:
    """对话语音生成器"""
    
    def __init__(
        self,
        preset: str = "daily",
        female_voice: str = None,
        male_voice: str = None,
        narrator_voice: str = None
    ):
        self.config = load_config()
        
        # 加载预设
        preset_data = load_preset(preset)
        
        # 设置音色（可被参数覆盖）
        self.female_voice = female_voice or preset_data.get('female_voice')
        self.male_voice = male_voice or preset_data.get('male_voice')
        self.narrator_voice = narrator_voice or self.male_voice
        
        # 输出目录
        self.output_dir = Path(
            self.config.get('output_dir', '~/.openclaw/workspace/output/audio')
        ).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_voice(self, speaker: str) -> str:
        """根据角色获取音色"""
        if speaker == 'female':
            return self.female_voice
        elif speaker == 'male':
            return self.male_voice
        else:  # narrator
            return self.narrator_voice
    
    async def generate(
        self,
        dialogue: List[Dict[str, str]],
        output_path: str = None
    ) -> str:
        """生成对话音频"""
        if not dialogue:
            raise ValueError("对话内容为空")
        
        # 生成输出路径
        if not output_path:
            output_path = self.output_dir / f"dialogue_{os.getpid()}.opus"
        else:
            output_path = Path(output_path)
        
        print(f"🎙️ 开始生成对话音频...")
        print(f"   预设: {self.female_voice.split('-')[-1]} + {self.male_voice.split('-')[-1]}")
        
        # 逐句生成
        temp_files = []
        for i, segment in enumerate(dialogue):
            voice = self._get_voice(segment['speaker'])
            temp_file = tempfile.mktemp(suffix='.mp3')
            
            print(f"   [{i+1}/{len(dialogue)}] {segment['speaker']}: {segment['text'][:20]}...")
            await generate_audio_segment(segment['text'], voice, temp_file)
            temp_files.append(temp_file)
        
        # 合并
        print("🔧 合并音频片段...")
        merge_audio_segments(temp_files, str(output_path))
        
        # 清理临时文件
        for f in temp_files:
            os.unlink(f)
        
        duration = get_audio_duration(str(output_path))
        size_kb = output_path.stat().st_size / 1024
        
        print(f"✅ 完成！")
        print(f"   文件: {output_path}")
        print(f"   时长: {duration} 秒")
        print(f"   大小: {size_kb:.1f} KB")
        
        return str(output_path)
    
    def generate_and_send(
        self,
        dialogue: List[Dict[str, str]],
        receive_id: str = None
    ) -> dict:
        """生成并发送到飞书"""
        # 运行异步生成
        audio_path = asyncio.run(self.generate(dialogue))
        
        # 发送到飞书
        print("📤 发送到飞书...")
        result = send_to_feishu(audio_path, self.config, receive_id)
        
        if result.get('code') == 0:
            print("✅ 发送成功！")
        else:
            print(f"❌ 发送失败: {result}")
        
        return {"audio_path": audio_path, "feishu_result": result}


def main():
    parser = argparse.ArgumentParser(description='双音色对话 TTS 生成器')
    parser.add_argument('--preset', '-p', default='daily', help='预设风格')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--send-feishu', '-s', action='store_true', help='发送到飞书')
    parser.add_argument('--receive-id', help='飞书接收者 ID')
    parser.add_argument('--female-voice', help='自定义女声')
    parser.add_argument('--male-voice', help='自定义男声')
    parser.add_argument('dialogue_file', nargs='?', help='对话文件路径')
    
    args = parser.parse_args()
    
    # 读取对话内容
    if args.dialogue_file:
        with open(args.dialogue_file) as f:
            dialogue_text = f.read()
    else:
        # 从 stdin 读取
        dialogue_text = sys.stdin.read()
    
    # 解析对话
    dialogue = parse_dialogue(dialogue_text)
    
    if not dialogue:
        print("❌ 未找到有效对话内容")
        print("格式示例：")
        print("女：你好，今天天气真不错。")
        print("男：是啊，我们一起去公园吧。")
        sys.exit(1)
    
    # 创建生成器
    gen = DialogueGenerator(
        preset=args.preset,
        female_voice=args.female_voice,
        male_voice=args.male_voice
    )
    
    # 生成
    if args.send_feishu:
        result = gen.generate_and_send(dialogue, args.receive_id)
    else:
        audio_path = asyncio.run(gen.generate(dialogue, args.output))
        print(f"\n音频文件: {audio_path}")


if __name__ == "__main__":
    main()
