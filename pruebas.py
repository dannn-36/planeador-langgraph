"""
pruebas.py — Ejecuta las seis preguntas de prueba del taller (Parte 5) más la
pregunta del reto (Parte 7) y muestra, para cada una, la traza, los agentes
que llamó el supervisor, el tiempo y las reservas creadas.

Uso:
    python pruebas.py          -> las 7 preguntas
    python pruebas.py 4        -> solo la pregunta 4
"""
import sys
import time

import datos
from grafo import app, estado_inicial

PREGUNTAS = {
    1: "¿Cómo estará el clima en Guatavita el domingo?",
    2: "Somos 4 amigos con 350000 pesos. ¿Nos alcanza para ir a Zipaquirá?",
    3: "Somos 2 y queremos ir a Villa de Leyva el sábado. ¿Cómo estará el clima y cuánto nos cuesta?",
    4: "Somos 3 y tenemos 250000. Si no llueve mucho y nos alcanza, reserva Suesca para el sábado a nombre de Laura.",
    5: "Somos 3 con 150000. Si nos alcanza, reserva Suesca el domingo a nombre de Laura.",
    6: "¿Quién ganó el mundial de 2022?",
    7: "¿Qué actividades podemos hacer en Villa de Leyva y cómo estará el clima el domingo?",  # reto
}


def ejecutar(numero: int) -> None:
    pregunta = PREGUNTAS[numero]
    reservas_antes = len(datos.RESERVAS)
    print(f"\n===== Pregunta {numero}: {pregunta}")
    inicio = time.perf_counter()
    estado = app.invoke(estado_inicial(pregunta))
    segundos = time.perf_counter() - inicio
    print(f"\nRespuesta final:\n{estado['respuesta_final']}")
    print(f"\n>> Agentes llamados: {', '.join(estado['consultados']) or 'ninguno'}")
    print(f">> Tiempo: {segundos:.0f} s")
    print(f">> Reservas nuevas: {datos.RESERVAS[reservas_antes:] or 'ninguna'}")


if __name__ == "__main__":
    numeros = [int(a) for a in sys.argv[1:]] or list(PREGUNTAS)
    for n in numeros:
        ejecutar(n)
