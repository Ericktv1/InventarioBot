import os

USE_OLLAMA = os.getenv("USE_OLLAMA", "0") == "1"

if USE_OLLAMA:
    import ollama

def chat(prompt):
    if USE_OLLAMA:
        # Modo local con Ollama
        return ollama.chat(model=os.getenv("MODEL"), messages=[{"role": "user", "content": prompt}])
    else:
        # Modo remoto (Render) usando Gemini
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
        response = model.generate_content(prompt)
        return {"message": response.text}
