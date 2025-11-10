from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from services.asr import transcribe_bytes
from services.llm import chat as llm_chat
from services.n8n import call_n8n
from domain.state import chats
from services.config import ASR_PROMPT

async def on_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg: return
    f = None
    if msg.voice: f = await msg.voice.get_file()
    elif msg.audio: f = await msg.audio.get_file()
    elif msg.video_note: f = await msg.video_note.get_file()
    elif msg.video: f = await msg.video.get_file()
    elif msg.document:
        fname = (msg.document.file_name or "").lower()
        mime = (msg.document.mime_type or "").lower()
        if fname.endswith((".mp3",".m4a",".wav",".ogg",".oga",".opus",".flac",".aac")) or mime.startswith("audio/"):
            f = await msg.document.get_file()
        elif fname.endswith((".mp4",".mov",".webm",".mkv",".avi")) or mime.startswith("video/"):
            f = await msg.document.get_file()
        else:
            return
    else:
        return

    async def _down(dst): await f.download_to_drive(dst)
    try:
        text = transcribe_bytes(_down)
        if not text:
            await msg.reply_text("(no se pudo transcribir el audio)"); return

        chat_id = update.effective_chat.id
        n8n_reply = await call_n8n({"type":"audio","text":text,"user_id":chat_id,"username":update.effective_user.username})
        if n8n_reply:
            chats[chat_id].append({"role":"assistant","content":n8n_reply})
            await msg.reply_text(n8n_reply); return

        instruccion = (
            "Eres un asistente que responde SIEMPRE en español, breve y correcto. "
            "Usa el texto transcrito del audio como entrada principal. "
            "Si hay una pregunta, respóndela; si no, responde útilmente en 1–2 oraciones."
        )
        contenido_usuario = f"{instruccion}\n\n[AUDIO TRANSCRITO]:\n{text}\n\nResponde con 1 a 2 oraciones, sin preámbulos."
        chats[chat_id].append({"role":"user","content":contenido_usuario})
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        reply = llm_chat(chat_id, temperature=0.15)
        chats[chat_id].append({"role":"assistant","content":reply})
        await msg.reply_text(reply if reply else "(Respuesta vacía)")
    except Exception as e:
        await msg.reply_text(f"Error procesando audio/video: {e}")
