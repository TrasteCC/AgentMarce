"""
AgentMarce - FastAPI Server
Exposes the agent as a REST API so n8n can communicate with it.

Endpoints:
    POST /agent/run   - Send a message to the agent
    GET  /health      - Check that the server is running
    GET  /status      - Detailed system status

Usage:
    source .venv/bin/activate
    python3 api_server.py

    Or via systemd:
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

logging.basicConfig(
    filename='/var/log/agent-marce.log',
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

from agent import agent

app = FastAPI(
    title="AgentMarce API",
    description="REST API for the homelab orchestration agent",
    version="1.0.0"
)


# ── Data models ───────────────────────────────────────────────────

class AgentRequest(BaseModel):
    input: str
    user: str = "unknown"
    channel: str = "api"    # "telegram", "slack", "api"

class AgentResponse(BaseModel):
    response: str
    user: str
    channel: str
    timestamp: str
    success: bool


# ── Logging middleware ────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response


# ── Endpoints ─────────────────────────────────────────────────────

@app.post("/agent/run", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    """
    Sends a message to the agent and returns the response.

    Body:
        input   (str): The user's message
        user    (str): User name or ID (for logs)
        channel (str): Origin channel ("telegram", "slack", "api")
    """
    if not request.input.strip():
        raise HTTPException(status_code=400, detail="The 'input' field cannot be empty")

    if len(request.input) > 4096:
        raise HTTPException(status_code=400, detail="Message exceeds the 4096-character limit")

    logger.info(f"Agent request from {request.user} via {request.channel}: {request.input[:100]}...")

    try:
        contextualized_input = f"[User: {request.user}] {request.input}"
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
        raise HTTPException(status_code=500, detail=f"Internal agent error: {str(e)}")


@app.get("/health")
async def health_check():
    """Quick check that the server is running."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/status")
async def system_status():
    """Detailed system status: Ollama, environment variables, etc."""
    import requests

    status = {
        "server": "running",
        "timestamp": datetime.now().isoformat(),
        "ollama": "unknown",
        "env_vars": {}
    }

    # Check Ollama
    try:
        ollama_resp = requests.get(
            f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/version",
            timeout=5
        )
        status["ollama"] = "ok" if ollama_resp.status_code == 200 else "error"
    except Exception:
        status["ollama"] = "unreachable"

    # Check critical variables (without revealing values)
    critical_vars = [
        "OLLAMA_BASE_URL", "GROQ_API_KEY", "TELEGRAM_BOT_TOKEN",
        "HOME_ASSISTANT_URL", "PROXMOX_HOST"
    ]
    for var in critical_vars:
        status["env_vars"][var] = "set" if os.getenv(var) else "missing"

    return JSONResponse(content=status)


# ── Server startup ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting AgentMarce API at http://0.0.0.0:8080")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        access_log=True
    )
