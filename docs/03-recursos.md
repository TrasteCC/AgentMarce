# 3. Asignacion Estricta de Recursos (Dell Precision 3640)

## Inventario del Hardware

| Recurso | Total | Disponible (Unraid reserva ~2 cores, 4 GB) |
|---|---|---|
| CPU Threads | 16 (8 cores HT) | 14 disponibles para VMs/contenedores |
| RAM | 32 GB | 28 GB disponibles |
| NVMe 512 GB | 512 GB | ~450 GB utiles |

## Mapa de Distribucion de Recursos

```
┌─────────────────────────────────────────────────────────┐
│  i7-10700  │  16 Threads  │  32 GB RAM  │  512 NVMe    │
├────────────┬─────────────┬─────────────┬───────────────┤
│ UNRAID OS  │  2 threads  │   4 GB RAM  │   50 GB       │
│ (host)     │  threads 0-1│             │               │
├────────────┼─────────────┼─────────────┼───────────────┤
│ VM AGENTE  │  6 threads  │   12 GB RAM │   100 GB      │
│ (principal)│  threads 2-7│             │               │
│            │             │             │               │
│  OS Ubuntu │             │   1.0 GB    │               │
│  ADK Python│             │   1.5 GB    │               │
│  Docker    │             │   0.5 GB    │               │
│  Ollama    │             │   3.0 GB    │               │
│  Buffer    │             │   2.0 GB    │               │
│  Reserva   │             │   4.0 GB    │               │
├────────────┼─────────────┼─────────────┼───────────────┤
│ n8n        │  2 threads  │   4 GB RAM  │   20 GB       │
│ (Docker en │  threads 8-9│             │               │
│  Unraid)   │             │             │               │
├────────────┼─────────────┼─────────────┼───────────────┤
│ RESERVA    │  4 threads  │   8 GB RAM  │   280 GB      │
│ (Proxmox,  │  threads    │             │               │
│  HA, otros)│  10-15      │             │               │
└────────────┴─────────────┴─────────────┴───────────────┘
```

## Configuracion de la VM en Unraid

Al crear la VM en Unraid (VMs → Add VM → Linux), usa estos valores exactos:

| Campo | Valor |
|---|---|
| Name | `agent-marce` |
| CPUs | `6` |
| CPU Pinning | Threads 2, 3, 4, 5, 6, 7 (deja 0-1 para Unraid) |
| Initial Memory | `12288` MB |
| Max Memory | `12288` MB |
| Primary vDisk Size | `100G` |
| Primary vDisk Bus | `VirtIO` |
| Network Bridge | `br0` |
| Network Model | `VirtIO` |

> **CPU Pinning importante:** En Unraid, activa "CPU Pinning" y selecciona solo los threads 2-7.
> Esto garantiza que la VM del agente nunca compita con los procesos del host Unraid por los
> mismos cores fisicos.

## Configuracion de Recursos dentro de la VM

Dentro de la VM, los contenedores Docker tienen sus propios limites.
Ver `docker-compose.yml` para los limites exactos de Ollama.

### Limites del proceso Python (ADK)

El proceso Python del agente no necesita limites estrictos ya que es
principalmente I/O bound (espera respuestas de APIs). Sin embargo, si quieres
protegerte, puedes iniciarlo con `systemd` con limites de memoria:

En `/etc/systemd/system/marce-agent.service` añadir bajo `[Service]`:

```ini
MemoryMax=2G
CPUQuota=150%
```

## Reglas de Gestion de Recursos

1. **Regla del 80%:** Si la RAM de la VM supera el 80% de uso, n8n debe redirigir
   TODAS las tareas al LLM cloud hasta que baje.

2. **Regla de Ollama inactivo:** Con `OLLAMA_KEEP_ALIVE=5m`, el modelo se descarga
   de RAM automaticamente si no se usa. Esto libera ~1.1 GB para el sistema.

3. **Nunca asignar mas de 6 threads a la VM agente.** El i7-10700 tiene 8 cores fisicos
   con Hyperthreading. Asignar mas de 6 threads saturaria los cores compartidos con Unraid.

4. **Proxmox en hardware separado** (si aplica): Si Proxmox corre en el mismo Dell 3640,
   reducir la VM agente a 4 threads y 8 GB RAM, y asignar los 4 threads restantes a Proxmox.

## Monitoreo de Recursos

Comandos utiles para verificar el estado desde SSH a la VM:

```bash
# Ver uso de RAM en tiempo real
watch -n 5 free -h

# Ver uso de CPU por proceso
top -o %CPU

# Ver stats de todos los contenedores Docker
docker stats

# Ver uso de disco
df -h
```
