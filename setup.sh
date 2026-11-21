#!/usr/bin/env bash
set -e

echo "=== Ambiente de DESENVOLVIMENTO BloodyLinux ==="
echo "(Para instalar o app no sistema use: sudo ./install.sh)"

# 1. Criação do Ambiente Virtual Python
if [ ! -d "venv" ]; then
    echo "-> Criando ambiente virtual (venv)..."
    python3 -m venv --system-site-packages venv
else
    echo "-> Ambiente virtual já existe."
fi

# 2. Instalação das dependências
echo "-> Instalando pacotes no venv..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 3. Permissões (udev)
if [ ! -f /etc/udev/rules.d/70-bloodylinux.rules ]; then
    echo ""
    echo "-> Para usar o mouse e o uinput sem root, instale a regra udev:"
    echo "  sudo cp 70-bloodylinux.rules /etc/udev/rules.d/"
    echo "  sudo udevadm control --reload-rules && sudo udevadm trigger"
fi
echo ""
echo "=== Instalação concluída com sucesso! ==="
echo "Você pode abrir o projeto no VS Code e apertar F5 para iniciar!"
