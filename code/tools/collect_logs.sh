#!/bin/bash
# ============================================================
# AgentMarce - Daily Log Collector
# Executed from n8n via SSH every morning.
#
# Usage:
#   bash collect_logs.sh
#   bash collect_logs.sh --output /custom/path/report.txt
# ============================================================

set -euo pipefail

OUTPUT_FILE="${1:-/tmp/daily_logs_$(date +%Y%m%d_%H%M).txt}"
HOSTNAME=$(hostname)
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "=== DAILY LOG REPORT: $DATE ===" > "$OUTPUT_FILE"
echo "Host: $HOSTNAME" >> "$OUTPUT_FILE"
echo "==========================================" >> "$OUTPUT_FILE"

# ── 1. System errors (last 24h) ───────────────────────────────────

echo -e "\n--- SYSTEM ERRORS (last 24h) ---" >> "$OUTPUT_FILE"
journalctl --since "24 hours ago" -p err..warning --no-pager 2>/dev/null \
    | tail -50 \
    | grep -v "^--" \
    >> "$OUTPUT_FILE" || echo "  (no errors recorded)" >> "$OUTPUT_FILE"

# ── 2. Docker container status ────────────────────────────────────

echo -e "\n--- DOCKER CONTAINERS ---" >> "$OUTPUT_FILE"
if command -v docker &>/dev/null; then
    docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" >> "$OUTPUT_FILE" 2>&1

    echo -e "\nNon-running containers:" >> "$OUTPUT_FILE"
    docker ps -a --filter "status=exited" --filter "status=dead" \
        --format "  {{.Names}}: {{.Status}}" >> "$OUTPUT_FILE" 2>/dev/null \
        || echo "  None" >> "$OUTPUT_FILE"
else
    echo "  Docker not found on this host" >> "$OUTPUT_FILE"
fi

# ── 3. Disk usage ─────────────────────────────────────────────────

echo -e "\n--- DISK USAGE ---" >> "$OUTPUT_FILE"
df -h 2>/dev/null >> "$OUTPUT_FILE"

echo -e "\nPartitions above 85% usage:" >> "$OUTPUT_FILE"
df -h | awk 'NR>1 && int($5) > 85 {print "  ALERT: " $0}' >> "$OUTPUT_FILE" \
    || echo "  None" >> "$OUTPUT_FILE"

# ── 4. RAM usage ──────────────────────────────────────────────────

echo -e "\n--- RAM USAGE ---" >> "$OUTPUT_FILE"
free -h >> "$OUTPUT_FILE"

RAM_USED=$(free | awk '/^Mem:/{printf "%.0f", $3/$2*100}')
echo "RAM usage: ${RAM_USED}%" >> "$OUTPUT_FILE"
if [ "$RAM_USED" -gt 85 ]; then
    echo "  ALERT: RAM at ${RAM_USED}% — consider freeing memory" >> "$OUTPUT_FILE"
fi

# ── 5. System load ────────────────────────────────────────────────

echo -e "\n--- SYSTEM LOAD ---" >> "$OUTPUT_FILE"
echo "Uptime: $(uptime)" >> "$OUTPUT_FILE"
echo "Load average: $(cat /proc/loadavg)" >> "$OUTPUT_FILE"

# ── 6. Agent logs ─────────────────────────────────────────────────

echo -e "\n--- AGENT LOGS (last 24h, errors only) ---" >> "$OUTPUT_FILE"
if [ -f "/var/log/agent-marce.log" ]; then
    grep "$(date -d 'yesterday' '+%Y-%m-%d')\|$(date '+%Y-%m-%d')" /var/log/agent-marce.log \
        | grep -i "error\|warning\|blocked" \
        | tail -20 \
        >> "$OUTPUT_FILE" 2>/dev/null \
        || echo "  No agent errors" >> "$OUTPUT_FILE"
else
    echo "  Agent log file not found" >> "$OUTPUT_FILE"
fi

# ── 7. Top processes by RAM ───────────────────────────────────────

echo -e "\n--- TOP 10 PROCESSES BY RAM ---" >> "$OUTPUT_FILE"
ps aux --sort=-%mem | head -11 | awk '{print $1, $2, $3, $4, $11}' >> "$OUTPUT_FILE"

echo -e "\n=== END OF REPORT ===" >> "$OUTPUT_FILE"

# Print the report (n8n captures this output via SSH)
cat "$OUTPUT_FILE"

# Clean up log files older than 7 days
find /tmp -name "daily_logs_*.txt" -mtime +7 -delete 2>/dev/null || true
