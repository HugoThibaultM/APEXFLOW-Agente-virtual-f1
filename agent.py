import socket
import json
import asyncio
import websockets

# Configuración del Juego (Local)
UDP_IP = "127.0.0.1"
UDP_PORT = 20777

# Configuración de la Nube (WebSocket)
CLOUD_WS_URL = "ws://127.0.0.1:8000/ws/telemetry"

async def intercept_and_forward():
    # 1. Preparamos el socket local para escuchar al juego
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False) # Hacemos que no bloquee el bucle asíncrono

    loop = asyncio.get_event_loop()
    
    print("==================================================")
    print(f"🚀 ApexFlow Agent v2.0 (Cloud Enabled)")
    print(f"📡 Conectando con los servidores centrales de ApexFlow...")
    
    try:
        # 2. Conectamos con la Nube
        async with websockets.connect(CLOUD_WS_URL) as ws:
            print("✅ Conexión con la Nube establecida. Esperando datos del juego...")
            print("==================================================\n")
            
            while True:
                # 3. Escuchamos al juego (UDP)
                try:
                    data, addr = await loop.sock_recvfrom(sock, 2048)
                    payload = json.loads(data.decode('utf-8'))
                    
                    print(f"🏎️ Enviando a la nube -> Vel: {payload['speed']} km/h", end="\r")
                    
                    # 4. Disparamos a la Nube (Convertimos a string JSON primero)
                    await ws.send(json.dumps(payload))
                    
                except BlockingIOError:
                    # Si no hay datos UDP en este milisegundo, cedemos el control
                    await asyncio.sleep(0.001)
                    
    except ConnectionRefusedError:
        print("\n❌ Error: No se pudo conectar con la Nube. ¿Está el servidor encendido?")
    except KeyboardInterrupt:
        print("\n\n🛑 Agente detenido.")
    finally:
        sock.close()

if __name__ == "__main__":
    asyncio.run(intercept_and_forward())