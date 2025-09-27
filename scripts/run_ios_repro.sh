#!/usr/bin/env bash
# Apply a reproducible environment to an iOS simulator using EnvVenv.
# Requires macOS with Xcode command line tools installed.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <config.yaml>"
  echo "If no config is provided, defaults to repro_template.yaml in the project root."
fi

CONFIG_FILE=${1:-$(dirname "$0")/../repro_template.yaml}

# Apply the environment described in the YAML configuration.
python3 "$(dirname "$0")/../envvenv.py" --config "$CONFIG_FILE"

echo "Repro environment applied to the iOS simulator.  Launch your app to reproduce the issue."