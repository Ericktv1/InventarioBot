# handlers/text.py
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from handlers.sales import (
    productos, buscar, add, carrito, vaciar, checkout, map_text_to_command
)
from handlers.multi_product import parse_and_add_multiple_products, parece_lista_productos
from services.gemini_chat import chat_natural
from services import dbx
from handlers.sales import _mensaje_instrucciones_pedido

import re

# ---------- UI: teclado rápido ----------
def _menu_teclado():
    kb = [
        [KeyboardButton("🛒 Ver productos"), KeyboardButton("🧺 Ver carrito")],
        [KeyboardButton("❓ Ayuda")],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ---------- /start ----------
async def start_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bienvenida = (
        "👋 ¡Hola! Soy *Damon*, tu asistente de compras.\n\n"
        "Puedo ayudarte a ver nuestro catálogo, buscar productos o armar tu carrito 🛒.\n\n"
        "👉 ¿Quieres que te muestre los productos disponibles?"
    )
    await update.message.reply_text(
        bienvenida, reply_markup=_menu_teclado(), parse_mode="Markdown"
    )

# ---------- reglas rápidas ----------
SALUDOS = {
    "hola", "buenas", "holi", "que más", "qué más", "buenos días",
    "buenas tardes", "buenas noches", "hey", "saludos"
}

# Resolver "/add" aceptando ID o nombre + cantidad opcional
async def _resolver_y_agregar(update: Update, context: ContextTypes.DEFAULT_TYPE, arg_tokens: list[str]):
    qty = 1
    if arg_tokens and arg_tokens[-1].isdigit():
        qty = max(1, int(arg_tokens[-1]))
        arg_tokens = arg_tokens[:-1]

    if not arg_tokens:
        await update.message.reply_text("Uso: /add <id|nombre> [cantidad]")
        return

    # ¿Es ID?
    if len(arg_tokens) == 1 and arg_tokens[0].isdigit():
        pid = int(arg_tokens[0])
    else:
        nombre = " ".join(arg_tokens)
        match = dbx.find_best_by_name(nombre)
        if not match:
            await update.message.reply_text(
                f"No encontré un producto parecido a '{nombre}'. "
                "Prueba con /buscar <texto>."
            )
            return
        pid = match[0]

    await add(update, context, pid, qty)

# ---------- manejador principal ----------
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    user_text_l = user_text.lower()

    # 0) Confirmaciones cortas tipo "sí"
    if user_text_l in {"si", "sí", "claro", "dale"}:
        await productos(update, context); return

    # 1) Saludo vendedor
    if any(g in user_text_l for g in SALUDOS):
        await update.message.reply_text(
            "¡Hola 👋! ¿Te muestro el catálogo o buscas algo en específico?",
            reply_markup=_menu_teclado(),
        )
        return

    # 2) Botones/atajos rápidos
    if user_text_l in ("🛒 ver productos".lower(), "ver productos", "mostrar productos", "catálogo", "catalogo"):
        await productos(update, context); return

    if (
        user_text_l in ("🧺 ver carrito".lower(), "ver carrito", "mi carrito") or
        re.search(r"(ver|mostrar|muestra|muéstrame|muestrame).*(carrito)", user_text_l)
    ):
        await carrito(update, context); return

    if user_text_l in ("❓ ayuda".lower(), "ayuda", "/ayuda", "/menu", "menu"):
        await update.message.reply_text(
            "Puedo mostrarte el catálogo (/productos), buscar (/buscar <texto>), "
            "agregar (/add <cantidad de productos> <nombre producto>), ver tu carrito (/carrito) y confirmar un pedido (/checkout).\n\n",
            reply_markup=_menu_teclado(),
        )
        return

    # 3) Checkout & Vaciar con lenguaje natural
    if re.search(r"\b(pagar|checkout|finalizar( la)? compra|confirmar( el)? pedido|confirmar compra|realizar compra|hacer pago)\b", user_text_l):
        await checkout(update, context); return

    if re.search(r"\b(vaciar|vacía|vaciar el carrito|vaciar carrito|limpia el carrito|limpiar carrito)\b", user_text_l):
        await vaciar(update, context); return

    # 🆕 4) DETECTAR MÚLTIPLES PRODUCTOS EN UN MENSAJE
    # Ejemplo: "quiero 2 papel, 1 jabón y 3 toallas"
    if parece_lista_productos(user_text):
        print(f"[MULTI-PRODUCTO] Detectado: {user_text}")
        if await parse_and_add_multiple_products(update, context, user_text):
            return  # Ya se procesó

    # 5) IA (Gemini) → comando (solo para comandos claros de compra)
    # Detectar si es una solicitud de COMPRA o una conversación casual
# 5) IA (Gemini) → comando (solo para comandos claros de compra)
    # Detectar si es una solicitud de COMPRA o una conversación casual
    palabras_compra = ['add', 'agrega', 'añade', 'quiero', 'dame', 'comprar', 
                       'productos', 'producto', 'catalogo', 'catálogo', 'buscar',
                       'carrito', 'pagar', 'checkout', 'vaciar']
    
    es_solicitud_compra = any(palabra in user_text_l for palabra in palabras_compra)
    
    if es_solicitud_compra:
        mapped = map_text_to_command(user_text)
        
        if mapped:
            lower = mapped.lower()
            
            if lower in ("/menu", "menu", "/ayuda", "ayuda"):
                await update.message.reply_text(
                    "Elige una opción o escribe: /productos, /buscar <texto>, /carrito, /checkout.",
                    reply_markup=_menu_teclado(),
                )
                return

            if lower.startswith("/productos"):
                await productos(update, context); return

            if lower.startswith("/buscar"):
                parts = mapped.split(maxsplit=1)
                term = parts[1].strip() if len(parts) > 1 else ""
                if not term:
                    await update.message.reply_text("Uso: /buscar <texto>"); return
                await buscar(update, context, term); return

            if lower.startswith("/add"):
                parts = mapped.split()
                args = parts[1:]

                if not args:
                    await update.message.reply_text("Uso: /add <id|nombre> [cantidad]"); 
                    return

                stop = {"de", "del", "la", "el", "los", "las"}
                args = [t for t in args if t.lower() not in stop]

                qty = 1
                if args and args[-1].isdigit():
                    qty = max(1, int(args[-1])); args = args[:-1]
                elif args and args[0].isdigit():
                    qty = max(1, int(args[0])); args = args[1:]

                if not args:
                    await update.message.reply_text("Uso: /add <id|nombre> [cantidad]")
                    return

                pid = None
                if len(args) == 1 and args[0].isdigit():
                    pid = int(args[0])
                else:
                    nombre = " ".join(args)
                    match = dbx.find_best_by_name(nombre)
                    if not match:
                        await update.message.reply_text(
                            f"No encontré un producto parecido a '{nombre}'. Prueba con /buscar <texto>."
                        )
                        return
                    pid = match[0]

                await add(update, context, pid, qty)
                return

            if lower.startswith("/carrito"):
                await carrito(update, context); return

            if lower.startswith("/vaciar"):
                await vaciar(update, context); return

            if lower.startswith("/checkout"):
                await checkout(update, context); return
    
    # 5.5) CHAT NATURAL - Si no es comando de compra
    else:
        user = update.effective_user
        user_name = user.first_name or user.username or "Usuario"
        
        print(f"[CHAT NATURAL] Usuario: {user_name} - Mensaje: {user_text}")
        respuesta = chat_natural(user_text, user_name)
        await update.message.reply_text(respuesta, reply_markup=_menu_teclado())
        return

    # 6) Orquestación n8n (opcional)
    from services.n8n import call_n8n
    n8n_result = await call_n8n({
        "type": "text",
        "text": user_text,
        "user_id": update.effective_chat.id,
        "username": update.effective_user.username,
    })

    if isinstance(n8n_result, str) and n8n_result.strip():
        await update.message.reply_text(n8n_result.strip(), reply_markup=_menu_teclado())
        return

    if isinstance(n8n_result, dict):
        cmd = (n8n_result.get("command") or "").lower().strip()
        if cmd:
            if cmd.startswith("/productos"):
                await productos(update, context); return
            if cmd.startswith("/carrito"):
                await carrito(update, context); return
            if cmd.startswith("/checkout"):
                await checkout(update, context); return
            if cmd.startswith("/vaciar"):
                await vaciar(update, context); return
            if cmd.startswith("/add"):
                parts = cmd.split()
                if len(parts) < 2:
                    await update.message.reply_text("Uso: /add <id|nombre> [cantidad]"); return
                await _resolver_y_agregar(update, context, parts[1:]); return

        reply = (
            n8n_result.get("respuesta")
            or n8n_result.get("reply")
            or n8n_result.get("res")
            or n8n_result.get("message")
        )
        if isinstance(reply, str) and reply.strip():
            await update.message.reply_text(reply.strip(), reply_markup=_menu_teclado())
            return

    # 7) Fallback final
    await update.message.reply_text(
        "No te entendí bien 🤔. ¿Quieres que te muestre los productos disponibles?\n\n"
        "💡 Tip: Puedes decir cosas como:\n"
        "• 'quiero 2 papel, 1 jabón y 3 toallas'\n"
        "• 'agrega 5 shampoo'\n"
        "• 'ver carrito'",
        + _mensaje_instrucciones_pedido(),
        reply_markup=_menu_teclado(),
         parse_mode="Markdown",
    )