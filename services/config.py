import os
from dotenv import load_dotenv

load_dotenv()

# HuggingFace cache
os.environ.setdefault("HF_HOME", os.getenv("HF_HOME", r"C:\Users\USER\hf_cache"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
assert TELEGRAM_BOT_TOKEN, "Falta TELEGRAM_BOT_TOKEN en .env"

# Modelos
MODEL = os.getenv("MODEL", "llama3.2:3b")
VISION_MODEL = os.getenv("VISION_MODEL", "moondream")
ASR_MODEL = os.getenv("ASR_MODEL", "base")
ASR_COMPUTE = os.getenv("ASR_COMPUTE", "int8")
ASR_PROMPT = os.getenv("ASR_PROMPT", "Ortografía y nombres en español. Usa puntuación clara.")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "Responde siempre en español neutro, breve y correcto.")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "8"))
DEBUG_TRANSCRIPCION = os.getenv("DEBUG_TRANSCRIPCION", "0") == "1"

# Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

# n8n
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
N8N_TIMEOUT_MS = int(os.getenv("N8N_TIMEOUT_MS", "8000"))
N8N_BASIC_AUTH_USER = os.getenv("N8N_BASIC_AUTH_USER")
N8N_BASIC_AUTH_PASSWORD = os.getenv("N8N_BASIC_AUTH_PASSWORD")

# Databricks
DATABRICKS_HOST = (os.getenv("DATABRICKS_HOST") or "").strip()
DBSQL_HTTP_PATH = (os.getenv("DBSQL_HTTP_PATH") or "").strip()
DATABRICKS_TOKEN = (os.getenv("DATABRICKS_TOKEN") or "").strip()
DBX_CATALOG = os.getenv("DBX_CATALOG", "workspace")
DBX_SCHEMA = os.getenv("DBX_SCHEMA", "default")

# Nuevas tablas y vista
V_CATALOG = f"{DBX_CATALOG}.{DBX_SCHEMA}.v_productos"     # Vista consolidada para consultas
INV_TABLE = f"{DBX_CATALOG}.{DBX_SCHEMA}.inventario"      # Stock real
CLIENTES_TABLE = f"{DBX_CATALOG}.{DBX_SCHEMA}.clientes"
PEDIDOS_TABLE = f"{DBX_CATALOG}.{DBX_SCHEMA}.pedidos"
