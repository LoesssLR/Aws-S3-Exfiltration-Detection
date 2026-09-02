# Emulación de Adversario en Cloud: Exfiltración a S3 vía URLs Prefirmadas y Detección

Agente de captura de teclado para **red team simulado / laboratorio propio**.
Exfiltra los logs a AWS S3 **sin que el agente tenga credenciales IAM**: un
backend API Gateway + Lambda emite pre-signed URLs temporales para `PUT`.

Proyecto educativo. Diseñado junto con su fase de detección (blue team):
cada técnica tiene su mapeo MITRE ATT&CK y sus oportunidades de detección.

## Por qué no usa credenciales IAM estáticas

La primera versión empaquetaba `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`
dentro del ejecutable (via `.env` en un SFX). Eso es un error de arquitectura:

- Cualquier analista extrae las credenciales del binario con `strings`.
- Unas claves IAM de escritura comprometidas permiten operar sobre toda la cuenta.
- No hay expiración, ni revocación granular, ni auditabilidad del uso.

Diseño actual:

- El agente solo conoce una URL de API Gateway y un token de API.
- El token solo permite pedir URLs de subida a una carpeta concreta de un bucket.
- Las URLs expiran (default 120 s) y solo sirven para `PUT` (no leer, no listar).
- Todo queda en CloudTrail: quién pidió URL y cuándo se subió cada objeto.

## Arquitectura

```
+----------------+  POST /url            +---------------+  presigned PUT (120s)
|  Agente        |  x-api-key: token --> |  API Gateway  |  +---------------+
|  (Keylogger.py)|                       |  + API key    |  |  Lambda       |
+----------------+                       +-------+-------+  |  (issuer)     |
        |                                        |          +-------+-------+
        | PUT log file -----------------------> |  S3 (logs/<agent>/...) <--+
        +----------------------------------------
```

## Estructura del repositorio

```
.
├── Keylogger.py           # Agente: captura + exfiltración
├── test_config.py         # Verificador de configuración
├── .env.example           # Plantilla de configuración (copiar a .env)
├── requirements.txt       # requests, python-dotenv
├── backend/
│   ├── template.yaml      # CloudFormation: API Gateway + Lambda + S3
│   └── README.md          # Despliegue del backend
├── ttp/                   # TTPs legacy de ejecución (solo documentación)
└── README.md
```

## Despliegue

### 1. Backend AWS

Sigue `backend/README.md`. En resumen:

```powershell
aws cloudformation create-stack `
  --stack-name keylogger-backend `
  --template-body file://backend/template.yaml `
  --capabilities CAPABILITY_IAM `
  --parameters ParameterKey=SharedToken,ParameterValue=TU-TOKEN-LARGO-Y-ALEATORIO
```

El output `ApiEndpoint` es tu `API_URL` y el token que elegiste es tu `SHARED_TOKEN`.

### 2. Agente

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
```

Completa el `.env`:

```ini
MODO=nube                       # o "local" para captura sin red
API_URL=https://abc123.execute-api.us-east-1.amazonaws.com/prod
SHARED_TOKEN=el-mismo-token-del-stack
AGENT_ID=LAB-PC01
UPLOAD_INTERVAL=60              # segundos entre subidas
MAX_FILE_MB=10                  # rotación del archivo local
HIDE_CONSOLE=false              # true = FreeConsole (ver ATT&CK T1564.003)
LOG_FILENAME=syslog_temp.dat
```

Verifica y ejecuta:

```powershell
python test_config.py
python Keylogger.py             # Ctrl+C detiene y sube el último lote
```

### 3. Ejecutable de laboratorio (opcional)

```powershell
pyinstaller --onefile --noconsole --name=agent Keylogger.py
```

El `.env` se copia **junto** al `.exe` en la máquina de laboratorio (se lee del
directorio del ejecutable). **Nunca** lo empaques dentro del binario ni lo
distribuyas: es el equivalente al error original que este proyecto corrige.

## Modo local

`MODO=local` captura teclado y guarda solo en `%TEMP%\syslog_temp.dat`, sin
tráfico de red. Útil para desarrollar la parte de detección en la propia máquina
(sin desplegar el backend).

## Mapeo MITRE ATT&CK

| Técnica | ID | Dónde |
|---|---|---|
| Input Capture: Keylogging | T1056.001 | Bucle `GetAsyncKeyState` en `Keylogger.py` |
| System Owner/User Discovery | T1033 | `os.getlogin()` en el header de sesión |
| System Information Discovery | T1082 | Nombre de máquina (`socket.gethostname`) |
| Exfiltration Over Web Service | T1567.002 | `PUT` directo a S3 con pre-signed URL |
| Hidden Window | T1564.003 | `HIDE_CONSOLE=true` (FreeConsole) |
| Obfuscated Files (log con tokens) | T1027 | Tokens `[ENTER]`, `[TAB]` en los logs |

La cadena legacy de entrega está documentada en `ttp/README.md`.

## Oportunidades de detección (adelanto de la fase blue)

- **CloudTrail:** `PutObject` desde IP residencial con `user-agent` de `requests`,
  sin `GetObject` previo, hacia un prefijo `logs/<agent>/...`.
- **GuardDuty:** llamadas a API Gateway desde IPs nuevas + tráfico saliente a S3.
- **Endpoint:** polling de `GetAsyncKeyState` (hooks de API), proceso Python sin
  consola escribiendo en `%TEMP%`, strings sospechosos en el binario.
- **Red:** conexiones TLS directas a `*.execute-api.*.amazonaws.com` y a `s3.*.amazonaws.com`
  desde procesos no navegadores.

Detalle completo en la fase 2 del proyecto (detección y respuesta).

## Aviso legal

Proyecto exclusivamente educativo. Usa este software **solo** en dispositivos
propios o con autorización escrita del propietario, en entornos de laboratorio
aislados. La captura de teclado sin consentimiento es ilegal en la mayoría de
las jurisdicciones.
