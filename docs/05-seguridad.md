# 5. Consideraciones de Seguridad

## Principio de Least Privilege

El agente solo tiene acceso a lo estrictamente necesario en cada sistema.
Nunca usar credenciales de administrador cuando existe una alternativa de solo lectura.

## Matriz de Permisos

```
┌─────────────────────────────────────────────────────────┐
│              MATRIZ DE PERMISOS DEL AGENTE              │
├───────────────────┬──────────────┬──────────────────────┤
│  Sistema          │  Acceso      │  Restriccion         │
├───────────────────┼──────────────┼──────────────────────┤
│  Home Assistant   │  API Token   │  Solo entidades      │
│                   │  (read+ctrl) │  listadas en config  │
├───────────────────┼──────────────┼──────────────────────┤
│  Proxmox          │  API Token   │  Solo lectura (GET)  │
│                   │  (read only) │  No VM create/delete │
├───────────────────┼──────────────┼──────────────────────┤
│  Unraid SSH       │  Usuario     │  Solo whitelist.sh   │
│                   │  restringido │  No root, no sudo    │
├───────────────────┼──────────────┼──────────────────────┤
│  Google APIs      │  OAuth2      │  Solo read scopes    │
│                   │  (readonly)  │  No send/delete      │
├───────────────────┼──────────────┼──────────────────────┤
│  Docker Ollama    │  localhost   │  No exponer al       │
│                   │  only        │  exterior            │
└───────────────────┴──────────────┴──────────────────────┘
```

## Configuracion del Acceso Restringido a Terminal

### Crear usuario restringido en Unraid

Ejecutar estos comandos en SSH al host Unraid (no a la VM):

```bash
# Crear usuario sin password (solo SSH key o comandos directos)
adduser agent-runner --disabled-password --gecos ""

# Crear directorio de scripts permitidos
mkdir -p /usr/local/agent-scripts

# Copiar el script whitelist.sh
cp whitelist.sh /usr/local/agent-scripts/
chmod +x /usr/local/agent-scripts/whitelist.sh

# Configurar sudo restringido (solo para el script whitelist)
echo "agent-runner ALL=(ALL) NOPASSWD: /usr/local/agent-scripts/whitelist.sh" >> /etc/sudoers
```

### Lista Blanca de Comandos (whitelist.sh)

Solo estos comandos estan permitidos al agente:

```
docker ps
docker stats --no-stream
docker logs [nombre-contenedor]
df -h
free -h
uptime
systemctl status [servicio]
netstat -tulpn
cat /proc/cpuinfo
```

**Comandos NUNCA permitidos:**
- `rm`, `rmdir` (borrado de archivos)
- `shutdown`, `reboot`, `poweroff`
- `passwd`, `su`, `sudo` (escalada de privilegios)
- `curl` con redirecciones o pipes
- `wget` con ejecucion directa
- Cualquier comando con `>` o `>>` (redireccion de escritura)

## Configuracion de API Token de Proxmox (Solo Lectura)

En la interfaz web de Proxmox:

1. `Datacenter` → `Permissions` → `API Tokens` → `Add`
2. User: `root@pam`
3. Token ID: `agent-readonly`
4. **Privilege Separation: YES** (esto es critico)
5. Click OK → copiar el token generado

6. `Datacenter` → `Permissions` → `Add` → `API Token Permission`
7. Path: `/`
8. API Token: `root@pam!agent-readonly`
9. Role: `PVEAuditor` (solo lectura, no puede modificar nada)

## Configuracion de Token de Home Assistant

En Home Assistant:

1. Perfil de usuario (icono abajo izquierda) → `Long-Lived Access Tokens`
2. `Create Token`
3. Nombre: `agent-marce` (nombre descriptivo para poder revocarlo)
4. Copiar el token → pegarlo en `.env`

**Entidades restringidas:** Considera crear un usuario separado en HA con acceso
solo a las entidades que el agente necesita controlar, en lugar de usar el token
de administrador.

## Checklist de Seguridad

- [ ] Todas las API keys estan en `.env`, nunca hardcoded en el codigo
- [ ] `.env` esta en `.gitignore` (NUNCA subir el .env real a GitHub)
- [ ] Ollama escucha solo en localhost (127.0.0.1:11434), no en 0.0.0.0
- [ ] Puerto 8080 del agente no expuesto a internet (solo accesible desde la LAN)
- [ ] n8n tiene autenticacion basica activada en su configuracion
- [ ] Proxmox API Token creado con rol `PVEAuditor` (solo lectura)
- [ ] Home Assistant token nombrado `agent-marce` para identificacion y revocacion
- [ ] Logs del agente guardados en `/var/log/agent-marce.log`
- [ ] Backups del `.env` en un gestor de contrasenas (Bitwarden, etc.)
- [ ] Usuario `agent-runner` de Unraid sin acceso shell interactivo

## Seguridad en el Codigo

El archivo `agent.py` implementa validacion de comandos antes de ejecutarlos:

```python
ALLOWED_COMMANDS = [
    "docker ps", "docker stats --no-stream",
    "df -h", "free -h", "uptime", "systemctl status"
]

def execute_safe_command(command: str) -> str:
    command_allowed = any(command.startswith(allowed) for allowed in ALLOWED_COMMANDS)
    if not command_allowed:
        return f"SEGURIDAD: Comando no permitido. Comandos disponibles: {ALLOWED_COMMANDS}"
    # ... ejecucion con timeout de 30 segundos
```

## Auditoria y Logs

El servidor FastAPI registra cada request con timestamp y usuario:

```python
logging.basicConfig(
    filename='/var/log/agent-marce.log',
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
```

Para ver los logs en tiempo real:
```bash
tail -f /var/log/agent-marce.log
```

Para ver los ultimos 50 eventos:
```bash
tail -50 /var/log/agent-marce.log
```
