#!/usr/bin/env bash
# Health-check the phone link end to end.
#   ./check_link.sh             -> check only
#   ./check_link.sh --refish    -> if dead, restart the tunnel and print a new URL
#
# Providers are tried in order. Cloudflare quick tunnels started returning 530
# for every new hostname once this sandbox had restarted them repeatedly, so
# localhost.run (SSH based, no account) is primary and cloudflared is backup.
set -uo pipefail
APP=http://127.0.0.1:8000
F=/home/user/ewaste_app/PHONE_URL.txt
LOG=/home/user/tunnel.log

url() { grep -m1 -o 'https://[a-z0-9.-]*\.\(trycloudflare\.com\|lhr\.life\|loca\.lt\)' "$F" | head -1; }
pub() { grep -m1 -o 'https://[a-z0-9.-]*\.\(trycloudflare\.com\|lhr\.life\|loca\.lt\)' "$LOG" | head -1; }

echo "1. app server (port 8000)"
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$APP/")
echo "   HTTP $code"
if [ "$code" != "200" ]; then
  echo "   -> APP IS DOWN. Restart with:"
  echo "      AI_PROVIDER=gemini python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --app-dir /home/user/ewaste_app"
  exit 1
fi

PUB=$(url)
echo "2. public URL: $PUB"
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 40 "$PUB/")
echo "   HTTP $code"

if [ "$code" = "200" ]; then
  echo "3. assets"
  for a in /styles.css /app.js /sw.js /manifest.json /icon-192.png; do
    printf "   %-16s " "$a"
    curl -s -o /dev/null -w 'HTTP %{http_code}  %{size_download} B\n' --max-time 30 "$PUB$a"
  done
  echo "4. api"
  curl -s --max-time 60 "$PUB/api/health"; echo
  echo "LINK OK"
  exit 0
fi

if [ "${1:-}" != "--refish" ]; then
  echo "   -> link is down (530 = hostname recycled/blocked at edge, 000 = DNS gone)"
  echo "   -> re-run with --refish to restart it"
  exit 1
fi

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
  sleep 2
}

# a fresh hostname needs time before DNS resolves, and a few more tries after
wait_up() {
  for _ in $(seq 1 14); do
    sleep 4
    N=$(pub)
    [ -z "$N" ] && continue
    c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 40 "$N/")
    [ "$c" = "200" ] && { echo "$N"; return 0; }
  done
  return 1
}

echo "   restarting tunnel (localhost.run)..."
kill_tunnels; : > "$LOG"
nohup ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
  -R 80:127.0.0.1:8000 nokey@localhost.run > "$LOG" 2>&1 &
if NEW=$(wait_up); then
  echo "   NEW URL: $NEW"
  sed -i -E "s#https://[a-z0-9.-]+\.(trycloudflare\.com|lhr\.life|loca\.lt)#$NEW#g" "$F"
  echo "   PHONE_URL.txt updated"
  exit 0
fi

echo "   localhost.run failed, falling back to cloudflared..."
kill_tunnels; : > "$LOG"
chmod +x /home/user/.cfbin/cloudflared
nohup /home/user/.cfbin/cloudflared tunnel --url http://localhost:8000 \
      --no-autoupdate --protocol http2 --metrics 127.0.0.1:20241 > "$LOG" 2>&1 &
if NEW=$(wait_up); then
  echo "   NEW URL: $NEW"
  sed -i -E "s#https://[a-z0-9.-]+\.(trycloudflare\.com|lhr\.life|loca\.lt)#$NEW#g" "$F"
  echo "   PHONE_URL.txt updated"
  exit 0
fi

echo "   both providers failed. see $LOG"
tail -5 "$LOG"
exit 1
