# 3. Strict Resource Allocation (Dell Precision 3640)

## Hardware Inventory

| Resource | Total | Available (Unraid reserves ~2 cores, 4 GB) |
|---|---|---|
| CPU Threads | 16 (8 cores HT) | 14 available for VMs/containers |
| RAM | 32 GB | 28 GB available |
| NVMe 512 GB | 512 GB | ~450 GB usable |

## Resource Distribution Map

```
┌─────────────────────────────────────────────────────────┐
│  i7-10700  │  16 Threads  │  32 GB RAM  │  512 NVMe    │
├────────────┬─────────────┬─────────────┬───────────────┤
│ UNRAID OS  │  2 threads  │   4 GB RAM  │   50 GB       │
│ (host)     │  threads 0-1│             │               │
├────────────┼─────────────┼─────────────┼───────────────┤
│ AGENT VM   │  6 threads  │   12 GB RAM │   100 GB      │
│ (main)     │  threads 2-7│             │               │
│            │             │             │               │
│  Ubuntu OS │             │   1.0 GB    │               │
│  ADK Python│             │   1.5 GB    │               │
│  Docker    │             │   0.5 GB    │               │
│  Ollama    │             │   3.0 GB    │               │
│  Buffer    │             │   2.0 GB    │               │
│  Reserve   │             │   4.0 GB    │               │
├────────────┼─────────────┼─────────────┼───────────────┤
│ n8n        │  2 threads  │   4 GB RAM  │   20 GB       │
│ (Docker on │  threads 8-9│             │               │
│  Unraid)   │             │             │               │
├────────────┼─────────────┼─────────────┼───────────────┤
│ RESERVE    │  4 threads  │   8 GB RAM  │   280 GB      │
│ (Proxmox,  │  threads    │             │               │
│  HA, other)│  10-15      │             │               │
└────────────┴─────────────┴─────────────┴───────────────┘
```

## VM Configuration in Unraid

When creating the VM in Unraid (VMs → Add VM → Linux), use these exact values:

| Field | Value |
|---|---|
| Name | `agent-marce` |
| CPUs | `6` |
| CPU Pinning | Threads 2, 3, 4, 5, 6, 7 (leave 0-1 for Unraid host) |
| Initial Memory | `12288` MB |
| Max Memory | `12288` MB |
| Primary vDisk Size | `100G` |
| Primary vDisk Bus | `VirtIO` |
| Network Bridge | `br0` |
| Network Model | `VirtIO` |

> **CPU Pinning is important:** In Unraid, enable "CPU Pinning" and select only threads 2-7.
> This guarantees the agent VM never competes with Unraid host processes for the same
> physical cores.

## Resource Limits Inside the VM

Inside the VM, Docker containers have their own limits.
See `docker-compose.yml` for the exact Ollama limits.

### Python Process Limits (ADK)

The Python agent process is mainly I/O bound (waiting for API responses), so strict
limits are not critical. However, to protect the system, you can add these under
`[Service]` in the systemd unit file:

```ini
MemoryMax=2G
CPUQuota=150%
```

## Resource Management Rules

1. **The 80% rule:** If VM RAM exceeds 80% usage, n8n must redirect ALL tasks to
   cloud LLMs until it drops back down.

2. **Ollama idle rule:** With `OLLAMA_KEEP_ALIVE=5m`, the model is automatically
   unloaded from RAM when idle. This frees ~1.1 GB for the rest of the system.

3. **Never assign more than 6 threads to the agent VM.** The i7-10700 has 8 physical
   cores with Hyperthreading. Assigning more than 6 threads would saturate cores
   shared with Unraid.

4. **Proxmox on separate hardware** (if applicable): If Proxmox runs on the same Dell
   3640, reduce the agent VM to 4 threads and 8 GB RAM, and allocate the remaining
   4 threads to Proxmox.

## Resource Monitoring

Useful commands to check status via SSH to the VM:

```bash
# Real-time RAM usage
watch -n 5 free -h

# CPU usage by process
top -o %CPU

# Stats for all Docker containers
docker stats

# Disk usage
df -h
```
