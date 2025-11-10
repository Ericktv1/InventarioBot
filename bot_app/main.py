import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from services.logging import logger
from .wiring import build_app  # si usas tu propia función build_app

TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_URL")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot de inventario 😊")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Recibí: {update.message.text}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    if RENDER_URL:
        logger.info("Iniciando bot con webhook en Render...")

        # ⚠️ Aquí es clave: el webhook_url debe incluir el token al final
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", 8443)),
            url_path=TOKEN,
            webhook_url=f"{RENDER_URL}/{TOKEN}",
        )
    else:
        logger.info("Iniciando bot en modo polling (local)...")
        app.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot detenido por el usuario.")
