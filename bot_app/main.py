from services.logging import logger
from .wiring import build_app

def main():
    app = build_app()
    logger.info("Bot iniciado. Escuchando actualizaciones...")
    app.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot detenido por el usuario.")
