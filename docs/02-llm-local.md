# 2. Configuracion de IA Local (Inferencia por CPU)

## Por que CPU y no GPU

El Dell Precision 3640 no tiene GPU dedicada. La inferencia de LLMs en CPU es significativamente
mas lenta pero perfectamente viable para tareas de clasificacion y comandos simples.

**Rendimiento esperado en i7-10700:**

| Modelo | Formato | RAM usada | Tokens/seg (CPU) | Uso recomendado |
|---|---|---|---|---|
| Qwen2.5-1.5B | Q4_K_M | ~1.1 GB | 12-18 tok/s | Router de intenciones (recomendado) |
| Llama3.2-3B | Q4_K_M | ~2.0 GB | 8-12 tok/s | Si necesitas mas capacidad |
| Llama3.2-1B | Q4_K_M | ~0.7 GB | 18-25 tok/s | Ultra-rapido, calidad basica |

**Modelo elegido: `qwen2.5:1.5b-instruct-q4_K_M`**
- Razon: Mejor equilibrio velocidad/calidad para clasificacion de intenciones
- 12-18 tok/s es suficiente para respuestas de 50-100 tokens en ~5 segundos
- Cabe comfortablemente en el presupuesto de 3 GB asignados a Ollama

## Instalacion de Ollama (Docker)

El archivo `docker-compose.yml` ya esta en `/code/docker-compose.yml`.

```bash
# Desde la VM, ejecutar:
cd ~/agent-services/ollama
docker compose up -d

# Descargar el modelo (~900 MB, tarda ~5 minutos)
docker exec ollama-cpu ollama pull qwen2.5:1.5b

# Probar que funciona
docker exec ollama-cpu ollama run qwen2.5:1.5b "di hola en 3 palabras"
```

## Modelfile — Configuracion del Modelo

El archivo `Modelfile` (en `/code/Modelfile`) configura el modelo para actuar SOLO como
clasificador de intenciones, respondiendo siempre en JSON. Esto reduce tokens de salida
y mejora la velocidad.

**Parametros clave explicados:**

| Parametro | Valor | Por que |
|---|---|---|
| `num_thread` | 4 | Usa 4 de los 6 threads asignados a la VM |
| `num_ctx` | 2048 | Ventana de contexto reducida (ahorra RAM) |
| `num_predict` | 512 | Maximo 512 tokens de respuesta (el router no necesita mas) |

Para crear el modelo personalizado desde el Modelfile:

```bash
# Copiar el Modelfile a la VM
docker cp Modelfile ollama-cpu:/tmp/Modelfile

# Crear el modelo personalizado
docker exec ollama-cpu ollama create marce-router -f /tmp/Modelfile

# Usar el modelo personalizado en lugar del base
# En .env: LOCAL_MODEL=marce-router
```

## Variables de Entorno Ollama

Configuradas en `docker-compose.yml`:

```
OLLAMA_NUM_PARALLEL=1      → Solo procesa 1 request a la vez (evita saturar CPU)
OLLAMA_MAX_LOADED_MODELS=1 → Solo 1 modelo en RAM al mismo tiempo
OLLAMA_KEEP_ALIVE=5m       → Descarga el modelo de RAM si no se usa en 5 minutos
```

## Estrategia de Enrutamiento LLM en n8n

En el Workflow 1 de n8n, el nodo IF clasifica el mensaje:

**Condicion del nodo IF (Regex):**
```
^(enciende|apaga|estado|toggle|luz|switch|lampara|abre|cierra|sube|baja|temperatura|humedad|sensor|camara|alarma)
```

Si el mensaje coincide → Ollama local (rapido, sin coste)
Si no coincide → Agente Python completo (que decide si usar Groq u OpenRouter)

**Logica de fallback en el agente Python:**

```python
def route_llm(task_type: str, content: str):
    if task_type == "simple_command":
        return ollama_local(content)
    elif task_type == "log_analysis" or len(content) > 1000:
        return groq_api(content)        # Rapido y gratis para textos largos
    elif task_type == "google_api":
        return openrouter_api(content)  # Mejor razonamiento para APIs
    else:
        return groq_api(content)        # Default: Groq por velocidad y coste
```

## Monitoreo de Recursos de Ollama

Para verificar que Ollama no esta consumiendo demasiada RAM:

```bash
# Ver stats en tiempo real
docker stats ollama-cpu

# Ver cuanto RAM usa el modelo cargado
docker exec ollama-cpu ollama ps
```

Si la RAM de la VM supera el 85%, agrega esta alerta en n8n:
- Schedule cada 5 minutos → SSH → `free -h` → IF usado > 85% → Telegram alerta
