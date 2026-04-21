#!/bin/sh
set -eu

if [ "$#" -gt 0 ]; then
  exec /usr/local/bin/gcs "$@"
fi

: "${GCS_ADMIN_TOKEN:?set GCS_ADMIN_TOKEN}"

if [ -n "${GCS_GITLAB_URL:-}" ]; then
  exec /usr/local/bin/gcs serve \
    --workdir "${GCS_WORKDIR:-/data}" \
    --admin-token "${GCS_ADMIN_TOKEN}" \
    --host 0.0.0.0 \
    --port "${GCS_PORT:-8765}" \
    --gitlab-url "${GCS_GITLAB_URL}" \
    --workers "${GCS_WORKERS:-8}"
fi

exec /usr/local/bin/gcs serve \
  --workdir "${GCS_WORKDIR:-/data}" \
  --admin-token "${GCS_ADMIN_TOKEN}" \
  --host 0.0.0.0 \
  --port "${GCS_PORT:-8765}" \
  --workers "${GCS_WORKERS:-8}"
