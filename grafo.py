"""
grafo.py — El sistema multiagente como un grafo de LangGraph.

              ┌──────────────┐
  START ────► │  supervisor  │ ◄─────────────────────────┐
              └──────┬───────┘                           │
        (arista condicional: ¿quién sigue?)              │
     ┌──────────┬────┴─────┬───────────┬──────────┐      │
     ▼          ▼          ▼           ▼          ▼      │
   clima   presupuesto  reservas  actividades  sintetizador ──► END
     │          │          │           │                 │
     └──────────┴──────────┴───────────┴─────────────────┘
                   (vuelven al supervisor)

"actividades" es el especialista agregado en el reto de la Parte 7.
"""
import operator
from typing import Annotated

from langchain_core.messages import ToolMessage
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from agentes import (agente_actividades, agente_clima, agente_presupuesto, agente_reservas,
                     crear_modelo)
from config import MAX_PASOS
from datos import normalizar


# ----------------------------------------------------------------------------
# 1. ESTADO: la "memoria compartida" que viaja por todos los nodos.
#    Annotated[list, operator.add] = REDUCER: lo que devuelve un nodo se
#    AGREGA a la lista en lugar de reemplazarla.
# ----------------------------------------------------------------------------
class EstadoPlaneador(TypedDict):
    pregunta: str
    resultados: Annotated[list[str], operator.add]
    consultados: Annotated[list[str], operator.add]
    siguiente: str
    respuesta_final: str


# ----------------------------------------------------------------------------
# 2. SALIDA ESTRUCTURADA del supervisor: en vez de texto libre, el modelo
#    debe devolver un objeto con estos campos (Ollama lo garantiza con un
#    JSON Schema). Así la decisión de enrutamiento es confiable.
# ----------------------------------------------------------------------------
#
#    Ajuste sobre el taller (ver bitácora): con qwen2.5:3b, pedirle al modelo
#    que eligiera directamente "siguiente" fallaba mucho (repetía agentes o
#    nunca decía "fin"). Ahora el modelo responde una LISTA DE VERIFICACIÓN
#    (¿la pregunta necesita clima? ¿presupuesto? ...), que es una tarea más
#    fácil, y el campo "siguiente" lo calcula el código en nodo_supervisor.
#    El LLM sigue decidiendo QUÉ agentes se necesitan; el código garantiza
#    el ORDEN (reservas de último) y el límite de autonomía.
# ----------------------------------------------------------------------------
class Decision(BaseModel):
    # Va PRIMERO a propósito: obliga al modelo a "leer" la pregunta por partes
    # antes de marcar los temas (razonamiento paso a paso dentro del esquema).
    partes: list[str] = Field(
        description="Copia literal de cada petición y de cada condición de la pregunta, una por elemento. "
                    "Ejemplo: ['si no llueve mucho', 'si nos alcanza', 'reserva Chicaque el domingo'].")
    menciona_clima_o_lluvia: bool = Field(
        description="true si la pregunta menciona clima, tiempo, lluvia, llover, sol o temperatura, "
                    "aunque sea como condición ('si no llueve').")
    menciona_dinero_o_costo: bool = Field(
        description="true si la pregunta menciona dinero, costo, precio, pesos o si 'alcanza'.")
    pide_actividades: bool = Field(
        description="true solo si la pregunta pide actividades, planes o qué hacer en el destino.")
    pide_reservar_o_cupos: bool = Field(
        description="true solo si la pregunta pide reservar o pregunta por cupos.")


# Campo de la Decision -> agente que lo atiende. El ORDEN del diccionario es el
# orden de atención: reservas SIEMPRE de último, para que vea los resultados de
# clima y presupuesto antes de reservar.
CAMPO_A_AGENTE = {
    "menciona_clima_o_lluvia": "clima",
    "menciona_dinero_o_costo": "presupuesto",
    "pide_actividades": "actividades",
    "pide_reservar_o_cupos": "reservas",
}

# Red de seguridad determinista (ver bitácora): con qwen2.5:3b el supervisor a
# veces no marca un tema que sí está en la pregunta (por ejemplo la condición
# "si no llueve mucho"). Si la pregunta contiene una de estas palabras, el
# agente se consulta aunque el LLM no lo haya marcado. Solo AGREGA agentes:
# nunca quita uno que el LLM sí pidió. (Texto ya normalizado: sin tildes.)
PALABRAS_CLAVE = {
    "clima": ("clima", "llueve", "lluvia", "llover", "llovera", "temperatura", "pronostico"),
    "presupuesto": ("alcanza", "cuesta", "costo", "precio", "presupuesto"),
    "actividades": ("actividad", "que hacer", "que podemos hacer"),
    "reservas": ("reserv", "cupo"),
}


PROMPT_SUPERVISOR = """Eres el SUPERVISOR de un planeador de salidas de fin de semana cerca de Bogotá.
Coordinas a cuatro agentes especialistas:
- clima: pronóstico del tiempo de un destino para el sábado o el domingo.
- presupuesto: costo del plan para un grupo y si el dinero alcanza.
- reservas: cupos disponibles y creación de reservas.
- actividades: qué hacer en el destino (senderismo, gastronomía, museos, aventura).

Lee la pregunta del usuario. Primero copia en "partes" cada petición y cada condición que contiene.
Después marca qué temas aparecen en esas partes. Marca true solo lo que la pregunta
dice de forma explícita; no agregues temas "por si acaso".
- menciona_clima_o_lluvia: clima, tiempo, lluvia, llover, sol o temperatura (también como condición).
- menciona_dinero_o_costo: dinero, costo, precio, pesos, presupuesto o "nos alcanza".
- pide_actividades: pregunta qué hacer, qué planes hay o pide recomendaciones.
- pide_reservar_o_cupos: pide reservar o pregunta por cupos.
Si la pregunta no trata de salidas de fin de semana (deportes, historia, tareas...), todo es false.

Ejemplos:
- "¿Lloverá en Suesca el sábado?" -> menciona_clima_o_lluvia=true; lo demás false.
- "Somos 4 con 300000, ¿nos alcanza para Chicaque?" -> menciona_dinero_o_costo=true; lo demás false.
- "Si nos alcanza, reserva Guatavita el domingo a nombre de Ana" -> menciona_dinero_o_costo=true,
  pide_reservar_o_cupos=true; lo demás false.
- "Somos 5 y tenemos 400000. Si no llueve mucho y nos alcanza, reserva Chicaque el domingo a nombre
  de Juan" -> menciona_clima_o_lluvia=true, menciona_dinero_o_costo=true, pide_reservar_o_cupos=true.
- "¿Qué podemos hacer en Zipaquirá?" -> pide_actividades=true; lo demás false.
- "¿Cuál es la capital de Francia?" -> todo false."""

PROMPT_SINTETIZADOR = """Eres el asistente final de un planeador de salidas de fin de semana.
Redacta la respuesta para el usuario usando SOLO los resultados de los agentes.
- No inventes datos que no estén en los resultados.
- Las cifras (temperaturas, % de lluvia, pesos, cupos, códigos) cópialas de los
  "Datos verificados de las herramientas". Si un agente dice algo distinto, valen los datos verificados.
- Solo di que hay una reserva si aparece "Reserva confirmada" con su código RES-.
- Organiza la respuesta en un párrafo corto o en viñetas, en español y con tono amable.
- Si se hizo una reserva, muestra el código.
- Si no hay resultados, explica que puedes ayudar con clima, presupuesto, reservas y actividades
  para Guatavita, Zipaquirá, Villa de Leyva, Suesca y Chicaque."""

modelo_supervisor = crear_modelo().with_structured_output(Decision)
modelo_sintetizador = crear_modelo()


def _contexto(estado: EstadoPlaneador) -> str:
    """Texto con la pregunta y lo que ya respondieron los agentes."""
    previos = "\n".join(estado["resultados"]) or "(todavía no hay resultados)"
    return f"Pregunta del usuario: {estado['pregunta']}\n\nResultados de otros agentes:\n{previos}"


# ----------------------------------------------------------------------------
# 3. NODOS: funciones que reciben el estado y devuelven SOLO lo que cambian.
# ----------------------------------------------------------------------------
def nodo_supervisor(estado: EstadoPlaneador) -> dict:
    consultados = estado["consultados"]
    if len(consultados) >= MAX_PASOS:            # límite de autonomía
        return {"siguiente": "fin"}

    mensaje = f"Pregunta del usuario: {estado['pregunta']}"
    try:
        decision = modelo_supervisor.invoke([("system", PROMPT_SUPERVISOR), ("human", mensaje)])
        pregunta = normalizar(estado["pregunta"])
        necesarios = [
            agente for campo, agente in CAMPO_A_AGENTE.items()
            if getattr(decision, campo)                                   # lo que decidió el LLM
            or any(palabra in pregunta for palabra in PALABRAS_CLAVE[agente])  # red de seguridad
        ]
        pendientes = [a for a in necesarios if a not in consultados]
        siguiente = pendientes[0] if pendientes else "fin"
        print(f"   [supervisor] necesita: {', '.join(necesarios) or 'ninguno'} | "
              f"consultados: {', '.join(consultados) or 'ninguno'} -> {siguiente} (partes: {decision.partes})")
    except Exception as error:                   # el modelo no devolvió un JSON válido
        print(f"   [supervisor] decisión inválida ({error}); se pasa a la respuesta final")
        siguiente = "fin"

    if siguiente in consultados:                 # evita ciclos infinitos
        siguiente = "fin"
    return {"siguiente": siguiente}


def crear_nodo_especialista(nombre: str, agente, ve_resultados_previos: bool = False):
    """Fábrica de nodos: envuelve un agente (create_agent) como nodo del grafo.

    Dos mejoras sobre el taller, para que un modelo pequeño no invente datos:
    - Solo el agente que lo necesita (reservas) ve los resultados de los demás;
      los otros reciben únicamente la pregunta, así no se confunden.
    - Al resultado se le adjunta la salida LITERAL de las tools: el supervisor,
      el agente de reservas y el sintetizador trabajan con datos verificados y
      no con la paráfrasis del modelo.
    """
    def nodo(estado: EstadoPlaneador) -> dict:
        entrada = _contexto(estado) if ve_resultados_previos else f"Pregunta del usuario: {estado['pregunta']}"
        resultado = agente.invoke({"messages": [{"role": "user", "content": entrada}]})
        mensajes = resultado["messages"]
        for m in mensajes:                           # traza de las tools pedidas
            for llamada in getattr(m, "tool_calls", None) or []:
                print(f"   [{nombre}] tool: {llamada['name']}({llamada['args']})")
        texto = mensajes[-1].content
        print(f"   [{nombre}] {texto}")
        datos_tools = " | ".join(m.content for m in mensajes if isinstance(m, ToolMessage))
        evidencia = f"\n  Datos verificados de las herramientas: {datos_tools}" if datos_tools else \
                    "\n  (El agente no usó herramientas: su respuesta no tiene datos verificados.)"
        return {"resultados": [f"[{nombre}] {texto}{evidencia}"], "consultados": [nombre]}
    return nodo


def nodo_sintetizador(estado: EstadoPlaneador) -> dict:
    respuesta = modelo_sintetizador.invoke([("system", PROMPT_SINTETIZADOR), ("human", _contexto(estado))])
    return {"respuesta_final": respuesta.content}


# ----------------------------------------------------------------------------
# 4. ARISTA CONDICIONAL: lee el estado y dice a qué nodo ir.
# ----------------------------------------------------------------------------
def enrutar(estado: EstadoPlaneador) -> str:
    return estado["siguiente"]


# ----------------------------------------------------------------------------
# 5. CONSTRUCCIÓN Y COMPILACIÓN DEL GRAFO
# ----------------------------------------------------------------------------
ESPECIALISTAS = {
    "clima": agente_clima,
    "presupuesto": agente_presupuesto,
    "reservas": agente_reservas,
    "actividades": agente_actividades,           # RETO (Parte 7)
}


def construir_grafo():
    grafo = StateGraph(EstadoPlaneador)

    grafo.add_node("supervisor", nodo_supervisor)
    for nombre, agente in ESPECIALISTAS.items():
        grafo.add_node(nombre, crear_nodo_especialista(
            nombre, agente, ve_resultados_previos=(nombre == "reservas")))
    grafo.add_node("sintetizador", nodo_sintetizador)

    grafo.add_edge(START, "supervisor")
    grafo.add_conditional_edges("supervisor", enrutar, {
        "clima": "clima",
        "presupuesto": "presupuesto",
        "reservas": "reservas",
        "actividades": "actividades",
        "fin": "sintetizador",
    })
    for especialista in ESPECIALISTAS:
        grafo.add_edge(especialista, "supervisor")
    grafo.add_edge("sintetizador", END)

    return grafo.compile()


def estado_inicial(pregunta: str) -> dict:
    return {"pregunta": pregunta, "resultados": [], "consultados": []}


app = construir_grafo()


def planear(pregunta: str) -> str:
    """Punto de entrada usado por main.py y api.py."""
    estado_final = app.invoke(estado_inicial(pregunta))
    return estado_final["respuesta_final"]
