# 6. Guia de Arranque (Dia 0)

> Haz esto hoy, en este orden exacto. Cada paso te desbloqueara el siguiente.
> Tiempo total estimado: 1.5 horas.

---

## Paso 1: Obtener tus API Keys Gratuitas (30 minutos)

Abre el navegador y crea estas cuentas. Todas tienen capa gratuita suficiente para este proyecto.

### Groq (para analisis de logs — GRATIS)

1. Ve a https://console.groq.com
2. `Sign Up` con Google
3. `API Keys` → `Create API Key`
4. Copia y guarda en un bloc de notas: `GROQ_API_KEY=gsk_...`

**Por que Groq:** Procesa ~6000 tokens/segundo. Un log de 500 lineas se analiza en 2 segundos.
La capa gratuita permite 30 requests/minuto y 14.400 requests/dia — mas que suficiente.

### OpenRouter (modelo de fallback)

1. Ve a https://openrouter.ai
2. `Sign In` con Google → `Keys` → `Create Key`
3. Copia: `OPENROUTER_API_KEY=sk-or-...`

**Por que OpenRouter:** Un solo endpoint que da acceso a Claude, GPT-4, Gemini y decenas de modelos
mas. Util cuando Groq no tiene el modelo adecuado para una tarea especifica.

### Telegram Bot

1. Abre Telegram en tu movil o PC
2. Busca `@BotFather` (el oficial, tiene tilde azul)
3. Escribe `/newbot`
4. Cuando pregunte el nombre: escribe `AgentMarce` (o el nombre que prefieras)
5. Cuando pregunte el username: escribe `agentmarce_bot` (debe terminar en `_bot`)
6. Copia el token: `TELEGRAM_BOT_TOKEN=1234567890:ABCdef...`

> Guarda los tres tokens en un lugar seguro (gestor de contrasenas como Bitwarden).
> Los necesitaras en el Dia 4 cuando configures el archivo `.env`.

---

## Paso 2: Crear la VM en Unraid (45 minutos)

### 2.1 Descargar la ISO de Ubuntu Server

1. En tu navegador, ve a: https://ubuntu.com/download/server
2. Descarga `Ubuntu Server 24.04.x LTS` (el archivo .iso, ~2 GB)
3. Copia el archivo ISO a la carpeta `isos` de Unraid
   - En Unraid UI → `Main` → localiza tu array → busca el share `isos`
   - O usa la ruta de red: `\\IP-DE-UNRAID\isos\`

### 2.2 Crear la VM

1. En Unraid UI → tab `VMs` → boton `Add VM`
2. Selecciona `Linux` en el listado de tipos
3. Rellena los campos:

| Campo | Valor exacto |
|---|---|
| Name | `agent-marce` |
| CPUs | `6` |
| Initial Memory | `12288` MB |
| Max Memory | `12288` MB |
| Machine | `i440fx-9.1` |
| BIOS | `SeaBIOS` |
| Primary vDisk Size | `100G` |
| ISO | (selecciona la Ubuntu que descargaste) |

4. Click `Create`

### 2.3 Instalar Ubuntu Server

1. Click en el icono de pantalla (VNC) de la VM en Unraid
2. Se abrira una ventana con el instalador de Ubuntu
3. Durante la instalacion, cuando pregunte:
   - **Your name / Server name:** `agentuser` / `agent-vm`
   - **Username:** `agentuser`
   - **Password:** elige uno seguro y guardalo
   - **OpenSSH Server:** selecciona **YES** con la barra espaciadora
4. Deja que la instalacion termine (~15 minutos) y reinicia cuando lo pida

---

## Paso 3: Verificar Conectividad (15 minutos)

### 3.1 Encontrar la IP de la VM

Opcion A — Desde Unraid:
- VMs → tu VM `agent-marce` → mira los detalles de red

Opcion B — Desde la consola VNC de la VM, escribe:
```bash
ip addr show | grep "inet "
```
Busca la linea que empieza con `inet 192.168.x.x` (no la que dice `127.0.0.1`).

### 3.2 Conectar por SSH

**En Windows** (abre PowerShell con Win+X → Windows PowerShell):
```bash
ssh agentuser@192.168.1.XXX
```

**En Mac o Linux** (abre Terminal):
```bash
ssh agentuser@192.168.1.XXX
```

Reemplaza `192.168.1.XXX` con la IP real de tu VM.

Cuando veas esto, todo esta correcto:
```
agentuser@agent-vm:~$
```

### 3.3 Verificar que n8n puede conectarse a la VM

1. En n8n → `Credentials` → `New Credential`
2. Busca y selecciona `SSH`
3. Rellena:
   - Host: IP de la VM
   - Port: `22`
   - Username: `agentuser`
   - Authentication: `Password`
   - Password: el que elegiste en la instalacion
4. Click `Test` → debe aparecer "Connection successful"

---

## Cuando termines el Paso 3...

Tienes todo lo necesario para continuar con el Dia 1 del Sprint Backlog:

- La VM existe y es accesible por SSH
- n8n puede comunicarse con ella
- Tienes tus API keys para el `.env`

**Siguiente paso:** Ir a [Sprint Backlog - Dia 2](04-sprint-backlog.md) para instalar Docker y Ollama.

---

## Resolucion de Problemas Comunes

**No puedo conectar por SSH:**
- Verifica que la VM esta encendida (Unraid → VMs → estado "Running")
- Verifica que la IP es correcta con el comando `ip addr show` en la consola VNC
- Verifica que el firewall de Unraid no bloquea el puerto 22

**La ISO no aparece en Unraid al crear la VM:**
- Asegurate de que el archivo .iso esta en la carpeta correcta del array de Unraid
- Recarga la pagina de Unraid y vuelve a intentarlo

**El test SSH de n8n falla:**
- Asegurate de que la VM esta encendida
- Verifica usuario y contrasena
- Asegurate de seleccionar SSH (no SFTP) como tipo de credencial
