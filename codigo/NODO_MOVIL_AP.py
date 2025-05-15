# mobile_node_ap.py
# Rol: Actuar como un Punto de Acceso WiFi (AP).
# Su señal WiFi será medida por los Nodos Fijos.
# No utiliza NRF24L01 para su función principal de ser "localizado".

import network
import time
from machine import Pin

# --- Configuración del Punto de Acceso (AP) ---
AP_SSID = "NodoMovil_Proyecto"
AP_PASSWORD = "password123"  # Mínimo 8 caracteres para WPA2-PSK

# Pin para el LED integrado (Pico W tiene el LED conectado a 'LED' o al pin del chip CYW43)
# En algunos firmwares de MicroPython para Pico W, el LED se controla así:
try:
    led = Pin("LED", Pin.OUT)
except TypeError: # Manejo para firmwares más antiguos o diferentes
    # Si lo anterior falla, el LED podría estar asociado directamente al chip WiFi
    # y no ser un objeto Pin estándar, o tener otro nombre.
    # En ese caso, omitimos el control del LED o se busca la forma específica
    # para ese firmware. Por ahora, lo hacemos opcional.
    print("Advertencia: No se pudo inicializar el LED integrado con Pin('LED', Pin.OUT).")
    led = None


def setup_ap():
    """Configura e inicia el Punto de Acceso WiFi."""
    ap = network.WLAN(network.AP_IF)
    ap.active(False) # Asegurar que esté desactivado antes de configurar
    time.sleep_ms(100)
    ap.active(True)
    
    # Authmode: 0-Open, 1-WEP, 2-WPA-PSK, 3-WPA2-PSK, 4-WPA/WPA2-PSK
    ap.config(essid=AP_SSID, password=AP_PASSWORD)
    
    # Esperar a que el AP esté completamente activo
    # No hay una forma directa de esperar, pero podemos verificar la IP
    max_wait = 10
    while max_wait > 0:
        if ap.active() and ap.ifconfig()[0] != '0.0.0.0':
            break
        max_wait -= 1
        time.sleep(1)

    if ap.active() and ap.ifconfig()[0] != '0.0.0.0':
        print("Nodo Móvil configurado como Access Point.")
        print(f"SSID: {ap.config('essid')}")
        print(f"IP: {ap.ifconfig()[0]}") # Usualmente 192.168.4.1
        return ap
    else:
        print("Error: No se pudo activar el AP correctamente.")
        return None

# --- Bucle Principal ---
if __name__ == "__main__":
    access_point = setup_ap()
    
    if access_point:
        try:
            blink_interval_ms = 1000
            last_blink_time = time.ticks_ms()
            led_state = False

            while True:
                current_time = time.ticks_ms()
                if time.ticks_diff(current_time, last_blink_time) >= blink_interval_ms:
                    if led:
                        led_state = not led_state
                        led.value(led_state)
                    last_blink_time = current_time
                
                # Opcional: Imprimir número de clientes conectados
                print(f"Clientes conectados: {len(access_point.status('stations'))}")
                
                time.sleep_ms(100) # Pequeña pausa para no sobrecargar el CPU

        except KeyboardInterrupt:
            print("\nDeteniendo AP del Nodo Móvil...")
        finally:
            if access_point and access_point.active():
                access_point.active(False)
                print("AP detenido.")
            if led:
                led.off()