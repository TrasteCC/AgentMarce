# 4. Sprint Backlog: Detailed Implementation Plan

> Each block is independent (modular). You can pause and resume at any point.
> Total estimate: 4 weeks at ~2-3 hours per day.

---

## WEEK 1 — Base Infrastructure

### Day 1 (3 hours): Agent VM on Unraid

**Block 1A (1.5h): Create the VM**

- Unraid UI → `VMs` → `Add VM`
- Type: Linux
- OS: Ubuntu Server 24.04 LTS (download ISO from ubuntu.com/download/server)
- CPU: `6 vCPUs` (enable CPU Pinning, select threads 2-7)
- RAM: `12288 MB` (12 GB)
- Primary vDisk: `100 GB`
- Network Bridge: `br0`
- Click `Create`

**Block 1B (1.5h): Install Ubuntu Server**

During Ubuntu installation:
- Hostname: `agent-vm`
- Username: `agentuser`
- Install OpenSSH Server: **YES**

Connect via SSH from your PC:
```bash
ssh agentuser@<VM_IP_ADDRESS>
```

---

### Day 2 (2 hours): Docker + Ollama

**Block 2A (45 min): Install Docker**

```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker agentuser
sudo apt install docker-compose-plugin -y
docker --version
```

**Block 2B (1h 15min): Set up Ollama**

```bash
mkdir -p ~/agent-services/ollama
cd ~/agent-services/ollama
# Copy docker-compose.yml from this repository
docker compose up -d
docker exec ollama-cpu ollama pull qwen2.5:1.5b
docker exec ollama-cpu ollama run qwen2.5:1.5b "say hello in 3 words"
```

---

### Day 3 (2.5 hours): Python + Google ADK

**Block 3A (45 min): Python virtual environment**

```bash
sudo apt install python3-pip python3-venv -y
mkdir -p ~/agent-services/antigravity-agent
cd ~/agent-services/antigravity-agent
python3 -m venv .venv
source .venv/bin/activate
```

**Block 3B (1h 45min): Install dependencies**

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

### Day 4 (3 hours): Agent Structure

**Block 4A: Create the file structure**

```bash
cd ~/agent-services/antigravity-agent
mkdir -p tools logs config
```

**Block 4B: Configure environment variables**

Copy `.env.example` from this repository to `.env` and fill in the values:

```bash
cp .env.example .env
nano .env
```

**Block 4C: Copy and test the agent**

```bash
# Copy agent.py and api_server.py from this repository
python3 agent.py
# Type "check proxmox status" to test
```

---

## WEEK 2 — n8n as the Nervous System

### Day 5 (2.5 hours): Telegram Workflow in n8n

Create a new workflow in n8n with these nodes in order:

```
[Telegram Trigger] → [IF classifier] → [Route A: Ollama] → [Telegram Send]
                                      → [Route B: Agent]  ↗
```

**Node 1 - Telegram Trigger:**
- Type: `Telegram Trigger`
- Events: `Message`

**Node 2 - IF Classifier:**
- Value 1: `{{ $json.message.text }}`
- Operation: `Regex`
- Value 2: `^(turn on|turn off|toggle|light|switch|open|close)`

**Node 3A (TRUE) - Ollama Direct:**
- Type: HTTP Request
- Method: POST
- URL: `http://VM_IP:11434/api/generate`
- Body: see architecture section

**Node 3B (FALSE) - Full Agent:**
- Type: HTTP Request
- Method: POST
- URL: `http://VM_IP:8080/agent/run`

**Node 4 - Telegram Send:**
- Operation: Send Message
- Chat ID: `{{ $('Telegram Trigger').item.json.message.chat.id }}`

---

### Day 6 (2 hours): Agent API Server

**Block 6A: Start the FastAPI server**

```bash
cd ~/agent-services/antigravity-agent
source .venv/bin/activate

# Copy marce-agent.service to /etc/systemd/system/
sudo cp marce-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable marce-agent
sudo systemctl start marce-agent
sudo systemctl status marce-agent
```

**Block 6B: Test from n8n**

```bash
# From the VM, test that the server responds
curl -X POST http://localhost:8080/agent/run \
  -H "Content-Type: application/json" \
  -d '{"input": "what is the proxmox status", "user": "test"}'
```

---

### Day 7 (3 hours): Daily Log Review Workflow

**Block 7A: Prepare the log collection script**

```bash
# Copy collect_logs.sh from this repository
mkdir -p ~/agent-services/antigravity-agent/tools
cp collect_logs.sh ~/agent-services/antigravity-agent/tools/
chmod +x ~/agent-services/antigravity-agent/tools/collect_logs.sh

# Test manually
bash ~/agent-services/antigravity-agent/tools/collect_logs.sh
```

**Block 7B: n8n daily review workflow**

```
[Schedule: 08:00 AM] → [SSH: run collect_logs.sh] → [HTTP: Groq API] → [Telegram Send]
```

- Schedule Trigger: Cron `0 8 * * *`
- SSH: connect to VM, run the script
- HTTP Request to Groq: send logs for analysis
- Telegram: send the summarized report

---

## WEEK 3 — Advanced Integrations

### Days 8-9 (4 hours total): Google APIs (OAuth2)

**Step 1: Create a Google Cloud Console project**
1. Go to console.cloud.google.com
2. Create Project: `AgentMarce`
3. Enable APIs: Gmail API, Google Drive API, Google Calendar API
4. Create OAuth2 credentials (type "Desktop application")
5. Download JSON → save as `config/google_credentials.json` on the VM

**Step 2: First-time authentication**

```bash
cd ~/agent-services/antigravity-agent
source .venv/bin/activate
python3 -c "from tools.google_tools import get_today_calendar_events; print(get_today_calendar_events())"
# A browser will open to authorize — only needed once
```

---

### Day 10 (2 hours): Slack Integration

**Step 1: Create a Slack App**
1. api.slack.com/apps → Create New App
2. OAuth & Permissions → Bot Token Scopes: `chat:write`, `channels:read`, `im:history`
3. Event Subscriptions → URL: `https://YOUR_N8N_URL/webhook/slack-events`
4. Subscribe to: `message.im`, `app_mention`

**Step 2: Duplicate the Telegram workflow in n8n**
- Change the Trigger to `Slack Trigger`
- Change the response to a `Slack → Post Message` node

---

## WEEK 4 — Secure Terminal Access and Polish

### Days 11-12 (4 hours): Terminal with Least Privilege

See `/docs/05-security.md` for the full restricted terminal setup.

```bash
# On the Unraid host (not inside the VM)
adduser agent-runner --disabled-password
mkdir -p /usr/local/agent-scripts
# Copy whitelist.sh from this repository
chmod +x /usr/local/agent-scripts/whitelist.sh
echo "agent-runner ALL=(ALL) NOPASSWD: /usr/local/agent-scripts/whitelist.sh" >> /etc/sudoers
```

### Days 13-14 (4 hours): Testing and Alerts

**Testing checklist:**
- [ ] Telegram: "turn off the living room light" → HA executes the action
- [ ] Telegram: "analyze today's logs" → Groq responds with a summary
- [ ] Daily report arrives at 8:00 AM
- [ ] Telegram: "how many VMs does Proxmox have" → correct response
- [ ] Telegram: "what events do I have today" → Google Calendar responds
- [ ] Slack: same tests as above
- [ ] VM does not exceed 10 GB RAM under normal usage
- [ ] Ollama unloads from RAM when idle

---

## Implementation Notes

- **One thing at a time:** Complete and test each block before moving to the next.
- **Save API keys from the start:** Fill in `.env` on Day 4 with all the keys you already have.
- **n8n is your ally:** Almost all connection logic lives in n8n, not Python. Python is the brain, n8n is the nervous system.
- **If something fails:** Check `sudo systemctl status marce-agent` and `docker logs ollama-cpu` first.
