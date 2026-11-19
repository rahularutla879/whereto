# Inactive real-native candidates

These exact local images passed container/browser fixture verification. They are not published, financially enrolled, model-qualified, security-accepted or cloud-deployed. See [implementation/results](../../../docs/task52-real-role-packaging.md), images.json, cohort.json and security.json.

From the repository root, using Python3.12 and the reviewed zlib archive:

```sh
python3.12 -m deployment.prepare_real_candidate /tmp/whereto-real-build /path/to/verified/zlib1g.deb
python3.12 -m deployment.build_real_candidates /tmp/whereto-real-build
python3.12 -m deployment.smoke_real_candidates /tmp/whereto-real-build
python3.12 experiments/real_images/run.py /tmp/whereto-real-build
python3.12 -m deployment.scan_real_candidates /tmp/whereto-real-build
python3.12 -m deployment.cloud_run_real deployment/cloud-run/staging.example.json
```

Build tools use local Docker context colima-whereto-task52, Linux amd64 and exact reviewed base/dependency hashes. The image runtime does not depend on Colima, Docker administration, the Mac, fixtures or local Ollama. Chrome/Node and the separate disposable storage/test harness are required only for local verification. Build contexts must be new; do not overwrite old evidence. Rebuilds need new actual image records/scans. No push/provision/provider command is run by the compiler. The current frontend lacks genuine enrollment trust and cannot activate; approved public-key enrollment requires a separately bound frontend build.
