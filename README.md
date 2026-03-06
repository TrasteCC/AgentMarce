# AgentMarce — Agente de IA para Orquestación de Homelab

Arquitectura completa y plan de implementación para construir un agente de IA personal que orquesta infraestructura Homelab (Unraid, Proxmox, Home Assistant) usando Google ADK, n8n y enrutamiento dinámico de LLMs.

## Hardware Objetivo

| Componente | Especificación |
|---|---|
| Host | Dell Precision 3640 Torre |
| CPU | Intel Core i7-10700 (8 cores / 16 threads) |
| RAM | 32 GB DDR4 |
| Almacenamiento | 512 GB NVMe |
| GPU | **Ninguna** (inferencia por CPU) |

## Infraestructura

- **Unraid** — Host principal y sistema operativo del servidor
- **Proxmox** — Hipervisor de VMs adicionales
- **Home Assistant** — Domótica y automatización del hogar
- **n8n** — Automatización Low-Code (sistema nervioso del agente)

## Capacidades del Agente

- Interfaces de comunicacion via **Telegram** y **Slack**
- Revision diaria automatica de logs (Unraid, Proxmox, Home Assistant, n8n)
- Acceso controlado a terminal (lista blanca de comandos)
- Navegacion web agéntica
- Integracion OAuth2 con **Google Drive**, **Gmail** y **Google Calendar**
- Enrutamiento dinamico de LLMs: Groq, OpenRouter, Qwen, OpenAI, Gemini, Claude
- LLM local GGUF via Ollama para tareas simples (sin GPU, inferencia CPU)

## Estructura del Repositorio

```
AgentMarce/
├── README.md                    # Este archivo
├── docs/
│   ├── 01-arquitectura.md       # Diagrama y logica del sistema
│   ├── 02-llm-local.md          # Configuracion de IA local (CPU)
│   ├── 03-recursos.md           # Asignacion de recursos del Dell 3640
│   ├── 04-sprint-backlog.md     # Plan de implementacion detallado
│   ├── 05-seguridad.md          # Consideraciones de seguridad
│   └── 06-primeros-pasos.md     # Guia de arranque (Dia 0)
└── code/
    ├── agent.py                 # Agente principal (Google ADK)
    ├── api_server.py            # Servidor FastAPI para n8n
    ├── docker-compose.yml       # Ollama con limites de recursos
    ├── Modelfile                # Configuracion del modelo GGUF
    ├── marce-agent.service      # Servicio systemd
    ├── .env.example             # Variables de entorno (plantilla)
    └── tools/
        ├── google_tools.py      # Herramientas Gmail/Calendar/Drive
        └── collect_logs.sh      # Script de recoleccion de logs
```

## Inicio Rapido

Lee primero la [Guia de Primeros Pasos](docs/06-primeros-pasos.md) antes de cualquier otra cosa.

Luego sigue el orden:
1. [Arquitectura del Sistema](docs/01-arquitectura.md)
2. [Configuracion de IA Local](docs/02-llm-local.md)
3. [Asignacion de Recursos](docs/03-recursos.md)
4. [Sprint Backlog](docs/04-sprint-backlog.md)
5. [Seguridad](docs/05-seguridad.md)

## Stack Tecnologico

| Capa | Tecnologia | Proposito |
|---|---|---|
| Agente | Google ADK (Antigravity) | Orquestacion, herramientas, memoria |
| Automatizacion | n8n | Conectar APIs, webhooks, scheduler |
| LLM Local | Ollama + Qwen2.5-1.5B Q4 | Tareas simples, sin coste, baja latencia |
| LLM Rapido | Groq (Llama 3.3 70B) | Analisis de logs, razonamiento (gratis) |
| LLM Fallback | OpenRouter | Acceso a Claude/GPT/Gemini |
| API REST | FastAPI + Uvicorn | Interfaz entre n8n y el agente Python |
| Contenedores | Docker + Docker Compose | Aislamiento de servicios |
| OS VM | Ubuntu Server 24.04 LTS | Sistema operativo de la VM del agente |

---

> Proyecto personal de homelab. No tiene afiliacion con Google ni con ninguno de los proveedores de LLM mencionados.
