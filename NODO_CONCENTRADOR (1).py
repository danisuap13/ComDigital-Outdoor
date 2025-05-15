"""
Nodo Concentrador:
Este script actúa como receptor de los datos enviados por los Nodos Fijos usando radiofrecuencia NRF24L01.
Recibe el ID del nodo y la intensidad RSSI medida, y los imprime para su posterior procesamiento.
"""

# concentrator_node_nrf_rx.py
# Rol: Recibir datos (ID de Nodo Fijo y RSSI) vía NRF24L01.

import time
from machine import Pin, SPI
from nrf24l01 import NRF24L01 # Asegúrate de tener la librería correcta
import struct

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
# Utiliza las constantes de tu librería NRF24L01 si están disponibles
NRF_DATARATE = NRF24L01.DR_1MBPS
NRF_PA_LEVEL = NRF24L01.PA_MAX # Aunque PA_LEVEL es más para el TX, es bueno definirlo consistentemente

try:
    led = Pin("LED", Pin.OUT)
except TypeError:
    led = None

def setup_nrf24l01_rx():
    # Crear objetos Pin
    sck_pin  = Pin(SCK_PIN_NRF_NUM)
    mosi_pin = Pin(MOSI_PIN_NRF_NUM)
    miso_pin = Pin(MISO_PIN_NRF_NUM)
    csn_pin  = Pin(CSN_PIN_NRF_NUM, Pin.OUT, value=1)
    ce_pin   = Pin(CE_PIN_NRF_NUM, Pin.OUT, value=0)

    spi_nrf = SPI(SPI_ID, sck=sck_pin, mosi=mosi_pin, miso=miso_pin)
    nrf = NRF24L01(spi_nrf, csn_pin, ce_pin, payload_size=PAYLOAD_SIZE_NRF)
    
    # Aplicar configuraciones adicionales
    try:
        nrf.config(channel=NRF_CHANNEL, data_rate=NRF_DATARATE, pa_level=NRF_PA_LEVEL)
        print(f"Concentrador: NRF Config: Ch={NRF_CHANNEL}, DR={NRF_DATARATE}, PA={NRF_PA_LEVEL}")
    except AttributeError:
        print("Concentrador: Advertencia - nrf.config() no disponible. Usando valores por defecto o métodos individuales.")
        if hasattr(nrf, 'set_channel'): nrf.set_channel(NRF_CHANNEL)
        if hasattr(nrf, 'set_data_rate'): nrf.set_data_rate(NRF_DATARATE)
        if hasattr(nrf, 'set_pa_level'): nrf.set_pa_level(NRF_PA_LEVEL)
        
    nrf.open_rx_pipe(1, PIPE_ADDR_NRF)
    nrf.start_listening()
    print("Concentrador: NRF24L01 configurado como receptor.")
    print(f"Concentrador: Escuchando en Pipe 1, Addr: {PIPE_ADDR_NRF.hex()}")
    return nrf

if __name__ == "__main__":
    nrf_rx = setup_nrf24l01_rx()

    if not nrf_rx:
        print("Concentrador: Fallo en la inicialización del NRF. Deteniendo.")
    else:
        try:
            while True:
                if nrf_rx.any():
                    if led: led.on()
                    
                    try:
                        payload_bytes = nrf_rx.recv()
                        
                        if len(payload_bytes) == PAYLOAD_SIZE_NRF:
                            node_id, rssi_value = struct.unpack("<Bi", payload_bytes)
                            print(f"Recibido -> Nodo ID: {node_id}, RSSI: {rssi_value} dBm")
                            
                            # TODO: Enviar estos datos al PC (ej. print(f"{node_id},{rssi_value}"))
                        else:
                            print(f"Concentrador: Payload de tamaño inesperado: {len(payload_bytes)} bytes, data: {payload_bytes.hex()}")
                    
                    except OSError as e:
                        print(f"Concentrador: Error NRF al recibir: {e}")
                    except Exception as e:
                        print(f"Concentrador: Error al procesar payload: {e}")

                    if led: led.off()
                    time.sleep_ms(10)
                
                time.sleep_ms(50)

        except KeyboardInterrupt:
            print("\nDeteniendo Concentrador...")
        finally:
            if nrf_rx:
                nrf_rx.stop_listening()
            if led: led.off()