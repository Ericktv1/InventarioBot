import os
from services.logging import logger
from .wiring import build_app

def main():
    app = build_app()

    # Limpia posibles webhooks antiguos
    app.bot.delete_webhook(drop_pending_updates=True)

    logger.info("Bot iniciado con webhook en Render...")

    # Obtén la URL pública de Render
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not render_url or not token:
        raise RuntimeError("Faltan variables RENDER_EXTERNAL_URL o TELEGRAM_BOT_TOKEN")

    # Configura el webhook
    webhook_url = f"{render_url}/{token}"  # Telegram recomienda usar el token al final

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        webhook_url=webhook_url
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot detenido por el usuario.")
