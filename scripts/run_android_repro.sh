#!/usr/bin/env bash
# Boot or wait for an Android emulator and apply a reproducible environment using EnvVenv.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <config.yaml>"
  echo "If no config is provided, defaults to repro_template.yaml in the project root."
fi

CONFIG_FILE=${1:-$(dirname "$0")/../repro_template.yaml}

# Wait for any emulator or device to be ready.
echo "Waiting for device..."
adb wait-for-device

# Apply the environment described in the YAML configuration.
python3 "$(dirname "$0")/../envvenv.py" --config "$CONFIG_FILE"

echo "Repro environment applied.  Interact with the app or attach UI tests now."
