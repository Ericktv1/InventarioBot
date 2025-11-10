# services/gemini.py
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()


env_path = Path(__file__).resolve().parents[1] / ".env"
if env_path.is_file():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    print(f"[WARN] .env no encontrado en: {env_path}")
import google.generativeai as genai


ENV_CANDIDATES = [
    Path(__file__).resolve().parents[1] / ".env",   # <repo>/.env
    Path.cwd() / ".env",                            # cwd/.env (por si ejecutas desde otro lado)
]
for p in ENV_CANDIDATES:
    if p.is_file():
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=p, override=False)
        except Exception:
            pass
        break
    
_FALLBACK_MODELS = [
    os.getenv("GEMINI_MODEL", "").strip() or "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

# Config por defecto para respuestas estables
_GEN_CFG = dict(
    temperature=0.2,
    top_p=0.9,
    candidate_count=1,
)

# Quita bloqueos agresivos (si tu cuenta lo permite)
try:
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    _SAFETY = {
        HarmCategory.HARM_CATEGORY_SEXUAL: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
except Exception:
    _SAFETY = None


def _extract_text(resp) -> str:
    """Evita resp.text; rescata texto recorriendo candidates/parts."""
    try:
        for cand in getattr(resp, "candidates", []) or []:
            # finish_reason 1 = STOP. Si no es STOP, puede estar bloqueado o vacío.
            fr = getattr(cand, "finish_reason", None)
            if fr is not None and int(fr) not in (1,):  # 1 == STOP
                continue
            parts = getattr(cand, "content", None)
            parts = getattr(parts, "parts", []) if parts else []
            chunks = []
            for p in parts:
                t = getattr(p, "text", None)
                if t:
                    chunks.append(t)
            if chunks:
                return "".join(chunks).strip()
        # último intento: algunos SDKs devuelven 'text' suelto
        t = getattr(resp, "text", "") or ""
        return t.strip()
    except Exception:
        return ""


def _load_model():
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Falta GOOGLE_API_KEY en .env")
    genai.configure(api_key=api_key)

    last_err = None
    for m in _FALLBACK_MODELS:
        try:
            if not m:
                continue
            model = genai.GenerativeModel(
                m,
                generation_config=_GEN_CFG,
                safety_settings=_SAFETY,
            )
            # Ping corto para validar
            probe = model.generate_content("ok")
            if _extract_text(probe):
                return model, m
        except Exception as e:
            last_err = e
    raise RuntimeError(f"No se pudo cargar Gemini. Último error: {last_err}")


_model = None
_model_name = None

def _get_model():
    global _model, _model_name
    if _model is None:
        _model, _model_name = _load_model()
        print(f"[Gemini] usando modelo: {_model_name}")
    return _model


_ALLOWED = ("/productos", "/carrito", "/checkout", "/add", "/buscar")

def _sanitize_command(s: str) -> str:
    s = (s or "").strip().splitlines()[0].strip()
    s = " ".join(s.split())
    lower = s.lower()

    if not lower:
        return "/productos"

    if lower.startswith("/add"):
        # Aceptar: /add <id> <qty> | /add <nombre...> <qty>
        # Y también variantes como: /add <qty> <nombre...> | "/add <qty> de <nombre...>"
        tokens = lower.split()
        args = tokens[1:]

        # quitar stop-words típicas
        stop = {"de", "del", "la", "el", "los", "las"}
        args = [t for t in args if t not in stop]

        if not args:
            return "/productos"

        # casos: qty primero o qty al final
        qty = None
        if args and args[-1].isdigit():
            qty = int(args[-1]); name_or_id = args[:-1]
        elif args and args[0].isdigit():
            qty = int(args[0]); name_or_id = args[1:]
        else:
            # sin cantidad explícita
            qty = 1; name_or_id = args

        if not name_or_id:
            return f"/add {qty} 1"  # fallback raro pero válido

        # si es un único token y es número, tratamos como id
        if len(name_or_id) == 1 and name_or_id[0].isdigit():
            return f"/add {name_or_id[0]} {qty}"

        # singulariza para mejorar el match con catálogo
        try:
            from services.dbx import _singularize_phrase_es, _norm
            nombre = _singularize_phrase_es(nombre)
            nombre = _norm(nombre)
        except Exception:
            pass
        return f"/add {nombre} {qty}"

    if lower.startswith("/buscar"):
        parts = lower.split(maxsplit=1)
        return parts[0] if len(parts) == 1 else f"/buscar {parts[1]}"

    if any(lower.startswith(x) for x in ("/productos", "/carrito", "/checkout")):
        return lower.split()[0]

    return "/productos"




def interpret_user_message(text: str) -> str:
    """
    Convierte el mensaje en uno de:
      /productos | /buscar <palabra> | /add <id> <cantidad> | /carrito | /checkout
    En duda → /productos.
    """
    prompt = f"""
Actúa como un bot VENDEDOR. Devuelve exactamente UN comando entre:
  /productos
  /buscar <palabra>
  /add <id> <cantidad>
  /add <nombre> <cantidad>   # si no sabes el id, usa el nombre del producto
  /carrito
  /checkout

Reglas:
- Si el usuario saluda o pide ver/mostrar/enséñame/quiero el catálogo o los productos → /productos
- Si el usuario quiere agregar pero no da ID, usa /add <nombre> <cantidad>
- Si no estás seguro → /productos
- SOLO devuelve el comando, sin explicaciones.

Ejemplos:
Usuario: "quiero agregar 2 de papel higiénico"
Comando: /add papel higienico 2

Usuario: "ponme 3 jabones"
Comando: /add jabon 3

Usuario: "agrega 1 shampoo"
Comando: /add shampoo 1

Usuario: "pagar"
Comando: /checkout

Usuario: "finalizar la compra"
Comando: /checkout

Usuario: "confirmar el pedido"
Comando: /checkout


Usuario: "{text}"
Comando:
""".strip()


    try:
        model = _get_model()
        resp = model.generate_content(prompt)
        cmd_raw = _extract_text(resp)
        cmd = _sanitize_command(cmd_raw)
        print(f"[Gemini interpretó]: {text!r} → {cmd}")
        return cmd
    except Exception as e:
        print("Error llamando a Gemini:", e)
        return "/productos"
