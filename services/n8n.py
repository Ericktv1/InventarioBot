import httpx, base64
from services.config import (
    N8N_WEBHOOK_URL, N8N_TIMEOUT_MS,
    N8N_BASIC_AUTH_USER, N8N_BASIC_AUTH_PASSWORD
)
import logging

logger = logging.getLogger(__name__)

async def call_n8n(payload: dict):
    if not N8N_WEBHOOK_URL:
        return None
    try:
        headers = {"Content-Type": "application/json"}
        if N8N_BASIC_AUTH_USER and N8N_BASIC_AUTH_PASSWORD:
            token = base64.b64encode(
                f"{N8N_BASIC_AUTH_USER}:{N8N_BASIC_AUTH_PASSWORD}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {token}"

        async with httpx.AsyncClient(timeout=N8N_TIMEOUT_MS / 1000) as client:
            r = await client.post(N8N_WEBHOOK_URL, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

            # Si n8n devuelve un JSON con un comando o una respuesta, lo devolvemos completo
            if isinstance(data, dict):
                if any(k in data for k in ("command", "respuesta", "reply", "res", "message")):
                    return data

            # Si devuelve un array (por ejemplo [{json: {...}}])
            if isinstance(data, list) and data and isinstance(data[0], dict) and "json" in data[0]:
                inner = data[0]["json"]
                if any(k in inner for k in ("command", "respuesta", "reply", "res", "message")):
                    return inner

            return None

    except Exception as e:
        logger.warning(f"Error llamando a n8n: {e}")
        return None
