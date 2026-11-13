"""Explicit private image entry. Normal backend startup is not modified."""
from pathlib import Path
import os,json,sys,threading,signal
from private_runtime.private_service import runtime,privileged_server,backend_app

def main():
    # Config is an independently supplied Secret Manager projection, not request data.
    path=Path('/run/secrets/whereto-private.json')
    if not path.is_file() or not os.environ.get('K_SERVICE'):raise RuntimeError('Private hosted enrollment missing')
    config=json.loads(path.read_text())
    if config.get('identityEnvironment')!='private-staging' or config.get('transportTermination')!='cloud-run':raise RuntimeError('Private hosted identity/transport enrollment missing')
    from private_runtime.image_build import ROLE
    with runtime(config) as ports:
        # Metadata result must independently verify this exact workload subject.
        ports.identity.token(config['audiences'][config['service']])
        if ROLE=='backend':
            import uvicorn
            uvicorn.run(backend_app(config),host='0.0.0.0',port=config['port'],access_log=False,log_level='warning')
        else:
            server=privileged_server(config)
            def stop(*_):
                from private_runtime import owned_dispatch
                if ROLE=='factory':owned_dispatch.owner().drain(8)
                threading.Thread(target=server.shutdown,daemon=True).start()
            signal.signal(signal.SIGTERM,stop);server.serve_forever(poll_interval=.2);server.server_close()
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        print('Private service startup refused: verified dependencies and enrollment required.',file=sys.stderr);raise SystemExit(78)
