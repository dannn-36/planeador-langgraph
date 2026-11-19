# Planeador de fin de semana multiagente (LangGraph + Ollama)

Taller del Módulo 3 — *Aplicaciones basadas en grandes modelos de lenguaje*, Universidad El Bosque.

Un supervisor coordina a cuatro agentes especialistas (clima, presupuesto, reservas y
**actividades**, este último es el reto de la Parte 7) que usan herramientas sobre datos
ficticios en memoria. Un sintetizador redacta la respuesta final. El modelo corre en local con Ollama.

```
pregunta → supervisor → (clima | presupuesto | actividades | reservas) → supervisor → … → sintetizador → respuesta
```

## Requisitos

- Python 3.11 o superior
- [Ollama](https://ollama.com) corriendo en `http://localhost:11434`
- Un modelo con capacidad `tools` (por defecto `qwen2.5:3b`, ≈ 1,9 GB)

## Instalación

### Opción recomendada: Docker Compose

Solo requiere Docker Desktop. El primer arranque descarga la imagen de Ollama y el modelo
`qwen2.5:3b` (aproximadamente 1,9 GB); los siguientes reutilizan el volumen local.

```bash
docker compose up --build
```

Cuando los servicios estén listos:

- API: http://localhost:8080
- Documentación interactiva: http://localhost:8080/docs
- Salud de Ollama: http://localhost:8080/health/llm

Prueba rápida desde otra terminal:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8080/api/v1/chat" `
  -ContentType "application/json" `
  -Body '{"question":"¿Cómo estará el clima en Guatavita el domingo?"}'
```

Para detener los servicios sin borrar el modelo descargado:

```bash
docker compose down
```

Para ver la traza de los agentes si los servicios se levantaron en segundo plano:

```bash
docker compose logs -f api
```

Para usar otro modelo compatible con tools:

```bash
# PowerShell
$env:MODELO_OLLAMA = "llama3.2:3b"
docker compose up --build
```

> `docker compose down -v` también elimina el volumen y el modelo descargado.

### Opción manual: Python y Ollama instalados localmente

```bash
ollama pull qwen2.5:3b
ollama show qwen2.5:3b        # en "Capabilities" debe aparecer: tools

python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Windows (cmd):         .venv\Scripts\activate
# macOS / Linux:         source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecución

| Comando | Qué hace |
|---|---|
| `python prueba_ollama.py` | Punto de control 1: Python habla con el modelo |
| `python prueba_agente.py` | Punto de control 3: ciclo ReAct de un solo agente |
| `python main.py` | Chat por consola con el planeador |
| `python main.py --grafo` | Imprime el grafo en Mermaid (pegar en https://mermaid.live) |
| `python pruebas.py` | Corre las 6 preguntas de prueba + la del reto, con traza y tiempos |
| `python pruebas.py 4` | Corre solo la pregunta 4 |
| `uvicorn api:app --port 8080` | API REST con el contrato de pruebachat (`POST /api/v1/chat`, `GET /health/llm`) |
| `docker compose up --build` | Levanta Ollama, descarga el modelo y arranca la API |

Para cambiar de modelo o de servidor sin tocar el código:

```bash
# PowerShell
$env:MODELO_OLLAMA = "llama3.2:3b"
$env:OLLAMA_URL = "http://localhost:11434"
```

### Conectar con el frontend del curso (Parte 6)

```bash
docker stop pruebachat_backend            # libera el puerto 8080
uvicorn api:app --port 8080
# desde la carpeta del proyecto pruebachat:
docker compose -f docker/docker-compose.yml up -d --no-deps frontend
# o sin Docker:  npx http-server frontend/src -p 4200
```

Abrir http://localhost:4200. Documentación interactiva de la API en http://localhost:8080/docs.

## Archivos

| Archivo | Contenido |
|---|---|
| `config.py` | Modelo, URL de Ollama y límite de autonomía (`MAX_PASOS = 3`) |
| `datos.py` | Destinos, pronóstico, cupos, actividades y normalización de texto |
| `herramientas.py` | Las 7 tools (`@tool`) |
| `agentes.py` | Los 4 agentes especialistas (`create_agent`) |
| `grafo.py` | Estado, supervisor, nodos, arista condicional y grafo compilado |
| `main.py` | Chat por consola |
| `api.py` | API FastAPI |
| `Dockerfile` | Imagen reproducible de la API en Python 3.12 |
| `compose.yaml` | Orquesta Ollama, descarga del modelo y API |
| `pruebas.py` | Preguntas de prueba con traza y tiempos |
| `docs/bitacora.pdf` | Bitácora del grupo (fuente: `docs/bitacora.html`) |
| `docs/traza_pruebas.txt` | Traza completa de la última corrida de `pruebas.py` |

## Reto elegido (Parte 7): nuevo especialista — Agente de Actividades

- **Datos:** `ACTIVIDADES` en `datos.py` (3 actividades por destino, con tipo y duración).
- **Tool:** `recomendar_actividades(destino)` en `herramientas.py`.
- **Agente:** `agente_actividades` y `PROMPT_ACTIVIDADES` en `agentes.py`.
- **Grafo:** nodo `actividades`, su arista de vuelta al supervisor, la entrada en la arista
  condicional, el campo `pide_actividades` en `Decision` y los prompts del supervisor y del sintetizador.

Prueba: `python pruebas.py 7`.

## Ajustes respecto al código guía del taller

Con el código tal cual de la guía, `qwen2.5:3b` fallaba varias preguntas. Los cambios (todos
comentados en el código y explicados en la bitácora) son:

1. **Supervisor con lista de verificación.** `Decision` ya no pide elegir directamente el
   siguiente agente: el modelo marca qué temas aparecen en la pregunta y el código calcula
   `siguiente` con un orden fijo (reservas siempre de último).
2. **Red de seguridad por palabras clave** en el supervisor: si la pregunta dice "llueve",
   "alcanza", "reserva"…, el agente se consulta aunque el LLM no lo haya marcado.
3. **`calcular_saldo(destino, personas, presupuesto)`** en vez de `(presupuesto, costo_total)`:
   el modelo pedía las dos tools en paralelo e inventaba el costo.
4. **Datos verificados:** al resultado de cada especialista se le adjunta la salida literal de
   sus tools, y solo el agente de reservas ve los resultados de los demás.
5. **Destinos mal escritos** ("Sueska", "Villa de Leyca") se aceptan por similitud (`difflib`).
