"""
AgentMarce - Agente principal usando Google ADK (Antigravity)
Orquestacion de homelab: Unraid, Proxmox, Home Assistant

Requisitos:
    pip install google-adk python-dotenv requests groq fastapi uvicorn

Uso directo (modo interactivo):
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

# ── Importacion del ADK ────────────────────────────────────────────

try:
    from google.adk.agents import Agent
    from google.adk.models.lite_llm import LiteLlm
except ImportError:
    raise SystemExit(
        "ERROR: google-adk no instalado.\n"
        "Ejecuta: pip install google-adk"
    )

# ── Herramientas del Agente ────────────────────────────────────────

def home_assistant_action(entity_id: str, action: str) -> str:
    """
    Controla dispositivos en Home Assistant.

    Args:
        entity_id: ID de la entidad (ej: 'light.salon', 'switch.impresora')
        action: Accion a ejecutar ('turn_on', 'turn_off', 'toggle')

    Returns:
        Mensaje de confirmacion o error.
    """
    import requests

    valid_actions = ("turn_on", "turn_off", "toggle")
    if action not in valid_actions:
        return f"Accion invalida: {action}. Usa: {valid_actions}"

    url = f"{os.getenv('HOME_ASSISTANT_URL')}/api/services/homeassistant/{action}"
    headers = {
        "Authorization": f"Bearer {os.getenv('HOME_ASSISTANT_TOKEN')}",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(url, headers=headers, json={"entity_id": entity_id}, timeout=10)
        if resp.status_code in (200, 201):
            logging.info(f"HA action: {action} on {entity_id}")
            return f"OK: {action} ejecutado en {entity_id}"
        return f"ERROR HA {resp.status_code}: {resp.text[:200]}"
    except requests.exceptions.RequestException as e:
        return f"Error de conexion con Home Assistant: {e}"


def get_ha_state(entity_id: str) -> str:
    """
    Consulta el estado actual de un dispositivo en Home Assistant.

    Args:
        entity_id: ID de la entidad (ej: 'sensor.temperatura_salon')

    Returns:
        Estado y atributos del dispositivo.
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
                f"Estado de {entity_id}: {data.get('state')}\n"
                f"Atributos: {json.dumps(attrs, ensure_ascii=False)}"
            )
        return f"Entidad no encontrada: {resp.status_code}"
    except requests.exceptions.RequestException as e:
        return f"Error de conexion con Home Assistant: {e}"


def check_proxmox_status() -> str:
    """
    Consulta el estado de los nodos y VMs en Proxmox via API Token (solo lectura).

    Returns:
        Resumen del estado de nodos Proxmox.
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
            return f"Error conectando con Proxmox: {nodes_resp.status_code}"

        nodes = nodes_resp.json().get('data', [])
        resultado = "Estado Proxmox:\n"
        for node in nodes:
            cpu_pct = node.get('cpu', 0) * 100
            ram_used = node.get('mem', 0) / 1024 / 1024 / 1024
            ram_total = node.get('maxmem', 1) / 1024 / 1024 / 1024
            resultado += (
                f"  Nodo {node['node']}: {node['status']}\n"
                f"    CPU: {cpu_pct:.1f}%\n"
                f"    RAM: {ram_used:.1f} GB / {ram_total:.1f} GB\n"
            )
        logging.info("Proxmox status checked")
        return resultado
    except requests.exceptions.RequestException as e:
        return f"Error de conexion con Proxmox: {e}"


def analyze_with_groq(content: str, task: str = "analisis general") -> str:
    """
    Envia contenido a Groq para analisis pesado (logs, razonamiento complejo).
    Usar cuando el contenido es extenso o requiere razonamiento avanzado.

    Args:
        content: Texto a analizar (logs, emails, etc.)
        task: Descripcion de la tarea para contextualizar el prompt

    Returns:
        Analisis de Groq en texto.
    """
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        chat = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un experto en DevOps e infraestructura IT para homelabs. "
                        "Analiza el contenido proporcionado y responde en espanol. "
                        "Se conciso y prioriza informacion accionable."
                    )
                },
                {"role": "user", "content": f"Tarea: {task}\n\nContenido:\n{content}"}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=2048,
            temperature=0.3
        )
        result = chat.choices[0].message.content
        logging.info(f"Groq analysis completed for task: {task}")
        return result
    except Exception as e:
        return f"Error llamando a Groq: {e}"


# Lista blanca de comandos permitidos (seguridad)
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
    Ejecuta un comando del sistema de forma segura contra una lista blanca.
    NUNCA ejecuta comandos fuera de la lista blanca.

    Args:
        command: Comando a ejecutar (debe estar en la lista blanca)

    Returns:
        Output del comando o mensaje de error de seguridad.
    """
    command_allowed = any(command.strip().startswith(allowed) for allowed in ALLOWED_COMMANDS)

    if not command_allowed:
        logging.warning(f"BLOCKED command attempt: {command}")
        return (
            f"SEGURIDAD: El comando '{command}' no esta en la lista blanca.\n"
            f"Comandos permitidos: {ALLOWED_COMMANDS}"
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
        return "Error: El comando supero el limite de 30 segundos y fue cancelado."
    except Exception as e:
        return f"Error al ejecutar comando: {e}"


# ── Configuracion del Agente ADK ──────────────────────────────────

local_llm = LiteLlm(
    model=f"ollama/{os.getenv('LOCAL_MODEL', 'qwen2.5:1.5b')}",
    api_base=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
)

agent = Agent(
    name="marce_agent",
    model=local_llm,
    description="Agente de orquestacion de infraestructura homelab personal",
    instruction="""
    Eres AgentMarce, un asistente de infraestructura inteligente para un homelab personal.
    Siempre respondes en espanol. Eres conciso y directo.

    Reglas de uso de herramientas:
    - Para controlar dispositivos (luces, switches): usa home_assistant_action o get_ha_state
    - Para estado del servidor Proxmox: usa check_proxmox_status
    - Para analisis de logs o textos largos: usa analyze_with_groq
    - Para comandos del sistema (solo los permitidos): usa execute_safe_command
    - Si no sabes como hacer algo, dilo claramente en lugar de inventar

    Nunca ejecutes acciones destructivas. Cuando tengas dudas, pregunta al usuario.
    """,
    tools=[
        home_assistant_action,
        get_ha_state,
        check_proxmox_status,
        analyze_with_groq,
        execute_safe_command,
    ]
)

# ── Modo interactivo (para testing directo) ────────────────────────

if __name__ == "__main__":
    print("AgentMarce iniciado en modo interactivo.")
    print("Escribe tu consulta o 'salir' para terminar.\n")
    while True:
        try:
            user_input = input("Tu: ").strip()
            if user_input.lower() in ("salir", "exit", "quit"):
                print("Agente detenido.")
                break
            if not user_input:
                continue
            response = agent.run(user_input)
            print(f"\nAgente: {response}\n")
        except KeyboardInterrupt:
            print("\nAgente detenido.")
            break
