#!/usr/bin/env bash
set -euo pipefail
gcloud run jobs update batch-translator \
  --region=europe-north2 \
  --env-vars-file=env.yaml
