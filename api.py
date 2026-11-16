"""
api.py — Expone el planeador con el MISMO contrato REST del proyecto pruebachat.

Así el frontend del curso (frontend/src/index.html) funciona sin cambios
contra este backend en Python, igual que contra el backend en Spring AI.

Uso:
    uvicorn api:app --port 8080
"""
import json
import time
import urllib.request
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import OLLAMA_URL
from grafo import planear

app = FastAPI(title="Planeador de fin de semana - LangGraph")

# Mismo permiso CORS que @CrossOrigin del ChatController en Spring.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    sessionId: str | None = None


@app.post("/api/v1/chat")
def chat(req: ChatRequest):
    inicio = time.perf_counter()
    respuesta = planear(req.question)
    elapsed_ms = int((time.perf_counter() - inicio) * 1000)
    status = "ok" if respuesta and respuesta.strip() else "error"
    cuerpo = {"requestId": str(uuid.uuid4()), "answer": respuesta or "",
              "elapsedMs": elapsed_ms, "status": status}
    return JSONResponse(cuerpo, status_code=200 if status == "ok" else 502)


@app.get("/health/llm")
def health_llm():
    """Equivalente a LlmHealthController: consulta /api/tags de Ollama."""
    endpoint = OLLAMA_URL.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(endpoint, timeout=5) as r:
            return {"ok": True, "endpoint": endpoint, "result": json.load(r)}
    except Exception as error:
        return JSONResponse({"ok": False, "error": str(error)}, status_code=502)
