"""prueba_ollama.py — Verifica que Python se comunica con el modelo de Ollama."""
from langchain_ollama import ChatOllama

from config import MODELO, OLLAMA_URL

modelo = ChatOllama(model=MODELO, base_url=OLLAMA_URL, temperature=0)
respuesta = modelo.invoke("Responde en una sola frase: ¿qué es un agente de IA?")
print(f"Modelo: {MODELO}")
print(respuesta.content)
