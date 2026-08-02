import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import sqlite3
import time
import asyncio

app = FastAPI(title="ApexFlow Cloud Ingestor")

# Lista para guardar a los espectadores (navegadores web viendo el directo)
web_clients = []

# --- 1. INICIALIZACIÓN DE LA BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect("apexflow.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, 
            timestamp REAL, 
            speed INTEGER, 
            rpm INTEGER, 
            gear INTEGER, 
            throttle REAL, 
            brake REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()


# --- 2. RUTAS FRONTEND (PÁGINAS WEB) ---

@app.get("/")
def get_dashboard():
    """Devuelve la pantalla del Live Dashboard"""
    return FileResponse("index.html")

@app.get("/history")
def get_history_dashboard():
    """Devuelve la pantalla de Análisis Histórico"""
    return FileResponse("history.html")


# --- 3. RUTAS API REST (MODO STRAVA) ---

@app.get("/api/sessions")
def get_sessions():
    """Devuelve una lista con todos los IDs de las sesiones guardadas"""
    conn = sqlite3.connect("apexflow.db")
    cursor = conn.cursor()
    # Buscamos todas las sesiones únicas, de la más reciente a la más antigua
    cursor.execute('SELECT DISTINCT session_id FROM telemetry ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return {"sessions": [row[0] for row in rows]}

@app.get("/api/telemetry/{session_id}")
def get_session_telemetry(session_id: str):
    """Devuelve toda la telemetría de una sesión específica formateada para Chart.js"""
    conn = sqlite3.connect("apexflow.db")
    cursor = conn.cursor()
    cursor.execute('SELECT speed, brake, timestamp FROM telemetry WHERE session_id = ? ORDER BY timestamp ASC', (session_id,))
    rows = cursor.fetchall()
    conn.close()
    
    speed_data = [row[0] for row in rows]
    brake_data = [row[1] for row in rows]
    
    labels = []
    if rows:
        start_time = rows[0][2]
        # Generamos el eje X en segundos desde que empezó la vuelta (ej: 0.1s, 0.2s...)
        labels = [f"{(row[2] - start_time):.1f}s" for row in rows]

    return {
        "session_id": session_id,
        "labels": labels,
        "speed": speed_data,
        "brake": brake_data
    }


# --- 4. RUTAS WEBSOCKETS (TIEMPO REAL) ---

@app.websocket("/ws/viewer")
async def websocket_viewer(websocket: WebSocket):
    """Maneja a los usuarios que entran a ver el Dashboard Live"""
    await websocket.accept()
    web_clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(1) # Mantenemos la conexión viva
    except Exception:
        pass
    finally:
        if websocket in web_clients:
            web_clients.remove(websocket)

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """Recibe los datos del Agente Local, los guarda en lotes y los retransmite"""
    await websocket.accept()
    print(f"\n☁️ [NUBE] Piloto transmitiendo...")
    
    # Creamos un ID único para esta nueva salida a pista
    session_id = f"sess_{int(time.time())}"
    batch = []
    conn = sqlite3.connect("apexflow.db")
    cursor = conn.cursor()

    try:
        while True:
            data = await websocket.receive_json()
            
            # A. Guardado en base de datos (Batching de 60 frames)
            batch.append((session_id, time.time(), data['speed'], data['rpm'], data['gear'], data['throttle'], data['brake']))
            if len(batch) >= 60:
                cursor.executemany('INSERT INTO telemetry (session_id, timestamp, speed, rpm, gear, throttle, brake) VALUES (?, ?, ?, ?, ?, ?, ?)', batch)
                conn.commit()
                batch.clear()

            # B. Retransmisión segura a todos los navegadores web conectados
            disconnected = []
            for client in web_clients:
                try:
                    await client.send_json(data)
                except Exception:
                    disconnected.append(client)
            
            # Limpiamos conexiones muertas
            for dead_client in disconnected:
                if dead_client in web_clients:
                    web_clients.remove(dead_client)
            
    except WebSocketDisconnect:
        print(f"\n☁️ [NUBE] Piloto desconectado.")
        # Guardar datos residuales si el piloto se desconecta antes de llegar a 60 frames
        if batch:
            cursor.executemany('INSERT INTO telemetry (session_id, timestamp, speed, rpm, gear, throttle, brake) VALUES (?, ?, ?, ?, ?, ?, ?)', batch)
            conn.commit()
        conn.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)