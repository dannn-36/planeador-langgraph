"""
config.py — Configuración central del taller.

Todo lo que un estudiante podría querer cambiar (modelo, URL de Ollama,
límite de pasos del supervisor) vive aquí, en un solo lugar.
"""
import os

# Modelo de Ollama. DEBE soportar "tools" (compruébalo con: ollama show <modelo>).
# qwen2.5:3b (~1.9 GB) funciona en portátiles básicos sin GPU.
# Alternativas: llama3.2:3b (más rápido) o qwen3.5:4b (más preciso, más lento).
MODELO = os.getenv("MODELO_OLLAMA", "qwen2.5:3b")

# Dirección del servidor de Ollama (local o contenedor Docker con el puerto publicado).
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Límite de autonomía: cuántos agentes especialistas puede llamar el supervisor
# antes de pasar obligatoriamente a la respuesta final.
# (Con el reto hay 4 especialistas, pero el límite sigue siendo 3 por pregunta.)
MAX_PASOS = 3
