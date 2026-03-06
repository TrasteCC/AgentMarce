# 5. Security Considerations

## Principle of Least Privilege

The agent only has access to what it strictly needs in each system.
Never use admin credentials when a read-only alternative exists.

## Permissions Matrix

```
┌─────────────────────────────────────────────────────────┐
│                  AGENT PERMISSIONS MATRIX               │
├───────────────────┬──────────────┬──────────────────────┤
│  System           │  Access      │  Restriction         │
├───────────────────┼──────────────┼──────────────────────┤
│  Home Assistant   │  API Token   │  Only entities       │
│                   │  (read+ctrl) │  listed in config    │
├───────────────────┼──────────────┼──────────────────────┤
│  Proxmox          │  API Token   │  Read-only (GET)     │
│                   │  (read only) │  No VM create/delete │
├───────────────────┼──────────────┼──────────────────────┤
│  Unraid SSH       │  Restricted  │  Only whitelist.sh   │
│                   │  user        │  No root, no sudo    │
├───────────────────┼──────────────┼──────────────────────┤
│  Google APIs      │  OAuth2      │  Read-only scopes    │
│                   │  (readonly)  │  No send/delete      │
├───────────────────┼──────────────┼──────────────────────┤
│  Docker Ollama    │  localhost   │  Not exposed to      │
│                   │  only        │  the network         │
└───────────────────┴──────────────┴──────────────────────┘
```

## Setting Up Restricted Terminal Access

### Create a restricted user on Unraid

Run these commands via SSH on the Unraid host (not inside the VM):

```bash
# Create user without password (SSH key or direct commands only)
adduser agent-runner --disabled-password --gecos ""

# Create the allowed scripts directory
mkdir -p /usr/local/agent-scripts

# Copy the whitelist script
cp whitelist.sh /usr/local/agent-scripts/
chmod +x /usr/local/agent-scripts/whitelist.sh

# Configure restricted sudo (only for the whitelist script)
echo "agent-runner ALL=(ALL) NOPASSWD: /usr/local/agent-scripts/whitelist.sh" >> /etc/sudoers
```

### Command Whitelist (whitelist.sh)

Only these commands are allowed for the agent:

```
docker ps
docker stats --no-stream
docker logs [container-name]
df -h
free -h
uptime
systemctl status [service]
netstat -tulpn
cat /proc/cpuinfo
```

**Commands NEVER allowed:**
- `rm`, `rmdir` (file deletion)
- `shutdown`, `reboot`, `poweroff`
- `passwd`, `su`, `sudo` (privilege escalation)
- `curl` with redirections or pipes
- `wget` with direct execution
- Any command with `>` or `>>` (write redirection)

## Proxmox API Token Configuration (Read-Only)

In the Proxmox web interface:

1. `Datacenter` → `Permissions` → `API Tokens` → `Add`
2. User: `root@pam`
3. Token ID: `agent-readonly`
4. **Privilege Separation: YES** (this is critical)
5. Click OK → copy the generated token

6. `Datacenter` → `Permissions` → `Add` → `API Token Permission`
7. Path: `/`
8. API Token: `root@pam!agent-readonly`
9. Role: `PVEAuditor` (read-only, cannot modify anything)

## Home Assistant Token Configuration

In Home Assistant:

1. User profile (bottom-left icon) → `Long-Lived Access Tokens`
2. `Create Token`
3. Name: `agent-marce` (descriptive name so it can be revoked)
4. Copy the token → paste it in `.env`

**Restricted entities:** Consider creating a separate HA user with access
only to the entities the agent needs to control, rather than using an
admin token.

## Security Checklist

- [ ] All API keys are in `.env`, never hardcoded in the source code
- [ ] `.env` is in `.gitignore` (NEVER push the real .env to GitHub)
- [ ] Ollama only listens on localhost (127.0.0.1:11434), not 0.0.0.0
- [ ] Agent port 8080 is not exposed to the internet (LAN access only)
- [ ] n8n has basic authentication enabled in its settings
- [ ] Proxmox API Token created with `PVEAuditor` role (read-only)
- [ ] Home Assistant token named `agent-marce` for identification and revocation
- [ ] Agent logs saved to `/var/log/agent-marce.log` for auditing
- [ ] `.env` backed up in a password manager (Bitwarden, etc.)
- [ ] Unraid `agent-runner` user has no interactive shell access

## Security in Code

The `agent.py` file validates commands before executing them:

```python
ALLOWED_COMMANDS = [
    "docker ps", "docker stats --no-stream",
    "df -h", "free -h", "uptime", "systemctl status"
]

def execute_safe_command(command: str) -> str:
    command_allowed = any(command.startswith(allowed) for allowed in ALLOWED_COMMANDS)
    if not command_allowed:
        return f"SECURITY: Command not allowed. Available commands: {ALLOWED_COMMANDS}"
    # ... execution with 30-second timeout
```

## Audit and Logs

The FastAPI server logs every request with timestamp and user:

```python
logging.basicConfig(
    filename='/var/log/agent-marce.log',
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
```

To follow logs in real time:
```bash
tail -f /var/log/agent-marce.log
```

To view the last 50 events:
```bash
tail -50 /var/log/agent-marce.log
```
