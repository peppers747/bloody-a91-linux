import copy
import json
import os
import shutil
import threading

DEFAULT_CONFIG = {
    "core_mode": 3,  # 1: Normal, 2: Burst (1/N/3), 3: Ultra Core (Recoil)
    "recoil": {
        "enabled": True,
        "pull_y": 6,           # Compensação vertical para baixo a cada tick
        "pull_x": 0,           # Compensação horizontal
        "delay_ms": 25,        # Intervalo entre correções (ms)
        "start_delay_ms": 120, # Tempo antes de começar a puxar (primeiro tiro limpo)
        "active_preset": "Padrão"
    },
    "presets": {
        "Padrão": {"pull_y": 6, "pull_x": 0, "delay_ms": 25, "start_delay_ms": 120},
        "CS2 AK-47": {"pull_y": 8, "pull_x": -1, "delay_ms": 22, "start_delay_ms": 100},
        "CS2 M4A4": {"pull_y": 6, "pull_x": 0, "delay_ms": 20, "start_delay_ms": 100},
        "Rust AK": {"pull_y": 10, "pull_x": 0, "delay_ms": 30, "start_delay_ms": 140},
        "Leve": {"pull_y": 3, "pull_x": 0, "delay_ms": 30, "start_delay_ms": 150}
    },
    "burst": {
        "active_mode": 1,       # 1: tiro simples, 2: modo N, 3: modo 3
        "mode_n_shots": 2,      # Modo N dispara 2 vezes
        "mode_3_shots": 3,      # Modo 3 dispara 3 vezes
        "shot_interval_ms": 40  # Intervalo entre disparos na rajada
    },
    "autoclicker": {
        "enabled": False,
        "trigger": "BTN_SIDE",  # Botão que, segurado, dispara os cliques
        "cps": 18,              # Cliques por segundo
        "randomize_jitter": True
    },
    "rgb": {
        "brightness": 3,        # 0: Desligado, 1: Fraco, 2: Médio, 3: Forte
        "mode": "breathing"
    }
}


def default_config_path():
    """~/.config/bloodylinux/config.json (respeita $XDG_CONFIG_HOME)."""
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "bloodylinux", "config.json")


def _deep_merge(base, override):
    """Mescla 'override' sobre 'base' recursivamente, sem alterar nenhum dos dois."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class ConfigManager:
    SAVE_DEBOUNCE_S = 0.5

    def __init__(self, filepath=None, legacy_path=None):
        self.filepath = filepath or default_config_path()
        self._lock = threading.Lock()
        self._save_timer = None
        self._migrate_legacy(legacy_path)
        self.data = self.load()

    def _migrate_legacy(self, legacy_path):
        """Copia o config.json antigo (salvo na pasta do projeto) para o novo local."""
        if legacy_path and os.path.isfile(legacy_path) and not os.path.exists(self.filepath):
            try:
                os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
                shutil.copyfile(legacy_path, self.filepath)
                print(f"[Config] Configuração antiga migrada para {self.filepath}")
            except OSError as e:
                print(f"[Config] Não foi possível migrar {legacy_path}: {e}")

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    return _deep_merge(DEFAULT_CONFIG, loaded)
                print(f"[Config] {self.filepath} inválido. Usando padrões.")
            except (OSError, ValueError) as e:
                print(f"[Config] Erro ao carregar {self.filepath}: {e}. Usando padrões.")
        return copy.deepcopy(DEFAULT_CONFIG)

    def save(self):
        with self._lock:
            if self._save_timer:
                self._save_timer.cancel()
                self._save_timer = None
            try:
                os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
                tmp = self.filepath + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=4, ensure_ascii=False)
                os.replace(tmp, self.filepath)  # gravação atômica
                return True
            except OSError as e:
                print(f"[Config] Erro ao salvar {self.filepath}: {e}")
                return False

    def save_later(self):
        """Agenda um salvamento; chamadas seguidas (ex.: arrastar slider) viram uma só gravação."""
        with self._lock:
            if self._save_timer:
                self._save_timer.cancel()
            self._save_timer = threading.Timer(self.SAVE_DEBOUNCE_S, self.save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save_later()

    def update_section(self, section, **values):
        """Atualiza campos de uma seção (ex.: update_section('burst', mode_n_shots=3))."""
        self.data.setdefault(section, {}).update(values)
        self.save_later()
