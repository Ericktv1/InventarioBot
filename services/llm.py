import ollama
from domain.state import chats
from domain.prompts import system_prompt
from services.config import OLLAMA_HOST, MODEL
from utils.text import strip_think

_client = ollama.Client(host=OLLAMA_HOST)

def messages_for(chat_id: int):
    msgs = [{"role": "system", "content": system_prompt()}]
    msgs.extend(list(chats[chat_id]))
    return msgs

def chat(chat_id: int, temperature: float = 0.2):
    resp = _client.chat(
        model=MODEL,
        messages=messages_for(chat_id),
        options={"num_ctx": 1024, "temperature": temperature},
        keep_alive="1h",
    )
    raw = (resp.get("message") or {}).get("content", "")
    return strip_think(raw).strip()
