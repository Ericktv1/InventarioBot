# handlers/multi_product.py
import re
from telegram import Update
from telegram.ext import ContextTypes
from services import dbx
from handlers.sales import add


# Mapeo de números en texto a dígitos
NUMEROS_TEXTO = {
    'un': 1, 'uno': 1, 'una': 1,
    'dos': 2,
    'tres': 3,
    'cuatro': 4,
    'cinco': 5,
    'seis': 6,
    'siete': 7,
    'ocho': 8,
    'nueve': 9,
    'diez': 10,
    'once': 11,
    'doce': 12,
    'quince': 15,
    'veinte': 20
}


def normalizar_numeros(text: str) -> str:
    """Convierte números en texto a dígitos"""
    text_lower = text.lower()
    for palabra, numero in NUMEROS_TEXTO.items():
        text_lower = re.sub(rf'\b{palabra}\b', str(numero), text_lower)
    return text_lower


async def parse_and_add_multiple_products(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """
    Parsea mensajes con múltiples productos y los agrega al carrito.
    
    Ejemplos:
    - "agrega 2 papel, 1 jabón y 3 toallas"
    - "quiero 2 de papel 1 jabon y 3 toallas"
    - "añade 5 shampoo, 2 jabones y 1 papel"
    - "dame dos papel y un jabon"
    """
    
    # Normalizar números en texto a dígitos
    text_normalizado = normalizar_numeros(text)
    print(f"[PARSER] Texto normalizado: {text_normalizado}")
    
    # Intentar encontrar patrones como "2 papel", "1 jabón", "3 toallas"
    # Patrón mejorado que captura hasta el siguiente número o conector
    matches = re.findall(
        r'(\d+)\s+(?:de\s+)?([a-záéíóúñü\s]+?)(?=\s+\d+|\s+y\s+|\s*,\s*|$)',
        text_normalizado,
        re.IGNORECASE
    )
    
    print(f"[PARSER] Matches encontrados: {matches}")
    
    if not matches:
        print("[PARSER] No se encontraron matches")
        return False
    
    productos_encontrados = []
    
    for qty_str, producto_nombre in matches:
        qty = int(qty_str)
        
        # Limpiar nombre del producto
        producto_nombre = producto_nombre.strip()
        # Remover conectores al final
        producto_nombre = re.sub(r'\s+(y|de|del|la|el|los|las|un|una)\s*$', '', producto_nombre, flags=re.IGNORECASE).strip()
        
        print(f"[PARSER] Procesando: '{producto_nombre}' qty={qty}")
        
        if not producto_nombre or len(producto_nombre) < 2:
            print(f"[PARSER] Nombre muy corto, saltando")
            continue
        
        # Buscar el producto en la base de datos
        result = dbx.find_best_by_name(producto_nombre)
        
        if result:
            pid, nombre_real = result
            print(f"[PARSER] ✅ Encontrado: {nombre_real} (ID: {pid})")
            productos_encontrados.append({
                'pid': pid,
                'qty': qty,
                'nombre': nombre_real,
                'busqueda': producto_nombre
            })
        else:
            print(f"[PARSER] ❌ No encontrado: {producto_nombre}")
    
    # Si no encontramos ningún producto, retornar False
    if not productos_encontrados:
        print("[PARSER] No se encontraron productos en la BD")
        return False
    
    # Agregar todos los productos encontrados
    exitosos = []
    fallidos = []
    
    for producto in productos_encontrados:
        try:
            await add(update, context, producto['pid'], producto['qty'])
            exitosos.append(f"{producto['nombre']} x{producto['qty']}")
            print(f"[PARSER] ✅ Agregado: {producto['nombre']} x{producto['qty']}")
        except Exception as e:
            print(f"[PARSER] ❌ Error agregando {producto['nombre']}: {e}")
            fallidos.append(f"{producto['busqueda']} (error al agregar)")
    
    # Mensaje de resumen
    if exitosos:
        mensaje = "✅ Agregado al carrito:\n" + "\n".join(f"• {p}" for p in exitosos)
        if fallidos:
            mensaje += "\n\n⚠️ No se pudieron agregar:\n" + "\n".join(f"• {p}" for p in fallidos)
        await update.message.reply_text(mensaje)
        return True
    
    return False


def parece_lista_productos(text: str) -> bool:
    """
    Detecta si el mensaje parece contener múltiples productos.
    
    Indicadores:
    - Tiene números seguidos de palabras
    - Contiene "y" o comas entre productos
    - Palabras clave como "quiero", "agrega", "añade"
    """
    text_lower = text.lower()
    
    # Verificar palabras clave
    keywords = ['agrega', 'añade', 'añadir', 'agregar', 'quiero', 'dame']
    tiene_keyword = any(kw in text_lower for kw in keywords)
    
    # Contar cuántos números tiene (dígitos o palabras)
    numeros_digitos = re.findall(r'\d+', text)
    numeros_palabras = [palabra for palabra in NUMEROS_TEXTO.keys() if palabra in text_lower]
    total_numeros = len(numeros_digitos) + len(numeros_palabras)
    
    # Verificar conectores
    tiene_conectores = bool(re.search(r'\s+y\s+|\s*,\s*', text_lower))
    
    # Es probable que sea lista si:
    # - Tiene keyword Y al menos un número
    # - O tiene múltiples números (2+) Y conectores
    return (tiene_keyword and total_numeros >= 1) or (total_numeros >= 2 and tiene_conectores)