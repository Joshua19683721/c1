# -*- coding: utf-8 -*-
"""Speech input and output for ReadExpress-CoT.

Two independent paths, each with its own graceful degradation:

**Output (朗讀)** — the Web Speech API, injected as a small Streamlit component.
It needs no server-side dependency, works offline, and uses a real zh-TW voice
when the browser has one. An optional gTTS download button is offered for
teachers who want an audio file to keep.

**Input (語音輸入)** — local Whisper. Recording is done with sounddevice and
transcription with the openai-whisper model, so a student's voice never leaves
the machine. If either package or the microphone is missing, the feature
disables itself and the UI explains why instead of raising.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    'stt_status',
    'render_tts',
    'synthesize_mp3',
    'transcribe_array',
    'SAMPLE_RATE',
]

SAMPLE_RATE = 16000

#: Slower than the default: these are dense Chinese texts read aloud.
DEFAULT_RATE = 0.92

_CACHE_DIR = Path(__file__).resolve().parent.parent / '.cache' / 'tts'


# --------------------------------------------------------------------------
# Output — Web Speech API
# --------------------------------------------------------------------------

def render_tts(text: str, label: str = '朗讀文章', rate: float = DEFAULT_RATE) -> None:
    """Render a 播放/暫停 read-aloud control backed by the browser's voices.

    Implemented as an iframe component rather than a server-side TTS call
    because it is instant, offline, and uses whatever zh-TW voice the student's
    own device already has.
    """
    import streamlit.components.v1 as components

    payload = json.dumps({'text': text, 'rate': rate}, ensure_ascii=False)
    components.html(_TTS_HTML.replace('__PAYLOAD__', payload), height=92)


_TTS_HTML = """
<style>
  .wrap { font-family: -apple-system, "PingFang TC", "Microsoft JhengHei", sans-serif; }
  button {
    font-size: 16px; padding: 9px 16px; margin-right: 8px; cursor: pointer;
    border-radius: 10px; border: 1px solid #7d8ca3;
    background: #e8ecf2; color: #2f3b4c; font-weight: 600;
  }
  button:hover { background: #dbe2ec; }
  .note { font-size: 12px; color: #6b7a90; margin-top: 6px; }
</style>
<div class="wrap">
  <button id="play">🔊 播放</button>
  <button id="pause">⏸ 暫停</button>
  <button id="stop">⏹ 停止</button>
  <div class="note" id="status">使用電腦/平板的系統語音（建議選擇中文 Taiwan）</div>
</div>
<script>
const CFG = __PAYLOAD__;
const synth = window.speechSynthesis;
const status = document.getElementById('status');

function pickVoice() {
  const voices = synth.getVoices();
  if (!voices.length) return null;
  const zhTW = voices.filter(v => /^zh(-|_)?(TW|Hant|KG|MO)/i.test(v.lang) ||
                                   /Taiwan|Mandarin|Chinese/i.test(v.name));
  return zhTW[0] || voices.find(v => /^zh/i.test(v.lang)) || voices[0];
}

function speakFrom(start) {
  const u = new SpeechSynthesisUtterance(CFG.text.slice(start));
  u.lang = 'zh-TW';
  u.rate = CFG.rate;
  u.pitch = 1.0;
  const v = pickVoice();
  if (v) u.voice = v;
  u.onend = () => { status.textContent = '讀完囉，試著回答右邊的題目吧！'; };
  synth.speak(u);
}

document.getElementById('play').onclick = () => {
  synth.cancel();
  status.textContent = '朗讀中…';
  speakFrom(0);
};
document.getElementById('pause').onclick = () => { synth.pause(); status.textContent = '已暫停'; };
document.getElementById('stop').onclick = () => { synth.cancel(); status.textContent = '已停止'; };

if (synth.onvoiceschanged !== undefined) {
  synth.onvoiceschanged = () => {
    const v = pickVoice();
    status.textContent = v ? ('語音：' + v.name) : '系統語音（未安裝中文語音）';
  };
}
</script>
"""


def synthesize_mp3(text: str, lang: str = 'zh-TW', slow: bool = True) -> bytes:
    """Return MP3 bytes via gTTS, cached on disk.

    Only used for the optional 「下載音檔」 button — network is required, so the
    app must never depend on it for normal operation.
    """
    try:
        from gtts import gTTS
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError('gTTS 未安裝，無法產生音檔') from exc

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(f'{lang}|{slow}|{text}'.encode('utf-8')).hexdigest()[:20]
    cached = _CACHE_DIR / f'{digest}.mp3'
    if cached.exists():
        return cached.read_bytes()

    buffer = io.BytesIO()
    gTTS(text=text, lang=lang, slow=slow).write_to_fp(buffer)
    data = buffer.getvalue()
    cached.write_bytes(data)
    return data


# --------------------------------------------------------------------------
# Input — local Whisper
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class SttStatus:
    available: bool
    reason: str
    recorder_ok: bool
    transcriber_ok: bool


def stt_status() -> SttStatus:
    """Report why speech input is or is not usable, without raising."""
    recorder_ok = False
    transcriber_ok = False

    try:
        import sounddevice  # noqa: F401
        recorder_ok = True
    except Exception:  # noqa: BLE001 - import can fail on missing PortAudio
        recorder_ok = False

    try:
        import whisper  # noqa: F401
        transcriber_ok = True
    except Exception:  # noqa: BLE001
        transcriber_ok = False

    if not recorder_ok and not transcriber_ok:
        return SttStatus(False, '未安裝 sounddevice / whisper，請改用打字輸入', False, False)
    if not recorder_ok:
        return SttStatus(False, '找不到麥克風或音訊驅動（sounddevice），請改用打字輸入', False, True)
    if not transcriber_ok:
        return SttStatus(False, '未安裝 openai-whisper，請改用打字輸入', True, False)
    return SttStatus(True, '可以使用語音輸入', True, True)


_whisper_model = None


def _load_whisper(model_name: str = 'base'):
    global _whisper_model
    if _whisper_model is None:
        import whisper

        _whisper_model = whisper.load_model(model_name)
    return _whisper_model


def record_audio(seconds: float = 6.0, samplerate: int = SAMPLE_RATE):
    """Record from the default microphone. Returns a float32 mono array or None."""
    try:
        import numpy as np
        import sounddevice as sd
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f'無法使用麥克風：{exc}') from exc

    frames = int(seconds * samplerate)
    buffer = np.zeros(frames, dtype='float32')
    try:
        with sd.InputStream(samplerate=samplerate, channels=1, dtype='float32') as stream:
            stream.start()
            stream.readinto(buffer)
            stream.stop()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f'錄音失敗：{exc}') from exc
    return buffer


def transcribe_array(audio, model_name: str = 'base', language: str = 'zh'):
    """Transcribe a mono float32 array. Returns cleaned Traditional Chinese text."""
    import numpy as np

    model = _load_whisper(model_name)
    audio = np.asarray(audio, dtype='float32')
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if audio.size == 0:
        return ''

    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0:
        audio = audio / peak

    result = model.transcribe(audio, language=language, fp16=False, temperature=0.0)
    return _tidy(result.get('text', ''))


def _tidy(text: str) -> str:
    """Strip whisper's filler and normalise spacing for a Chinese classroom UI."""
    text = text.strip()
    text = re.sub(r'^\s*(字幕由.*?提供|[Cc]字幕.*?)$', '', text, flags=re.MULTILINE)
    text = re.sub(r'[ \t]+', '', text)
    return text.strip(' ，,。.')
