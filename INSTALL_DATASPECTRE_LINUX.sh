#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="DataSpectre CLI"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=10
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
VENV_DIR="$ROOT_DIR/.venv"
BIN_DIR="${HOME}/.local/bin"
LAUNCHER="$BIN_DIR/dataspectre"

info()  { printf '\033[1;32m[DATASPECTRE]\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m[AVISO]\033[0m %s\n' "$*" >&2; }
fail()  { printf '\033[1;31m[ERRO]\033[0m %s\n' "$*" >&2; exit 1; }

if [[ "$(uname -s 2>/dev/null || true)" != "Linux" ]]; then
  fail "Este instalador foi criado para Linux. No Windows, use INSTALL_DATASPECTRE.bat."
fi

find_python() {
  local candidate
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<PY >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (${MIN_PYTHON_MAJOR}, ${MIN_PYTHON_MINOR}) else 1)
PY
      then
        printf '%s' "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

package_hint() {
  if command -v apt-get >/dev/null 2>&1; then
    printf '%s' "sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
  elif command -v dnf >/dev/null 2>&1; then
    printf '%s' "sudo dnf install -y python3 python3-pip"
  elif command -v pacman >/dev/null 2>&1; then
    printf '%s' "sudo pacman -S --needed python python-pip"
  elif command -v zypper >/dev/null 2>&1; then
    printf '%s' "sudo zypper install python3 python3-pip python3-virtualenv"
  elif command -v apk >/dev/null 2>&1; then
    printf '%s' "sudo apk add python3 py3-pip py3-virtualenv"
  elif command -v xbps-install >/dev/null 2>&1; then
    printf '%s' "sudo xbps-install -S python3 python3-pip"
  else
    printf '%s' "Instale Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ com pip e o modulo venv pelo gerenciador da sua distribuicao."
  fi
}

PYTHON_BIN="$(find_python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  fail "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ nao foi encontrado. Execute: $(package_hint)"
fi

info "Sistema Linux detectado: $(uname -srmo 2>/dev/null || uname -a)"
info "Python: $($PYTHON_BIN --version 2>&1)"

if ! "$PYTHON_BIN" -m venv --help >/dev/null 2>&1; then
  fail "O modulo venv nao esta disponivel. Execute: $(package_hint)"
fi

if [[ ! -d "$VENV_DIR" ]]; then
  info "Criando ambiente Python isolado em .venv..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  info "Ambiente virtual existente encontrado. Sera reutilizado."
fi

VENV_PYTHON="$VENV_DIR/bin/python"
[[ -x "$VENV_PYTHON" ]] || fail "O ambiente virtual foi criado, mas o Python interno nao esta executavel."

info "Atualizando o instalador Python..."
if ! "$VENV_PYTHON" -m pip install --disable-pip-version-check --timeout 20 --retries 2 --upgrade pip; then
  fail "Nao foi possivel atualizar o pip. Verifique sua conexao e execute novamente o instalador."
fi

info "Instalando o DataSpectre e suas dependencias..."
if ! "$VENV_PYTHON" -m pip install --disable-pip-version-check --timeout 20 --retries 2 --editable "$ROOT_DIR"; then
  fail "Nao foi possivel instalar as dependencias Python. Verifique sua conexao e execute novamente o instalador."
fi

mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<LAUNCHER_EOF
#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR=$(printf '%q' "$ROOT_DIR")
exec "\$ROOT_DIR/.venv/bin/dataspectre" --root "\$ROOT_DIR" "\$@"
LAUNCHER_EOF
chmod 755 "$LAUNCHER"

info "Executando verificacao local segura..."
if ! "$LAUNCHER" status >/dev/null; then
  fail "A verificacao inicial falhou. Rode '$LAUNCHER status' para ver os detalhes."
fi

printf '\n'
info "Instalacao concluida."
printf '  Abrir:        %s\n' "dataspectre"
printf '  Ajuda:        %s\n' "dataspectre help"
printf '  Status:       %s\n' "dataspectre status"
printf '  Setup/check:  %s\n' "dataspectre setup check"
printf '  Alternativa:  %s\n' "./START_DATASPECTRE.sh"

case ":${PATH}:" in
  *":${BIN_DIR}:"*) ;;
  *)
    warn "$BIN_DIR ainda nao esta no PATH desta sessao."
    printf 'Adicione ao shell com:\n  export PATH="$HOME/.local/bin:$PATH"\n'
    printf 'Para manter apos reiniciar, coloque essa linha em ~/.bashrc, ~/.zshrc ou arquivo equivalente.\n'
    ;;
esac

printf '\nFerramentas externas opcionais:\n'
if command -v nmap >/dev/null 2>&1; then
  printf '  [OK] Nmap: %s\n' "$(command -v nmap)"
else
  printf '  [--] Nmap nao encontrado. O modulo continua instalado, mas scans reais com Nmap exigem o binario.\n'
fi
if command -v nuclei >/dev/null 2>&1; then
  printf '  [OK] Nuclei: %s\n' "$(command -v nuclei)"
else
  printf '  [--] Nuclei nao encontrado. O modulo continua instalado, mas auditorias reais com Nuclei exigem o binario.\n'
fi
printf '\nUse somente em sistemas, laboratorios e ativos proprios ou com autorizacao explicita.\n'
