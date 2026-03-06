# AgentMarce — AI Agent for Homelab Orchestration

Full architecture and implementation plan for building a personal AI agent that orchestrates homelab infrastructure (Unraid, Proxmox, Home Assistant) using Google ADK, n8n, and dynamic LLM routing.

## Target Hardware

| Component | Specification |
|---|---|
| Host | Dell Precision 3640 Tower |
| CPU | Intel Core i7-10700 (8 cores / 16 threads) |
| RAM | 32 GB DDR4 |
| Storage | 512 GB NVMe |
| GPU | **None** (CPU-only inference) |

## Infrastructure

- **Unraid** — Primary host and server OS
- **Proxmox** — Additional VM hypervisor
- **Home Assistant** — Home automation
- **n8n** — Low-Code automation (agent's nervous system)

## Agent Capabilities

- Communication interfaces via **Telegram** and **Slack**
- Automated daily log review (Unraid, Proxmox, Home Assistant, n8n)
- Controlled terminal access (command whitelist)
- Agentic web browsing
- OAuth2 integration with **Google Drive**, **Gmail**, and **Google Calendar**
- Dynamic LLM routing: Groq, OpenRouter, Qwen, OpenAI, Gemini, Claude
- Local GGUF LLM via Ollama for simple tasks (no GPU, CPU inference)

## Repository Structure

```
AgentMarce/
├── README.md                    # This file
├── docs/
│   ├── 01-architecture.md       # System diagram and logic
│   ├── 02-local-llm.md          # Local AI configuration (CPU)
│   ├── 03-resources.md          # Resource allocation for the Dell 3640
│   ├── 04-sprint-backlog.md     # Detailed implementation plan
│   ├── 05-security.md           # Security considerations
│   └── 06-getting-started.md    # Day 0 quickstart guide
└── code/
    ├── agent.py                 # Main agent (Google ADK)
    ├── api_server.py            # FastAPI server for n8n
    ├── docker-compose.yml       # Ollama with resource limits
    ├── Modelfile                # GGUF model configuration
    ├── marce-agent.service      # systemd service unit
    ├── .env.example             # Environment variables template
    └── tools/
        ├── google_tools.py      # Gmail / Calendar / Drive tools
        └── collect_logs.sh      # Daily log collection script
```

## Quick Start

Read the [Getting Started Guide](docs/06-getting-started.md) before anything else.

Then follow this order:
1. [System Architecture](docs/01-architecture.md)
2. [Local AI Configuration](docs/02-local-llm.md)
3. [Resource Allocation](docs/03-resources.md)
4. [Sprint Backlog](docs/04-sprint-backlog.md)
5. [Security](docs/05-security.md)

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Agent | Google ADK (Antigravity) | Orchestration, tools, memory |
| Automation | n8n | API connectors, webhooks, scheduler |
| Local LLM | Ollama + Qwen2.5-1.5B Q4 | Simple tasks, zero cost, low latency |
| Fast LLM | Groq (Llama 3.3 70B) | Log analysis, reasoning (free tier) |
| Fallback LLM | OpenRouter | Access to Claude/GPT/Gemini |
| REST API | FastAPI + Uvicorn | Interface between n8n and the Python agent |
| Containers | Docker + Docker Compose | Service isolation |
| VM OS | Ubuntu Server 24.04 LTS | Agent VM operating system |

---

> Personal homelab project. Not affiliated with Google or any of the LLM providers mentioned.
