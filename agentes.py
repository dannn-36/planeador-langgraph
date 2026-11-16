"""
agentes.py — Los agentes especialistas (3 del taller + 1 del reto).

Cada agente = modelo + herramientas + instrucciones (system prompt).
create_agent() construye por dentro un pequeño grafo de LangGraph con el ciclo
ReAct: el modelo piensa -> pide una tool -> recibe el resultado -> vuelve a
pensar... hasta que responde sin pedir más tools.
"""
from langchain.agents import create_agent
from langchain_ollama import ChatOllama

from config import MODELO, OLLAMA_URL
from herramientas import (calcular_saldo, consultar_disponibilidad, consultar_pronostico,
                          crear_reserva, estimar_costo, listar_destinos, recomendar_actividades)


def crear_modelo() -> ChatOllama:
    """Modelo local servido por Ollama. temperature=0 => respuestas más estables."""
    return ChatOllama(model=MODELO, base_url=OLLAMA_URL, temperature=0)


PROMPT_CLIMA = """Eres el AGENTE DE CLIMA de un planeador de salidas de fin de semana cerca de Bogotá.
Tu único trabajo es informar el pronóstico del tiempo.
- Usa SIEMPRE la herramienta consultar_pronostico. Nunca inventes datos del clima.
- Si el usuario no dice el día, consulta sábado y domingo.
- Ignora las partes de la pregunta que no son de clima (dinero, reservas).
- Responde en español, en máximo 3 frases, con una recomendación práctica (ropa, impermeable...)."""

PROMPT_PRESUPUESTO = """Eres el AGENTE DE PRESUPUESTO de un planeador de salidas de fin de semana.
Tu único trabajo es calcular cuánto cuesta el plan y si el dinero alcanza.
- Usa estimar_costo para obtener el costo total. Nunca hagas las cuentas de memoria.
- Si el usuario dijo cuánto dinero tiene, usa también calcular_saldo con el destino, el número
  de personas y ese dinero como presupuesto.
- Si el usuario NO dijo cuánto dinero tiene, NO llames calcular_saldo ni inventes un presupuesto.
- Copia el número de personas tal como lo dice el usuario ("Somos 3" significa personas=3).
- Si una herramienta devuelve un error, corrige los argumentos y vuelve a llamarla.
- En la respuesta copia el costo total y cuánto sobra o falta tal como lo dicen las herramientas.
- Escribe los valores en pesos como números enteros (300000, no 300.000) al llamar las herramientas.
- Ignora las partes de la pregunta que no son de dinero.
- Responde en español, en máximo 3 frases."""

PROMPT_RESERVAS = """Eres el AGENTE DE RESERVAS de un planeador de salidas de fin de semana.
Tu único trabajo es consultar cupos y crear reservas.
- Usa consultar_disponibilidad antes de reservar.
- Usa crear_reserva SOLO si el usuario pidió reservar explícitamente y dio el nombre del responsable.
- Si el usuario condicionó la reserva (por ejemplo "si no llueve" o "si nos alcanza") y los
  resultados de otros agentes muestran que la condición NO se cumple, NO reserves y explica por qué.
- Copia el número de personas tal como lo dice el usuario ("Somos 3" significa personas=3).
- Responde SIEMPRE en español (nunca en otro idioma), en máximo 3 frases.
  Si reservaste, incluye el código de la reserva."""

# RETO (Parte 7): cuarto especialista.
PROMPT_ACTIVIDADES = """Eres el AGENTE DE ACTIVIDADES de un planeador de salidas de fin de semana cerca de Bogotá.
Tu único trabajo es recomendar qué hacer en el destino.
- Usa SIEMPRE la herramienta recomendar_actividades. Nunca inventes actividades.
- Menciona solo actividades que devuelva la herramienta, con su tipo y duración.
- Ignora las partes de la pregunta que no son de actividades (clima, dinero, reservas).
- Responde en español, en máximo 3 frases."""


agente_clima = create_agent(
    model=crear_modelo(),
    tools=[listar_destinos, consultar_pronostico],
    system_prompt=PROMPT_CLIMA,
)

agente_presupuesto = create_agent(
    model=crear_modelo(),
    tools=[estimar_costo, calcular_saldo],
    system_prompt=PROMPT_PRESUPUESTO,
)

agente_reservas = create_agent(
    model=crear_modelo(),
    tools=[consultar_disponibilidad, crear_reserva],
    system_prompt=PROMPT_RESERVAS,
)

agente_actividades = create_agent(
    model=crear_modelo(),
    tools=[recomendar_actividades],
    system_prompt=PROMPT_ACTIVIDADES,
)
