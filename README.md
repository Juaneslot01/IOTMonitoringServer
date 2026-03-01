# Solución Reto de Aplicación

## 1. Descripción de la Modificación

Se implementó una nueva regla de negocio para la **Gestión de Emergencia por Calor Sostenido**. A diferencia de las alertas de rango simples que reaccionan a un dato instantáneo, este evento realiza un análisis de tendencia para evitar falsas alarmas causadas por picos de temperatura momentáneos o ruido en los sensores.

### Condición (Pre-requisito: Consulta a Base de Datos)
El sistema evalúa el estado del dispositivo basándose en su comportamiento histórico:
* **Consulta:** Se utiliza el ORM de Django para realizar una consulta agregada sobre la tabla de mediciones. El sistema filtra los datos de la **última hora** y calcula el **promedio (`Avg`)** de la temperatura.
* **Lógica:** Si el promedio calculado es estrictamente superior a **30.0°C**, se considera una anomalía térmica sostenida y se dispara la acción.

### Acción del Actuador
Cuando se cumple la condición histórica, el servidor envía un mensaje de control específico al tópico de entrada del dispositivo (`.../in`).
* **Actuador:** El emulador actúa como receptor de este comando y simula la activación de un **Ventilador de Emergencia**, imprimiendo un bloque visual de advertencia en la consola de ejecución.

---

## 2. Fragmentos de Código

### A. Lógica del Servidor (`control/monitor.py`)

Se modificó la función `analyze_data` para incorporar la validación del promedio histórico antes de publicar el mensaje en el bróker.

```python
if variable.lower() == "temperatura" and avg_value > 30.0:
    # Acción: Enviar comando al actuador
    command_msg = "ACTUATOR_COMMAND SET_FAN_ON"
    print(
        f"!!! EVENTO CRÍTICO: Promedio {avg_value}°C. Enviando comando a actuador en {topic}"
    )
    client.publish(topic, command_msg)
```

## B. Lógica del Dispositivo (`IOTEmulatorScript.py`)

Se actualizó el método `process_message` para reconocer la cadena de comando y simular la respuesta del actuador físico.

```python
def process_message(msg: str):
    """
    Simula la ejecución de acciones en actuadores.
    """
    # Reacción al comando del servidor (Actuador)
    if "ACTUATOR_COMMAND SET_FAN_ON" in msg:
        print("\n" + "!"*50)
        print(">>> ACTUADOR ACTIVADO: ENCENDIENDO VENTILADOR")
        print(">>> MOTIVO: TEMPERATURA PROMEDIO CRÍTICA (>30°C)")
        print("!"*50 + "\n")
    
    # Compatibilidad con alertas de rango normales
    elif "ALERT" in msg:
        print("ALERTA DE Rango: " + msg)
```
