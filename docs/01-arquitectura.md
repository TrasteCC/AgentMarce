# 1. Arquitectura Logica y Ecosistema n8n

## Diagrama de Flujo del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE ENTRADA (Interfaces)                  │
│   [Telegram Bot]          [Slack App]          [Scheduler n8n]  │
└──────────────┬─────────────────┬──────────────────┬────────────┘
               │   Webhooks      │   Events API      │  Cron Jobs
               ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│              n8n  (Sistema Nervioso Central)                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Workflow 1: Intake & Router                             │   │
│  │  [Recibe mensaje] → [Clasifica complejidad] → [Decide]   │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│              ┌────────────┴────────────┐                        │
│              ▼                         ▼                        │
│  ┌─────────────────────┐  ┌──────────────────────────────┐      │
│  │  Ruta A: LOCAL      │  │  Ruta B: CLOUD               │      │
│  │  Ollama GGUF (VM)   │  │  Groq / OpenRouter / Gemini  │      │
│  │  Tareas simples     │  │  Logs, razonamiento complejo  │      │
│  └──────────┬──────────┘  └──────────────┬───────────────┘      │
│             └────────────────────────────┘                      │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Workflow 2: Agent Executor (Antigravity ADK)            │   │
│  │  [Recibe respuesta LLM] → [Ejecuta Tool/Accion]          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│ Home Assistant│  │  Proxmox API │  │  Google APIs     │
│  REST API    │  │  SSH (jail)  │  │  Drive/Gmail/Cal  │
└──────────────┘  └──────────────┘  └──────────────────┘
```

## Roles de Cada Componente

| Componente | Rol | Por que esta eleccion |
|---|---|---|
| **n8n** | Sistema nervioso, router, scheduler | Ya disponible, visual, sin necesidad de codigo |
| **Antigravity ADK** | Cerebro agentico, gestion de herramientas, memoria | Framework oficial Google para multi-agente |
| **Ollama (Docker)** | Inferencia local CPU para tareas simples | Control total de RAM/CPU, sin API key |
| **Groq** | Analisis de logs (capa gratuita, ultra-rapido) | 30 req/min gratis, ~6000 tok/s vs ~10 tok/s local |
| **OpenRouter** | Fallback y tareas complejas | Acceso a Claude/GPT/Gemini en un endpoint |

## Tabla de Enrutamiento de Tareas

La decision mas critica del sistema: **sin GPU, el LLM local es lento**. Un log de 500 lineas
tardaria 45-90 segundos procesado localmente. Por eso el LLM local actua solo como clasificador
de intenciones y ejecutor de comandos simples predefinidos.

```
┌─────────────────────────────────────────────────────────┐
│           TABLA DE ENRUTAMIENTO DE TAREAS               │
├─────────────────────┬───────────────────────────────────┤
│  OLLAMA LOCAL       │  GROQ / OPENROUTER (Cloud)        │
│  (< 2 seg respuesta)│  (Tarea pesada / latencia ok)     │
├─────────────────────┼───────────────────────────────────┤
│ "Apaga la luz X"    │ Analisis diario de logs           │
│ "Esta Proxmox ok?"  │ Resumen de emails (Gmail)         │
│ Clasificar intent   │ Generacion de reportes            │
│ Comandos HA simples │ Investigacion web (browser agent) │
│ On/Off switches     │ Procesamiento Google Drive        │
│ Router de intencion │ Razonamiento complejo multi-paso  │
└─────────────────────┴───────────────────────────────────┘
```

## Flujo Detallado de un Mensaje

```
Usuario escribe en Telegram: "Apaga las luces del salon"
        │
        ▼
n8n Telegram Trigger recibe el webhook
        │
        ▼
Nodo IF: ¿Coincide con regex de comandos simples?
(^(enciende|apaga|estado|toggle|luz|switch|lampara))
        │
    SÍ  │  NO
        │   └──→ HTTP POST a /agent/run (Python ADK completo)
        ▼
HTTP POST a Ollama: extrae entity_id y accion en JSON
        │
        ▼
n8n ejecuta HTTP POST a Home Assistant REST API
        │
        ▼
n8n envia confirmacion por Telegram: "Luces del salon apagadas"
```

## Flujo de Log Review Diario (Automatico)

```
08:00 AM → Schedule Trigger en n8n
        │
        ▼
SSH a la VM → ejecuta collect_logs.sh
        │
        ▼
Texto de logs → HTTP POST a Groq API (analisis pesado)
        │
        ▼
Groq devuelve resumen en bullets
        │
        ▼
n8n envia el reporte por Telegram
```

## Principios de Diseno

1. **Modularidad**: Cada capacidad es un bloque independiente. Puedes tener solo Telegram sin Slack, o solo HA sin Proxmox.
2. **Least Privilege**: El agente solo tiene acceso a lo estrictamente necesario en cada sistema.
3. **Fallback graceful**: Si Ollama esta caido, n8n redirige a Groq. Si Groq falla, va a OpenRouter.
4. **Observabilidad**: Todos los logs del agente se guardan en `/var/log/agent-marce.log`.
