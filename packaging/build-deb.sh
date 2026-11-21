#!/usr/bin/env bash
# Gera dist/bloodylinux_<versão>_all.deb (Debian, Ubuntu, Mint, Pop!_OS...).
#
# O pacote usa evdev/pyusb/tk do próprio sistema (apt) e embute apenas o
# customtkinter + darkdetect (Python puro) em /opt/bloodylinux/vendor,
# então a instalação não precisa de internet nem de compilador.
#
# Requisitos para gerar: bash, python3 com pip, dpkg-deb.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "${ROOT}/src/__init__.py")"
[[ -n "$VERSION" ]] || { echo "Versão não encontrada em src/__init__.py" >&2; exit 1; }

PKG="bloodylinux"
BUILD="${ROOT}/build/deb/${PKG}_${VERSION}_all"
OUT="${ROOT}/dist"

echo "==> Montando ${PKG} ${VERSION}"
rm -rf "${BUILD}"
mkdir -p "${BUILD}/DEBIAN" "${OUT}"

# Aplicativo
APP="${BUILD}/opt/${PKG}"
mkdir -p "${APP}"
cp -r "${ROOT}/src" "${APP}/"
cp "${ROOT}/main.py" "${ROOT}/LICENSE" "${APP}/"
find "${APP}" -name '__pycache__' -type d -prune -exec rm -rf {} +

echo "==> Embutindo customtkinter em vendor/"
python3 -m pip install --quiet --no-deps --no-compile --target "${APP}/vendor" \
    "customtkinter>=5.2.0" "darkdetect"
rm -rf "${APP}/vendor/bin"

# Lançador
install -Dm755 /dev/stdin "${BUILD}/usr/bin/${PKG}" <<EOF
#!/bin/sh
exec /usr/bin/python3 /opt/${PKG}/main.py "\$@"
EOF

# Menu, ícone, udev, módulo uinput, licença
install -Dm644 "${ROOT}/packaging/bloodylinux.desktop" "${BUILD}/usr/share/applications/${PKG}.desktop"
install -Dm644 "${ROOT}/packaging/bloodylinux.svg"     "${BUILD}/usr/share/icons/hicolor/scalable/apps/${PKG}.svg"
install -Dm644 "${ROOT}/70-bloodylinux.rules"          "${BUILD}/lib/udev/rules.d/70-bloodylinux.rules"
install -Dm644 /dev/stdin "${BUILD}/usr/lib/modules-load.d/${PKG}.conf" <<< "uinput"
install -Dm644 "${ROOT}/LICENSE" "${BUILD}/usr/share/doc/${PKG}/copyright"

INSTALLED_KB="$(du -sk "${BUILD}" | cut -f1)"

cat > "${BUILD}/DEBIAN/control" <<EOF
Package: ${PKG}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), python3-tk, python3-evdev, python3-usb, python3-packaging, libusb-1.0-0
Installed-Size: ${INSTALLED_KB}
Maintainer: BloodyLinux <noreply@users.noreply.github.com>
Description: Controlador do mouse A4Tech Bloody A91 para Linux
 Interface gráfica com no-recoil (Ultra-Core 3), rajada (Core 2),
 auto-clicker, controle de LEDs e medidor de CPS para mouses
 A4Tech Bloody, usando evdev/uinput.
EOF

cat > "${BUILD}/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    rm -f /etc/udev/rules.d/99-bloody.rules   # regra antiga com permissão 0666
    modprobe uinput 2>/dev/null || true
    if command -v udevadm >/dev/null; then
        udevadm control --reload-rules || true
        udevadm trigger --subsystem-match=misc --subsystem-match=input \
            --subsystem-match=usb --subsystem-match=hidraw || true
    fi
    command -v update-desktop-database >/dev/null && update-desktop-database -q || true
    command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
fi
exit 0
EOF

cat > "${BUILD}/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    command -v udevadm >/dev/null && udevadm control --reload-rules || true
    rm -rf /opt/bloodylinux/src/__pycache__ /opt/bloodylinux/vendor 2>/dev/null || true
fi
exit 0
EOF
chmod 755 "${BUILD}/DEBIAN/postinst" "${BUILD}/DEBIAN/postrm"

DEB="${OUT}/${PKG}_${VERSION}_all.deb"
dpkg-deb --root-owner-group --build "${BUILD}" "${DEB}"
echo "==> Pacote gerado: ${DEB}"
echo "    Instale com: sudo apt install ./$(basename "${DEB}")"
