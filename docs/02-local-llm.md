# 2. Local AI Configuration (CPU Inference)

## Why CPU and Not GPU

The Dell Precision 3640 has no dedicated GPU. LLM inference on CPU is significantly
slower but perfectly viable for intent classification and simple commands.

**Expected performance on i7-10700:**

| Model | Format | RAM usage | Tokens/sec (CPU) | Recommended use |
|---|---|---|---|---|
| Qwen2.5-1.5B | Q4_K_M | ~1.1 GB | 12-18 tok/s | Intent router (recommended) |
| Llama3.2-3B | Q4_K_M | ~2.0 GB | 8-12 tok/s | If you need more capability |
| Llama3.2-1B | Q4_K_M | ~0.7 GB | 18-25 tok/s | Ultra-fast, basic quality |

**Chosen model: `qwen2.5:1.5b-instruct-q4_K_M`**
- Reason: Best speed/quality balance for intent classification
- 12-18 tok/s is enough for 50-100 token responses in ~5 seconds
- Fits comfortably within the 3 GB budget allocated to Ollama

## Installing Ollama (Docker)

The `docker-compose.yml` file is already in `/code/docker-compose.yml`.

```bash
# From the VM, run:
cd ~/agent-services/ollama
docker compose up -d

# Download the model (~900 MB, takes ~5 minutes)
docker exec ollama-cpu ollama pull qwen2.5:1.5b

# Test it works
docker exec ollama-cpu ollama run qwen2.5:1.5b "say hello in 3 words"
```

## Modelfile — Model Configuration

The `Modelfile` (in `/code/Modelfile`) configures the model to act ONLY as an
intent classifier, always responding in JSON. This reduces output tokens
and improves speed.

**Key parameters explained:**

| Parameter | Value | Why |
|---|---|---|
| `num_thread` | 4 | Uses 4 of the 6 threads assigned to the VM |
| `num_ctx` | 2048 | Reduced context window (saves significant RAM) |
| `num_predict` | 512 | Max 512 output tokens (the router doesn't need more) |

To create the custom model from the Modelfile:

```bash
# Copy the Modelfile to the VM
docker cp Modelfile ollama-cpu:/tmp/Modelfile

# Create the custom model
docker exec ollama-cpu ollama create marce-router -f /tmp/Modelfile

# Use the custom model instead of the base one
# In .env: LOCAL_MODEL=marce-router
```

## Ollama Environment Variables

Configured in `docker-compose.yml`:

```
OLLAMA_NUM_PARALLEL=1      → Only processes 1 request at a time (avoids CPU saturation)
OLLAMA_MAX_LOADED_MODELS=1 → Only 1 model loaded in RAM at a time
OLLAMA_KEEP_ALIVE=5m       → Unloads the model from RAM after 5 minutes of inactivity
```

## LLM Routing Strategy in n8n

In n8n Workflow 1, the IF node classifies the message:

**IF node condition (Regex):**
```
^(turn on|turn off|toggle|light|switch|open|close|raise|lower|temperature|humidity|sensor|camera|alarm)
```

If the message matches → local Ollama (fast, zero cost)
If it does not match → full Python agent (which decides between Groq or OpenRouter)

**Fallback logic in the Python agent:**

```python
def route_llm(task_type: str, content: str):
    if task_type == "simple_command":
        return ollama_local(content)
    elif task_type == "log_analysis" or len(content) > 1000:
        return groq_api(content)        # Fast and free for long texts
    elif task_type == "google_api":
        return openrouter_api(content)  # Better reasoning for API tasks
    else:
        return groq_api(content)        # Default: Groq for speed and cost
```

## Monitoring Ollama Resources

To verify that Ollama is not consuming too much RAM:

```bash
# Real-time stats
docker stats ollama-cpu

# Check how much RAM the loaded model is using
docker exec ollama-cpu ollama ps
```

If VM RAM exceeds 85%, add this alert in n8n:
- Schedule every 5 minutes → SSH → `free -h` → IF usage > 85% → Telegram alert
