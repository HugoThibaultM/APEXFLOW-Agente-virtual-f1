import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import sqlite3
import time
import asyncio

app = FastAPI(title="ApexFlow Cloud Ingestor")

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
            lap INTEGER,
            distance REAL,
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
    return FileResponse("index.html")

@app.get("/history")
def get_history_dashboard():
    return FileResponse("history.html")


# --- 3. RUTAS API REST (MODO STRAVA) ---

@app.get("/api/sessions")
def get_sessions():
    conn = sqlite3.connect("apexflow.db")
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT session_id FROM telemetry ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return {"sessions": [row[0] for row in rows]}

@app.get("/api/telemetry/{session_id}")
def get_session_telemetry(session_id: str):
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
        labels = [f"{(row[2] - start_time):.1f}s" for row in rows]

    return {
        "session_id": session_id,
        "labels": labels,
        "speed": speed_data,
        "brake": brake_data
    }

# --- NUEVA API: OBTENER LA MEJOR VUELTA DE UNA SESIÓN ---
# --- NUEVA API: OBTENER TODAS LAS VUELTAS Y DETECTAR LA MEJOR ---
@app.get("/api/telemetry/{session_id}/laps")
def get_session_laps(session_id: str):
    """Devuelve la lista de todas las vueltas de la sesión, indicando cuál es la más rápida"""
    conn = sqlite3.connect("apexflow.db")
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT lap FROM telemetry WHERE session_id = ? ORDER BY lap ASC', (session_id,))
    laps = [row[0] for row in cursor.fetchall()]
    
    if not laps:
        conn.close()
        return {"error": "No hay vueltas registradas"}
    
    lap_details = []
    best_lap = laps[0]
    min_duration = float('inf')
    
    for lap in laps:
        cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM telemetry WHERE session_id = ? AND lap = ?', (session_id, lap))
        res = cursor.fetchone()
        if res and res[0] and res[1]:
            duration = res[1] - res[0]
            if duration > 5.0: # Ignorar vueltas incompletas
                lap_details.append({"lap": lap, "duration": round(duration, 2)})
                if duration < min_duration:
                    min_duration = duration
                    best_lap = lap

    conn.close()
    
    return {
        "session_id": session_id,
        "laps": lap_details,
        "best_lap": best_lap
    }

# Y mantenedor de datos por vuelta específica
@app.get("/api/telemetry/{session_id}/lap/{lap_number}")
def get_specific_lap_telemetry(session_id: str, lap_number: int):
    """Devuelve los datos de una vuelta concreta ordenada por distancia"""
    conn = sqlite3.connect("apexflow.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT distance, speed, brake 
        FROM telemetry 
        WHERE session_id = ? AND lap = ? 
        ORDER BY distance ASC
    ''', (session_id, lap_number))
    rows = cursor.fetchall()
    conn.close()
    
    distances = [row[0] for row in rows]
    speed_data = [row[1] for row in rows]
    brake_data = [row[2] for row in rows]
    
    return {
        "lap": lap_number,
        "distances": [f"{int(d)}m" for d in distances],
        "speed": speed_data,
        "brake": brake_data
    }

# --- NUEVA API: COMPARATIVA DE DOS VUELTAS (GHOST) ---
@app.get("/api/telemetry/{session_id}/compare")
def compare_laps(session_id: str, lap1: int, lap2: int):
    """Devuelve los datos de dos vueltas diferentes alineadas por distancia para comparar"""
    conn = sqlite3.connect("apexflow.db")
    cursor = conn.cursor()
    
    def get_lap_data(l_num):
        cursor.execute('''
            SELECT distance, speed, brake 
            FROM telemetry 
            WHERE session_id = ? AND lap = ? 
            ORDER BY distance ASC
        ''', (session_id, l_num))
        return cursor.fetchall()

    rows1 = get_lap_data(lap1)
    rows2 = get_lap_data(lap2)
    conn.close()

    return {
        "lap1": {
            "number": lap1,
            "distances": [f"{int(r[0])}m" for r in rows1],
            "speed": [r[1] for r in rows1],
            "brake": [r[2] for r in rows1]
        },
        "lap2": {
            "number": lap2,
            "distances": [f"{int(r[0])}m" for r in rows2],
            "speed": [r[1] for r in rows2],
            "brake": [r[2] for r in rows2]
        }
    }

# --- 4. RUTAS WEBSOCKETS (TIEMPO REAL) ---

@app.websocket("/ws/viewer")
async def websocket_viewer(websocket: WebSocket):
    await websocket.accept()
    web_clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except Exception:
        pass
    finally:
        if websocket in web_clients:
            web_clients.remove(websocket)

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
            
            # A. Guardado en base de datos incluyendo lap y distance
            batch.append((
                session_id, 
                time.time(), 
                data.get('lap', 1), 
                data.get('distance', 0.0), 
                data['speed'], 
                data['rpm'], 
                data['gear'], 
                data['throttle'], 
                data['brake']
            ))
            
            if len(batch) >= 60:
                cursor.executemany('''
                    INSERT INTO telemetry (session_id, timestamp, lap, distance, speed, rpm, gear, throttle, brake) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', batch)
                conn.commit()
                batch.clear()

            # B. Retransmisión a la web
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
            cursor.executemany('''
                INSERT INTO telemetry (session_id, timestamp, lap, distance, speed, rpm, gear, throttle, brake) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', batch)
            conn.commit()
        conn.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)