"""
AgentMarce - Main agent using Google ADK (Antigravity)
Homelab orchestration: Unraid, Proxmox, Home Assistant

Requirements:
    pip install google-adk python-dotenv requests groq fastapi uvicorn

Direct usage (interactive mode):
    source .venv/bin/activate
    python3 agent.py
"""

import os
import json
import logging
import subprocess
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    filename='/var/log/agent-marce.log',
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)

# ── ADK Import ────────────────────────────────────────────────────

try:
    from google.adk.agents import Agent
    from google.adk.models.lite_llm import LiteLlm
except ImportError:
    raise SystemExit(
        "ERROR: google-adk is not installed.\n"
        "Run: pip install google-adk"
    )

# ── Agent Tools ───────────────────────────────────────────────────

def home_assistant_action(entity_id: str, action: str) -> str:
    """
    Controls devices in Home Assistant.

    Args:
        entity_id: Entity ID (e.g. 'light.living_room', 'switch.printer')
        action: Action to perform ('turn_on', 'turn_off', 'toggle')

    Returns:
        Confirmation or error message.
    """
    import requests

    valid_actions = ("turn_on", "turn_off", "toggle")
    if action not in valid_actions:
        return f"Invalid action: {action}. Use one of: {valid_actions}"

    url = f"{os.getenv('HOME_ASSISTANT_URL')}/api/services/homeassistant/{action}"
    headers = {
        "Authorization": f"Bearer {os.getenv('HOME_ASSISTANT_TOKEN')}",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(url, headers=headers, json={"entity_id": entity_id}, timeout=10)
        if resp.status_code in (200, 201):
            logging.info(f"HA action: {action} on {entity_id}")
            return f"OK: {action} executed on {entity_id}"
        return f"HA ERROR {resp.status_code}: {resp.text[:200]}"
    except requests.exceptions.RequestException as e:
        return f"Connection error with Home Assistant: {e}"


def get_ha_state(entity_id: str) -> str:
    """
    Queries the current state of a device in Home Assistant.

    Args:
        entity_id: Entity ID (e.g. 'sensor.living_room_temperature')

    Returns:
        Current state and attributes of the device.
    """
    import requests

    url = f"{os.getenv('HOME_ASSISTANT_URL')}/api/states/{entity_id}"
    headers = {"Authorization": f"Bearer {os.getenv('HOME_ASSISTANT_TOKEN')}"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            attrs = data.get('attributes', {})
            return (
                f"State of {entity_id}: {data.get('state')}\n"
                f"Attributes: {json.dumps(attrs, ensure_ascii=False)}"
            )
        return f"Entity not found: {resp.status_code}"
    except requests.exceptions.RequestException as e:
        return f"Connection error with Home Assistant: {e}"


def check_proxmox_status() -> str:
    """
    Queries the status of Proxmox nodes and VMs via API Token (read-only).

    Returns:
        Summary of Proxmox node status.
    """
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    host = os.getenv('PROXMOX_HOST')
    token_id = os.getenv('PROXMOX_API_TOKEN_ID')
    token_secret = os.getenv('PROXMOX_API_TOKEN_SECRET')

    headers = {"Authorization": f"PVEAPIToken={token_id}={token_secret}"}
    base_url = f"https://{host}:8006/api2/json"

    try:
        nodes_resp = requests.get(
            f"{base_url}/nodes",
            headers=headers,
            verify=False,
            timeout=10
        )
        if nodes_resp.status_code != 200:
            return f"Error connecting to Proxmox: {nodes_resp.status_code}"

        nodes = nodes_resp.json().get('data', [])
        result = "Proxmox Status:\n"
        for node in nodes:
            cpu_pct = node.get('cpu', 0) * 100
            ram_used = node.get('mem', 0) / 1024 / 1024 / 1024
            ram_total = node.get('maxmem', 1) / 1024 / 1024 / 1024
            result += (
                f"  Node {node['node']}: {node['status']}\n"
                f"    CPU: {cpu_pct:.1f}%\n"
                f"    RAM: {ram_used:.1f} GB / {ram_total:.1f} GB\n"
            )
        logging.info("Proxmox status checked")
        return result
    except requests.exceptions.RequestException as e:
        return f"Connection error with Proxmox: {e}"


def analyze_with_groq(content: str, task: str = "general analysis") -> str:
    """
    Sends content to Groq for heavy analysis (logs, complex reasoning).
    Use when content is large or requires advanced reasoning.

    Args:
        content: Text to analyze (logs, emails, etc.)
        task: Task description to contextualize the prompt

    Returns:
        Groq's analysis as text.
    """
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        chat = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a DevOps and IT infrastructure expert for homelabs. "
                        "Analyze the provided content and respond concisely, "
                        "prioritizing actionable information."
                    )
                },
                {"role": "user", "content": f"Task: {task}\n\nContent:\n{content}"}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=2048,
            temperature=0.3
        )
        result = chat.choices[0].message.content
        logging.info(f"Groq analysis completed for task: {task}")
        return result
    except Exception as e:
        return f"Error calling Groq: {e}"


# Allowed command whitelist (security)
ALLOWED_COMMANDS = [
    "docker ps",
    "docker stats --no-stream",
    "docker logs",
    "df -h",
    "free -h",
    "uptime",
    "systemctl status",
    "netstat -tulpn",
]


def execute_safe_command(command: str) -> str:
    """
    Executes a system command safely against a whitelist.
    NEVER executes commands outside the whitelist.

    Args:
        command: Command to execute (must be in the whitelist)

    Returns:
        Command output or security error message.
    """
    command_allowed = any(command.strip().startswith(allowed) for allowed in ALLOWED_COMMANDS)

    if not command_allowed:
        logging.warning(f"BLOCKED command attempt: {command}")
        return (
            f"SECURITY: Command '{command}' is not in the whitelist.\n"
            f"Allowed commands: {ALLOWED_COMMANDS}"
        )

    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/tmp"
        )
        logging.info(f"Command executed: {command}")
        return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command exceeded the 30-second limit and was cancelled."
    except Exception as e:
        return f"Error executing command: {e}"


# ── ADK Agent Configuration ───────────────────────────────────────

local_llm = LiteLlm(
    model=f"ollama/{os.getenv('LOCAL_MODEL', 'qwen2.5:1.5b')}",
    api_base=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
)

agent = Agent(
    name="marce_agent",
    model=local_llm,
    description="Personal homelab infrastructure orchestration agent",
    instruction="""
    You are AgentMarce, an intelligent infrastructure assistant for a personal homelab.
    Always respond concisely and directly.

    Tool usage rules:
    - To control devices (lights, switches): use home_assistant_action or get_ha_state
    - For Proxmox server status: use check_proxmox_status
    - For log analysis or large texts: use analyze_with_groq
    - For system commands (whitelisted only): use execute_safe_command
    - If you don't know how to do something, say so clearly instead of guessing

    Never perform destructive actions. When in doubt, ask the user first.
    """,
    tools=[
        home_assistant_action,
        get_ha_state,
        check_proxmox_status,
        analyze_with_groq,
        execute_safe_command,
    ]
)

# ── Interactive mode (for direct testing) ─────────────────────────

if __name__ == "__main__":
    print("AgentMarce started in interactive mode.")
    print("Type your query or 'exit' to quit.\n")
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("exit", "quit"):
                print("Agent stopped.")
                break
            if not user_input:
                continue
            response = agent.run(user_input)
            print(f"\nAgent: {response}\n")
        except KeyboardInterrupt:
            print("\nAgent stopped.")
            break
