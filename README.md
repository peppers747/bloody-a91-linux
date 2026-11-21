# 🩸 BloodyLinux - Controlador A4Tech Bloody A91 para Linux

Suíte em Python para mouses **A4Tech Bloody A91** no Linux, com os recursos essenciais do software oficial (**Bloody 5 / 6 / 7**):

- 🎯 **Ultra-Core 3 (No-Recoil)**: compensação vertical (Y) e horizontal (X), atraso do primeiro disparo e presets de armas editáveis.
- ⚡ **Core 2 (Burst Fire)**: modos 1 (tiro simples), N e 3, com número de tiros e intervalo ajustáveis.
- 🖱️ **Auto-Clicker**: segure um botão gatilho (lateral ou do meio) para clicar de 5 a 50 CPS, com jitter opcional.
- 💡 **Iluminação (experimental)**: intensidade dos LEDs via USB.
- ⏱️ **Medidor de CPS** para testes de butterfly / drag click.

---

## 📦 Instalação

### Opção 1 — Pacote `.deb` (Ubuntu, Debian, Mint, Pop!_OS)
Baixe o `bloodylinux_<versão>_all.deb` na página de **Releases** (ou nos artefatos da aba **Actions**) e rode:
```bash
sudo apt install ./bloodylinux_*_all.deb
```

### Opção 2 — Instalador universal (qualquer distro)
Funciona em Debian/Ubuntu, Fedora, Arch/Manjaro e openSUSE:
```bash
tar xzf bloodylinux-*.tar.gz      # ou clone o repositório
cd bloodylinux-*
sudo ./install.sh
```
O instalador:
1. instala as dependências do sistema (Python, Tk, evdev, pyusb, libusb);
2. copia o app para `/opt/bloodylinux` e cria um ambiente Python isolado;
3. cria o comando `bloodylinux` e o atalho no menu de aplicativos;
4. instala as regras udev e ativa o módulo `uinput` (sem precisar de sudo para usar o app).

Depois é só abrir **BloodyLinux** no menu. Se o mouse já estava conectado durante a instalação, desconecte e reconecte uma vez.

**Desinstalar:** `sudo /opt/bloodylinux/uninstall.sh` (adicione `--purge` para apagar também suas configurações), ou `sudo apt remove bloodylinux` no caso do `.deb`.

As configurações ficam em `~/.config/bloodylinux/config.json`.

---

## 🧑‍💻 Desenvolvimento (VS Code)

```bash
./setup.sh                      # cria o venv/ com as dependências
sudo cp 70-bloodylinux.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
./venv/bin/python main.py       # ou F5 no VS Code
```

### Gerar os pacotes
- **Local:** `bash packaging/build-deb.sh` → `dist/bloodylinux_<versão>_all.deb` (precisa de `dpkg-deb`).
- **GitHub Actions:** todo push em `main` gera o `.deb` e o `.tar.gz` como artefatos do workflow **Build**. Ao criar uma tag `v*` (ex.: `git tag v1.1.0 && git push --tags`), eles são publicados automaticamente em uma Release.

A versão fica em [src/__init__.py](src/__init__.py).

---

## 🔐 Permissões

O arquivo [70-bloodylinux.rules](70-bloodylinux.rules) libera `/dev/uinput` e o mouse para o **usuário logado na sessão** (`TAG+="uaccess"`) e para o grupo `input`, com modo `0660`. O prefixo `70-` é necessário: a tag `uaccess` só tem efeito se for aplicada antes do `73-seat-late.rules` do systemd.

Em sistemas sem systemd-logind, adicione seu usuário ao grupo `input` (`sudo usermod -aG input $USER`) e reinicie a sessão.

---

## 🧠 Dicas de Hardware do Bloody A91

### Debounce Time (0.2 ms)
Os switches ópticos **Light Strike (LK)** gravam o tempo de resposta na memória interna do mouse. Se você já configurou 0.2 ms no software oficial do Windows, ele continua valendo no Linux sem nenhum software rodando.

### Mudar o DPI direto no hardware
1. Dê um **duplo clique rápido no botão '1'** (acima da rodinha).
2. O LED da rodinha começa a piscar.
3. **Role a rodinha** para alternar o perfil de DPI (indicado pela cor).
4. **Clique uma vez no botão '1'** para salvar e sair.

---

## 🛠️ Estrutura

```
├── src/
│   ├── config.py           # Configurações (~/.config/bloodylinux), merge e salvamento
│   ├── hardware_usb.py     # Detecção USB e controle de LEDs (PyUSB)
│   ├── input_engine.py     # Captura evdev + mouse virtual uinput (recoil, rajada, auto-click)
│   └── gui.py              # Interface CustomTkinter (com fallback em Tk puro)
├── main.py                 # Ponto de entrada
├── install.sh / uninstall.sh
├── 70-bloodylinux.rules    # Regras udev
├── packaging/              # build-deb.sh, ícone e atalho .desktop
├── setup.sh                # Ambiente de desenvolvimento
└── .github/workflows/      # Build automático do .deb e .tar.gz
```
