import socket
import time
import json
import math

UDP_IP = "127.0.0.1"
UDP_PORT = 20777

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("🎮 [MOCK GAME] Iniciando simulador de carreras (Con Track Distance)...")

tiempo = 0.0
lap = 1             # Empezamos en la vuelta 1
distance = 0.0      # Empezamos en la línea de meta (0 metros)
TRACK_LENGTH = 5000 # El circuito mide 5000 metros

try:
    while True:
        # Simulamos los pedales y velocidad
        velocidad = abs(math.sin(tiempo) * 320)
        rpm = 4000 + abs(math.sin(tiempo) * 8000)
        marcha = max(1, min(8, int(velocidad / 40) + 1))
        freno = 1.0 if math.cos(tiempo) < 0 else 0.0
        acelerador = 1.0 if math.cos(tiempo) >= 0 else 0.0

        # Calculamos la distancia real recorrida en este frame
        vel_metros_por_segundo = velocidad / 3.6
        distance += vel_metros_por_segundo * (1/60)

        # Lógica de cruzar la línea de meta
        if distance >= TRACK_LENGTH:
            distance -= TRACK_LENGTH  # Reseteamos la distancia
            lap += 1                  # Sumamos una vuelta
            print(f"🏁 ¡Vuelta completada! Iniciando vuelta {lap}...")

        payload = {
            "lap": lap,
            "distance": round(distance, 2),
            "speed": int(velocidad),
            "rpm": int(rpm),
            "gear": marcha,
            "throttle": round(acelerador, 2),
            "brake": round(freno, 2)
        }

        mensaje = json.dumps(payload).encode('utf-8')
        sock.sendto(mensaje, (UDP_IP, UDP_PORT))

        tiempo += 0.05
        time.sleep(1/60)

except KeyboardInterrupt:
    print("\n🛑 Juego cerrado.")
    sock.close()