#!/usr/bin/env bash
# Remove o BloodyLinux instalado pelo install.sh.
#   sudo ./uninstall.sh           remove o app (mantém suas configurações)
#   sudo ./uninstall.sh --purge   remove também ~/.config/bloodylinux do usuário
set -euo pipefail

APP_NAME="bloodylinux"
PREFIX="/opt/${APP_NAME}"

if [[ $EUID -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

echo "==> Removendo BloodyLinux..."
rm -f "/usr/local/bin/${APP_NAME}" \
      "/usr/share/applications/${APP_NAME}.desktop" \
      "/usr/share/icons/hicolor/scalable/apps/${APP_NAME}.svg" \
      "/etc/udev/rules.d/70-bloodylinux.rules" \
      "/etc/udev/rules.d/99-bloody.rules" \
      "/etc/modules-load.d/${APP_NAME}.conf"
rm -rf "${PREFIX}"

command -v udevadm >/dev/null && udevadm control --reload-rules || true
command -v update-desktop-database >/dev/null && update-desktop-database -q /usr/share/applications || true

if [[ "${1:-}" == "--purge" && -n "${SUDO_USER:-}" ]]; then
    user_home="$(getent passwd "${SUDO_USER}" | cut -d: -f6)"
    rm -rf "${user_home}/.config/${APP_NAME}"
    echo "==> Configurações de ${SUDO_USER} removidas."
fi

echo "==> BloodyLinux removido."
