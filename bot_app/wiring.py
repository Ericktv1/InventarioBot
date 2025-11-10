# bot_app/wiring.py
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.request import HTTPXRequest
from services.config import TELEGRAM_BOT_TOKEN
from telegram.error import TelegramError
from services.logging import logger
from handlers.text import on_message, start_message
from handlers.commands import (
    reset,
    cmd_productos, cmd_buscar, cmd_add, cmd_carrito, cmd_vaciar, cmd_checkout
)
from handlers.audio import on_audio
from handlers.photo import on_photo
from telegram.constants import ParseMode

async def on_error(update, context):
    logger.exception("Excepción no controlada", exc_info=context.error)
    try:
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Ups, hubo un error. Intenta de nuevo por favor 🙏"
            )
    except TelegramError:
        pass

async def _post_init(app):
    # Opcional: que Telegram muestre el menú de comandos
    await app.bot.set_my_commands([
        ("start", "Iniciar"),
        ("productos", "Ver catálogo"),
        ("buscar", "Buscar producto"),
        ("add", "Agregar al carrito"),
        ("carrito", "Ver carrito"),
        ("vaciar", "Vaciar carrito"),
        ("checkout", "Confirmar pedido"),
        ("reset", "Reiniciar contexto"),
    ])

def build_app():
    request = HTTPXRequest(connect_timeout=20.0, read_timeout=60.0, write_timeout=20.0, pool_timeout=20.0)
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(request)
        .post_init(_post_init)   # <- para set_my_commands
        .build()
    )

    # Comandos explícitos
    app.add_handler(CommandHandler("start", start_message))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("productos", cmd_productos))
    app.add_handler(CommandHandler("buscar", cmd_buscar))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("carrito", cmd_carrito))
    app.add_handler(CommandHandler("vaciar", cmd_vaciar))
    app.add_handler(CommandHandler("checkout", cmd_checkout))

    # Otros manejadores
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, on_photo))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.VIDEO_NOTE | filters.VIDEO | filters.Document.ALL, on_audio))

    # Texto libre (IA, multi-producto, etc.) — excluye comandos
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    app.add_error_handler(on_error)
    return app
