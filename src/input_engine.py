import os
import random
import re
import select
import threading
import time
from collections import deque

A4TECH_VID = 0x09DA
VIRTUAL_DEVICE_NAME = "BloodyLinux Virtual Mouse"

# Botões que podem ser usados como gatilho do auto-clicker (nome evdev -> rótulo na GUI)
AUTOCLICK_TRIGGERS = {
    "BTN_SIDE": "Botão lateral traseiro",
    "BTN_EXTRA": "Botão lateral dianteiro",
    "BTN_MIDDLE": "Botão do meio (scroll)",
}


class InputEngine:
    """
    Captura o mouse físico (evdev, com grab exclusivo) e repassa os eventos para um
    mouse virtual (uinput), aplicando os modos Core 1/2/3 e o auto-clicker.
    """

    def __init__(self, config_manager):
        self.cfg = config_manager
        self.running = False
        self.last_error = None
        self.node_path = None
        self.mouse_device = None
        self.uinput_device = None
        self.worker_thread = None

        self._write_lock = threading.Lock()
        self._press_id = 0          # incrementa a cada clique; invalida threads de recoil antigas
        self._burst_busy = False
        self._autoclick_holding = False
        self._lmb_forwarded = False

        self.lmb_pressed = False
        self.click_timestamps = deque()

    # ------------------------------------------------------------------
    # Descoberta do dispositivo
    # ------------------------------------------------------------------
    @staticmethod
    def _is_pointer(dev, ecodes):
        caps = dev.capabilities()
        return (ecodes.REL_X in caps.get(ecodes.EV_REL, [])
                and ecodes.BTN_LEFT in caps.get(ecodes.EV_KEY, []))

    def find_bloody_event_node(self):
        """Encontra o /dev/input/eventX do mouse Bloody (ignorando o próprio mouse virtual)."""
        try:
            import evdev
            from evdev import ecodes
        except ImportError:
            return None

        name_fallback = None
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
            except OSError:
                continue
            try:
                if dev.name == VIRTUAL_DEVICE_NAME or not self._is_pointer(dev, ecodes):
                    continue
                if dev.info.vendor == A4TECH_VID:
                    return dev.path
                lname = dev.name.lower()
                if name_fallback is None and ("bloody" in lname or "a4tech" in lname):
                    name_fallback = dev.path
            finally:
                dev.close()
        if name_fallback:
            return name_fallback

        # Sem permissão para abrir os nós, evdev não lista nada: tenta /proc para dar
        # uma mensagem de erro útil (o nó existe, mas falta permissão).
        try:
            with open("/proc/bus/input/devices", "r") as f:
                sections = f.read().strip().split("\n\n")
            for sec in sections:
                if "vendor=09da" in sec.lower() and VIRTUAL_DEVICE_NAME not in sec:
                    m = re.search(r"Handlers=.*\bmouse\d+.*?\b(event\d+)", sec) or \
                        re.search(r"Handlers=.*?\b(event\d+).*\bmouse\d+", sec)
                    if m:
                        return f"/dev/input/{m.group(1)}"
        except OSError:
            pass
        return None

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def start(self):
        if self.running:
            return True, "Engine já está em execução."

        try:
            import evdev
            from evdev import UInput
        except ImportError:
            return False, "Biblioteca 'evdev' não instalada. Execute o instalador (install.sh)."

        node_path = self.find_bloody_event_node()
        if not node_path:
            return False, "Mouse Bloody não encontrado em /dev/input/. Verifique se o mouse está conectado."

        perm_hint = (
            "Instale as regras udev com o instalador (sudo ./install.sh) ou, "
            "temporariamente:\n"
            f"sudo chmod 666 {node_path} /dev/uinput"
        )
        if not os.access(node_path, os.R_OK):
            return False, f"Permissão negada no mouse ({node_path}).\n\n{perm_hint}"
        if not os.path.exists("/dev/uinput"):
            return False, "/dev/uinput não existe. Carregue o módulo com: sudo modprobe uinput"
        if not os.access("/dev/uinput", os.W_OK):
            return False, f"Permissão negada no /dev/uinput.\n\n{perm_hint}"

        try:
            self.mouse_device = evdev.InputDevice(node_path)
            # Mouse virtual com exatamente os mesmos botões/eixos do físico
            self.uinput_device = UInput.from_device(self.mouse_device, name=VIRTUAL_DEVICE_NAME)
        except PermissionError:
            self._close_devices()
            return False, f"Permissão negada.\n\n{perm_hint}"
        except Exception as e:
            self._close_devices()
            return False, f"Falha ao iniciar engine: {e}"

        try:
            self.mouse_device.grab()
        except OSError as e:
            # Sem grab, o sistema receberia os cliques em dobro (físico + virtual).
            self._close_devices()
            return False, f"Não foi possível capturar o mouse com exclusividade: {e}"

        self.node_path = node_path
        self.last_error = None
        self.lmb_pressed = False
        self._lmb_forwarded = False
        self.running = True
        self.worker_thread = threading.Thread(target=self._event_loop, daemon=True)
        self.worker_thread.start()
        return True, f"Engine ativa em {node_path}"

    def stop(self):
        self.running = False
        self.lmb_pressed = False
        self._autoclick_holding = False
        if self.worker_thread and self.worker_thread is not threading.current_thread():
            self.worker_thread.join(timeout=1.0)
        self.worker_thread = None
        self._close_devices()

    def _close_devices(self):
        if self.mouse_device:
            try:
                self.mouse_device.ungrab()
            except OSError:
                pass
            try:
                self.mouse_device.close()
            except OSError:
                pass
            self.mouse_device = None
        with self._write_lock:
            if self.uinput_device:
                try:
                    # garante que nenhum botão fique "preso" pressionado
                    self.uinput_device.write(1, 0x110, 0)  # EV_KEY, BTN_LEFT, 0
                    self.uinput_device.syn()
                    self.uinput_device.close()
                except OSError:
                    pass
                self.uinput_device = None

    # ------------------------------------------------------------------
    # Escrita no mouse virtual
    # ------------------------------------------------------------------
    def _emit(self, *events, syn=True):
        """Escreve eventos (type, code, value) de forma thread-safe."""
        with self._write_lock:
            dev = self.uinput_device
            if not dev:
                return
            try:
                for etype, code, value in events:
                    dev.write(etype, code, value)
                if syn:
                    dev.syn()
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------
    def _event_loop(self):
        from evdev import ecodes

        trigger_cache = None
        while self.running:
            dev = self.mouse_device
            if dev is None:
                break
            try:
                r, _, _ = select.select([dev.fd], [], [], 0.2)
                if not r:
                    continue
                events = list(dev.read())
            except (OSError, ValueError) as e:
                if self.running:
                    self.last_error = f"Mouse desconectado ou erro de leitura: {e}"
                    print(f"[Engine] {self.last_error}")
                    self.running = False
                    self._close_devices()
                break

            ac_cfg = self.cfg.get("autoclicker", {})
            ac_enabled = ac_cfg.get("enabled", False)
            trigger_name = ac_cfg.get("trigger", "BTN_SIDE")
            if trigger_cache is None or trigger_cache[0] != trigger_name:
                trigger_cache = (trigger_name, getattr(ecodes, trigger_name, ecodes.BTN_SIDE))
            trigger_code = trigger_cache[1]

            for ev in events:
                if ev.type == ecodes.EV_KEY and ev.code == ecodes.BTN_LEFT:
                    if ev.value == 1:
                        self._record_click()
                        self._on_lmb_down()
                    elif ev.value == 0:
                        self._on_lmb_up()
                    continue  # autorepeat (value 2) é descartado

                if ac_enabled and ev.type == ecodes.EV_KEY and ev.code == trigger_code:
                    if ev.value == 1:
                        self._start_autoclick_hold()
                    elif ev.value == 0:
                        self._autoclick_holding = False
                    continue  # o gatilho não é repassado ao sistema

                # Todo o resto (movimento, scroll, outros botões e EV_SYN) passa direto
                self._emit((ev.type, ev.code, ev.value), syn=False)

    # ------------------------------------------------------------------
    # Clique esquerdo: Core 1 / 2 / 3
    # ------------------------------------------------------------------
    def _on_lmb_down(self):
        from evdev import ecodes
        self.lmb_pressed = True
        self._press_id += 1
        core_mode = self.cfg.get("core_mode", 1)

        if core_mode == 2:
            if self._burst_busy:
                return
            burst_cfg = self.cfg.get("burst", {})
            mode = burst_cfg.get("active_mode", 1)
            shots = {2: burst_cfg.get("mode_n_shots", 2), 3: burst_cfg.get("mode_3_shots", 3)}.get(mode, 1)
            interval = max(10, burst_cfg.get("shot_interval_ms", 40)) / 1000.0
            self._burst_busy = True
            threading.Thread(target=self._execute_burst, args=(shots, interval), daemon=True).start()
            return

        self._emit((ecodes.EV_KEY, ecodes.BTN_LEFT, 1))
        self._lmb_forwarded = True
        if core_mode == 3 and self.cfg.get("recoil", {}).get("enabled", True):
            threading.Thread(target=self._execute_recoil, args=(self._press_id,), daemon=True).start()

    def _on_lmb_up(self):
        from evdev import ecodes
        self.lmb_pressed = False
        # Só solta se o clique foi repassado (no Core 2 a rajada controla os próprios eventos).
        # Usar a flag em vez do modo atual evita botão preso se o modo mudar com o botão segurado.
        if self._lmb_forwarded:
            self._lmb_forwarded = False
            self._emit((ecodes.EV_KEY, ecodes.BTN_LEFT, 0))

    def _execute_burst(self, shots, interval):
        from evdev import ecodes
        try:
            for _ in range(shots):
                if not self.running:
                    break
                self._emit((ecodes.EV_KEY, ecodes.BTN_LEFT, 1))
                time.sleep(interval / 2.0)
                self._emit((ecodes.EV_KEY, ecodes.BTN_LEFT, 0))
                time.sleep(interval / 2.0)
        finally:
            self._burst_busy = False

    def _execute_recoil(self, press_id):
        """Compensação contínua de recuo enquanto o botão segue pressionado."""
        from evdev import ecodes
        recoil_cfg = self.cfg.get("recoil", {})
        start_delay = recoil_cfg.get("start_delay_ms", 100) / 1000.0
        pull_y = int(recoil_cfg.get("pull_y", 6))
        pull_x = int(recoil_cfg.get("pull_x", 0))
        delay = max(5, recoil_cfg.get("delay_ms", 25)) / 1000.0

        def still_holding():
            return self.running and self.lmb_pressed and press_id == self._press_id

        deadline = time.monotonic() + start_delay
        while still_holding() and time.monotonic() < deadline:
            time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))

        while still_holding():
            events = []
            if pull_y:
                events.append((ecodes.EV_REL, ecodes.REL_Y, pull_y))
            if pull_x:
                events.append((ecodes.EV_REL, ecodes.REL_X, pull_x))
            if events:
                self._emit(*events)
            time.sleep(delay)

    # ------------------------------------------------------------------
    # Auto-clicker (segurar o botão gatilho)
    # ------------------------------------------------------------------
    def _start_autoclick_hold(self):
        if self._autoclick_holding:
            return
        self._autoclick_holding = True
        threading.Thread(target=self._autoclicker_loop, daemon=True).start()

    def _autoclicker_loop(self):
        from evdev import ecodes
        while self.running and self._autoclick_holding:
            ac_cfg = self.cfg.get("autoclicker", {})
            half = 1.0 / max(1, ac_cfg.get("cps", 18)) / 2.0
            if ac_cfg.get("randomize_jitter", True):
                half = max(0.004, half + random.uniform(-0.003, 0.003))
            self._emit((ecodes.EV_KEY, ecodes.BTN_LEFT, 1))
            self._record_click()
            time.sleep(half)
            self._emit((ecodes.EV_KEY, ecodes.BTN_LEFT, 0))
            time.sleep(half)

    # ------------------------------------------------------------------
    # Estatísticas
    # ------------------------------------------------------------------
    def _record_click(self):
        now = time.monotonic()
        self.click_timestamps.append(now)
        while self.click_timestamps and now - self.click_timestamps[0] > 1.0:
            self.click_timestamps.popleft()

    def get_current_cps(self):
        now = time.monotonic()
        while self.click_timestamps and now - self.click_timestamps[0] > 1.0:
            self.click_timestamps.popleft()
        return len(self.click_timestamps)
