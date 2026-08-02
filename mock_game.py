import socket
import time
import json
import math

UDP_IP = "127.0.0.1"
UDP_PORT = 20777

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("🎮 [MOCK GAME] Iniciando simulador de juego de carreras...")
print(f"📡 Transmitiendo telemetría a {UDP_IP}:{UDP_PORT} a 60Hz")

tiempo = 0.0

try:
    while True:
        # Simulamos un coche acelerando y frenando usando una onda senoidal
        velocidad = abs(math.sin(tiempo) * 320) # Velocidad de 0 a 320 km/h
        rpm = 4000 + abs(math.sin(tiempo) * 8000) # RPM de 4000 a 12000
        
        # Calculamos la marcha aproximada según la velocidad
        marcha = max(1, min(8, int(velocidad / 40) + 1))
        
        # Simulamos que frena si la velocidad está bajando
        freno = 1.0 if math.cos(tiempo) < 0 else 0.0
        acelerador = 1.0 if math.cos(tiempo) >= 0 else 0.0

        payload = {
            "speed": int(velocidad),
            "rpm": int(rpm),
            "gear": marcha,
            "throttle": round(acelerador, 2),
            "brake": round(freno, 2)
        }

        # Empaquetamos y enviamos
        mensaje = json.dumps(payload).encode('utf-8')
        sock.sendto(mensaje, (UDP_IP, UDP_PORT))

        tiempo += 0.05 # Avanzamos el tiempo simulado
        
        # 60 Hz = 1/60 segundos de pausa
        time.sleep(1/60)

except KeyboardInterrupt:
    print("\n🛑 Juego cerrado.")
    sock.close()