#!/usr/bin/env bash
# Forward all args to the paved CLI. `docker compose run app repair /data/x.mp4`.
set -euo pipefail
exec paved "$@"
