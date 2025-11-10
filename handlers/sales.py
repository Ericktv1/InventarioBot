# handlers/sales.py
from telegram import Update
from telegram.ext import ContextTypes
from services import dbx
from utils.money import fmt_money
from utils.text import _norm, to_qty
from domain.state import carts
from typing import Optional
from services.gemini import interpret_user_message


def _texto_producto(pid, nombre, precio, stock):
    return f"#{pid} {nombre}\nPrecio: {fmt_money(precio)}\nStock: {stock}"


# handlers/sales.py (arriba, junto a _texto_producto)
def _mensaje_instrucciones_pedido() -> str:
    return (
        "📋 *Cómo pedir productos*\n"
        "• Por nombre: <cantidad de productos> <nombre producto>  \n"
        "  Ej: `agrega 2 papel higienico`\n\n"
        "• Puedes decir *ver carrito*, para ver los productos que haz agregado.\n"
        "• Puedes decir *pagar*, para registrar el pedido.\n"
    )


async def cmd_menu(update: Update):
    from .commands import MENU_TEXT
    await update.message.reply_text(MENU_TEXT)


# ===== Listar catálogo =====
async def productos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rows = dbx.list_products(limit=6)  # (id, nombre, precio, stock)
    except Exception as e:
        await update.message.reply_text(f"Error consultando catálogo: {e}")
        return
    
    if not rows:
        await update.message.reply_text("No hay productos disponibles.")
        return
    
    for (pid, nombre, precio, stock) in rows:
        await update.message.reply_text(_texto_producto(pid, nombre, precio, stock))
    
    await update.message.reply_text(_mensaje_instrucciones_pedido(),parse_mode="Markdown")


# ===== Buscar =====
async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE, term: str):
    try:
        rows = dbx.search_products(term, limit=6)  # (id, nombre, precio, stock)
    except Exception as e:
        await update.message.reply_text(f"Error buscando: {e}")
        return
    
    if not rows:
        await update.message.reply_text("Sin resultados.")
        return
    
    for (pid, nombre, precio, stock) in rows:
        await update.message.reply_text(_texto_producto(pid, nombre, precio, stock))
    
    await update.message.reply_text("Usa /add <Cantidad> <producto> para agregar al carrito.")


# ===== Agregar al carrito =====
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE, pid: int, qty: int):
    try:
        row = dbx.get_product(pid)  # (id, nombre, precio, stock)
    except Exception as e:
        await update.message.reply_text(f"Error consultando producto: {e}")
        return
    
    if not row:
        await update.message.reply_text("Producto no encontrado.")
        return
    
    _, nombre, precio, stock = row
    
    if stock < qty:
        await update.message.reply_text(f"Stock insuficiente. Disponible: {stock}")
        return
    
    carts[update.effective_chat.id][pid] += qty
    await update.message.reply_text(
        f"Agregado: {nombre} x{qty}. Usa /carrito para ver tu carrito."
    )


# ===== Ver carrito =====
async def carrito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cart = carts[update.effective_chat.id]
    
    if not cart:
        await update.message.reply_text("Tu carrito está vacío.")
        return
    
    lines, total = [], 0.0
    for pid, qty in cart.items():
        row = dbx.get_product(pid)  # (id, nombre, precio, stock)
        if not row:
            continue
        _, nombre, precio, _ = row
        subtotal = float(precio) * qty
        total += subtotal
        lines.append(f"#{pid} {nombre} x{qty} = {fmt_money(int(subtotal))}")
    
    lines.append(f"\nTOTAL: {fmt_money(int(total))}")
    lines.append("\nUsa /checkout para confirmar o /vaciar para vaciar el carrito.")
    await update.message.reply_text("\n".join(lines))


# ===== Vaciar =====
async def vaciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    carts[update.effective_chat.id].clear()
    await update.message.reply_text("Carrito vaciado.")


# ===== Checkout =====
async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cart = carts[update.effective_chat.id]
    
    if not cart:
        await update.message.reply_text("Tu carrito está vacío.")
        return
    
    # Obtener nombre del usuario
    user = update.effective_user
    user_name = user.first_name or user.username or f"Usuario_{user.id}"
    
    try:
        # Guardar el pedido ANTES de descontar stock
        if not dbx.save_order(update.effective_chat.id, user_name, dict(cart)):
            await update.message.reply_text(
                "⚠️ Hubo un error al guardar tu pedido. Intenta nuevamente."
            )
            return
        
        print(f"✅ Pedido guardado exitosamente para {user_name}")
        
        # Ahora descontar stock
        fallos = []
        for pid, qty in cart.items():
            try:
                if not dbx.decrease_stock(pid, qty):
                    fallos.append(pid)
            except Exception as e:
                print(f"Error descontando stock para producto {pid}: {e}")
                fallos.append(pid)
        
        if fallos:
            await update.message.reply_text(
                f"⚠️ Pedido guardado, pero no se pudo actualizar stock de algunos ítems: {fallos}. "
                "Contacta al administrador."
            )
            # No vaciamos el carrito en caso de fallo
            return
        
        cart.clear()
        await update.message.reply_text(
            "✅ ¡Pedido confirmado y guardado! Te contactaremos por este chat para coordinar entrega y pago. 🙌\n\n"
            f"📦 Tu pedido ha sido registrado como: {user_name}"
        )
        
    except Exception as e:
        print(f"Error en checkout: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "⚠️ Hubo un error procesando tu pedido. Por favor intenta nuevamente."
        )


# ---------- Reglas NLP para mapear texto libre a comandos ----------
def map_text_to_command(text: str) -> Optional[str]:
    """Usa IA (Gemini) para entender la intención del usuario."""
    command = interpret_user_message(text)
    print(f"[Gemini interpretó]: '{text}' → {command}")  # 👈 depuración temporal
    
    if command.lower() in ("ninguno", "none", ""):
        return None
    
    return command