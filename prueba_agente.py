"""prueba_agente.py — Prueba UN agente y muestra cada mensaje del ciclo ReAct."""
from agentes import agente_presupuesto

pregunta = "Somos 4 amigos con 350000 pesos. ¿Nos alcanza para ir a Zipaquirá?"
resultado = agente_presupuesto.invoke({"messages": [{"role": "user", "content": pregunta}]})

for mensaje in resultado["messages"]:
    llamadas = getattr(mensaje, "tool_calls", None)  # solo los AIMessage pueden pedir tools
    print(f"--- {type(mensaje).__name__}")
    print(llamadas if llamadas else mensaje.content)
