#!/usr/bin/env bash
# Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
if [[ ! -x .venv/bin/python ]]; then
  echo "Prepare o ambiente virtual seguindo o README.md." >&2
  exit 1
fi
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${DL_PORT:-8840}" --workers 1 --no-access-log
