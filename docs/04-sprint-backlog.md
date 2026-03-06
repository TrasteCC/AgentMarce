# 4. Sprint Backlog: Plan de Implementacion Detallado

> Cada bloque es independiente (modular). Puedes pausar y retomar en cualquier punto.
> Estimacion total: 4 semanas a ~2-3 horas por dia.

---

## SEMANA 1 — Infraestructura Base

### Dia 1 (3 horas): VM del Agente en Unraid

**Bloque 1A (1.5h): Crear la VM**

- Unraid UI → `VMs` → `Add VM`
- Tipo: Linux
- OS: Ubuntu Server 24.04 LTS (descargar ISO desde ubuntu.com/download/server)
- CPU: `6 vCPUs` (activar CPU Pinning, seleccionar threads 2-7)
- RAM: `12288 MB` (12 GB)
- Primary vDisk: `100 GB`
- Network Bridge: `br0`
- Click `Create`

**Bloque 1B (1.5h): Instalar Ubuntu Server**

Durante la instalacion de Ubuntu:
- Hostname: `agent-vm`
- Usuario: `agentuser`
- Instalar OpenSSH Server: **SI**

Conectar por SSH desde tu PC:
```bash
ssh agentuser@<IP_DE_LA_VM>
```

---

### Dia 2 (2 horas): Docker + Ollama

**Bloque 2A (45 min): Instalar Docker**

```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker agentuser
sudo apt install docker-compose-plugin -y
docker --version
```

**Bloque 2B (1h 15min): Configurar Ollama**

```bash
mkdir -p ~/agent-services/ollama
cd ~/agent-services/ollama
# Copiar docker-compose.yml de este repositorio
docker compose up -d
docker exec ollama-cpu ollama pull qwen2.5:1.5b
docker exec ollama-cpu ollama run qwen2.5:1.5b "di hola en 3 palabras"
```

---

### Dia 3 (2.5 horas): Python + Google ADK

**Bloque 3A (45 min): Entorno virtual Python**

```bash
sudo apt install python3-pip python3-venv -y
mkdir -p ~/agent-services/antigravity-agent
cd ~/agent-services/antigravity-agent
python3 -m venv .venv
source .venv/bin/activate
```

**Bloque 3B (1h 45min): Instalar dependencias**

```bash
pip install google-adk \
            python-telegram-bot \
            slack-sdk \
            google-auth-oauthlib \
            google-api-python-client \
            paramiko \
            requests \
            python-dotenv \
            aiohttp \
            fastapi \
            uvicorn \
            groq

python3 -c "import google.adk; print('ADK OK')"
```

---

### Dia 4 (3 horas): Estructura del Agente

**Bloque 4A: Crear estructura de archivos**

```bash
cd ~/agent-services/antigravity-agent
mkdir -p tools logs config
```

**Bloque 4B: Configurar variables de entorno**

Copiar `.env.example` de este repositorio a `.env` y rellenar los valores:

```bash
cp .env.example .env
nano .env
```

**Bloque 4C: Copiar y probar el agente**

```bash
# Copiar agent.py y api_server.py de este repositorio
python3 agent.py
# Escribe "estado de proxmox" para probar
```

---

## SEMANA 2 — n8n como Sistema Nervioso

### Dia 5 (2.5 horas): Workflow Telegram en n8n

Crear un nuevo workflow en n8n con estos nodos en orden:

```
[Telegram Trigger] → [IF clasificador] → [Ruta A: Ollama] → [Telegram Send]
                                       → [Ruta B: Agente]  ↗
```

**Nodo 1 - Telegram Trigger:**
- Tipo: `Telegram Trigger`
- Events: `Message`

**Nodo 2 - IF Clasificador:**
- Valor 1: `{{ $json.message.text }}`
- Operacion: `Regex`
- Valor 2: `^(enciende|apaga|estado|toggle|luz|switch|lampara|abre|cierra)`

**Nodo 3A (TRUE) - Ollama Directo:**
- Tipo: HTTP Request
- Method: POST
- URL: `http://IP_VM:11434/api/generate`
- Body: ver seccion de arquitectura

**Nodo 3B (FALSE) - Agente Completo:**
- Tipo: HTTP Request
- Method: POST
- URL: `http://IP_VM:8080/agent/run`

**Nodo 4 - Telegram Send:**
- Operacion: Send Message
- Chat ID: `{{ $('Telegram Trigger').item.json.message.chat.id }}`

---

### Dia 6 (2 horas): Servidor API del Agente

**Bloque 6A: Iniciar el servidor FastAPI**

```bash
cd ~/agent-services/antigravity-agent
source .venv/bin/activate

# Copiar marce-agent.service a /etc/systemd/system/
sudo cp marce-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable marce-agent
sudo systemctl start marce-agent
sudo systemctl status marce-agent
```

**Bloque 6B: Probar desde n8n**

```bash
# Desde la VM, probar que el servidor responde
curl -X POST http://localhost:8080/agent/run \
  -H "Content-Type: application/json" \
  -d '{"input": "cual es el estado de proxmox", "user": "test"}'
```

---

### Dia 7 (3 horas): Workflow de Log Review Diario

**Bloque 7A: Preparar el script de logs**

```bash
# Copiar collect_logs.sh de este repositorio
mkdir -p ~/agent-services/antigravity-agent/tools
cp collect_logs.sh ~/agent-services/antigravity-agent/tools/
chmod +x ~/agent-services/antigravity-agent/tools/collect_logs.sh

# Probar manualmente
bash ~/agent-services/antigravity-agent/tools/collect_logs.sh
```

**Bloque 7B: Workflow n8n de revision diaria**

```
[Schedule: 08:00 AM] → [SSH: ejecuta collect_logs.sh] → [HTTP: Groq API] → [Telegram Send]
```

- Schedule Trigger: Cron `0 8 * * *`
- SSH: conectar a la VM, ejecutar el script
- HTTP Request a Groq: enviar los logs para analisis
- Telegram: enviar el reporte resumido

---

## SEMANA 3 — Integraciones Avanzadas

### Dias 8-9 (4 horas total): Google APIs (OAuth2)

**Paso 1: Crear proyecto en Google Cloud Console**
1. Ir a console.cloud.google.com
2. Crear Proyecto: `AgentMarce`
3. Habilitar APIs: Gmail API, Google Drive API, Google Calendar API
4. Crear credenciales OAuth2 (tipo "Aplicacion de escritorio")
5. Descargar JSON → guardar como `config/google_credentials.json` en la VM

**Paso 2: Primera autenticacion**

```bash
cd ~/agent-services/antigravity-agent
source .venv/bin/activate
python3 -c "from tools.google_tools import get_today_calendar_events; print(get_today_calendar_events())"
# Se abrira un navegador para autorizar — solo la primera vez
```

---

### Dia 10 (2 horas): Integracion Slack

**Paso 1: Crear Slack App**
1. api.slack.com/apps → Create New App
2. OAuth & Permissions → Bot Token Scopes: `chat:write`, `channels:read`, `im:history`
3. Event Subscriptions → URL: `https://TU_N8N_URL/webhook/slack-events`
4. Subscribe: `message.im`, `app_mention`

**Paso 2: Duplicar workflow de Telegram en n8n**
- Cambiar Trigger por `Slack Trigger`
- Cambiar respuesta por nodo `Slack → Post Message`

---

## SEMANA 4 — Acceso Seguro a Terminal y Pulido

### Dias 11-12 (4 horas): Terminal con Least Privilege

Ver `/docs/05-seguridad.md` para la configuracion completa del acceso restringido a terminal.

```bash
# En Unraid host (no en la VM)
adduser agent-runner --disabled-password
mkdir -p /usr/local/agent-scripts
# Copiar whitelist.sh del repositorio
chmod +x /usr/local/agent-scripts/whitelist.sh
echo "agent-runner ALL=(ALL) NOPASSWD: /usr/local/agent-scripts/whitelist.sh" >> /etc/sudoers
```

### Dias 13-14 (4 horas): Testing y Alertas

**Checklist de pruebas:**
- [ ] Telegram: "apaga la luz del salon" → HA ejecuta la accion
- [ ] Telegram: "analiza los logs de hoy" → Groq responde con resumen
- [ ] Reporte diario llega a las 8:00 AM
- [ ] Telegram: "cuantas VMs tiene proxmox" → respuesta correcta
- [ ] Telegram: "que eventos tengo hoy" → Google Calendar responde
- [ ] Slack: los mismos tests anteriores
- [ ] La VM no supera 10 GB de RAM en uso normal
- [ ] Ollama se descarga de RAM cuando esta inactivo

---

## Notas de Implementacion

- **Principio de una cosa a la vez:** Completa y prueba cada bloque antes de pasar al siguiente.
- **Guarda las API keys desde el principio:** Rellena el `.env` en el Dia 4 con todas las keys que ya tengas.
- **n8n es tu aliado:** Casi toda la logica de conexion vive en n8n, no en Python. Python es el cerebro, n8n son los nervios.
- **Si algo falla:** Revisa primero `sudo systemctl status marce-agent` y `docker logs ollama-cpu`.
