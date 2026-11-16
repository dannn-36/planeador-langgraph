"""
main.py — Chat por consola con el planeador multiagente.

Uso:
    python main.py            -> conversa con el planeador
    python main.py --grafo    -> imprime el grafo en formato Mermaid
"""
import sys
import time

from config import MODELO


def main() -> None:
    from grafo import app, planear   # se importa aquí para mostrar primero el mensaje de carga

    if "--grafo" in sys.argv:
        # Pega la salida en https://mermaid.live para ver el dibujo del grafo.
        print(app.get_graph().draw_mermaid())
        return

    print(f"Planeador de fin de semana (modelo: {MODELO}). Escribe 'salir' para terminar.")
    while True:
        pregunta = input("\nTú: ").strip()
        if pregunta.lower() in {"salir", "exit", "q"}:
            break
        if not pregunta:
            continue
        inicio = time.perf_counter()
        respuesta = planear(pregunta)
        segundos = time.perf_counter() - inicio
        print(f"\nPlaneador ({segundos:.0f} s):\n{respuesta}")


if __name__ == "__main__":
    print("Cargando agentes...")
    main()
