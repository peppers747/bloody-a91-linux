# 🩸 BloodyLinux - Controlador A4Tech Bloody A91 para Linux

Suíte completa em Python para mouses **A4Tech Bloody A91** no Linux, com os mesmos recursos essenciais do software oficial (**Bloody 5 / 6 / 7 / Oscar**):

- 🎯 **Ultra-Core 3 & 4 (No-Recoil / Compensação de Recuo)**: Controle de spray dinâmico vertical (Y) e horizontal (X), delay inicial e presets de armas (CS2, Rust, etc.).
- ⚡ **Core 2 (Burst Fire / Rajada)**: Modos 1 (tiro simples), N (2 tiros rápidos) e 3 (3 tiros rápidos).
- 🖱️ **Auto-Clicker & Drag Click Simulator**: Simulador de cliques ultra rápidos com taxa ajustável (10 a 50+ CPS) e variação milimétrica (jitter).
- 💡 **Controle de Iluminação**: Ajuste de intensidade de luz dos LEDs (desligado, baixo, médio, forte) via USB direto.
- ⏱️ **CPS & Benchmark em Tempo Real**: Medidor interativo de cliques por segundo e latência para testes de butterfly e drag click.
- 🎨 **Interface Gamer Moderna**: Desenvolvida em CustomTkinter com visual esportivo vermelho e preto da Bloody.

---

## 🚀 Como Abrir e Rodar no VS Code

### Passo 1: Abrir a pasta no VS Code
No seu terminal Linux, execute:
```bash
code /home/peppers/.gemini/antigravity/scratch/bloody-linux
```
*(Ou abra o VS Code e vá em **File > Open Folder** e selecione esta pasta).*

---

### Passo 2: Executar o Instalador de Ambiente
Abra o terminal integrado do VS Code (`Ctrl + ~` ou `Terminal > New Terminal`) e execute:
```bash
./setup.sh
```
Esse script cria o ambiente virtual Python (`venv`) e instala todas as dependências (`customtkinter`, `evdev`, `pyusb`, `pillow`).

---

### Passo 3: Configurar as Regras udev (Acesso sem Root)
Para que o software consiga ler o mouse e criar o dispositivo virtual de macros (`/dev/uinput`) **sem você precisar rodar o VS Code como root/sudo**, execute uma única vez no terminal:

```bash
# 1. Copia a regra udev
sudo cp 99-bloody.rules /etc/udev/rules.d/

# 2. Recarrega as regras do sistema
sudo udevadm control --reload-rules && sudo udevadm trigger

# 3. Adiciona seu usuário aos grupos necessários
sudo usermod -aG input $USER
```
*(Após rodar o comando acima, se for a primeira vez que você entra no grupo `input`, encerre a sessão do usuário e entre novamente para o Linux atualizar as permissões).*

---

### Passo 4: Executar no VS Code
Existem duas formas fáceis:
1. **Via Tecla F5**: Pressione **F5** no VS Code. O arquivo `.vscode/launch.json` já está pronto e iniciará o `main.py` diretamente no ambiente virtual!
2. **Via Terminal**:
   ```bash
   ./venv/bin/python main.py
   ```

---

## 🧠 Segredos e Funcionamento do Hardware do Bloody A91

### 1. Debounce Time (0.2 ms) e Memória On-Board (EEPROM)
- O mouse Bloody A91 utiliza switches ópticos **Light Strike (LK)**, que não possuem o rebote mecânico das teclas convencionais.
- O tempo de resposta de **0.2 ms** é gravado **diretamente no chip de memória flash (EEPROM) interno do mouse**.
- **O que isso significa no Linux?** Se você alguma vez configurou o debounce time de 0.2 ms no software da Bloody no Windows (ou via máquina virtual), **ele já está salvo para sempre no hardware do mouse**. Não é necessário ter nenhum software rodando em segundo plano no Linux para desfrutar da velocidade máxima dos cliques!

### 2. Como Mudar o DPI Diretamente no Hardware (Sem Software)
O Bloody A91 possui um recurso de hardware nativo para mudar o DPI:
1. Dê um **duplo clique rápido no botão '1'** (acima da rodinha do mouse).
2. O LED da rodinha de rolagem (scroll wheel) começará a piscar.
3. **Role a rodinha para cima ou para baixo**: cada giro altera o perfil de DPI (indicado pela cor do LED).
4. Dê **um único clique no botão '1'** para salvar o DPI na memória do mouse e sair do modo de ajuste!

---

## 🛠️ Estrutura do Código

```
bloody-linux/
├── .vscode/
│   ├── launch.json       # Configuração para rodar com F5
│   └── settings.json     # Aponta o interpretador do VS Code para o venv
├── src/
│   ├── config.py         # Gerenciamento de perfis e salvamento em JSON
│   ├── hardware_usb.py   # Varredura de portas USB e controle de LEDs via PyUSB
│   ├── input_engine.py   # Motor de interceptação evdev e uinput (No-recoil e burst)
│   └── gui.py            # Interface gráfica gamer (CustomTkinter com fallback Tkinter)
├── main.py               # Ponto de entrada da aplicação
├── requirements.txt      # Dependências Python
├── 99-bloody.rules       # Regras udev para Linux
└── setup.sh              # Script automatizado de instalação
```
