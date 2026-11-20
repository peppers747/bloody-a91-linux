import time
import threading
import random
import os

class InputEngine:
    def __init__(self, config_manager):
        self.cfg = config_manager
        self.running = False
        self.mouse_device = None
        self.uinput_device = None
        self.worker_thread = None
        self.recoil_thread = None
        
        # Estado atual
        self.lmb_pressed = False
        self.active_burst_mode = 1  # 1: single, 2: N-burst, 3: 3-burst
        self.autoclicker_active = False
        self.autoclicker_thread = None
        
        # Estatísticas para o benchmark de CPS
        self.click_timestamps = []
        self.last_cps = 0.0

    def find_bloody_event_node(self):
        """Encontra o arquivo /dev/input/eventX correspondente ao mouse Bloody."""
        import re

        # Método 1: Leitura direta de /proc/bus/input/devices (sempre funciona)
        try:
            if os.path.exists("/proc/bus/input/devices"):
                with open("/proc/bus/input/devices", "r") as f:
                    content = f.read()
                sections = content.strip().split("\n\n")
                for sec in sections:
                    sec_lower = sec.lower()
                    if ("09da" in sec_lower or "company  usb device" in sec_lower or "bloody" in sec_lower or "a4tech" in sec_lower):
                        if "mouse" in sec_lower:
                            m = re.search(r"Handlers=.*?(event\d+)", sec)
                            if m:
                                path = f"/dev/input/{m.group(1)}"
                                if os.path.exists(path):
                                    return path
        except Exception as e:
            print(f"[Engine] Erro ao ler /proc/bus/input/devices: {e}")

        # Método 2: Verificação por link simbólico em /dev/input/by-id
        try:
            for item in os.listdir("/dev/input/by-id"):
                item_lower = item.lower()
                if ("company_usb_device" in item_lower or "bloody" in item_lower or "a4tech" in item_lower) and "event-mouse" in item_lower:
                    full = os.path.realpath(os.path.join("/dev/input/by-id", item))
                    if os.path.exists(full):
                        return full
        except Exception:
            pass

        # Método 3: Fallback varrendo dispositivos evdev
        try:
            import evdev
            for path in evdev.list_devices():
                try:
                    dev = evdev.InputDevice(path)
                    if dev.info.vendor == 0x09DA:
                        caps = dev.capabilities()
                        if evdev.ecodes.EV_REL in caps and evdev.ecodes.REL_X in caps[evdev.ecodes.EV_REL]:
                            return dev.path
                except Exception:
                    continue
        except Exception as e:
            print(f"[Engine] Erro no fallback evdev: {e}")

        return None

    def start(self):
        """Inicializa a captura evdev e o dispositivo virtual uinput."""
        if self.running:
            return True, "Engine já está em execução."

        try:
            import evdev
            from evdev import UInput, ecodes
        except ImportError:
            return False, "Biblioteca 'evdev' não instalada. Execute ./setup.sh para instalar dependências."

        node_path = self.find_bloody_event_node()
        if not node_path:
            return False, "Mouse Bloody não encontrado em /dev/input/. Verifique se o mouse está conectado."

        # Verifica permissão de leitura no nó do mouse
        if not os.access(node_path, os.R_OK):
            return False, (
                f"Permissão negada no mouse ({node_path})!\n\n"
                f"Para liberar, execute no terminal do VS Code:\n"
                f"sudo chmod 666 {node_path} /dev/uinput"
            )

        # Verifica permissão de gravação no uinput
        if os.path.exists("/dev/uinput") and not os.access("/dev/uinput", os.W_OK):
            return False, (
                "Permissão negada no /dev/uinput!\n\n"
                "Para liberar, execute no terminal do VS Code:\n"
                "sudo chmod 666 /dev/uinput"
            )

        try:
            self.mouse_device = evdev.InputDevice(node_path)
            # Cria dispositivo virtual com suporte a mouse
            cap = {
                ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_RIGHT, ecodes.BTN_MIDDLE, ecodes.BTN_SIDE, ecodes.BTN_EXTRA],
                ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y, ecodes.REL_WHEEL, ecodes.REL_HWHEEL]
            }
            self.uinput_device = UInput(cap, name="Bloody-Virtual-Core-Mouse")
            
            # Tenta capturar o dispositivo de forma exclusiva
            try:
                self.mouse_device.grab()
            except Exception as grab_err:
                print(f"[Engine] Aviso: grab() falhou ({grab_err}). Operando em modo de injeção complementar.")

            self.running = True
            self.worker_thread = threading.Thread(target=self._event_loop, daemon=True)
            self.worker_thread.start()
            return True, f"Engine ativa no nó {node_path} com uinput!"
        except PermissionError:
            return False, (
                f"Permissão negada!\n\n"
                f"Execute no terminal do VS Code:\n"
                f"sudo chmod 666 {node_path} /dev/uinput"
            )
        except Exception as e:
            return False, f"Falha ao iniciar engine: {e}"

    def stop(self):
        self.running = False
        self.lmb_pressed = False
        self.autoclicker_active = False
        if self.mouse_device:
            try:
                self.mouse_device.ungrab()
            except Exception:
                pass
            self.mouse_device = None
        if self.uinput_device:
            try:
                self.uinput_device.close()
            except Exception:
                pass
            self.uinput_device = None

    def _event_loop(self):
        """Loop de captura de eventos do hardware original."""
        from evdev import ecodes

        while self.running and self.mouse_device:
            try:
                for event in self.mouse_device.read_loop():
                    if not self.running:
                        break

                    # Monitora clique esquerdo
                    if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_LEFT:
                        if event.value == 1:  # Botão pressionado
                            self.lmb_pressed = True
                            self._record_click()
                            self._handle_lmb_down()
                        elif event.value == 0:  # Botão solto
                            self.lmb_pressed = False
                            if self.uinput_device:
                                self.uinput_device.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
                                self.uinput_device.syn()

                    # Repassa movimento e demais botões normalmente
                    elif self.uinput_device:
                        self.uinput_device.write(event.type, event.code, event.value)
                        self.uinput_device.syn()

            except Exception as e:
                if self.running:
                    print(f"[Engine Loop] Erro: {e}")
                    time.sleep(0.5)

    def _handle_lmb_down(self):
        """Trata o clique esquerdo baseado no modo atual (Core 1, 2 ou 3)."""
        from evdev import ecodes
        core_mode = self.cfg.get("core_mode", 1)

        # Core 1: Normal
        if core_mode == 1:
            if self.uinput_device:
                self.uinput_device.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 1)
                self.uinput_device.syn()

        # Core 2: Burst Fire (Botões 1, N, 3)
        elif core_mode == 2:
            burst_cfg = self.cfg.get("burst", {})
            shots = 1
            if self.active_burst_mode == 2:
                shots = burst_cfg.get("mode_n_shots", 2)
            elif self.active_burst_mode == 3:
                shots = burst_cfg.get("mode_3_shots", 3)
            
            interval = burst_cfg.get("shot_interval_ms", 40) / 1000.0
            threading.Thread(target=self._execute_burst, args=(shots, interval), daemon=True).start()

        # Core 3: Ultra Core / No-Recoil
        elif core_mode == 3:
            if self.uinput_device:
                self.uinput_device.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 1)
                self.uinput_device.syn()

            recoil_cfg = self.cfg.get("recoil", {})
            if recoil_cfg.get("enabled", True):
                threading.Thread(target=self._execute_recoil, daemon=True).start()

    def _execute_burst(self, shots, interval):
        """Dispara uma rajada precisa de tiros."""
        from evdev import ecodes
        if not self.uinput_device:
            return

        for _ in range(shots):
            self.uinput_device.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 1)
            self.uinput_device.syn()
            time.sleep(interval / 2.0)
            self.uinput_device.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
            self.uinput_device.syn()
            time.sleep(interval / 2.0)

    def _execute_recoil(self):
        """Thread responsável pela compensação contínua de recuo (pull-down)."""
        from evdev import ecodes
        recoil_cfg = self.cfg.get("recoil", {})
        start_delay = recoil_cfg.get("start_delay_ms", 100) / 1000.0
        pull_y = recoil_cfg.get("pull_y", 6)
        pull_x = recoil_cfg.get("pull_x", 0)
        delay = recoil_cfg.get("delay_ms", 25) / 1000.0

        # Espera o delay do tiro inicial
        time.sleep(start_delay)

        while self.running and self.lmb_pressed and self.uinput_device:
            # Emite deslocamento relativo vertical e horizontal
            if pull_y != 0:
                self.uinput_device.write(ecodes.EV_REL, ecodes.REL_Y, pull_y)
            if pull_x != 0:
                self.uinput_device.write(ecodes.EV_REL, ecodes.REL_X, pull_x)
            self.uinput_device.syn()
            time.sleep(delay)

    def start_autoclicker(self, cps=20, jitter=True):
        """Ativa o auto-clicker com taxa de CPS configurável."""
        if self.autoclicker_active:
            return
        self.autoclicker_active = True
        self.autoclicker_thread = threading.Thread(target=self._autoclicker_loop, args=(cps, jitter), daemon=True)
        self.autoclicker_thread.start()

    def stop_autoclicker(self):
        self.autoclicker_active = False

    def _autoclicker_loop(self, cps, jitter):
        from evdev import ecodes
        base_delay = 1.0 / max(1, cps)
        
        while self.running and self.autoclicker_active and self.uinput_device:
            sleep_time = base_delay / 2.0
            if jitter:
                sleep_time += random.uniform(-0.003, 0.003)
                sleep_time = max(0.005, sleep_time)

            self.uinput_device.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 1)
            self.uinput_device.syn()
            self._record_click()
            time.sleep(sleep_time)

            self.uinput_device.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
            self.uinput_device.syn()
            time.sleep(sleep_time)

    def _record_click(self):
        """Registra timestamps dos cliques para cálculo de CPS em tempo real."""
        now = time.time()
        self.click_timestamps.append(now)
        # Mantém apenas o último segundo
        self.click_timestamps = [t for t in self.click_timestamps if now - t <= 1.0]
        self.last_cps = len(self.click_timestamps)

    def get_current_cps(self):
        now = time.time()
        self.click_timestamps = [t for t in self.click_timestamps if now - t <= 1.0]
        return len(self.click_timestamps)
