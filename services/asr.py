import os, pathlib, shutil, subprocess, tempfile
from faster_whisper import WhisperModel
from services.config import ASR_MODEL, ASR_COMPUTE, ASR_PROMPT, DEBUG_TRANSCRIPCION
from services.logging import logger

_whisper = None
def _get_whisper():
    global _whisper
    if _whisper is None:
        _whisper = WhisperModel(ASR_MODEL, compute_type=ASR_COMPUTE, download_root=os.environ.get("HF_HOME"))
    return _whisper

def convert_to_wav(src_path: str, dst_path: str):
    if not os.path.exists(src_path): raise FileNotFoundError(src_path)
    if shutil.which("ffmpeg") is None: raise RuntimeError("FFmpeg no está en PATH.")
    subprocess.run(["ffmpeg","-y","-i",src_path,"-ac","1","-ar","16000",dst_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if not os.path.exists(dst_path): raise RuntimeError("FFmpeg no generó el WAV.")

def transcribe_bytes(download_fn) -> str:
    with tempfile.TemporaryDirectory() as td:
        src = str(pathlib.Path(td) / "in_media")
        wav = str(pathlib.Path(td) / "out.wav")
        download_fn(src)   # función async externa escribirá acá
        convert_to_wav(src, wav)
        asr = _get_whisper()
        segments, _ = asr.transcribe(wav, language="es", vad_filter=True, beam_size=5, initial_prompt=ASR_PROMPT)
        text = " ".join(s.text.strip() for s in segments if s.text).strip()
        if len(text) < 8 or sum(c in "aeiouáéíóú" for c in text.lower()) < 3:
            segments2, _ = asr.transcribe(wav, language="es", vad_filter=True, beam_size=8, initial_prompt=ASR_PROMPT)
            text2 = " ".join(s.text.strip() for s in segments2 if s.text).strip()
            if len(text2) > len(text): text = text2
        return text
