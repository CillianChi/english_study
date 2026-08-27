"""Text-to-speech via edge-tts (Microsoft Edge's neural voices — unofficial
API, no key needed, but free, so it's worth caching aggressively instead of
hitting Microsoft on every playback)."""
import os

import edge_tts

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "audio_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

VOICE = "en-US-AriaNeural"


def _cache_path(word: str) -> str:
    return os.path.join(CACHE_DIR, f"{word}.mp3")


async def get_or_create_audio(word: str) -> str:
    path = _cache_path(word)
    if not os.path.exists(path):
        communicate = edge_tts.Communicate(word, VOICE)
        await communicate.save(path)
    return path
