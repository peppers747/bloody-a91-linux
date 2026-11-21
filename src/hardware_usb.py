import glob
import os

# IDs conhecidos da A4Tech / Bloody
A4TECH_VID = 0x09DA

KNOWN_BLOODY_PIDS = {
    0xFAFD: "Bloody A91 / Gaming Mouse (Detectado)",
    0x112C: "Bloody A90 / A91 Optical Gaming Mouse",
    0x1068: "Bloody V8M Gaming Mouse",
    0x1069: "Bloody V7M Gaming Mouse",
    0x106A: "Bloody V5M Gaming Mouse",
    0x106B: "Bloody V3M Gaming Mouse",
    0x13BC: "Bloody AL90 Laser Gaming Mouse",
    0x1404: "Bloody RT7 Wireless Gaming Mouse"
}

class BloodyHardware:
    def __init__(self):
        self.device = None
        self.pid = None
        self.device_name = "Desconhecido"
        self.pyusb_available = False
        
        try:
            import usb.core
            import usb.util
            self.usb = usb
            self.pyusb_available = True
        except ImportError:
            self.usb = None

    def scan_device(self):
        """Procura pelo mouse Bloody conectado."""
        self.device = None
        # Método 1: via PyUSB
        if self.pyusb_available and self.usb:
            try:
                devs = list(self.usb.core.find(find_all=True, idVendor=A4TECH_VID))
                if devs:
                    self.device = devs[0]
                    self.pid = self.device.idProduct
                    self.device_name = KNOWN_BLOODY_PIDS.get(self.pid, f"Bloody Device (PID: 0x{self.pid:04x})")
                    return True, f"Encontrado via USB: {self.device_name} (0x{A4TECH_VID:04x}:0x{self.pid:04x})"
            except Exception:
                # Pode falhar por permissão USB / backend libusb ausente
                pass

        # Método 2: Leitura direta do sysfs do Linux (/sys/bus/usb/devices)
        try:
            for path in glob.glob("/sys/bus/usb/devices/*"):
                id_vendor_path = os.path.join(path, "idVendor")
                id_product_path = os.path.join(path, "idProduct")
                if os.path.exists(id_vendor_path) and os.path.exists(id_product_path):
                    with open(id_vendor_path, "r") as f:
                        vid = int(f.read().strip(), 16)
                    with open(id_product_path, "r") as f:
                        pid = int(f.read().strip(), 16)
                    
                    if vid == A4TECH_VID:
                        self.pid = pid
                        self.device_name = KNOWN_BLOODY_PIDS.get(pid, f"Bloody Device (PID: 0x{pid:04x})")
                        return True, f"Encontrado via sysfs: {self.device_name} (0x{vid:04x}:0x{pid:04x})"
        except OSError as e:
            return False, f"Erro ao escanear dispositivos: {e}"

        return False, "Nenhum mouse Bloody (VID 0x09da) detectado nas portas USB."

    def set_backlight_level(self, level: int):
        """
        Ajusta a intensidade dos LEDs da Bloody (EXPERIMENTAL).
        level: 0 (desligado) a 3 (máximo)

        O protocolo da A4Tech não é documentado; este comando (SET_REPORT, Feature
        Report 7) pode não ter efeito em todas as revisões do A91.
        """
        if not self.pyusb_available:
            return False, "PyUSB não está instalado."
        if not self.device:
            return False, ("Mouse não acessível via USB. Verifique a conexão e se as regras "
                           "udev foram instaladas (sudo ./install.sh).")

        interface = 1
        level = max(0, min(3, int(level)))
        data = bytes([0x07, 0x00, level, 0x00, 0x00, 0x00, 0x00, 0x00])
        detached = False
        try:
            # Desanexa o driver do kernel só durante o comando, e reanexa depois;
            # caso contrário a interface (teclas extras do mouse) pararia de funcionar.
            try:
                if self.device.is_kernel_driver_active(interface):
                    self.device.detach_kernel_driver(interface)
                    detached = True
            except Exception:
                pass

            # bmRequestType 0x21 (Host->Device, Class, Interface), bRequest 0x09 (SET_REPORT),
            # wValue 0x0307 (Feature Report ID 7)
            self.device.ctrl_transfer(0x21, 0x09, 0x0307, interface, data)
            return True, f"Brilho ajustado para nível {level}"
        except Exception as e:
            return False, f"Falha ao enviar comando USB: {e}"
        finally:
            if detached:
                try:
                    self.usb.util.dispose_resources(self.device)
                    self.device.attach_kernel_driver(interface)
                except Exception as e:
                    print(f"[USB] Aviso: não foi possível reanexar o driver do kernel: {e}")
