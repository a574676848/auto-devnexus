"""Load the owner's saved environment and ask before expensive local fallback."""
from __future__ import annotations

import getpass
import os
import shlex
import sys
from pathlib import Path


def load_saved_environment(path: Path | None = None) -> None:
    path = path or Path.home() / '.config/kangarooking-skills/video-downloader/env'
    wanted = ('ARK_API_KEY', 'SILICONFLOW_API_KEY')
    if any(os.environ.get(name) for name in wanted):
        return
    if not path.is_file():
        return
    if path.stat().st_mode & 0o077:
        raise RuntimeError('Saved ASR credentials must have mode 0600; refusing to load an exposed configuration.')
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip().removeprefix('export ')
        name, sep, value = line.partition('=')
        if sep and name.strip() in wanted:
            # Parse a literal only: never source/execute arbitrary shell code in Python.
            parts = shlex.split(value, comments=True)
            if len(parts) == 1 and parts[0].strip():
                os.environ[name.strip()] = parts[0]


def choose_missing_key_backend(*, interactive=None, input_fn=input, secret_fn=None, output=None):
    stream = output or sys.stderr
    print('没有可用的云端转写密钥（ARK_API_KEY / SILICONFLOW_API_KEY）。请选择：\n'
          '  1. 使用火山 Ark 豆包流式语音识别 2.0（doubao-seed-asr-2.0，推荐）\n'
          '  2. 提供硅基流动密钥，使用 SenseVoiceSmall\n'
          '  3. 使用本地 Whisper（最慢，仅明确选择后运行）', file=stream, flush=True)
    if interactive is None:
        interactive = sys.stdin.isatty()
    if not interactive:
        print('当前为非交互运行：请由 Agent 询问用户，设置 ARK_API_KEY / SILICONFLOW_API_KEY，'
              '或明确传入 --asr whisper 后继续。', file=stream)
        return None
    try:
        choice = input_fn('选择 1 / 2 / 3（回车取消）：').strip()
        if choice == '1':
            key = (secret_fn or getpass.getpass)('ARK_API_KEY（输入不回显）：').strip()
            if key and not any(char.isspace() for char in key):
                os.environ['ARK_API_KEY'] = key
                return 'ark'
        elif choice == '2':
            key = (secret_fn or getpass.getpass)('SILICONFLOW_API_KEY（输入不回显）：').strip()
            if key and not any(char.isspace() for char in key):
                os.environ['SILICONFLOW_API_KEY'] = key
                return 'siliconflow'
        elif choice == '3':
            return 'whisper'
    except (EOFError, KeyboardInterrupt):
        pass
    return None
