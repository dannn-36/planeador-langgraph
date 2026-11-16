"""
herramientas.py — Las herramientas (tools) que usan los agentes.

Una tool es una función normal de Python. El decorador @tool la convierte en
algo que el LLM puede "pedir" que se ejecute:
  - el NOMBRE de la función es el nombre de la tool,
  - el DOCSTRING es la descripción que lee el modelo para decidir cuándo usarla,
  - los TYPE HINTS (str, int) definen el esquema de los argumentos.

El modelo nunca ejecuta código: solo propone "llama a X con estos argumentos".
Quien ejecuta es LangGraph, y el resultado vuelve al modelo como un mensaje.
"""
from langchain.tools import tool

import datos

DESTINOS_VALIDOS = ", ".join(d["nombre"] for d in datos.DESTINOS.values())


# ----------------------------------------------------------------------------
# Tools del AGENTE DE CLIMA
# ----------------------------------------------------------------------------
@tool
def listar_destinos() -> str:
    """Lista los destinos de fin de semana disponibles cerca de Bogotá."""
    return "Destinos disponibles: " + DESTINOS_VALIDOS


@tool
def consultar_pronostico(destino: str, dia: str) -> str:
    """Consulta el pronóstico del clima de un destino para el sábado o el domingo.
    destino: nombre del destino, por ejemplo "Guatavita".
    dia: "sabado" o "domingo"."""
    clave = datos.buscar_destino(destino)
    if clave is None:
        return f"No conozco el destino '{destino}'. Destinos válidos: {DESTINOS_VALIDOS}."
    d = datos.normalizar_dia(dia)
    if d is None:
        return "Solo tengo pronóstico para 'sabado' o 'domingo'."
    p = datos.PRONOSTICO[(clave, d)]
    return (f"{datos.DESTINOS[clave]['nombre']} el {d}: {p['cielo']}, "
            f"entre {p['min']} °C y {p['max']} °C, probabilidad de lluvia {p['lluvia']} %.")


# ----------------------------------------------------------------------------
# Tools del AGENTE DE PRESUPUESTO
# ----------------------------------------------------------------------------
@tool
def estimar_costo(destino: str, personas: int) -> str:
    """Calcula el costo total de ir a un destino (transporte, entrada y alimentación)
    para un número de personas."""
    clave = datos.buscar_destino(destino)
    if clave is None:
        return f"No conozco el destino '{destino}'. Destinos válidos: {DESTINOS_VALIDOS}."
    if personas <= 0:
        return "El número de personas debe ser mayor que cero."
    c = datos.DESTINOS[clave]
    por_persona = c["transporte"] + c["entrada"] + c["alimentacion"]
    total = por_persona * personas
    return (f"{c['nombre']}: por persona transporte {datos.pesos(c['transporte'])} + "
            f"entrada {datos.pesos(c['entrada'])} + alimentación {datos.pesos(c['alimentacion'])} "
            f"= {datos.pesos(por_persona)}. Costo total para {personas} personas: {datos.pesos(total)}.")


@tool
def calcular_saldo(destino: str, personas: int, presupuesto: int) -> str:
    """Dice si el presupuesto del grupo alcanza para ir a un destino y cuánto sobra o falta.
    Úsala SOLO si el usuario dijo cuánto dinero tiene.
    presupuesto: dinero total del grupo en pesos, sin puntos ni signos (por ejemplo 350000)."""
    # Ajuste sobre el taller (ver bitácora): la versión original recibía
    # (presupuesto, costo_total) y dependía de que el modelo copiara el resultado
    # de estimar_costo. qwen2.5:3b pide las dos tools EN PARALELO, así que
    # inventaba costo_total antes de conocerlo. Ahora la tool calcula el costo
    # ella misma: cada tool es autosuficiente y no depende del orden de llamada.
    clave = datos.buscar_destino(destino)
    if clave is None:
        return f"No conozco el destino '{destino}'. Destinos válidos: {DESTINOS_VALIDOS}."
    if personas <= 0:
        return "El número de personas debe ser mayor que cero."
    c = datos.DESTINOS[clave]
    costo_total = (c["transporte"] + c["entrada"] + c["alimentacion"]) * personas
    saldo = presupuesto - costo_total
    if saldo >= 0:
        return (f"Sí alcanza: presupuesto {datos.pesos(presupuesto)} - costo {datos.pesos(costo_total)} "
                f"= sobran {datos.pesos(saldo)}.")
    return (f"No alcanza: presupuesto {datos.pesos(presupuesto)} - costo {datos.pesos(costo_total)} "
            f"= faltan {datos.pesos(-saldo)}.")


# ----------------------------------------------------------------------------
# Tools del AGENTE DE RESERVAS
# ----------------------------------------------------------------------------
@tool
def consultar_disponibilidad(destino: str, dia: str) -> str:
    """Consulta cuántos cupos quedan para un destino el sábado o el domingo."""
    clave = datos.buscar_destino(destino)
    if clave is None:
        return f"No conozco el destino '{destino}'. Destinos válidos: {DESTINOS_VALIDOS}."
    d = datos.normalizar_dia(dia)
    if d is None:
        return "Solo se puede reservar para 'sabado' o 'domingo'."
    return f"{datos.DESTINOS[clave]['nombre']} el {d}: quedan {datos.CUPOS[(clave, d)]} cupos."


@tool
def crear_reserva(destino: str, dia: str, personas: int, responsable: str) -> str:
    """Crea una reserva para un grupo. Úsala SOLO si el usuario pidió reservar
    y dio el nombre del responsable."""
    clave = datos.buscar_destino(destino)
    if clave is None:
        return f"No conozco el destino '{destino}'. Destinos válidos: {DESTINOS_VALIDOS}."
    d = datos.normalizar_dia(dia)
    if d is None:
        return "Solo se puede reservar para 'sabado' o 'domingo'."
    if not responsable or not responsable.strip():
        return "Falta el nombre del responsable de la reserva. Pídeselo al usuario."
    cupos = datos.CUPOS[(clave, d)]
    if personas > cupos:
        return f"No hay cupo suficiente: se piden {personas} y quedan {cupos}."
    datos.CUPOS[(clave, d)] = cupos - personas
    codigo = f"RES-{len(datos.RESERVAS) + 1:03d}"
    datos.RESERVAS.append({"codigo": codigo, "destino": clave, "dia": d,
                           "personas": personas, "responsable": responsable.strip()})
    return (f"Reserva confirmada {codigo}: {datos.DESTINOS[clave]['nombre']}, {d}, "
            f"{personas} personas, a nombre de {responsable.strip()}.")


# ----------------------------------------------------------------------------
# RETO (Parte 7): Tool del AGENTE DE ACTIVIDADES
# ----------------------------------------------------------------------------
@tool
def recomendar_actividades(destino: str) -> str:
    """Recomienda actividades para hacer en un destino (senderismo, gastronomía,
    museos, aventura...). destino: nombre del destino, por ejemplo "Suesca"."""
    clave = datos.buscar_destino(destino)
    if clave is None:
        return f"No conozco el destino '{destino}'. Destinos válidos: {DESTINOS_VALIDOS}."
    lineas = [f"{a['nombre']} ({a['tipo']}, {a['horas']} h)" for a in datos.ACTIVIDADES[clave]]
    return f"Actividades en {datos.DESTINOS[clave]['nombre']}: " + "; ".join(lineas) + "."
