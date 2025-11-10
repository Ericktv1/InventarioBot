import pathlib, tempfile
from telegram import Update
from telegram.ext import ContextTypes
from services.vision import describe_image
from services.llm import chat as llm_chat
from services.n8n import call_n8n
from services.config import SYSTEM_PROMPT
from domain.state import chats

async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photos = update.message.photo
        tg_photo = photos[-1] if len(photos) < 3 else photos[-2]
        file_id = tg_photo.file_id
    elif update.message.document and (update.message.document.mime_type or "").startswith("image/"):
        file_id = update.message.document.file_id
    else:
        return

    tg_file = await context.bot.get_file(file_id)
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "img.bin"
        await tg_file.download_to_drive(str(p))
        img_bytes = p.read_bytes()

    vlm_reply = describe_image(img_bytes, SYSTEM_PROMPT)
    chat_id = update.effective_chat.id
    n8n_reply = await call_n8n({"type":"image","text":vlm_reply,"user_id":chat_id,"username":update.effective_user.username})
    final_reply = (n8n_reply or vlm_reply or "").strip()

    # Si vino en inglés, traduce rápido con el LLM de texto
    if final_reply and any(ch in final_reply for ch in "abcdefghijklmnopqrstuvwxyz") and not any(ch in final_reply for ch in "áéíóúñÁÉÍÓÚÑ"):
        chats[chat_id].append({"role":"user","content":f"Traduce al español, conciso: {final_reply}"})
        final_reply = llm_chat(chat_id, temperature=0.2) or final_reply

    await update.message.reply_text(final_reply or "(sin respuesta)")
