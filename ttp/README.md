# TTPs de Ejecución y Ocultamiento (Legacy)

Esta carpeta conserva la cadena de lanzamiento que usaba la primera versión del
proyecto, **ya no forma parte del diseño actual**. Se mantiene únicamente como
material de estudio para la fase de detección (blue team).

## Contenido

| Archivo | Rol |
|---|---|
| `ejecuciones.bat` | Ejecuta el señuelo y el agente en secuencia |
| `ocultador.vbs` | Lanza el batch oculto vía `WScript.Shell.Run(..., vbHide)` |

El empaquetado original era: SFX de WinRAR (modo silencioso, "Ocultar todo")
→ `ocultador.vbs` → `ejecuciones.bat` → `DiscordSetup.exe` (señuelo) + `main.exe` (agente).
El SFX se renombraba como `DiscordSetup.exe` para aparentar un instalador legítimo.

## Mapeo MITRE ATT&CK

| TTP | Técnica | Evidencia |
|---|---|---|
| Ejecución por usuario | T1204.002 User Execution: Malicious File | SFX autoextraíble disfrazado de instalador |
| Ocultar ventana | T1564.003 Hidden Window | `ocultador.vbs` con `vbHide` |
| Ejecución scripting | T1059.005 Visual Basic | WScript ejecuta el VBS |
| Ejecución batch | T1059.003 Windows Command Shell | `ejecuciones.bat` |
| Disfraz de binario | T1036.005 Match Legitimate Name or Location | Renombrar a `DiscordSetup.exe` |
| Despliegue inicial | T1105 Ingress Tool Transfer | SFX entrega el agente |

## Oportunidades de detección (adelanto de la fase blue)

- `wscript.exe` como proceso padre de `cmd.exe` (escala poco común en equipos de oficina)
- Procesos con ventana oculta (`STARTF_USESHOWWINDOW` / flags `SW_HIDE`)
- Archivos SFX con "Ejecutar después de extraer" → firma de WinRAR en el binario
- Descarga/ejecución en `%TEMP%` + doble ejecutable (señuelo + agente)
- Sysmon Event ID 1: padre `wscript.exe` → hijo `cmd.exe` → nietos `.exe`

## Por qué ya no se usa

El enfoque de entrega con disfraz y ocultamiento no aporta a un perfil
profesional (y agrega superficie innecesaria). La versión actual es un agente
simple y auditable, con exfiltración por pre-signed URLs, pensado para estudiar
técnicas y sus detecciones en un laboratorio.
