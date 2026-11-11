"""Container-only launcher. The application's hosted-production refusal is intact."""
import os
import sys
from urllib.parse import urlsplit


def validate(env):
    port = env.get('PORT','8080')
    if not port.isascii() or not port.isdigit() or not 1 <= int(port) <= 65535:
        raise ValueError('Invalid port')
    if any(k.startswith('WHERETO_') and k.endswith('_DEV') and v not in ('','0') for k,v in env.items()):
        raise ValueError('Development integration unavailable in this artifact')
    if env.get('VENUE_DATA_MODE','mock') != 'mock':
        raise ValueError('Real provider activation is not implemented')
    if env.get('AI_PROVIDER','ollama') != 'ollama' or env.get('AI_MODEL','qwen3:4b') != 'qwen3:4b':
        raise ValueError('Model change is not approved')
    url = urlsplit(env.get('AI_BASE_URL','http://127.0.0.1:11434'))
    if url.scheme != 'http' or url.hostname not in ('127.0.0.1','localhost','::1') or url.username or url.password or url.query or url.fragment:
        raise ValueError('Hosted inference adapter is unavailable')
    from backend.admission import validate_environment
    validate_environment()  # no force/resume/cloud-ready bypass
    return port


def main():
    try:
        port = validate(os.environ)
    except (ValueError,RuntimeError):
        print('Backend startup refused: deployment dependencies or configuration require review.',file=sys.stderr)
        return 78
    os.execv(sys.executable,[sys.executable,'-m','uvicorn','backend.main:app',
        '--host','0.0.0.0','--port',port,'--workers','1','--no-access-log',
        '--timeout-graceful-shutdown','5'])


if __name__ == '__main__':
    raise SystemExit(main())
