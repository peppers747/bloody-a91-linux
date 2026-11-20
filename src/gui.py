import tkinter as tk
from tkinter import ttk, messagebox
import time

try:
    import customtkinter as ctk
    USE_CTK = True
except ImportError:
    USE_CTK = False

class BloodyApp:
    def __init__(self, root, config_manager, hardware_usb, input_engine):
        self.root = root
        self.cfg = config_manager
        self.hw = hardware_usb
        self.engine = input_engine
        
        self.max_cps = 0
        self.click_box_timestamps = []

        if USE_CTK:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("dark-blue")
            self.root.title("Bloody Linux Suite - A4Tech A91 Controller")
            self.root.geometry("820x620")
            self.root.resizable(False, False)
            self._build_ctk_ui()
        else:
            self.root.title("Bloody Linux Suite - A4Tech A91 Controller")
            self.root.geometry("820x620")
            self.root.configure(bg="#121212")
            self._build_tk_ui()

        # Inicia loop de atualização de status na interface
        self._poll_status()

    # -------------------------------------------------------------
    # INTERFACE MODERNA (CustomTkinter)
    # -------------------------------------------------------------
    def _build_ctk_ui(self):
        # Cabeçalho
        header = ctk.CTkFrame(self.root, fg_color="#181818", corner_radius=0, height=70)
        header.pack(fill="x", side="top")

        title = ctk.CTkLabel(
            header, text="BLOODY A91 LINUX",
            font=ctk.CTkFont(family="Arial", size=24, weight="bold"),
            text_color="#ff2a2a"
        )
        title.pack(side="left", padx=20, pady=15)

        self.lbl_device_status = ctk.CTkLabel(
            header, text="Detectando mouse...",
            font=ctk.CTkFont(size=12),
            text_color="#a0a0a0"
        )
        self.lbl_device_status.pack(side="right", padx=20, pady=20)

        # Abas de Navegação
        self.tabview = ctk.CTkTabview(self.root, fg_color="#1e1e1e", segmented_button_selected_color="#b71c1c")
        self.tabview.pack(fill="both", expand=True, padx=15, pady=10)

        self.tab_core = self.tabview.add("🎯 Ultra Core / Recoil")
        self.tab_macro = self.tabview.add("⚡ Macros & Auto-Click")
        self.tab_hw = self.tabview.add("💡 Iluminação & Hardware")
        self.tab_bench = self.tabview.add("⏱️ CPS & Benchmark")

        self._build_core_tab_ctk()
        self._build_macro_tab_ctk()
        self._build_hardware_tab_ctk()
        self._build_bench_tab_ctk()

        # Barra de rodapé com botão Iniciar / Parar Engine
        footer = ctk.CTkFrame(self.root, fg_color="#141414", corner_radius=0, height=50)
        footer.pack(fill="x", side="bottom")

        self.btn_engine_toggle = ctk.CTkButton(
            footer, text="▶ ATIVAR ENGINE (uinput)",
            fg_color="#b71c1c", hover_color="#d32f2f",
            font=ctk.CTkFont(weight="bold"),
            command=self._toggle_engine
        )
        self.btn_engine_toggle.pack(side="left", padx=20, pady=10)

        self.lbl_engine_msg = ctk.CTkLabel(
            footer, text="Status: Parado",
            text_color="#888888", font=ctk.CTkFont(size=11)
        )
        self.lbl_engine_msg.pack(side="left", padx=10)

    def _build_core_tab_ctk(self):
        tab = self.tab_core

        # Seletor de Core (Core 1, Core 2, Core 3)
        lbl_mode = ctk.CTkLabel(tab, text="Selecione o Sistema Core:", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_mode.pack(anchor="w", padx=20, pady=(10, 5))

        self.var_core = tk.IntVar(value=self.cfg.get("core_mode", 3))
        mode_frame = ctk.CTkFrame(tab, fg_color="transparent")
        mode_frame.pack(fill="x", padx=20, pady=5)

        for mode_num, mode_name, desc in [
            (1, "Core 1 (Padrão)", "Ideal para MMO / Uso normal (Sem recoil ou burst)"),
            (2, "Core 2 (Burst Fire)", "Botões 1, N, 3 disparam 1, 2 ou 3 tiros rápidos"),
            (3, "Ultra-Core 3 (No-Recoil)", "Compensação de recuo vertical e horizontal ativa")
        ]:
            rb = ctk.CTkRadioButton(
                mode_frame, text=f"{mode_name} - {desc}",
                variable=self.var_core, value=mode_num,
                command=self._on_core_change,
                fg_color="#b71c1c"
            )
            rb.pack(anchor="w", pady=4)

        # Configurações de Compensação de Recuo
        recoil_frame = ctk.CTkFrame(tab, fg_color="#252525")
        recoil_frame.pack(fill="both", expand=True, padx=20, pady=15)

        recoil_header = ctk.CTkLabel(recoil_frame, text="Ajuste Fino de No-Recoil (Ultra-Core 3)", font=ctk.CTkFont(size=13, weight="bold"))
        recoil_header.pack(anchor="w", padx=15, pady=(10, 5))

        # Preset selector
        preset_row = ctk.CTkFrame(recoil_frame, fg_color="transparent")
        preset_row.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(preset_row, text="Preset de Arma:").pack(side="left")
        
        presets = list(self.cfg.get("presets", {}).keys())
        self.combo_presets = ctk.CTkComboBox(
            preset_row, values=presets,
            command=self._on_select_preset
        )
        self.combo_presets.set(self.cfg.get("recoil", {}).get("active_preset", "Padrão"))
        self.combo_presets.pack(side="left", padx=10)

        # Sliders de controle
        r_cfg = self.cfg.get("recoil", {})
        self.slider_y = self._create_slider_row(recoil_frame, "Puxar para Baixo (Y):", 0, 25, r_cfg.get("pull_y", 6))
        self.slider_x = self._create_slider_row(recoil_frame, "Correção Lateral (X):", -10, 10, r_cfg.get("pull_x", 0))
        self.slider_delay = self._create_slider_row(recoil_frame, "Intervalo de Correção (ms):", 10, 60, r_cfg.get("delay_ms", 25))
        self.slider_start = self._create_slider_row(recoil_frame, "Atraso do 1º Disparo (ms):", 0, 300, r_cfg.get("start_delay_ms", 120))

    def _create_slider_row(self, parent, label_text, from_val, to_val, current_val):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=4)
        
        lbl = ctk.CTkLabel(row, text=label_text, width=170, anchor="w")
        lbl.pack(side="left")

        val_label = ctk.CTkLabel(row, text=str(int(current_val)), width=40)
        
        def on_slide(v):
            val_label.configure(text=str(int(v)))
            self._save_recoil_sliders()

        slider = ctk.CTkSlider(
            row, from_=from_val, to=to_val,
            number_of_steps=to_val - from_val,
            command=on_slide,
            button_color="#b71c1c", progress_color="#d32f2f"
        )
        slider.set(current_val)
        slider.pack(side="left", fill="x", expand=True, padx=10)
        val_label.pack(side="left")
        return slider

    def _build_macro_tab_ctk(self):
        tab = self.tab_macro

        # Auto-Clicker
        ac_frame = ctk.CTkFrame(tab, fg_color="#252525")
        ac_frame.pack(fill="x", padx=20, pady=15)

        ac_title = ctk.CTkLabel(ac_frame, text="⚡ Auto-Clicker / Butterfly & Drag Click Simulator", font=ctk.CTkFont(size=14, weight="bold"))
        ac_title.pack(anchor="w", padx=15, pady=(10, 5))

        self.switch_ac = ctk.CTkSwitch(
            ac_frame, text="Ativar Auto-Clicker Contínuo",
            command=self._on_toggle_autoclicker,
            progress_color="#b71c1c"
        )
        self.switch_ac.pack(anchor="w", padx=15, pady=5)

        ac_cfg = self.cfg.get("autoclicker", {})
        self.slider_cps = self._create_slider_row(ac_frame, "Taxa de CPS Desejada:", 5, 50, ac_cfg.get("cps", 20))

        # Burst Settings
        burst_frame = ctk.CTkFrame(tab, fg_color="#252525")
        burst_frame.pack(fill="x", padx=20, pady=10)

        burst_title = ctk.CTkLabel(burst_frame, text="Configuração de Rajada (Core 2)", font=ctk.CTkFont(size=14, weight="bold"))
        burst_title.pack(anchor="w", padx=15, pady=(10, 5))

        b_cfg = self.cfg.get("burst", {})
        self.slider_burst_n = self._create_slider_row(burst_frame, "Tiros no Botão N:", 2, 5, b_cfg.get("mode_n_shots", 2))
        self.slider_burst_3 = self._create_slider_row(burst_frame, "Tiros no Botão 3:", 3, 7, b_cfg.get("mode_3_shots", 3))

    def _build_hardware_tab_ctk(self):
        tab = self.tab_hw

        # Controle de Iluminação
        led_frame = ctk.CTkFrame(tab, fg_color="#252525")
        led_frame.pack(fill="x", padx=20, pady=15)

        lbl_led = ctk.CTkLabel(led_frame, text="Controle de Iluminação (Logo e Scroll LED)", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_led.pack(anchor="w", padx=15, pady=(10, 5))

        btn_row = ctk.CTkFrame(led_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=10)

        for lvl, name in [(0, "Desligado"), (1, "Baixo"), (2, "Médio"), (3, "Máximo")]:
            btn = ctk.CTkButton(
                btn_row, text=name, width=80,
                command=lambda l=lvl: self._set_led_level(l),
                fg_color="#333333", hover_color="#b71c1c"
            )
            btn.pack(side="left", padx=5)

        # Informações de Hardware & Segredo do A91
        info_frame = ctk.CTkFrame(tab, fg_color="#1b1b1b")
        info_frame.pack(fill="both", expand=True, padx=20, pady=10)

        info_title = ctk.CTkLabel(info_frame, text="ℹ️ Segredos de Hardware do Bloody A91 no Linux:", font=ctk.CTkFont(weight="bold"))
        info_title.pack(anchor="w", padx=15, pady=(10, 5))

        dicas = (
            "1. Debounce Time (0.2 ms):\n"
            "   Os switches LK ópticos da Bloody gravam o tempo de resposta diretamente na EEPROM\n"
            "   do mouse. Se configurado uma vez no software original, ele permanece salvo para sempre,\n"
            "   mesmo no Linux, sem precisar do software oficial aberto!\n\n"
            "2. Como Mudar o DPI Diretamente no Hardware (Sem Software):\n"
            "   - Dê um duplo-clique rápido no botão '1' do mouse.\n"
            "   - A luz da rodinha de rolagem (scroll) começará a piscar.\n"
            "   - Role o scroll para cima ou para baixo para alternar os estágios de DPI.\n"
            "   - Clique no botão '1' uma vez para confirmar e salvar o DPI na memória interna!\n\n"
            "3. Permissões no Linux:\n"
            "   Para que o software acesse o uinput e controle os LEDs sem sudo, copie a regra:\n"
            "   sudo cp 99-bloody.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules"
        )
        ctk.CTkLabel(info_frame, text=dicas, justify="left", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=15, pady=5)

    def _build_bench_tab_ctk(self):
        tab = self.tab_bench

        box_frame = ctk.CTkFrame(tab, fg_color="#252525")
        box_frame.pack(fill="both", expand=True, padx=20, pady=20)

        lbl = ctk.CTkLabel(box_frame, text="Área de Teste de CPS (Clique com o Mouse Aqui)", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(pady=10)

        # Caixa interativa de clique
        self.click_target = ctk.CTkButton(
            box_frame, text="CLIQUE AQUI RAPIDAMENTE\n(Butterfly / Drag / Normal)",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=160, fg_color="#2b2b2b", hover_color="#3d3d3d",
            command=self._on_bench_click
        )
        self.click_target.pack(fill="x", padx=30, pady=10)

        # Medidores
        stats_row = ctk.CTkFrame(box_frame, fg_color="transparent")
        stats_row.pack(fill="x", padx=30, pady=10)

        self.lbl_cps_val = ctk.CTkLabel(stats_row, text="CPS Atual: 0", font=ctk.CTkFont(size=20, weight="bold"), text_color="#ff2a2a")
        self.lbl_cps_val.pack(side="left", padx=20)

        self.lbl_max_cps = ctk.CTkLabel(stats_row, text="CPS Recorde: 0", font=ctk.CTkFont(size=16), text_color="#aaaaaa")
        self.lbl_max_cps.pack(side="left", padx=20)

        btn_reset = ctk.CTkButton(stats_row, text="Zerar Recorde", width=100, command=self._reset_bench, fg_color="#444444")
        btn_reset.pack(side="right", padx=10)

    # -------------------------------------------------------------
    # INTERFACE DE FALLBACK (Tkinter Standard)
    # -------------------------------------------------------------
    def _build_tk_ui(self):
        # Header básico
        header = tk.Frame(self.root, bg="#181818", height=60)
        header.pack(fill="x", side="top")
        tk.Label(header, text="BLOODY A91 LINUX", fg="#ff2a2a", bg="#181818", font=("Arial", 18, "bold")).pack(side="left", padx=20, pady=15)
        self.lbl_device_status = tk.Label(header, text="Detectando...", fg="#888888", bg="#181818")
        self.lbl_device_status.pack(side="right", padx=20)

        content = tk.Frame(self.root, bg="#121212")
        content.pack(fill="both", expand=True, padx=15, pady=15)

        tk.Label(content, text="Aviso: 'customtkinter' não encontrado. Interface em modo de compatibilidade.", fg="#ffbb00", bg="#121212").pack(pady=10)
        tk.Label(content, text="Execute no terminal: ./setup.sh para ativar a interface completa com tema gamer.", fg="#cccccc", bg="#121212").pack(pady=5)

        self.btn_engine_toggle = tk.Button(content, text="ATIVAR ENGINE", bg="#b71c1c", fg="white", font=("Arial", 12, "bold"), command=self._toggle_engine)
        self.btn_engine_toggle.pack(pady=20)

        self.lbl_engine_msg = tk.Label(content, text="Status: Parado", fg="#888888", bg="#121212")
        self.lbl_engine_msg.pack(pady=5)

    # -------------------------------------------------------------
    # AÇÕES E EVENTOS
    # -------------------------------------------------------------
    def _poll_status(self):
        # Atualiza status do dispositivo apenas se ainda não detectado ou a cada 10s
        if not hasattr(self, "_last_scan_time") or time.time() - self._last_scan_time > 10.0:
            self._last_scan_time = time.time()
            ok, msg = self.hw.scan_device()
            if ok:
                self.lbl_device_status.configure(text=f"Conectado: {self.hw.device_name}", text_color="#4caf50" if USE_CTK else "green")
            else:
                self.lbl_device_status.configure(text="Mouse desconectado", text_color="#f44336" if USE_CTK else "red")

        # Atualiza CPS de clique na aba de benchmark
        now = time.time()
        self.click_box_timestamps = [t for t in self.click_box_timestamps if now - t <= 1.0]
        cur_cps = len(self.click_box_timestamps)
        if hasattr(self, "lbl_cps_val"):
            self.lbl_cps_val.configure(text=f"CPS Atual: {cur_cps}")

        self.root.after(200, self._poll_status)

    def _toggle_engine(self):
        if not self.engine.running:
            ok, msg = self.engine.start()
            if ok:
                self.btn_engine_toggle.configure(text="⏹ PARAR ENGINE", fg_color="#333333" if USE_CTK else "#555")
                self.lbl_engine_msg.configure(text=f"Status: Ativo ({msg})", text_color="#4caf50" if USE_CTK else "green")
            else:
                messagebox.showerror("Erro ao Iniciar", msg)
        else:
            self.engine.stop()
            self.btn_engine_toggle.configure(text="▶ ATIVAR ENGINE (uinput)", fg_color="#b71c1c" if USE_CTK else "#b71c1c")
            self.lbl_engine_msg.configure(text="Status: Parado", text_color="#888888" if USE_CTK else "#888")

    def _on_core_change(self):
        val = self.var_core.get()
        self.cfg.set("core_mode", val)

    def _on_select_preset(self, preset_name):
        presets = self.cfg.get("presets", {})
        if preset_name in presets:
            p = presets[preset_name]
            self.slider_y.set(p["pull_y"])
            self.slider_x.set(p["pull_x"])
            self.slider_delay.set(p["delay_ms"])
            self.slider_start.set(p["start_delay_ms"])
            self._save_recoil_sliders()

    def _save_recoil_sliders(self):
        recoil = self.cfg.get("recoil", {})
        recoil["pull_y"] = int(self.slider_y.get())
        recoil["pull_x"] = int(self.slider_x.get())
        recoil["delay_ms"] = int(self.slider_delay.get())
        recoil["start_delay_ms"] = int(self.slider_start.get())
        self.cfg.set("recoil", recoil)

    def _on_toggle_autoclicker(self):
        active = self.switch_ac.get() == 1
        if active:
            cps = int(self.slider_cps.get())
            self.engine.start_autoclicker(cps=cps)
        else:
            self.engine.stop_autoclicker()

    def _set_led_level(self, level):
        ok, msg = self.hw.set_backlight_level(level)
        if ok:
            messagebox.showinfo("Iluminação", msg)
        else:
            messagebox.showwarning("Aviso", msg)

    def _on_bench_click(self):
        self.click_box_timestamps.append(time.time())
        now = time.time()
        self.click_box_timestamps = [t for t in self.click_box_timestamps if now - t <= 1.0]
        cur = len(self.click_box_timestamps)
        if cur > self.max_cps:
            self.max_cps = cur
            if hasattr(self, "lbl_max_cps"):
                self.lbl_max_cps.configure(text=f"CPS Recorde: {self.max_cps}")

    def _reset_bench(self):
        self.max_cps = 0
        self.click_box_timestamps.clear()
        if hasattr(self, "lbl_max_cps"):
            self.lbl_max_cps.configure(text="CPS Recorde: 0")
