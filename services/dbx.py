# services/dbx.py
import os
import unicodedata
from databricks import sql as dbsql


DATABRICKS_HOST = (os.getenv("DATABRICKS_HOST") or "").replace("https://", "").replace("http://", "")
DBSQL_HTTP_PATH = (os.getenv("DBSQL_HTTP_PATH") or "").strip()
DATABRICKS_TOKEN = (os.getenv("DATABRICKS_TOKEN") or "").strip()
DBX_CATALOG = os.getenv("DBX_CATALOG", "workspace")
DBX_SCHEMA = os.getenv("DBX_SCHEMA", "default")

V_CATALOG = f"{DBX_CATALOG}.{DBX_SCHEMA}.v_productos"
INV_TABLE = f"{DBX_CATALOG}.{DBX_SCHEMA}.inventario"
PEDIDOS_TABLE = f"{DBX_CATALOG}.{DBX_SCHEMA}.pedidos"


def _conn():
    """Crea conexión a Databricks SQL"""
    if not (DATABRICKS_HOST and DBSQL_HTTP_PATH and DATABRICKS_TOKEN):
        raise RuntimeError("Faltan credenciales de Databricks (.env)")
    
    return dbsql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DBSQL_HTTP_PATH,
        access_token=DATABRICKS_TOKEN
    )


def _norm(s: str) -> str:
    """Normaliza texto removiendo acentos y convirtiendo a minúsculas"""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.lower().strip()

def _singularize_token_es(t: str) -> str:
    """Singulariza muy básico para español: papeles->papel, jabones->jabon, luces->luz, toallas->toalla."""
    t = t.strip()
    if not t:
        return t

    # luces -> luz, arroces -> arroz
    if t.endswith("ces") and len(t) > 3:
        return t[:-3] + "z"

    # palabras acabadas en 'es' con consonante antes: papeles->papel, jabones->jabon, flores->flor
    if t.endswith("es") and len(t) > 3:
        # si antes de 'es' hay consonante o 'n/r/l/z', suele quitarse 'es'
        if t[-3] not in "aeiou":
            return t[:-2]

    # acabadas en 's' (toallas->toalla, cepillos->cepillo). Evita días de la semana, etc.
    if t.endswith("s") and len(t) > 3:
        return t[:-1]

    return t


def _singularize_phrase_es(s: str) -> str:
    """Singulariza cada token de una frase normalizada (sin acentos)."""
    parts = [p for p in _norm(s).split() if p]
    return " ".join(_singularize_token_es(p) for p in parts)


def list_products(limit=6):
    """Lista productos disponibles con stock"""
    limit = int(limit)
    with _conn() as c, c.cursor() as cur:
        cur.execute(f"""
            SELECT inventario_id AS id, nombre, precio_cop, stock
            FROM {V_CATALOG}
            WHERE stock > 0
            ORDER BY inventario_id
            LIMIT {limit}
        """)
        return cur.fetchall()


def search_products(q, limit=6):
    limit = int(limit)
    like_pattern = f"%{q}%"

    with _conn() as c, c.cursor() as cur:
        cur.execute(f"""
            SELECT inventario_id AS id, nombre, precio_cop, stock
            FROM {V_CATALOG}
            WHERE stock > 0
              AND (
                lower(nombre) LIKE lower(%s)
                OR lower(descripcion) LIKE lower(%s)
              )
            ORDER BY inventario_id
            LIMIT {limit}
        """, (like_pattern, like_pattern))
        results = cur.fetchall()

        if results:
            return results

        # 1) Intento sin acentos (ya lo tenías)
        q_clean = (q or "")
        for a,b in (("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u")):
            q_clean = q_clean.replace(a,b)
        like_clean = f"%{q_clean}%"
        cur.execute(f"""
            SELECT inventario_id AS id, nombre, precio_cop, stock
            FROM {V_CATALOG}
            WHERE stock > 0
              AND (
                lower(replace(replace(replace(replace(replace(nombre, 'á', 'a'), 'é', 'e'), 'í', 'i'), 'ó', 'o'), 'ú', 'u')) LIKE lower(%s)
                OR lower(replace(replace(replace(replace(replace(descripcion, 'á', 'a'), 'é', 'e'), 'í', 'i'), 'ó', 'o'), 'ú', 'u')) LIKE lower(%s)
              )
            ORDER BY inventario_id
            LIMIT {limit}
        """, (like_clean, like_clean))
        results = cur.fetchall()
        if results:
            return results

        # 2) Intento singularizado (clave para "papeles", "jabones", etc.)
        q_sing = _singularize_phrase_es(q)
        if q_sing and q_sing != _norm(q):
            like_sing = f"%{q_sing}%"
            cur.execute(f"""
                SELECT inventario_id AS id, nombre, precio_cop, stock
                FROM {V_CATALOG}
                WHERE stock > 0
                  AND (
                    lower(replace(replace(replace(replace(replace(nombre, 'á', 'a'), 'é', 'e'), 'í', 'i'), 'ó', 'o'), 'ú', 'u')) LIKE lower(%s)
                    OR lower(replace(replace(replace(replace(replace(descripcion, 'á', 'a'), 'é', 'e'), 'í', 'i'), 'ó', 'o'), 'ú', 'u')) LIKE lower(%s)
                  )
                ORDER BY inventario_id
                LIMIT {limit}
            """, (like_sing, like_sing))
            results = cur.fetchall()

        return results



def get_product(pid):
    """Obtiene un producto específico por ID"""
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            f"SELECT inventario_id AS id, nombre, precio_cop, CAST(COALESCE(stock,0) AS BIGINT) AS stock "
            f"FROM {V_CATALOG} WHERE inventario_id = %s",
            (pid,)
        )
        return cur.fetchone()


def find_best_by_name(term: str):
    if not term or len(term.strip()) < 2:
        return None

    # Normaliza y crea variantes singularizadas
    term_norm = _norm(term)
    term_sing = _singularize_phrase_es(term_norm)

    # Usa ambas versiones para construir palabras
    palabras = [p for p in term_norm.split() if len(p) > 1]
    palabras_sing = [p for p in term_sing.split() if len(p) > 1]

    # Mezcla única de tokens (normales + sing.)
    tokens = []
    seen = set()
    for lst in (palabras, palabras_sing):
        for t in lst:
            if t not in seen:
                tokens.append(t); seen.add(t)

    # Si no quedaron tokens, intenta contra frase completa
    if not tokens:
        like_pattern = f"%{term_sing or term_norm}%"
        with _conn() as c, c.cursor() as cur:
            cur.execute(f"""
                SELECT inventario_id AS id, nombre, precio_cop, stock
                FROM {V_CATALOG}
                WHERE stock > 0
                  AND (
                    lower(replace(replace(replace(replace(replace(nombre, 'á', 'a'), 'é', 'e'), 'í', 'i'), 'ó', 'o'), 'ú', 'u')) LIKE %s
                    OR lower(replace(replace(replace(replace(replace(descripcion, 'á', 'a'), 'é', 'e'), 'í', 'i'), 'ó', 'o'), 'ú', 'u')) LIKE %s
                  )
                ORDER BY LENGTH(nombre) ASC
                LIMIT 5
            """, (like_pattern, like_pattern))
            row = cur.fetchone()
            return (row[0], row[1]) if row else None

    like_patterns = [f"%{p}%" for p in tokens]

    or_conditions_nombre = " OR ".join([
        "lower(replace(replace(replace(replace(replace(nombre, 'á', 'a'), 'é', 'e'), 'í', 'i'), 'ó', 'o'), 'ú', 'u')) LIKE %s"
        for _ in like_patterns
    ])
    or_conditions_desc = " OR ".join([
        "lower(replace(replace(replace(replace(replace(descripcion, 'á', 'a'), 'é', 'e'), 'í', 'i'), 'ó', 'o'), 'ú', 'u')) LIKE %s"
        for _ in like_patterns
    ])

    query = f"""
        SELECT inventario_id AS id, nombre, precio_cop, stock
        FROM {V_CATALOG}
        WHERE stock > 0
          AND ({or_conditions_nombre} OR {or_conditions_desc})
        ORDER BY LENGTH(nombre) ASC
        LIMIT 15
    """
    params = tuple(like_patterns + like_patterns)

    with _conn() as c, c.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    if not rows:
        return None

    # Scoring: cuántos tokens (incluida la versión singular) aparecen en el nombre normalizado
    best, score = None, -1
    for r in rows:
        _, nombre, *_ = r
        nombre_norm = _norm(nombre)
        s = sum(1 for w in tokens if w in nombre_norm)
        if s > score:
            best, score = r, s

    return (best[0], best[1]) if best else None



def decrease_stock(pid, qty):
    """
    Baja de stock segura aun si hay NULLs.
    Retorna True si se pudo descontar, False si no hay stock suficiente.
    """
    with _conn() as c, c.cursor() as cur:
        try:
            # Estrategia: Hacer UPDATE directo con condición de stock suficiente
            # Si el UPDATE afecta 0 filas, significa que no hay stock o no existe
            query = f"""
                UPDATE {INV_TABLE}
                SET stock = CAST(COALESCE(stock, 0) AS BIGINT) - {int(qty)}
                WHERE id = {int(pid)}
                  AND CAST(COALESCE(stock, 0) AS BIGINT) >= {int(qty)}
            """
            
            print(f"[DEBUG] Ejecutando: {query}")
            cur.execute(query)
            
            # Verificar cuántas filas fueron afectadas
            # Si rowcount es None o 0, no se pudo descontar
            affected = cur.rowcount if hasattr(cur, 'rowcount') else None
            
            if affected is None or affected == 0:
                print(f"⚠️ No se pudo descontar stock para producto {pid} (sin stock o no existe)")
                return False
            
            print(f"✅ Stock descontado exitosamente: producto {pid}, cantidad {qty}, filas afectadas: {affected}")
            return True
            
        except Exception as e:
            print(f"❌ Error en decrease_stock para producto {pid}: {e}")
            import traceback
            traceback.print_exc()
            return False


def save_order(chat_id: int, user_name: str, cart: dict) -> bool:
    """
    Guarda un pedido en la tabla pedidos.
    
    Args:
        chat_id: ID del chat de Telegram (se usa como cliente_id)
        user_name: Nombre del usuario
        cart: Diccionario {producto_id: cantidad}
    
    Returns:
        True si se guardó exitosamente, False en caso contrario
    """
    if not cart:
        return False
    
    try:
        with _conn() as c, c.cursor() as cur:
            # Calcular total del pedido y preparar items
            total = 0
            items_list = []
            
            for pid, qty in cart.items():
                row = get_product(pid)
                if not row:
                    continue
                _, nombre, precio, _ = row
                subtotal = float(precio) * qty
                total += subtotal
                
                # Escapar comillas simples en el nombre
                nombre_escaped = str(nombre).replace("'", "''")
                
                # Crear STRUCT para cada item
                items_list.append(
                    f"STRUCT({int(pid)} AS inventario_id, {int(qty)} AS cantidad, "
                    f"{int(precio)} AS precio_cop, '{nombre_escaped}' AS nombre)"
                )
            
            if not items_list:
                return False
            
            # Construir el ARRAY de structs
            items_array = f"ARRAY({', '.join(items_list)})"
            
            # Escapar comillas en las notas
            notas = f"Pedido de {user_name} (Telegram ID: {chat_id})"
            notas_escaped = notas.replace("'", "''")
            
            # Construir query completo sin parámetros para items
            query = f"""
                INSERT INTO {PEDIDOS_TABLE} 
                (cliente_id, estado, total_cop, items, notas, created_at)
                VALUES (
                    {int(chat_id)}, 
                    'pendiente', 
                    {int(total)}, 
                    {items_array},
                    '{notas_escaped}', 
                    current_timestamp()
                )
            """
            
            print(f"[DEBUG] Ejecutando query: {query}")  # Para debug
            cur.execute(query)
            
            return True
            
    except Exception as e:
        print(f"Error guardando pedido: {e}")
        import traceback
        traceback.print_exc()
        return False