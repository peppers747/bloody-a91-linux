import json
import os

DEFAULT_CONFIG = {
    "core_mode": 3,  # 1: Normal, 2: Burst (1/N/3), 3: Ultra Core (Recoil & Headshot)
    "recoil": {
        "enabled": True,
        "pull_y": 6,          # Compensação vertical para baixo a cada tick
        "pull_x": 0,          # Compensação horizontal
        "delay_ms": 25,       # Intervalo entre correções (ms)
        "start_delay_ms": 120,# Tempo antes de começar a puxar (tempo do primeiro tiro limpo)
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
        "mode_n_shots": 2,    # Botão N dispara 2 vezes
        "mode_3_shots": 3,    # Botão 3 dispara 3 vezes
        "shot_interval_ms": 40# Intervalo entre disparos na rajada
    },
    "autoclicker": {
        "enabled": False,
        "cps": 18,            # Clicks por segundo (estilo Drag / Butterfly Click)
        "randomize_jitter": True # Pequena variação anti-detecção
    },
    "rgb": {
        "brightness": 3,      # 0: Desligado, 1: Fraco, 2: Médio, 3: Forte
        "mode": "breathing"   # breathing, static
    }
}

class ConfigManager:
    def __init__(self, filepath="config.json"):
        self.filepath = filepath
        self.data = self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Mescla valores padrão caso novas chaves tenham sido adicionadas
                    merged = DEFAULT_CONFIG.copy()
                    merged.update(loaded)
                    return merged
            except Exception as e:
                print(f"[Config] Erro ao carregar {self.filepath}: {e}. Usando padrões.")
        return DEFAULT_CONFIG.copy()

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Config] Erro ao salvar {self.filepath}: {e}")
            return False

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
