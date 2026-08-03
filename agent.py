import socket
import json
import asyncio
import websockets
import struct
import time

# Configuración de Assetto Corsa y la Nube
AC_SERVER_IP = "127.0.0.1"
AC_UDP_PORT = 9996
CLOUD_WS_URL = "ws://127.0.0.1:8000/ws/telemetry"

async def intercept_ac_telemetry():
    # 1. Preparamos el socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('127.0.0.1', 0)) # El SO nos asigna un puerto libre para escuchar
    sock.setblocking(False)

    loop = asyncio.get_event_loop()
    
    print("==================================================")
    print(f"🚀 ApexFlow Agent v3.0 (Assetto Corsa Mode)")
    print(f"📡 Conectando con los servidores de la Nube...")
    
    try:
        async with websockets.connect(CLOUD_WS_URL) as ws:
            print("✅ Conexión con la Nube establecida.")
            print("🤝 Enviando 'Handshake' a Assetto Corsa...")
            
            # 2. El Saludo Secreto (Handshake) a Assetto Corsa
            # identifier = 1, version = 1, operationId = 1 (Subscribe to updates)
            handshake = struct.pack('<iii', 1, 1, 1)
            sock.sendto(handshake, (AC_SERVER_IP, AC_UDP_PORT))
            print("🟢 Esperando que el piloto salga a pista...\n")
            
            # Variables para calcular la distancia nosotros mismos (como en el mock)
            last_time = time.time()
            distance = 0.0
            current_lap = -1
            
            while True:
                try:
                    data, addr = await loop.sock_recvfrom(sock, 2048)
                    
                    # 3. EL TRADUCTOR BINARIO (Parser)
                    # Assetto Corsa envía un struct C++ llamado RTCarInfo.
                    # Mapeamos los primeros 75 bytes para extraer lo que nos importa.
                    formato = '< c 3x i f f f ? ? ? ? ? ? 2x f f f i i i i f f f f f i'
                    
                    if len(data) >= struct.calcsize(formato):
                        unpacked = struct.unpack_from(formato, data)
                        
                        # Extraemos los datos del bloque desempaquetado
                        speed_kmh = unpacked[2]
                        lap_count = unpacked[17]
                        gas = unpacked[18]
                        brake = unpacked[19]
                        rpm = unpacked[21]
                        gear = unpacked[23] - 1 # AC manda la marcha R=0, N=1, 1=2. Restamos 1.
                        
                        # 4. Cálculo de Distancia y Vueltas
                        now = time.time()
                        delta_time = now - last_time
                        last_time = now
                        
                        # Si Assetto Corsa nos dice que la vuelta ha cambiado, reseteamos metros
                        if current_lap != lap_count:
                            current_lap = lap_count
                            distance = 0.0 
                            
                        # Sumamos los metros recorridos en este frame
                        distance += (speed_kmh / 3.6) * delta_time
                        
                        # 5. Formateamos y enviamos a nuestra Nube
                        payload = {
                            "lap": current_lap + 1, # Para que empiece en Vuelta 1
                            "distance": round(distance, 2),
                            "speed": int(speed_kmh),
                            "rpm": int(rpm),
                            "gear": gear,
                            "throttle": round(gas, 2),
                            "brake": round(brake, 2)
                        }

                        print(f"🏎️ AC -> Nube | Vuelta: {payload['lap']} | Vel: {payload['speed']} km/h", end="\r")
                        await ws.send(json.dumps(payload))
                    
                except BlockingIOError:
                    await asyncio.sleep(0.001)
                    
    except ConnectionRefusedError:
        print("\n❌ Error: No se pudo conectar con la Nube. ¿Está el backend encendido?")
    except KeyboardInterrupt:
        print("\n\n🛑 Agente detenido. Desconectando del coche...")
        # Nos despedimos amablemente de Assetto Corsa (operationId = 3)
        sock.sendto(struct.pack('<iii', 1, 1, 3), (AC_SERVER_IP, AC_UDP_PORT))
    finally:
        sock.close()

if __name__ == "__main__":
    asyncio.run(intercept_ac_telemetry())