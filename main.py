#!/usr/bin/env python3
import sys
import tkinter as tk
from src.config import ConfigManager
from src.hardware_usb import BloodyHardware
from src.input_engine import InputEngine
from src.gui import BloodyApp

def main():
    print("=" * 50)
    print("  Iniciando BloodyLinux Controller (A4Tech A91)")
    print("=" * 50)

    # 1. Carrega configurações salvas
    cfg = ConfigManager()

    # 2. Inicializa subsistema de hardware
    hw = BloodyHardware()
    found, msg = hw.scan_device()
    print(f"[*] Hardware USB: {msg}")

    # 3. Inicializa motor de eventos e macros
    engine = InputEngine(cfg)

    # 4. Inicializa interface gráfica
    try:
        import customtkinter as ctk
        root = ctk.CTk()
    except ImportError:
        root = tk.Tk()

    app = BloodyApp(root, cfg, hw, engine)

    # Encerramento limpo ao fechar a janela
    def on_closing():
        print("[*] Encerrando BloodyLinux...")
        engine.stop()
        root.destroy()
        sys.exit(0)

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
