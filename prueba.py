import google.generativeai as genai

API_KEY = "AIzaSyBRlGx-0ymfgMU7B6rvDDEOJF7DSkkaoEQ"  # pega aquí la clave nueva
genai.configure(api_key=API_KEY)

# Verifica que el servicio responde y que el modelo existe
models = [m.name for m in genai.list_models()]
print("Modelos disponibles (recorte):", models[:5])

model = genai.GenerativeModel("gemini-2.5-flash-lite")
resp = model.generate_content("Hola, ¿puedes responder?")
print("Respuesta:", resp.text)
