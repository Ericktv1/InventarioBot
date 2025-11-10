from telegram import Update
from telegram.ext import ContextTypes
from domain.state import chats, carts
from handlers.sales import productos, buscar, carrito, vaciar, checkout
from handlers.text import _resolver_y_agregar

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Soy tu bot con catálogo de productos, Ollama + n8n.\n"
        "• /menu para ver comandos.\n"
        "• Texto: respondo con n8n (si hay flujo) o con el modelo local.\n"
        "• Audio: transcribo y respondo.\n"
        "• Imágenes: describo y respondo.\n"
        "Usa /reset para borrar el contexto."
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chats[chat_id].clear()
    carts[chat_id].clear()
    await update.message.reply_text("Contexto y carrito borrados. ¡Empecemos de cero!")


async def cmd_productos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await productos(update, context)

async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    term = " ".join(context.args).strip()
    if not term:
        await update.message.reply_text("Uso: /buscar <texto>")
        return
    await buscar(update, context, term)

async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /add <cantidad><nombre> ")
        return
    # Reutiliza tu parser para id|nombre + cantidad
    await _resolver_y_agregar(update, context, context.args)

async def cmd_carrito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await carrito(update, context)

async def cmd_vaciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await vaciar(update, context)

async def cmd_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await checkout(update, context)
    
MENU_TEXT = (
    "Comandos disponibles:\n"
    "• /productos – ver catálogo\n"
    "• /buscar <texto> – buscar productos\n"
    "• /add <id> [cantidad] – agregar al carrito\n"
    "• /carrito – ver carrito actual\n"
    "• /vaciar – vaciar carrito\n"
    "• /checkout – confirmar compra"
)

