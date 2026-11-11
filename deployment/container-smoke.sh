#!/bin/sh
# Explicit local-only image build/probe. No registry push or deployment.
set -eu
cd "$(dirname "$0")/.."
if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo 'BLOCKED: a working local Docker engine is required; no images were verified.' >&2
  exit 78
fi
suffix="task52-$(date +%s)-$$"
backend=""; frontend=""
cleanup() {
  if [ -n "$frontend" ]; then docker rm -f "$frontend" >/dev/null 2>&1 || true; fi
  if [ -n "$backend" ]; then docker rm -f "$backend" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT HUP INT TERM
docker build --platform linux/amd64 -f deployment/Dockerfile.backend -t "whereto-backend:$suffix" .
docker build --platform linux/amd64 -f deployment/Dockerfile.frontend -t "whereto-frontend:$suffix" .
# Hosted/prod backend refusal and frontend missing-config refusal are expected.
set +e
docker run --rm --network none "whereto-backend:$suffix"
bstatus=$?
docker run --rm --network none "whereto-frontend:$suffix"
fstatus=$?
set -e
[ "$bstatus" -eq 78 ] && [ "$fstatus" -eq 78 ]
backend=$(docker run -d --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m --cap-drop ALL --security-opt no-new-privileges --pids-limit 128 --memory 512m --cpus 1 -e WHERETO_ENV=test -e AI_BASE_URL=http://127.0.0.1:1 -e AI_TIMEOUT_SECONDS=1 "whereto-backend:$suffix")
frontend=$(docker run -d --network "container:$backend" --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m --cap-drop ALL --security-opt no-new-privileges --pids-limit 128 --memory 512m --cpus 1 -e PORT=3000 -e BACKEND_URL=http://127.0.0.1:8080 "whereto-frontend:$suffix")
[ "$(docker exec "$backend" id -u)" -ne 0 ]
[ "$(docker exec "$frontend" id -u)" -ne 0 ]
docker exec "$backend" python -c "from pathlib import Path; assert not Path('/app/scripts').exists(); assert not Path('/app/.git').exists(); assert not list(Path('/app/backend').rglob('test_*.py')); assert not Path('/app/backend/evaluation').exists()"
docker exec -i "$backend" python - <<'PY'
import json,time,urllib.request,urllib.error
for attempt in range(100):
    try:
        with urllib.request.urlopen('http://127.0.0.1:3000/api/health',timeout=1) as r:
            assert json.load(r)=={'status':'ok','backend':'ok'}
        break
    except (OSError,AssertionError):time.sleep(.1)
else:raise AssertionError('Local containers failed readiness')
request=urllib.request.Request('http://127.0.0.1:3000/api/interpret',data=json.dumps({'text':'Synthetic dinner outing'}).encode(),headers={'Content-Type':'application/json'})
try:urllib.request.urlopen(request,timeout=5);raise AssertionError('AI unexpectedly succeeded')
except urllib.error.HTTPError as e:assert e.code==503
try:urllib.request.urlopen('http://127.0.0.1:8080/api/development-diagnostics',timeout=2);raise AssertionError('Diagnostics exposed')
except urllib.error.HTTPError as e:assert e.code in (403,404)
print('Container health/proxy/unavailable-AI/diagnostic checks passed; no functional cloud activation.')
PY
# Same container starts a fresh process: loss is a blocker, not durable recovery.
docker restart "$backend" >/dev/null
echo 'Local image probes completed; shared-state and cloud activation remain blocked.'
