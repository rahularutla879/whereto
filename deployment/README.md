# Local packaging verification — no cloud activation

From `/Users/rahularutla/Documents/whereto`:

```sh
npm run build
backend/.venv/bin/python -m unittest deployment.test_packaging -v
DOCKER_CONTEXT=colima-whereto-task52 sh deployment/container-smoke.sh
```

The Python suite executes assembled native payloads with loopback fakes. It is deliberately separate from normal backend discovery because it requires a built Next standalone server. The shell command requires an already installed/running local Docker engine, builds Linux amd64 images and probes them without publishing ports or contacting external providers at runtime. It does not push, deploy or grant access. Builds download public locked dependencies and base images.

**Current status:** native tests and actual Linux amd64 builds/runtime smoke passed on the approved local Colima profile. Image vulnerability findings remain unresolved; see [actual container/security evidence](../docs/task52-local-container-verification.md). Do not describe these artifacts as a working hosted deployment. Backend defaults to the existing production refusal. Do not override that refusal, mount local credentials or enable development provider flags.

See [environment/secret contract](environment-contract.md), [readiness and cost report](../docs/task52-cloud-deployment-preparation.md) and [verification](../docs/task52-local-container-verification.json). YAML templates contain placeholders and deliberately incomplete activation dependencies; there is no deployment command or approval here.

Current [security remediation](../docs/task52-container-security-remediation.md): one explicitly reviewed pyasn1 patch in the deployment Linux lock. Historical/local backend requirements remain frozen. The image build now runs pip check; remaining OS/lint findings are not waived.
