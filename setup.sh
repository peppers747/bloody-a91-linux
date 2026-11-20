#!/usr/bin/env bash
set -e

echo "=== Instalador do Ambiente BloodyLinux ==="

# 1. Criação do Ambiente Virtual Python
if [ ! -d "venv" ]; then
    echo "-> Criando ambiente virtual (venv)..."
    python3 -m venv venv
else
    echo "-> Ambiente virtual já existe."
fi

# 2. Instalação das dependências
echo "-> Instalando pacotes no venv..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 3. Adicionar usuário ao grupo input se necessário
CURRENT_USER=$(whoami)
echo "-> Verificando grupos do usuário $CURRENT_USER..."
if ! groups "$CURRENT_USER" | grep -q "\binput\b"; then
    echo "AVISO: É recomendável adicionar seu usuário ao grupo 'input':"
    echo "  sudo usermod -aG input $CURRENT_USER"
fi

# 4. Configuração das regras udev
echo ""
echo "-> Para permitir acesso direto ao mouse e ao uinput sem precisar rodar como root, instale a regra udev:"
echo "  sudo cp 99-bloody.rules /etc/udev/rules.d/"
echo "  sudo udevadm control --reload-rules && sudo udevadm trigger"
echo ""
echo "=== Instalação concluída com sucesso! ==="
echo "Você pode abrir o projeto no VS Code e apertar F5 para iniciar!"
