# 🏎️ ApexFlow: SimRacing Telemetry SaaS

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi&logoColor=white)
![Assetto Corsa](https://img.shields.io/badge/Assetto_Corsa-Supported-red.svg)
![Status](https://img.shields.io/badge/Status-MVP_Funcional-success.svg)

> **"La telemetría no debería ser un privilegio exclusivo de los ingenieros de la Fórmula 1."**

ApexFlow es un sistema completo de adquisición, análisis y visualización de telemetría en tiempo real construido desde cero. Diseñado inicialmente para integrarse con el motor físico de **Assetto Corsa**, este proyecto extrae paquetes binarios (C++) del simulador, los procesa y los sirve a través de un backend moderno hacia un Dashboard web interactivo y de baja latencia.

---

## ✨ Características Principales

*   🔴 **Live Dashboard (Muro de Boxes):** Visualización en tiempo real de RPM, marcha, pedales (acelerador/freno) y velocidad, con actualizaciones milisegundo a milisegundo mediante WebSockets. Interfaz *glassmorphism* de alto contraste.
*   📊 **Análisis Histórico y Comparativa (Ghost Lap):** Sistema de almacenamiento de sesiones que permite superponer tu mejor vuelta con una "vuelta de referencia", alineando las gráficas matemáticamente por **metros recorridos** (eje X lineal) en lugar de por tiempo.
*   🤖 **Ingeniero de Pista Inteligente:** Algoritmo heurístico integrado en el backend que analiza las curvas, detecta tus puntos débiles frente a la vuelta de referencia (ej. frenadas tempranas, baja velocidad en el ápice) y te da feedback escrito en lenguaje natural.
*   🔌 **Arquitectura Desacoplada:** El agente de extracción (IoT/Edge) y el servidor en la nube (Cloud/Backend) están completamente separados, abriendo la puerta a despliegues en Internet.

---

## 🏗️ Arquitectura del Sistema

ApexFlow se divide en tres grandes cerebros que se comunican entre sí:

1.  **El Agente Local (`agent.py`):** Actúa como traductor. Se conecta al servidor UDP oculto de Assetto Corsa (Puerto `9996`), realiza el *Handshake*, desempaqueta el código binario (`struct`) y envía JSON limpios a nuestra Nube.
2.  **El Ingestor Cloud (`cloud_backend.py`):** Construido con **FastAPI**. Recibe los datos del Agente vía WebSockets. Por un lado, retransmite los datos al instante a cualquier navegador conectado. Por otro, agrupa los datos en lotes y los guarda eficientemente en una base de datos **SQLite**.
3.  **El Frontend:** HTML/JS puro con **Tailwind CSS** para un diseño moderno y **Chart.js** para renderizar miles de puntos de datos de telemetría sin perder rendimiento.

---

## 🚀 Guía de Instalación y Uso

### 1. Requisitos Previos
*   Python 3.8 o superior.
*   Assetto Corsa (PC/Steam).
*   Librerías de Python: `pip install fastapi uvicorn websockets`

### 2. Puesta en Marcha

**Paso A: Arrancar el Servidor Central**
Abre una terminal y ejecuta el backend. Esto levantará la base de datos y la API web.
```bash
python cloud_backend.py

El panel de control estará disponible en http://127.0.0.1:8000

Paso B: Conectar el Coche (El Agente)
Abre tu simulador Assetto Corsa y entra a pista (Modo Práctica). Mientras estás en el coche, abre otra terminal y ejecuta:

Bash
python agent.py
Verás un mensaje confirmando el Handshake con el juego. ¡Pisa el acelerador y mira la web!

3. Navegación
/ -> Live Dashboard (Telemetría en vivo).

/history -> Módulo de Análisis y Comparación de Vueltas.

🧠 Lecciones de Ingeniería Aprendidas
Construir ApexFlow ha sido un reto de ingeniería que me ha obligado a resolver problemas reales de concurrencia y estructuras de datos:

Decodificación Binaria: Aprender a usar struct en Python para mapear bytes de C++ (< c 3x i f f f...) y evitar sobrecarga de CPU.

Sincronización de Gráficas: Lidiar con las Outlaps (vueltas desde boxes) y los tiempos muertos convirtiendo los índices de tiempo en ejes X de distancia métrica absoluta, evitando desincronizaciones en Chart.js.

WebSockets vs HTTP: Entender por qué HTTP no sirve para telemetría a 60Hz y migrar todo el flujo en vivo a WebSockets asíncronos (asyncio).

🔮 Roadmap (Próximos Pasos)
[ ] Despliegue en la nube (Render / Railway) para acceso remoto público.

[ ] Soporte para F1 23/24 (Implementar un nuevo parser UDP).

[ ] Mapa del circuito en 2D generado a partir de coordenadas GPS/G-Force.

Hugo Thibault.