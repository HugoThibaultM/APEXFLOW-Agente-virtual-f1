import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import sqlite3
import time
import asyncio

app = FastAPI(title="ApexFlow Cloud Ingestor")

web_clients = []

# Inicialización de la Base de Datos SQLite
def init_db():
    conn = sqlite3.connect("apexflow.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, timestamp REAL, speed INTEGER, 
            rpm INTEGER, gear INTEGER, throttle REAL, brake REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Ruta para servir el Dashboard Web
@app.get("/")
def get_dashboard():
    return FileResponse("index.html")

# WebSocket para los espectadores (Navegador Web)
@app.websocket("/ws/viewer")
async def websocket_viewer(websocket: WebSocket):
    await websocket.accept()
    web_clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(1) # Mantenemos la conexión viva y asíncrona
    except Exception:
        pass
    finally:
        if websocket in web_clients:
            web_clients.remove(websocket)

# WebSocket para el piloto (Agente Local)
@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"\n☁️ [NUBE] Piloto transmitiendo...")
    session_id = f"sess_{int(time.time())}"
    batch = []
    conn = sqlite3.connect("apexflow.db")
    cursor = conn.cursor()

    try:
        while True:
            data = await websocket.receive_json()
            
            # Guardado en base de datos (Batching 60 frames)
            batch.append((session_id, time.time(), data['speed'], data['rpm'], data['gear'], data['throttle'], data['brake']))
            if len(batch) >= 60:
                cursor.executemany('INSERT INTO telemetry (session_id, timestamp, speed, rpm, gear, throttle, brake) VALUES (?, ?, ?, ?, ?, ?, ?)', batch)
                conn.commit()
                batch.clear()

            # Retransmisión segura a la web
            disconnected = []
            for client in web_clients:
                try:
                    await client.send_json(data)
                except Exception:
                    disconnected.append(client)
            
            for dead_client in disconnected:
                if dead_client in web_clients:
                    web_clients.remove(dead_client)
            
    except WebSocketDisconnect:
        print(f"\n☁️ [NUBE] Piloto desconectado.")
        if batch:
            cursor.executemany('INSERT INTO telemetry (session_id, timestamp, speed, rpm, gear, throttle, brake) VALUES (?, ?, ?, ?, ?, ?, ?)', batch)
            conn.commit()
        conn.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)