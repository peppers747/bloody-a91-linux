#!/usr/bin/env python3
import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
# Permite rodar de qualquer diretório e usar dependências empacotadas em vendor/ (pacote .deb)
for path in (os.path.join(APP_DIR, "vendor"), APP_DIR):
    if os.path.isdir(path) and path not in sys.path:
        sys.path.insert(0, path)

from src import __version__  # noqa: E402


def main():
    if "--version" in sys.argv:
        print(f"BloodyLinux {__version__}")
        return 0

    if not sys.platform.startswith("linux"):
        print("[!] BloodyLinux depende de evdev/uinput e só funciona no Linux.")

    import tkinter as tk
    from src.config import ConfigManager
    from src.hardware_usb import BloodyHardware
    from src.input_engine import InputEngine
    from src.gui import BloodyApp

    print("=" * 50)
    print(f"  BloodyLinux Controller {__version__} (A4Tech A91)")
    print("=" * 50)

    # config.json antigo (na pasta do projeto) é migrado para ~/.config/bloodylinux/
    cfg = ConfigManager(legacy_path=os.path.join(APP_DIR, "config.json"))
    print(f"[*] Configuração: {cfg.filepath}")

    hw = BloodyHardware()
    _, msg = hw.scan_device()
    print(f"[*] Hardware USB: {msg}")

    engine = InputEngine(cfg)

    try:
        import customtkinter as ctk
        root = ctk.CTk()
    except ImportError:
        root = tk.Tk()

    BloodyApp(root, cfg, hw, engine)

    def on_closing():
        print("[*] Encerrando BloodyLinux...")
        engine.stop()
        cfg.save()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        on_closing()
    finally:
        # Garante que o mouse nunca fique "preso" (grab) se algo der errado
        engine.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
