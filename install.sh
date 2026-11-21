#!/usr/bin/env bash
# Instalador do BloodyLinux (qualquer distro: Debian/Ubuntu/Mint, Fedora, Arch/Manjaro, openSUSE).
#
#   sudo ./install.sh              instala em /opt/bloodylinux
#   sudo ./install.sh --no-deps    não instala pacotes do sistema (só o app)
#   sudo ./install.sh --uninstall  remove o app (equivale a uninstall.sh)
set -euo pipefail

APP_NAME="bloodylinux"
PREFIX="/opt/${APP_NAME}"
BIN_LINK="/usr/local/bin/${APP_NAME}"
DESKTOP_FILE="/usr/share/applications/${APP_NAME}.desktop"
ICON_FILE="/usr/share/icons/hicolor/scalable/apps/${APP_NAME}.svg"
UDEV_RULE="/etc/udev/rules.d/70-bloodylinux.rules"
LEGACY_UDEV_RULE="/etc/udev/rules.d/99-bloody.rules"
MODULES_FILE="/etc/modules-load.d/${APP_NAME}.conf"

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DEPS=1

c_red=$'\e[31m'; c_grn=$'\e[32m'; c_ylw=$'\e[33m'; c_rst=$'\e[0m'
info() { echo "${c_grn}==>${c_rst} $*"; }
warn() { echo "${c_ylw}AVISO:${c_rst} $*" >&2; }
die()  { echo "${c_red}ERRO:${c_rst} $*" >&2; exit 1; }

for arg in "$@"; do
    case "$arg" in
        --no-deps) INSTALL_DEPS=0 ;;
        --uninstall) exec bash "${SRC_DIR}/uninstall.sh" ;;
        -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
        *) die "Opção desconhecida: $arg" ;;
    esac
done

[[ "$(uname -s)" == "Linux" ]] || die "O BloodyLinux só funciona no Linux."

# Reexecuta com sudo se necessário (udev, /opt e /usr exigem root)
if [[ $EUID -ne 0 ]]; then
    info "Permissão de administrador necessária, solicitando sudo..."
    exec sudo bash "$0" "$@"
fi

# ---------------------------------------------------------------------------
# 1. Dependências do sistema
# ---------------------------------------------------------------------------
install_system_deps() {
    if command -v apt-get >/dev/null; then
        info "Instalando dependências (apt)..."
        apt-get update -qq
        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
            python3 python3-venv python3-tk python3-evdev python3-usb libusb-1.0-0
    elif command -v dnf >/dev/null; then
        info "Instalando dependências (dnf)..."
        dnf install -y -q python3 python3-tkinter python3-evdev python3-pyusb libusb1 \
            || dnf install -y -q python3 python3-tkinter python3-evdev python3-pyusb libusbx
    elif command -v pacman >/dev/null; then
        info "Instalando dependências (pacman)..."
        pacman -S --needed --noconfirm python tk python-evdev python-pyusb libusb
    elif command -v zypper >/dev/null; then
        info "Instalando dependências (zypper)..."
        zypper --non-interactive install python3 python3-tk python3-evdev python3-pyusb libusb-1_0-0
    else
        warn "Gerenciador de pacotes não reconhecido. Instale manualmente: python3, venv, tkinter, libusb."
    fi
}

if [[ $INSTALL_DEPS -eq 1 ]]; then
    install_system_deps || warn "Falha ao instalar algumas dependências do sistema; tentando continuar."
fi

command -v python3 >/dev/null || die "python3 não encontrado."
python3 -c "import tkinter" 2>/dev/null || die "tkinter não encontrado (pacote python3-tk / python3-tkinter)."
python3 -c "import venv, ensurepip" 2>/dev/null || die "Módulo venv indisponível (pacote python3-venv)."

# ---------------------------------------------------------------------------
# 2. Arquivos do aplicativo
# ---------------------------------------------------------------------------
info "Copiando aplicativo para ${PREFIX}..."
mkdir -p "${PREFIX}"
rm -rf "${PREFIX}/src"
cp -r "${SRC_DIR}/src" "${PREFIX}/"
cp "${SRC_DIR}/main.py" "${SRC_DIR}/requirements.txt" "${SRC_DIR}/LICENSE" \
   "${SRC_DIR}/uninstall.sh" "${PREFIX}/"
find "${PREFIX}/src" -name '__pycache__' -type d -prune -exec rm -rf {} +
chmod 755 "${PREFIX}/main.py" "${PREFIX}/uninstall.sh"

# ---------------------------------------------------------------------------
# 3. Ambiente Python (usa evdev/pyusb do sistema quando disponíveis)
# ---------------------------------------------------------------------------
info "Criando ambiente Python em ${PREFIX}/venv..."
rm -rf "${PREFIX}/venv"
python3 -m venv --system-site-packages "${PREFIX}/venv"
"${PREFIX}/venv/bin/python" -m pip install -q --upgrade pip
if ! "${PREFIX}/venv/bin/python" -m pip install -q -r "${PREFIX}/requirements.txt"; then
    die "Falha ao instalar dependências Python.
Se o erro foi ao compilar 'evdev', instale o pacote python3-evdev da sua distro
(ou gcc + python3-dev + linux headers) e rode o instalador de novo."
fi
"${PREFIX}/venv/bin/python" -c "import evdev, usb, customtkinter" \
    || die "Dependências Python não puderam ser importadas."

# ---------------------------------------------------------------------------
# 4. Lançador, menu e ícone
# ---------------------------------------------------------------------------
info "Criando lançador ${BIN_LINK} e atalho no menu..."
cat > "${BIN_LINK}" <<EOF
#!/bin/sh
exec "${PREFIX}/venv/bin/python" "${PREFIX}/main.py" "\$@"
EOF
chmod 755 "${BIN_LINK}"

install -Dm644 "${SRC_DIR}/packaging/bloodylinux.desktop" "${DESKTOP_FILE}"
install -Dm644 "${SRC_DIR}/packaging/bloodylinux.svg" "${ICON_FILE}"
command -v update-desktop-database >/dev/null && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true

# ---------------------------------------------------------------------------
# 5. Permissões: udev + módulo uinput
# ---------------------------------------------------------------------------
info "Instalando regras udev e habilitando o módulo uinput..."
if [[ -f "${LEGACY_UDEV_RULE}" ]]; then
    info "Removendo regra antiga ${LEGACY_UDEV_RULE} (permissões 0666)."
    rm -f "${LEGACY_UDEV_RULE}"
fi
install -Dm644 "${SRC_DIR}/70-bloodylinux.rules" "${UDEV_RULE}"
echo "uinput" > "${MODULES_FILE}"
modprobe uinput 2>/dev/null || warn "Não foi possível carregar o módulo uinput agora (será carregado no próximo boot)."
if command -v udevadm >/dev/null; then
    udevadm control --reload-rules
    udevadm trigger --subsystem-match=misc --subsystem-match=input --subsystem-match=usb --subsystem-match=hidraw || true
fi

echo
info "${c_grn}BloodyLinux $("${PREFIX}/venv/bin/python" "${PREFIX}/main.py" --version | awk '{print $2}') instalado!${c_rst}"
echo "    Abra pelo menu de aplicativos (BloodyLinux) ou rode: ${APP_NAME}"
echo "    Para remover: sudo ${PREFIX}/uninstall.sh"
echo
echo "    Se o mouse já estava conectado e a engine acusar falta de permissão,"
echo "    desconecte e reconecte o mouse (ou reinicie a sessão)."
