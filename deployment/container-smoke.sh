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
save_fixture=$(mktemp "${TMPDIR:-/tmp}/whereto-container-save.XXXXXX")
cleanup() {
  rm -f "$save_fixture"
  if [ -n "$frontend" ]; then docker rm -f "$frontend" >/dev/null 2>&1 || true; fi
  if [ -n "$backend" ]; then docker rm -f "$backend" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT HUP INT TERM
docker build --platform linux/amd64 -f deployment/Dockerfile.backend -t "whereto-backend:$suffix" .
docker build --platform linux/amd64 -f deployment/Dockerfile.frontend -t "whereto-frontend:$suffix" .
# Hosted/prod backend refusal and frontend missing-config refusal are expected.
set +e
docker run --rm --platform linux/amd64 --network none "whereto-backend:$suffix"
bstatus=$?
docker run --rm --platform linux/amd64 --network none "whereto-frontend:$suffix"
fstatus=$?
set -e
[ "$bstatus" -eq 78 ] && [ "$fstatus" -eq 78 ]
backend=$(docker run -d --platform linux/amd64 --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m --cap-drop ALL --security-opt no-new-privileges --pids-limit 128 --memory 512m --cpus 1 -e WHERETO_ENV=test -e AI_BASE_URL=http://127.0.0.1:1 -e AI_TIMEOUT_SECONDS=1 "whereto-backend:$suffix")
frontend=$(docker run -d --platform linux/amd64 --network "container:$backend" --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m --cap-drop ALL --security-opt no-new-privileges --pids-limit 128 --memory 512m --cpus 1 -e PORT=3000 -e BACKEND_URL=http://127.0.0.1:8080 "whereto-frontend:$suffix")
[ "$(docker exec "$backend" id -u)" -ne 0 ]
[ "$(docker exec "$frontend" id -u)" -ne 0 ]
# Inherited package managers must be absent from the final merged runtime.
docker exec "$frontend" sh -c '! command -v npm && ! command -v npx && ! command -v yarn && ! command -v corepack'
docker exec "$backend" python -c "import importlib.util; from pathlib import Path; assert importlib.util.find_spec('pip') is None; assert not list(Path('/usr/local/lib/python3.12/site-packages').glob('pip*'))"
for container in "$backend" "$frontend"; do
  [ "$(docker inspect --format '{{.HostConfig.Privileged}}' "$container")" = false ]
  [ "$(docker inspect --format '{{.HostConfig.ReadonlyRootfs}}' "$container")" = true ]
  [ "$(docker inspect --format '{{json .HostConfig.CapDrop}}' "$container")" = '["ALL"]' ]
  [ -z "$(docker port "$container")" ]
done
docker exec "$backend" python -c "from pathlib import Path; assert not Path('/app/scripts').exists(); assert not Path('/app/.git').exists(); assert not list(Path('/app/backend').rglob('test_*.py')); assert not Path('/app/backend/evaluation').exists()"
docker exec -i "$backend" python - <<'PY'
import json,time,urllib.request,urllib.error
from datetime import date,timedelta
from pathlib import Path
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
def post(path,body):
    request=urllib.request.Request('http://127.0.0.1:3000'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=5) as response:return response.status,json.load(response)
    except urllib.error.HTTPError as error:return error.code,None
status,result=post('/api/plans/generate',{'activities':['food','bowling'],'location':'Baltimore','date':(date.today()+timedelta(days=10)).isoformat(),'planningMode':'surprise'})
assert status==200
options=result['plans']+result['provisionalPlans'];assert options
save={'receipt':result['saveReceipt'],'accessToken':result['saveAccessToken'],'candidateIds':[p['candidate']['id'] for p in options],'selectedId':options[0]['candidate']['id']}
assert post('/api/plans/save',save)[0]==503 # SQL is unconfigured; no database connection.
Path('/tmp/smoke-save.json').write_text(json.dumps(save))
for path in ['/dev/diagnostics','/api/development-diagnostics']:
    try:urllib.request.urlopen('http://127.0.0.1:3000'+path,timeout=3);raise AssertionError('Frontend diagnostics exposed')
    except urllib.error.HTTPError as error:assert error.code in (403,404)
print('Container health/proxy/mock planning/missing-SQL/unavailable-AI/diagnostic checks passed.')
PY
# Only a fictional receipt leaves the container; never owner data or credentials.
docker exec "$backend" cat /tmp/smoke-save.json > "$save_fixture"
# Graceful termination must not require SIGKILL (137) or report OOM.
docker stop --time 8 "$frontend" >/dev/null
front_exit=$(docker inspect --format '{{.State.ExitCode}}' "$frontend")
echo "Frontend termination exit code: $front_exit"
# Installed Next exits 143 after awaited SIGTERM cleanup; 137 is never accepted.
case "$front_exit" in 0|143) ;; *) exit 1 ;; esac
[ "$(docker inspect --format '{{.State.OOMKilled}}' "$frontend")" = false ]
docker stop --time 8 "$backend" >/dev/null
back_exit=$(docker inspect --format '{{.State.ExitCode}}' "$backend")
echo "Backend termination exit code: $back_exit"
# Uvicorn re-raises SIGTERM only after its graceful cleanup.
case "$back_exit" in 0|143) ;; *) exit 1 ;; esac
docker logs "$backend" 2>&1 | grep -q 'Application shutdown complete'
[ "$(docker inspect --format '{{.State.OOMKilled}}' "$backend")" = false ]
docker start "$backend" >/dev/null
docker exec -i "$backend" python -c "import sys; from pathlib import Path; Path('/tmp/smoke-save.json').write_bytes(sys.stdin.buffer.read())" < "$save_fixture"
# Rejoin the restarted backend's isolated network namespace.
docker start "$frontend" >/dev/null
docker exec -i "$backend" python - <<'PYTEST'
import json,time,urllib.request,urllib.error
from pathlib import Path
for attempt in range(100):
    try:
        with urllib.request.urlopen('http://127.0.0.1:3000/api/health',timeout=1) as response:assert response.status==200
        break
    except (OSError,AssertionError):time.sleep(.1)
else:raise AssertionError('Restarted containers failed readiness')
request=urllib.request.Request('http://127.0.0.1:3000/api/plans/save',data=Path('/tmp/smoke-save.json').read_bytes(),headers={'Content-Type':'application/json'})
try:urllib.request.urlopen(request,timeout=3);raise AssertionError('Restart revived receipt')
except urllib.error.HTTPError as error:assert error.code==409
print('Graceful shutdown/restart passed; old receipt safely refused after process-state loss.')
PYTEST
echo "Local images: whereto-backend:$suffix whereto-frontend:$suffix"
echo 'Local image probes completed; shared-state and cloud activation remain blocked.'
