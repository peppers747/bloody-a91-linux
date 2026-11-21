import time
import tkinter as tk
from tkinter import messagebox

from src import __version__
from src.input_engine import AUTOCLICK_TRIGGERS

try:
    import customtkinter as ctk
    USE_CTK = True
except ImportError:
    USE_CTK = False

RED = "#b71c1c"
RED_HOVER = "#d32f2f"
GREEN = "#4caf50"
ERROR = "#f44336"
MUTED = "#888888"

BURST_MODES = {"1 (tiro simples)": 1, "N": 2, "3": 3}


class BloodyApp:
    def __init__(self, root, config_manager, hardware_usb, input_engine):
        self.root = root
        self.cfg = config_manager
        self.hw = hardware_usb
        self.engine = input_engine

        self.max_cps = 0
        self.click_box_timestamps = []
        self._last_scan_time = 0.0
        self._engine_was_running = False

        title = f"Bloody Linux Suite {__version__} - A4Tech A91 Controller"
        self.root.title(title)
        self.root.geometry("860x680")
        self.root.minsize(760, 600)

        if USE_CTK:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("dark-blue")
            self._build_ctk_ui()
        else:
            self.root.configure(bg="#121212")
            self._build_tk_ui()

        self._poll_status()

    # -------------------------------------------------------------
    # Utilitários
    # -------------------------------------------------------------
    @staticmethod
    def _set_label(label, text, color=None):
        """Atualiza um rótulo funcionando tanto em CustomTkinter quanto em Tk puro."""
        if color is None:
            label.configure(text=text)
        elif USE_CTK:
            label.configure(text=text, text_color=color)
        else:
            label.configure(text=text, fg=color)

    def _set_engine_button(self, running):
        if running:
            text, color = "⏹ PARAR ENGINE", "#333333"
        else:
            text, color = "▶ ATIVAR ENGINE (uinput)", RED
        if USE_CTK:
            self.btn_engine_toggle.configure(text=text, fg_color=color)
        else:
            self.btn_engine_toggle.configure(text=text, bg=color)

    # -------------------------------------------------------------
    # INTERFACE MODERNA (CustomTkinter)
    # -------------------------------------------------------------
    def _build_ctk_ui(self):
        header = ctk.CTkFrame(self.root, fg_color="#181818", corner_radius=0, height=70)
        header.pack(fill="x", side="top")

        ctk.CTkLabel(
            header, text="BLOODY A91 LINUX",
            font=ctk.CTkFont(family="Arial", size=24, weight="bold"),
            text_color="#ff2a2a"
        ).pack(side="left", padx=20, pady=15)

        self.lbl_device_status = ctk.CTkLabel(
            header, text="Detectando mouse...", font=ctk.CTkFont(size=12), text_color="#a0a0a0"
        )
        self.lbl_device_status.pack(side="right", padx=20, pady=20)

        # Rodapé antes das abas para não ser empurrado para fora da janela
        footer = ctk.CTkFrame(self.root, fg_color="#141414", corner_radius=0, height=50)
        footer.pack(fill="x", side="bottom")

        self.btn_engine_toggle = ctk.CTkButton(
            footer, text="", fg_color=RED, hover_color=RED_HOVER,
            font=ctk.CTkFont(weight="bold"), command=self._toggle_engine
        )
        self.btn_engine_toggle.pack(side="left", padx=20, pady=10)
        self._set_engine_button(False)

        self.lbl_engine_msg = ctk.CTkLabel(
            footer, text="Status: Parado", text_color=MUTED, font=ctk.CTkFont(size=11)
        )
        self.lbl_engine_msg.pack(side="left", padx=10)

        self.tabview = ctk.CTkTabview(self.root, fg_color="#1e1e1e", segmented_button_selected_color=RED)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=10)

        self.tab_core = self.tabview.add("🎯 Ultra Core / Recoil")
        self.tab_macro = self.tabview.add("⚡ Rajada & Auto-Click")
        self.tab_hw = self.tabview.add("💡 Iluminação & Hardware")
        self.tab_bench = self.tabview.add("⏱️ CPS & Benchmark")

        self._build_core_tab_ctk()
        self._build_macro_tab_ctk()
        self._build_hardware_tab_ctk()
        self._build_bench_tab_ctk()

    def _create_slider_row(self, parent, label_text, from_val, to_val, current_val, on_change):
        """Linha com rótulo + slider + valor. 'on_change(int)' é chamado ao mover."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=4)

        ctk.CTkLabel(row, text=label_text, width=190, anchor="w").pack(side="left")
        val_label = ctk.CTkLabel(row, text=str(int(current_val)), width=40)

        def on_slide(v):
            val_label.configure(text=str(int(round(v))))
            on_change(int(round(v)))

        slider = ctk.CTkSlider(
            row, from_=from_val, to=to_val, number_of_steps=to_val - from_val,
            command=on_slide, button_color=RED, progress_color=RED_HOVER
        )
        slider.set(current_val)
        slider.pack(side="left", fill="x", expand=True, padx=10)
        val_label.pack(side="left")

        def set_value(v):
            slider.set(v)
            val_label.configure(text=str(int(v)))
        slider.set_value = set_value  # atualiza slider + rótulo sem disparar callback
        return slider

    def _build_core_tab_ctk(self):
        tab = self.tab_core

        ctk.CTkLabel(tab, text="Selecione o Sistema Core:",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(10, 5))

        self.var_core = tk.IntVar(value=self.cfg.get("core_mode", 3))
        mode_frame = ctk.CTkFrame(tab, fg_color="transparent")
        mode_frame.pack(fill="x", padx=20, pady=5)

        for mode_num, mode_name, desc in [
            (1, "Core 1 (Padrão)", "Uso normal, sem recoil ou rajada"),
            (2, "Core 2 (Burst Fire)", "Cada clique dispara 1, N ou 3 tiros (aba Rajada)"),
            (3, "Ultra-Core 3 (No-Recoil)", "Compensação de recuo vertical e horizontal"),
        ]:
            ctk.CTkRadioButton(
                mode_frame, text=f"{mode_name} - {desc}",
                variable=self.var_core, value=mode_num,
                command=self._on_core_change, fg_color=RED
            ).pack(anchor="w", pady=4)

        recoil_frame = ctk.CTkFrame(tab, fg_color="#252525")
        recoil_frame.pack(fill="both", expand=True, padx=20, pady=15)

        top = ctk.CTkFrame(recoil_frame, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkLabel(top, text="Ajuste Fino de No-Recoil (Ultra-Core 3)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        r_cfg = self.cfg.get("recoil", {})
        self.switch_recoil = ctk.CTkSwitch(top, text="Ativo", command=self._on_toggle_recoil,
                                           progress_color=RED)
        if r_cfg.get("enabled", True):
            self.switch_recoil.select()
        self.switch_recoil.pack(side="right")

        preset_row = ctk.CTkFrame(recoil_frame, fg_color="transparent")
        preset_row.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(preset_row, text="Preset de Arma:").pack(side="left")

        self.combo_presets = ctk.CTkComboBox(
            preset_row, values=list(self.cfg.get("presets", {}).keys()),
            command=self._on_select_preset
        )
        self.combo_presets.set(r_cfg.get("active_preset", "Padrão"))
        self.combo_presets.pack(side="left", padx=10)

        ctk.CTkButton(preset_row, text="Salvar no preset", width=130, fg_color="#444444",
                      command=self._save_current_as_preset).pack(side="left", padx=5)

        def recoil_setter(key):
            return lambda v: self.cfg.update_section("recoil", **{key: v})

        self.slider_y = self._create_slider_row(recoil_frame, "Puxar para Baixo (Y):", 0, 25,
                                                r_cfg.get("pull_y", 6), recoil_setter("pull_y"))
        self.slider_x = self._create_slider_row(recoil_frame, "Correção Lateral (X):", -10, 10,
                                                r_cfg.get("pull_x", 0), recoil_setter("pull_x"))
        self.slider_delay = self._create_slider_row(recoil_frame, "Intervalo de Correção (ms):", 5, 60,
                                                    r_cfg.get("delay_ms", 25), recoil_setter("delay_ms"))
        self.slider_start = self._create_slider_row(recoil_frame, "Atraso do 1º Disparo (ms):", 0, 300,
                                                    r_cfg.get("start_delay_ms", 120), recoil_setter("start_delay_ms"))

    def _build_macro_tab_ctk(self):
        tab = self.tab_macro
        ac_cfg = self.cfg.get("autoclicker", {})
        b_cfg = self.cfg.get("burst", {})

        # ---- Rajada (Core 2)
        burst_frame = ctk.CTkFrame(tab, fg_color="#252525")
        burst_frame.pack(fill="x", padx=20, pady=(15, 10))

        ctk.CTkLabel(burst_frame, text="Configuração de Rajada (Core 2)",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))

        mode_row = ctk.CTkFrame(burst_frame, fg_color="transparent")
        mode_row.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(mode_row, text="Modo ativo:", width=190, anchor="w").pack(side="left")
        self.seg_burst = ctk.CTkSegmentedButton(
            mode_row, values=list(BURST_MODES.keys()), command=self._on_burst_mode,
            selected_color=RED, selected_hover_color=RED_HOVER
        )
        current_mode = b_cfg.get("active_mode", 1)
        self.seg_burst.set(next(k for k, v in BURST_MODES.items() if v == current_mode)
                           if current_mode in BURST_MODES.values() else "1 (tiro simples)")
        self.seg_burst.pack(side="left", padx=10)

        def burst_setter(key):
            return lambda v: self.cfg.update_section("burst", **{key: v})

        self._create_slider_row(burst_frame, "Tiros no modo N:", 2, 5,
                                b_cfg.get("mode_n_shots", 2), burst_setter("mode_n_shots"))
        self._create_slider_row(burst_frame, "Tiros no modo 3:", 3, 7,
                                b_cfg.get("mode_3_shots", 3), burst_setter("mode_3_shots"))
        self._create_slider_row(burst_frame, "Intervalo entre tiros (ms):", 10, 150,
                                b_cfg.get("shot_interval_ms", 40), burst_setter("shot_interval_ms"))
        ctk.CTkLabel(burst_frame, text="").pack(pady=1)

        # ---- Auto-clicker
        ac_frame = ctk.CTkFrame(tab, fg_color="#252525")
        ac_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(ac_frame, text="⚡ Auto-Clicker (segure o botão gatilho para clicar)",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))

        sw_row = ctk.CTkFrame(ac_frame, fg_color="transparent")
        sw_row.pack(fill="x", padx=15, pady=4)
        self.switch_ac = ctk.CTkSwitch(sw_row, text="Ativar Auto-Clicker",
                                       command=self._on_toggle_autoclicker, progress_color=RED)
        if ac_cfg.get("enabled", False):
            self.switch_ac.select()
        self.switch_ac.pack(side="left")

        self.switch_jitter = ctk.CTkSwitch(sw_row, text="Variação aleatória (jitter)",
                                           command=self._on_toggle_jitter, progress_color=RED)
        if ac_cfg.get("randomize_jitter", True):
            self.switch_jitter.select()
        self.switch_jitter.pack(side="left", padx=25)

        trig_row = ctk.CTkFrame(ac_frame, fg_color="transparent")
        trig_row.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(trig_row, text="Botão gatilho:", width=190, anchor="w").pack(side="left")
        self._trigger_labels = {label: code for code, label in AUTOCLICK_TRIGGERS.items()}
        self.combo_trigger = ctk.CTkComboBox(
            trig_row, values=list(self._trigger_labels.keys()), width=220,
            command=self._on_select_trigger, state="readonly"
        )
        self.combo_trigger.set(AUTOCLICK_TRIGGERS.get(ac_cfg.get("trigger", "BTN_SIDE"),
                                                      AUTOCLICK_TRIGGERS["BTN_SIDE"]))
        self.combo_trigger.pack(side="left", padx=10)

        self._create_slider_row(ac_frame, "Cliques por segundo (CPS):", 5, 50, ac_cfg.get("cps", 18),
                                lambda v: self.cfg.update_section("autoclicker", cps=v))
        ctk.CTkLabel(ac_frame, text="Requer a engine ativa. O botão gatilho deixa de ter sua função normal "
                                    "enquanto o auto-clicker estiver ligado.",
                     text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=15, pady=(0, 10))

    def _build_hardware_tab_ctk(self):
        tab = self.tab_hw

        led_frame = ctk.CTkFrame(tab, fg_color="#252525")
        led_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(led_frame, text="Controle de Iluminação (experimental)",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))

        btn_row = ctk.CTkFrame(led_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=10)
        for lvl, name in [(0, "Desligado"), (1, "Baixo"), (2, "Médio"), (3, "Máximo")]:
            ctk.CTkButton(
                btn_row, text=name, width=80, command=lambda l=lvl: self._set_led_level(l),
                fg_color="#333333", hover_color=RED
            ).pack(side="left", padx=5)

        info_frame = ctk.CTkFrame(tab, fg_color="#1b1b1b")
        info_frame.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(info_frame, text="ℹ️ Dicas de Hardware do Bloody A91 no Linux:",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))

        dicas = (
            "1. Debounce Time (0.2 ms):\n"
            "   Os switches ópticos LK gravam o tempo de resposta na memória interna do mouse.\n"
            "   Se configurado uma vez no software oficial, permanece salvo também no Linux.\n\n"
            "2. Como mudar o DPI direto no hardware:\n"
            "   - Dê um duplo-clique rápido no botão '1' do mouse.\n"
            "   - A luz da rodinha começará a piscar.\n"
            "   - Role a rodinha para alternar os estágios de DPI.\n"
            "   - Clique no botão '1' uma vez para confirmar e salvar.\n\n"
            "3. Permissões no Linux:\n"
            "   O instalador (sudo ./install.sh) ou o pacote .deb instalam as regras udev\n"
            "   necessárias para usar o uinput e os LEDs sem sudo."
        )
        ctk.CTkLabel(info_frame, text=dicas, justify="left",
                     font=ctk.CTkFont(size=12)).pack(anchor="w", padx=15, pady=5)

        ctk.CTkLabel(info_frame, text=f"Configuração salva em: {self.cfg.filepath}",
                     text_color=MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=15, pady=(5, 10))

    def _build_bench_tab_ctk(self):
        tab = self.tab_bench

        box_frame = ctk.CTkFrame(tab, fg_color="#252525")
        box_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(box_frame, text="Área de Teste de CPS (Clique com o Mouse Aqui)",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)

        self.click_target = ctk.CTkButton(
            box_frame, text="CLIQUE AQUI RAPIDAMENTE\n(Butterfly / Drag / Normal)",
            font=ctk.CTkFont(size=16, weight="bold"), height=160,
            fg_color="#2b2b2b", hover_color="#3d3d3d", command=self._on_bench_click
        )
        self.click_target.pack(fill="x", padx=30, pady=10)

        stats_row = ctk.CTkFrame(box_frame, fg_color="transparent")
        stats_row.pack(fill="x", padx=30, pady=10)

        self.lbl_cps_val = ctk.CTkLabel(stats_row, text="CPS Atual: 0",
                                        font=ctk.CTkFont(size=20, weight="bold"), text_color="#ff2a2a")
        self.lbl_cps_val.pack(side="left", padx=20)

        self.lbl_max_cps = ctk.CTkLabel(stats_row, text="CPS Recorde: 0",
                                        font=ctk.CTkFont(size=16), text_color="#aaaaaa")
        self.lbl_max_cps.pack(side="left", padx=20)

        ctk.CTkButton(stats_row, text="Zerar Recorde", width=100, command=self._reset_bench,
                      fg_color="#444444").pack(side="right", padx=10)

    # -------------------------------------------------------------
    # INTERFACE DE FALLBACK (Tkinter puro)
    # -------------------------------------------------------------
    def _build_tk_ui(self):
        header = tk.Frame(self.root, bg="#181818", height=60)
        header.pack(fill="x", side="top")
        tk.Label(header, text="BLOODY A91 LINUX", fg="#ff2a2a", bg="#181818",
                 font=("Arial", 18, "bold")).pack(side="left", padx=20, pady=15)
        self.lbl_device_status = tk.Label(header, text="Detectando...", fg=MUTED, bg="#181818")
        self.lbl_device_status.pack(side="right", padx=20)

        content = tk.Frame(self.root, bg="#121212")
        content.pack(fill="both", expand=True, padx=15, pady=15)

        tk.Label(content, text="Aviso: 'customtkinter' não encontrado. Interface em modo de compatibilidade.",
                 fg="#ffbb00", bg="#121212").pack(pady=10)
        tk.Label(content, text="Reinstale com ./install.sh para ativar a interface completa.",
                 fg="#cccccc", bg="#121212").pack(pady=5)

        self.btn_engine_toggle = tk.Button(content, text="", bg=RED, fg="white",
                                           font=("Arial", 12, "bold"), command=self._toggle_engine)
        self.btn_engine_toggle.pack(pady=20)
        self._set_engine_button(False)

        self.lbl_engine_msg = tk.Label(content, text="Status: Parado", fg=MUTED, bg="#121212")
        self.lbl_engine_msg.pack(pady=5)

    # -------------------------------------------------------------
    # AÇÕES E EVENTOS
    # -------------------------------------------------------------
    def _poll_status(self):
        now = time.time()
        if now - self._last_scan_time > 10.0:
            self._last_scan_time = now
            ok, _ = self.hw.scan_device()
            if ok:
                self._set_label(self.lbl_device_status, f"Conectado: {self.hw.device_name}", GREEN)
            else:
                self._set_label(self.lbl_device_status, "Mouse desconectado", ERROR)

        # Engine parou sozinha (ex.: mouse desconectado)?
        if self._engine_was_running and not self.engine.running:
            self._engine_was_running = False
            self._set_engine_button(False)
            msg = self.engine.last_error or "Parado"
            self._set_label(self.lbl_engine_msg, f"Status: {msg}", ERROR if self.engine.last_error else MUTED)

        self.click_box_timestamps = [t for t in self.click_box_timestamps if now - t <= 1.0]
        if hasattr(self, "lbl_cps_val"):
            self.lbl_cps_val.configure(text=f"CPS Atual: {len(self.click_box_timestamps)}")

        self.root.after(200, self._poll_status)

    def _toggle_engine(self):
        if not self.engine.running:
            ok, msg = self.engine.start()
            if ok:
                self._engine_was_running = True
                self._set_engine_button(True)
                self._set_label(self.lbl_engine_msg, f"Status: {msg}", GREEN)
            else:
                messagebox.showerror("Erro ao Iniciar", msg)
        else:
            self._engine_was_running = False
            self.engine.stop()
            self._set_engine_button(False)
            self._set_label(self.lbl_engine_msg, "Status: Parado", MUTED)

    def _on_core_change(self):
        self.cfg.set("core_mode", self.var_core.get())

    def _on_toggle_recoil(self):
        self.cfg.update_section("recoil", enabled=self.switch_recoil.get() == 1)

    def _on_select_preset(self, preset_name):
        p = self.cfg.get("presets", {}).get(preset_name)
        if not p:
            return
        self.slider_y.set_value(p["pull_y"])
        self.slider_x.set_value(p["pull_x"])
        self.slider_delay.set_value(p["delay_ms"])
        self.slider_start.set_value(p["start_delay_ms"])
        self.cfg.update_section(
            "recoil", active_preset=preset_name, pull_y=p["pull_y"], pull_x=p["pull_x"],
            delay_ms=p["delay_ms"], start_delay_ms=p["start_delay_ms"]
        )

    def _save_current_as_preset(self):
        name = self.combo_presets.get().strip()
        if not name:
            return
        presets = self.cfg.get("presets", {})
        presets[name] = {
            "pull_y": int(self.slider_y.get()), "pull_x": int(self.slider_x.get()),
            "delay_ms": int(self.slider_delay.get()), "start_delay_ms": int(self.slider_start.get()),
        }
        self.cfg.set("presets", presets)
        self.cfg.update_section("recoil", active_preset=name)
        self.combo_presets.configure(values=list(presets.keys()))
        messagebox.showinfo("Preset", f"Preset '{name}' salvo.")

    def _on_burst_mode(self, label):
        self.cfg.update_section("burst", active_mode=BURST_MODES.get(label, 1))

    def _on_toggle_autoclicker(self):
        self.cfg.update_section("autoclicker", enabled=self.switch_ac.get() == 1)

    def _on_toggle_jitter(self):
        self.cfg.update_section("autoclicker", randomize_jitter=self.switch_jitter.get() == 1)

    def _on_select_trigger(self, label):
        code = self._trigger_labels.get(label)
        if code:
            self.cfg.update_section("autoclicker", trigger=code)

    def _set_led_level(self, level):
        ok, msg = self.hw.set_backlight_level(level)
        if ok:
            self.cfg.update_section("rgb", brightness=level)
            messagebox.showinfo("Iluminação", msg)
        else:
            messagebox.showwarning("Aviso", msg)

    def _on_bench_click(self):
        now = time.time()
        self.click_box_timestamps.append(now)
        self.click_box_timestamps = [t for t in self.click_box_timestamps if now - t <= 1.0]
        cur = len(self.click_box_timestamps)
        if cur > self.max_cps:
            self.max_cps = cur
            self.lbl_max_cps.configure(text=f"CPS Recorde: {self.max_cps}")

    def _reset_bench(self):
        self.max_cps = 0
        self.click_box_timestamps.clear()
        if hasattr(self, "lbl_max_cps"):
            self.lbl_max_cps.configure(text="CPS Recorde: 0")
