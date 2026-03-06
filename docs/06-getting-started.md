# 6. Getting Started (Day 0)

> Do these steps today, in this exact order. Each step unlocks the next one.
> Total estimated time: 1.5 hours.

---

## Step 1: Get Your Free API Keys (30 minutes)

Open your browser and create these accounts. All of them have a free tier sufficient for this project.

### Groq (for log analysis — FREE)

1. Go to https://console.groq.com
2. `Sign Up` with Google
3. `API Keys` → `Create API Key`
4. Copy and save in a notepad: `GROQ_API_KEY=gsk_...`

**Why Groq:** Processes ~6000 tokens/second. A 500-line log file is analyzed in 2 seconds.
The free tier allows 30 requests/minute and 14,400 requests/day — more than enough.

### OpenRouter (fallback model)

1. Go to https://openrouter.ai
2. `Sign In` with Google → `Keys` → `Create Key`
3. Copy: `OPENROUTER_API_KEY=sk-or-...`

**Why OpenRouter:** A single endpoint that gives access to Claude, GPT-4, Gemini and dozens
of other models. Useful when Groq doesn't have the right model for a specific task.

### Telegram Bot

1. Open Telegram on your phone or PC
2. Search for `@BotFather` (the official one, has a blue checkmark)
3. Type `/newbot`
4. When it asks for a name: type `AgentMarce` (or whatever you prefer)
5. When it asks for a username: type `agentmarce_bot` (must end in `_bot`)
6. Copy the token: `TELEGRAM_BOT_TOKEN=1234567890:ABCdef...`

> Save all three tokens somewhere safe (a password manager like Bitwarden).
> You will need them on Day 4 when you configure the `.env` file.

---

## Step 2: Create the VM on Unraid (45 minutes)

### 2.1 Download the Ubuntu Server ISO

1. In your browser, go to: https://ubuntu.com/download/server
2. Download `Ubuntu Server 24.04.x LTS` (the .iso file, ~2 GB)
3. Copy the ISO file to the `isos` folder on Unraid
   - In Unraid UI → `Main` → locate your array → find the `isos` share
   - Or use the network path: `\\UNRAID_IP\isos\`

### 2.2 Create the VM

1. In Unraid UI → `VMs` tab → `Add VM` button
2. Select `Linux` from the list
3. Fill in the fields:

| Field | Exact value |
|---|---|
| Name | `agent-marce` |
| CPUs | `6` |
| Initial Memory | `12288` MB |
| Max Memory | `12288` MB |
| Machine | `i440fx-9.1` |
| BIOS | `SeaBIOS` |
| Primary vDisk Size | `100G` |
| ISO | (select the Ubuntu file you downloaded) |

4. Click `Create`

### 2.3 Install Ubuntu Server

1. Click the screen icon (VNC) of the VM in Unraid
2. A window will open with the Ubuntu installer
3. During installation, when prompted:
   - **Your name / Server name:** `agentuser` / `agent-vm`
   - **Username:** `agentuser`
   - **Password:** choose a secure one and save it
   - **OpenSSH Server:** select **YES** with the spacebar
4. Let the installation finish (~15 minutes) and reboot when prompted

---

## Step 3: Verify Connectivity (15 minutes)

### 3.1 Find the VM's IP address

Option A — From Unraid:
- VMs → your `agent-marce` VM → check the network details

Option B — From the VNC console of the VM, type:
```bash
ip addr show | grep "inet "
```
Look for the line starting with `inet 192.168.x.x` (not the one that says `127.0.0.1`).

### 3.2 Connect via SSH

**On Windows** (open PowerShell with Win+X → Windows PowerShell):
```bash
ssh agentuser@192.168.1.XXX
```

**On Mac or Linux** (open Terminal):
```bash
ssh agentuser@192.168.1.XXX
```

Replace `192.168.1.XXX` with your VM's actual IP.

When you see this, everything is working:
```
agentuser@agent-vm:~$
```

### 3.3 Verify that n8n can connect to the VM

1. In n8n → `Credentials` → `New Credential`
2. Search for and select `SSH`
3. Fill in:
   - Host: VM's IP address
   - Port: `22`
   - Username: `agentuser`
   - Authentication: `Password`
   - Password: the one you chose during installation
4. Click `Test` → should show "Connection successful"

---

## When You Finish Step 3...

You have everything you need to continue with Day 1 of the Sprint Backlog:

- The VM exists and is accessible via SSH
- n8n can communicate with it
- You have your API keys ready for `.env`

**Next step:** Go to [Sprint Backlog - Day 2](04-sprint-backlog.md) to install Docker and Ollama.

---

## Troubleshooting Common Issues

**Cannot connect via SSH:**
- Verify the VM is running (Unraid → VMs → status "Running")
- Verify the IP is correct with `ip addr show` in the VNC console
- Check that the Unraid firewall is not blocking port 22

**ISO doesn't appear in Unraid when creating the VM:**
- Make sure the .iso file is in the correct folder on the Unraid array
- Reload the Unraid page and try again

**n8n SSH test fails:**
- Make sure the VM is running
- Double-check the username and password
- Make sure you selected SSH (not SFTP) as the credential type
