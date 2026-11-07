#!/usr/bin/env bash
set -euo pipefail
gcloud run jobs deploy batch-translator \
  --source=. \
  --region=europe-north2 \
  --env-vars-file=env.yaml
