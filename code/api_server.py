"""
AgentMarce - Servidor FastAPI
Expone el agente como API REST para que n8n pueda comunicarse con el.

Endpoints:
    POST /agent/run   - Enviar un mensaje al agente
    GET  /health      - Verificar que el servidor esta activo
    GET  /status      - Estado detallado del sistema

Uso:
    source .venv/bin/activate
    python3 api_server.py

    O via systemd:
    sudo systemctl start marce-agent
"""

import os
import logging
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Configurar logging
logging.basicConfig(
    filename='/var/log/agent-marce.log',
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar el agente
from agent import agent

app = FastAPI(
    title="AgentMarce API",
    description="API REST del agente de orquestacion de homelab",
    version="1.0.0"
)


# ── Modelos de datos ───────────────────────────────────────────────

class AgentRequest(BaseModel):
    input: str
    user: str = "unknown"
    channel: str = "api"   # "telegram", "slack", "api"

class AgentResponse(BaseModel):
    response: str
    user: str
    channel: str
    timestamp: str
    success: bool


# ── Middleware de logging ──────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response


# ── Endpoints ──────────────────────────────────────────────────────

@app.post("/agent/run", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    """
    Envia un mensaje al agente y devuelve la respuesta.

    Body:
        input   (str): El mensaje del usuario
        user    (str): Nombre o ID del usuario (para logs)
        channel (str): Canal de origen ("telegram", "slack", "api")
    """
    if not request.input.strip():
        raise HTTPException(status_code=400, detail="El campo 'input' no puede estar vacio")

    if len(request.input) > 4096:
        raise HTTPException(status_code=400, detail="El mensaje supera el limite de 4096 caracteres")

    logger.info(f"Agent request from {request.user} via {request.channel}: {request.input[:100]}...")

    try:
        contextualized_input = f"[Usuario: {request.user}] {request.input}"
        response = agent.run(contextualized_input)
        response_text = str(response)

        logger.info(f"Agent response (first 100 chars): {response_text[:100]}...")

        return AgentResponse(
            response=response_text,
            user=request.user,
            channel=request.channel,
            timestamp=datetime.now().isoformat(),
            success=True
        )
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del agente: {str(e)}")


@app.get("/health")
async def health_check():
    """Verificacion rapida de que el servidor esta activo."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/status")
async def system_status():
    """Estado detallado del sistema: Ollama, variables de entorno, etc."""
    import requests

    status = {
        "server": "running",
        "timestamp": datetime.now().isoformat(),
        "ollama": "unknown",
        "env_vars": {}
    }

    # Verificar Ollama
    try:
        ollama_resp = requests.get(
            f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/version",
            timeout=5
        )
        status["ollama"] = "ok" if ollama_resp.status_code == 200 else "error"
    except Exception:
        status["ollama"] = "unreachable"

    # Verificar variables criticas (sin revelar valores)
    critical_vars = [
        "OLLAMA_BASE_URL", "GROQ_API_KEY", "TELEGRAM_BOT_TOKEN",
        "HOME_ASSISTANT_URL", "PROXMOX_HOST"
    ]
    for var in critical_vars:
        status["env_vars"][var] = "set" if os.getenv(var) else "missing"

    return JSONResponse(content=status)


# ── Arranque del servidor ──────────────────────────────────────────

if __name__ == "__main__":
    print("Iniciando AgentMarce API en http://0.0.0.0:8080")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        access_log=True
    )
