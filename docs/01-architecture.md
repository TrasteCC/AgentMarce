# 1. Logical Architecture and n8n Ecosystem

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      INPUT LAYER (Interfaces)                    │
│   [Telegram Bot]          [Slack App]          [n8n Scheduler]  │
└──────────────┬─────────────────┬──────────────────┬────────────┘
               │   Webhooks      │   Events API      │  Cron Jobs
               ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                  n8n  (Central Nervous System)                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Workflow 1: Intake & Router                             │   │
│  │  [Receive message] → [Classify complexity] → [Decide]    │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│              ┌────────────┴────────────┐                        │
│              ▼                         ▼                        │
│  ┌─────────────────────┐  ┌──────────────────────────────┐      │
│  │  Route A: LOCAL     │  │  Route B: CLOUD              │      │
│  │  Ollama GGUF (VM)   │  │  Groq / OpenRouter / Gemini  │      │
│  │  Simple tasks       │  │  Logs, complex reasoning     │      │
│  └──────────┬──────────┘  └──────────────┬───────────────┘      │
│             └────────────────────────────┘                      │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Workflow 2: Agent Executor (Antigravity ADK)            │   │
│  │  [Receive LLM response] → [Execute Tool/Action]          │   │
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

## Role of Each Component

| Component | Role | Why this choice |
|---|---|---|
| **n8n** | Nervous system, router, scheduler | Already available, visual, no code needed |
| **Antigravity ADK** | Agentic brain, tool management, memory | Official Google multi-agent framework |
| **Ollama (Docker)** | Local CPU inference for simple tasks | Full RAM/CPU control, no API key required |
| **Groq** | Log analysis (free tier, ultra-fast) | 30 req/min free, ~6000 tok/s vs ~10 tok/s local |
| **OpenRouter** | Fallback and complex tasks | Single endpoint for Claude/GPT/Gemini |

## Task Routing Table

The most critical design decision: **without a GPU, the local LLM is slow**. A 500-line log
file would take 45-90 seconds processed locally. The local LLM is used EXCLUSIVELY as an
intent classifier and executor of simple predefined commands.

```
┌─────────────────────────────────────────────────────────┐
│                  TASK ROUTING TABLE                     │
├─────────────────────┬───────────────────────────────────┤
│  OLLAMA LOCAL       │  GROQ / OPENROUTER (Cloud)        │
│  (< 2s response)    │  (heavy task / latency ok)        │
├─────────────────────┼───────────────────────────────────┤
│ "Turn off light X"  │ Daily log analysis                │
│ "Is Proxmox up?"    │ Email summarization (Gmail)       │
│ Intent classifier   │ Report generation                 │
│ Simple HA commands  │ Web research (browser agent)      │
│ On/Off switches     │ Google Drive processing           │
│ Intent router       │ Complex multi-step reasoning      │
└─────────────────────┴───────────────────────────────────┘
```

## Detailed Message Flow

```
User types in Telegram: "Turn off the living room lights"
        │
        ▼
n8n Telegram Trigger receives the webhook
        │
        ▼
IF node: Does it match the simple command regex?
(^(turn on|turn off|toggle|light|switch|open|close))
        │
    YES │  NO
        │   └──→ HTTP POST to /agent/run (full Python ADK)
        ▼
HTTP POST to Ollama: extract entity_id and action as JSON
        │
        ▼
n8n executes HTTP POST to Home Assistant REST API
        │
        ▼
n8n sends Telegram confirmation: "Living room lights turned off"
```

## Daily Log Review Flow (Automatic)

```
08:00 AM → Schedule Trigger in n8n
        │
        ▼
SSH to VM → runs collect_logs.sh
        │
        ▼
Log text → HTTP POST to Groq API (heavy analysis)
        │
        ▼
Groq returns bullet-point summary
        │
        ▼
n8n sends the report via Telegram
```

## Design Principles

1. **Modularity**: Each capability is an independent block. You can have just Telegram without Slack, or just HA without Proxmox.
2. **Least Privilege**: The agent only has access to what it strictly needs in each system.
3. **Graceful fallback**: If Ollama is down, n8n redirects to Groq. If Groq fails, it falls back to OpenRouter.
4. **Observability**: All agent logs are saved to `/var/log/agent-marce.log`.
