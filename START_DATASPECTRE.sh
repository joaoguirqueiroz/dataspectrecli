#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
VENV_BIN="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$VENV_BIN" ]]; then
  printf '\033[1;31m[ERRO]\033[0m DataSpectre ainda nao foi instalado neste Linux.\n' >&2
  printf 'Execute primeiro:\n  chmod +x INSTALL_DATASPECTRE_LINUX.sh\n  ./INSTALL_DATASPECTRE_LINUX.sh\n' >&2
  exit 1
fi

if (( $# == 0 )); then
  set -- interactive
fi

exec "$VENV_BIN" "$ROOT_DIR/main.py" --root "$ROOT_DIR" "$@"
