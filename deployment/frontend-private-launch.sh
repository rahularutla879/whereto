#!/bin/sh
# Run before Node: NODE_OPTIONS must not execute code before the JS refusal guard.
if [ -n "${NODE_OPTIONS+x}${NODE_PATH+x}${NODE_EXTRA_CA_CERTS+x}${NODE_TLS_REJECT_UNAUTHORIZED+x}${NODE_DEBUG+x}${NODE_V8_COVERAGE+x}${NODE_USE_ENV_PROXY+x}${HTTP_PROXY+x}${HTTPS_PROXY+x}${ALL_PROXY+x}${NO_PROXY+x}" ]; then
  echo 'Private frontend startup refused: unsafe runtime options.' >&2
  exit 78
fi
exec node /app/private-runtime/frontend-entry.mjs
