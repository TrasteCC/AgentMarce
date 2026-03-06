#!/bin/bash
# ============================================================
# AgentMarce - Recolector de Logs Diario
# Se ejecuta desde n8n via SSH cada manana
#
# Uso:
#   bash collect_logs.sh
#   bash collect_logs.sh --output /ruta/personalizada.txt
# ============================================================

set -euo pipefail

OUTPUT_FILE="${1:-/tmp/daily_logs_$(date +%Y%m%d_%H%M).txt}"
HOSTNAME=$(hostname)
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "=== REPORTE DIARIO DE LOGS: $DATE ===" > "$OUTPUT_FILE"
echo "Host: $HOSTNAME" >> "$OUTPUT_FILE"
echo "==========================================" >> "$OUTPUT_FILE"

# ── 1. Errores del sistema (ultimas 24h) ──────────────────────────

echo -e "\n--- ERRORES DEL SISTEMA (ultimas 24h) ---" >> "$OUTPUT_FILE"
journalctl --since "24 hours ago" -p err..warning --no-pager 2>/dev/null \
    | tail -50 \
    | grep -v "^--" \
    >> "$OUTPUT_FILE" || echo "  (sin errores registrados)" >> "$OUTPUT_FILE"

# ── 2. Estado de contenedores Docker ──────────────────────────────

echo -e "\n--- CONTENEDORES DOCKER ---" >> "$OUTPUT_FILE"
if command -v docker &>/dev/null; then
    docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" >> "$OUTPUT_FILE" 2>&1

    # Contenedores que no estan Running
    echo -e "\nContenedores NO activos:" >> "$OUTPUT_FILE"
    docker ps -a --filter "status=exited" --filter "status=dead" \
        --format "  {{.Names}}: {{.Status}}" >> "$OUTPUT_FILE" 2>/dev/null \
        || echo "  Ninguno" >> "$OUTPUT_FILE"
else
    echo "  Docker no encontrado en este host" >> "$OUTPUT_FILE"
fi

# ── 3. Uso de disco ───────────────────────────────────────────────

echo -e "\n--- USO DE DISCO ---" >> "$OUTPUT_FILE"
df -h 2>/dev/null >> "$OUTPUT_FILE"

# Advertencia si algun disco supera el 85%
echo -e "\nParticiones con uso > 85%:" >> "$OUTPUT_FILE"
df -h | awk 'NR>1 && int($5) > 85 {print "  ALERTA: " $0}' >> "$OUTPUT_FILE" \
    || echo "  Ninguna" >> "$OUTPUT_FILE"

# ── 4. Uso de memoria RAM ─────────────────────────────────────────

echo -e "\n--- MEMORIA RAM ---" >> "$OUTPUT_FILE"
free -h >> "$OUTPUT_FILE"

# Calcular porcentaje de uso
RAM_USED=$(free | awk '/^Mem:/{printf "%.0f", $3/$2*100}')
echo "Uso de RAM: ${RAM_USED}%" >> "$OUTPUT_FILE"
if [ "$RAM_USED" -gt 85 ]; then
    echo "  ALERTA: RAM al ${RAM_USED}% - considerar liberar memoria" >> "$OUTPUT_FILE"
fi

# ── 5. Carga del sistema ──────────────────────────────────────────

echo -e "\n--- CARGA DEL SISTEMA ---" >> "$OUTPUT_FILE"
echo "Uptime: $(uptime)" >> "$OUTPUT_FILE"
echo "Load average: $(cat /proc/loadavg)" >> "$OUTPUT_FILE"

# ── 6. Logs del agente Marce ──────────────────────────────────────

echo -e "\n--- LOGS DEL AGENTE (ultimas 24h) ---" >> "$OUTPUT_FILE"
if [ -f "/var/log/agent-marce.log" ]; then
    grep "$(date -d 'yesterday' '+%Y-%m-%d')\|$(date '+%Y-%m-%d')" /var/log/agent-marce.log \
        | grep -i "error\|warning\|blocked" \
        | tail -20 \
        >> "$OUTPUT_FILE" 2>/dev/null \
        || echo "  Sin errores del agente" >> "$OUTPUT_FILE"
else
    echo "  Archivo de log del agente no encontrado" >> "$OUTPUT_FILE"
fi

# ── 7. Procesos con alto uso de CPU/RAM ───────────────────────────

echo -e "\n--- TOP 10 PROCESOS POR RAM ---" >> "$OUTPUT_FILE"
ps aux --sort=-%mem | head -11 | awk '{print $1, $2, $3, $4, $11}' >> "$OUTPUT_FILE"

echo -e "\n=== FIN DEL REPORTE ===" >> "$OUTPUT_FILE"

# Imprimir el reporte (n8n captura este output via SSH)
cat "$OUTPUT_FILE"

# Limpiar archivos de log con mas de 7 dias
find /tmp -name "daily_logs_*.txt" -mtime +7 -delete 2>/dev/null || true
