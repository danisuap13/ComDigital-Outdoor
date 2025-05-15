"""
Nodo Fijo:
Este script escanea redes WiFi para detectar la señal del Nodo Móvil.
Promedia varias mediciones de RSSI y luego transmite el resultado al Nodo Concentrador usando un módulo NRF24L01.
"""

# fixed_node_scanner_with_nrf_tx.py
# Rol: Escanear el RSSI del AP del Nodo Móvil (promediando lecturas) 
# y transmitirlo vía NRF24L01.

import network
import time
from machine import Pin, SPI
from nrf24l01 import NRF24L01  # Asegúrate de tener la librería correcta
import struct 

# --- Configuración WiFi ---
TARGET_SSID = "NodoMovil_Proyecto"

# --- Identificador de este Nodo Fijo ---
NODE_ID = 0 # CAMBIAR ESTO PARA CADA NODO FIJO (0, 1, 2, 3)

# --- Configuración de Medición RSSI ---
RSSI_SAMPLES = 3           # Número de muestras de RSSI a promediar
RSSI_SAMPLE_DELAY_MS = 200 # Pausa entre escaneos para muestreo (ajustar según necesidad)
RSSI_MIN_VALID = -95       # RSSI mínimo aceptable
RSSI_MAX_VALID = -20       # RSSI máximo aceptable

# --- Configuración Pines NRF24L01 ---
SPI_ID = 0
SCK_PIN_NRF_NUM = 2
MOSI_PIN_NRF_NUM = 3
MISO_PIN_NRF_NUM = 4
CSN_PIN_NRF_NUM = 5
CE_PIN_NRF_NUM = 6

# --- Configuración Parámetros NRF24L01 ---
PIPE_ADDR_NRF = b"\xe1\xf0\xf0\xf0\xf0"
PAYLOAD_SIZE_NRF = 5  # 1 byte NODE_ID + 4 bytes RSSI
NRF_CHANNEL = 76
NRF_DATARATE = NRF24L01.DR_1MBPS 
NRF_PA_LEVEL = NRF24L01.PA_MAX   

try:
    led = Pin("LED", Pin.OUT)
except TypeError:
    led = None

def setup_wifi_sta():
    wlan = network.WLAN(network.STA_IF)
    if not wlan.active():
        wlan.active(True)
        max_wait = 10
        while max_wait > 0 and not wlan.active():
            time.sleep(1)
            max_wait -=1
        if not wlan.active():
            print(f"Nodo Fijo {NODE_ID}: Error al activar interfaz WLAN.")
            return None
    print(f"Nodo Fijo {NODE_ID}: Interfaz WLAN activada.")
    return wlan

def setup_nrf24l01_tx():
    sck_pin  = Pin(SCK_PIN_NRF_NUM)
    mosi_pin = Pin(MOSI_PIN_NRF_NUM)
    miso_pin = Pin(MISO_PIN_NRF_NUM)
    csn_pin  = Pin(CSN_PIN_NRF_NUM, Pin.OUT, value=1)
    ce_pin   = Pin(CE_PIN_NRF_NUM, Pin.OUT, value=0)
    
    spi_nrf = SPI(SPI_ID, sck=sck_pin, mosi=mosi_pin, miso=miso_pin)
    nrf = NRF24L01(spi_nrf, csn_pin, ce_pin, payload_size=PAYLOAD_SIZE_NRF)
    
    try:
        nrf.config(channel=NRF_CHANNEL, data_rate=NRF_DATARATE, pa_level=NRF_PA_LEVEL)
        print(f"Nodo Fijo {NODE_ID}: NRF Config: Ch={NRF_CHANNEL}, DR={NRF_DATARATE}, PA={NRF_PA_LEVEL}")
    except AttributeError:
        print(f"Nodo Fijo {NODE_ID}: Advertencia - nrf.config() no disponible.")
        if hasattr(nrf, 'set_channel'): nrf.set_channel(NRF_CHANNEL)
        # ... (otros setters si son necesarios y existen) ...
        
    nrf.open_tx_pipe(PIPE_ADDR_NRF)
    nrf.stop_listening()
    print(f"Nodo Fijo {NODE_ID}: NRF24L01 configurado como transmisor.")
    return nrf

if __name__ == "__main__":
    wlan_sta = setup_wifi_sta()
    nrf_tx = setup_nrf24l01_tx()

    if not wlan_sta or not nrf_tx:
        print(f"Nodo Fijo {NODE_ID}: Fallo en la inicialización. Deteniendo.")
    else:
        print(f"Nodo Fijo {NODE_ID}: Buscando '{TARGET_SSID}' y transmitiendo RSSI...")
        main_loop_interval_s = 5 # Intervalo principal del bucle

        try:
            while True:
                if led: led.on() # Indicar inicio de ciclo

                rssi_readings = []
                print(f"Nodo Fijo {NODE_ID}: Iniciando muestreo de RSSI ({RSSI_SAMPLES} muestras)...")
                for i in range(RSSI_SAMPLES):
                    sample_rssi = -127  # Valor por defecto para esta muestra
                    target_found_this_sample = False
                    try:
                        networks = wlan_sta.scan() # Realizar escaneo
                        for ssid, bssid, channel, rssi_from_scan, authmode, hidden in networks:
                            try:
                                ssid_str = ssid.decode('utf-8')
                            except UnicodeError:
                                ssid_str = str(ssid)
                            
                            if ssid_str == TARGET_SSID:
                                # Filtrar RSSI para que esté en un rango válido
                                if RSSI_MIN_VALID <= rssi_from_scan <= RSSI_MAX_VALID:
                                    sample_rssi = rssi_from_scan
                                    print(f"  Muestra {i+1}: SSID '{TARGET_SSID}' encontrado, RSSI: {sample_rssi} dBm")
                                else:
                                    print(f"  Muestra {i+1}: SSID '{TARGET_SSID}' encontrado, RSSI: {rssi_from_scan} dBm (descartado, fuera de rango)")
                                target_found_this_sample = True
                                break # Salir del bucle de redes, ya encontramos el target
                        
                        if target_found_this_sample and RSSI_MIN_VALID <= sample_rssi <= RSSI_MAX_VALID:
                            rssi_readings.append(sample_rssi)
                        elif target_found_this_sample: # Encontrado pero fuera de rango
                            pass # Ya se imprimió el mensaje de descarte
                        else:
                            print(f"  Muestra {i+1}: SSID '{TARGET_SSID}' no encontrado en este escaneo.")
                            
                    except Exception as e:
                        print(f"Nodo Fijo {NODE_ID}: Error durante escaneo WiFi para muestra {i+1}: {e}")
                    
                    if i < RSSI_SAMPLES - 1: # No dormir después de la última muestra del ciclo de muestreo
                        time.sleep_ms(RSSI_SAMPLE_DELAY_MS)
                
                # Calcular RSSI final y determinar si se encontró el objetivo
                final_rssi_value = -127
                target_effectively_found = False

                if rssi_readings: # Si tenemos al menos una lectura válida
                    final_rssi_value = sum(rssi_readings) // len(rssi_readings) # Promedio entero
                    target_effectively_found = True
                    print(f"Nodo Fijo {NODE_ID}: RSSI promedio final: {final_rssi_value} dBm (de {len(rssi_readings)} lecturas válidas de {RSSI_SAMPLES} intentos)")
                else:
                    print(f"Nodo Fijo {NODE_ID}: No se obtuvieron lecturas RSSI válidas para '{TARGET_SSID}' tras {RSSI_SAMPLES} intentos.")
                
                if led: led.off() # Indicar fin de escaneo/muestreo

                # --- Transmitir el NODE_ID y el final_rssi_value vía NRF24L01 ---
                nrf_tx.stop_listening() 
                payload = struct.pack("<Bi", NODE_ID, final_rssi_value) 
                
                print(f"Nodo Fijo {NODE_ID}: Intentando enviar Payload: (ID:{NODE_ID}, RSSI:{final_rssi_value})")
                try:
                    if nrf_tx.send(payload):
                        print(f"Nodo Fijo {NODE_ID}: Payload enviado exitosamente.")
                        if led: 
                            led.on()
                            time.sleep_ms(50)
                            led.off()
                    else:
                        print(f"Nodo Fijo {NODE_ID}: Fallo al enviar payload por NRF.")
                except OSError as e:
                    print(f"Nodo Fijo {NODE_ID}: Error NRF al enviar: {e}")
                
                # Esperar para el próximo ciclo completo
                time.sleep(main_loop_interval_s)

        except KeyboardInterrupt:
            print(f"\nDeteniendo Nodo Fijo {NODE_ID}...")
        finally:
            if wlan_sta and wlan_sta.active():
                wlan_sta.active(False)
                print(f"Nodo Fijo {NODE_ID}: Interfaz WLAN detenida.")
            if led: led.off()
