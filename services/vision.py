import ollama, base64
from services.config import OLLAMA_HOST, VISION_MODEL
_client = ollama.Client(host=OLLAMA_HOST)

def describe_image(img_bytes: bytes, system_prompt: str) -> str:
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    result = _client.chat(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": system_prompt + " Responde SIEMPRE en español."},
            {"role": "user", "content": "Analiza la imagen. 1) Describe lo que ves. 2) Si hay texto o precio, léelo. Sé breve.",
             "images": [b64]}
        ],
        options={"temperature": 0.2},
    )
    return ((result.get("message") or {}).get("content") or "").strip()
