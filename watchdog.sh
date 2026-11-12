#!/usr/bin/env bash
# Keeps the phone link alive without manual intervention.
#
# The sandbox reaps background processes and the SSH tunnel drops, so we poll
# every 20s and rebuild whatever died. The URL only changes when the tunnel
# genuinely has to be rebuilt - while the session lives it stays put.
set -uo pipefail

APP=http://127.0.0.1:8000
DIR=/home/user/ewaste_app
F=$DIR/PHONE_URL.txt
LOG=/home/user/watchdog.log
CF=/home/user/.cfbin/cloudflared

log() { echo "[$(date -u '+%H:%M:%S')] $*" >> "$LOG"; }

cur_url() { grep -m1 -o 'https://[a-z0-9.-]*\.\(trycloudflare\.com\|lhr\.life\|loca\.lt\)' "$F" | head -1; }
log_url() { grep -m1 -o 'https://[a-z0-9.-]*\.\(trycloudflare\.com\|lhr\.life\|loca\.lt\)' /home/user/tunnel.log | head -1; }

kill_tunnels() {
  python3 - <<'PY'
import os, signal, subprocess
me = os.getpid()
for line in subprocess.run(["ps","-eo","pid,args"],capture_output=True,text=True).stdout.splitlines()[1:]:
    pid, _, args = line.strip().partition(" ")
    try: pid = int(pid)
    except ValueError: continue
    if pid == me: continue
    if ("cloudflared tunnel" in args or "nokey@localhost.run" in args) and "ps -eo" not in args:
        try: os.kill(pid, signal.SIGKILL)
        except Exception: pass
PY
}

start_app() {
  log "app down -> starting"
  ( cd "$DIR" && AI_PROVIDER=gemini nohup python3 -m uvicorn server:app \
      --host 0.0.0.0 --port 8000 >> /home/user/app.log 2>&1 & )
}

start_tunnel() {
  kill_tunnels; sleep 2
  : > /home/user/tunnel.log
  nohup ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -R 80:127.0.0.1:8000 nokey@localhost.run > /home/user/tunnel.log 2>&1 &
  for _ in $(seq 1 12); do
    sleep 4
    N=$(log_url)
    [ -z "$N" ] && continue
    c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 25 "$N/")
    if [ "$c" = "200" ]; then
      sed -i -E "s#https://[a-z0-9.-]+\.(trycloudflare\.com|lhr\.life|loca\.lt)#$N#g" "$F"
      log "tunnel up -> $N"
      return 0
    fi
  done
  # localhost.run failed this time, try cloudflared
  log "localhost.run failed -> trying cloudflared"
  kill_tunnels; sleep 2
  [ -x "$CF" ] || chmod +x "$CF" 2>/dev/null
  : > /home/user/tunnel.log
  nohup "$CF" tunnel --url http://localhost:8000 --no-autoupdate \
        --protocol http2 --metrics 127.0.0.1:20241 > /home/user/tunnel.log 2>&1 &
  for _ in $(seq 1 12); do
    sleep 4
    N=$(log_url)
    [ -z "$N" ] && continue
    c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 25 "$N/")
    if [ "$c" = "200" ]; then
      sed -i -E "s#https://[a-z0-9.-]+\.(trycloudflare\.com|lhr\.life|loca\.lt)#$N#g" "$F"
      log "tunnel up (cloudflared) -> $N"
      return 0
    fi
  done
  log "!! both providers failed"
  return 1
}

log "watchdog started"
while true; do
  # 1. app
  if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "$APP/api/health")" != "200" ]; then
    start_app; sleep 8
  fi
  # 2. tunnel
  U=$(cur_url)
  if [ -z "$U" ]; then
    start_tunnel
  else
    C=$(curl -s -o /dev/null -w '%{http_code}' --max-time 25 "$U/")
    if [ "$C" != "200" ]; then
      log "link $C on $U -> rebuilding"
      start_tunnel
    fi
  fi
  sleep 20
done
