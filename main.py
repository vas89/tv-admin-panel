import os
import sys
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.adb_device import AdbDeviceTcp

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class TVAdminApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TV Remote Administrator")
        self.geometry("600x650")
        self.resizable(False, False)
        
        self.device = None
        self.signer = self.setup_crypto_keys()

        ctk.CTkLabel(self, text="Полный доступ к Android TV", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=15)

        conn_frame = ctk.CTkFrame(self)
        conn_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(conn_frame, text="IP-адрес телевизора:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15, pady=15)
        self.ip_entry = ctk.CTkEntry(conn_frame, placeholder_text="192.168.1.XX", width=150)
        self.ip_entry.pack(side="left", padx=10, pady=15)
        
        self.btn_connect = ctk.CTkButton(conn_frame, text="Подключиться", command=self.start_connect)
        self.btn_connect.pack(side="right", padx=15, pady=15)

        self.apk_frame = ctk.CTkFrame(self)
        self.apk_frame.pack(fill="x", padx=20, pady=10)
        self.apk_frame.pack_forget() 
        
        ctk.CTkLabel(self.apk_frame, text="Удаленная установка программ", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        self.btn_choose_apk = ctk.CTkButton(self.apk_frame, text="Выбрать .APK и установить на ТВ", fg_color="#2b6cb0", command=self.install_apk_flow)
        self.btn_choose_apk.pack(fill="x", padx=30, pady=15)

        self.pic_frame = ctk.CTkFrame(self)
        self.pic_frame.pack(fill="x", padx=20, pady=10)
        self.pic_frame.pack_forget()

        ctk.CTkLabel(self.pic_frame, text="Управление экраном и картинкой", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.add_slider_cmd(self.pic_frame, "Яркость экрана", "screen_brightness", 0, 255, 150)
        self.add_slider_cmd(self.pic_frame, "Таймаут экрана (сек)", "screen_off_timeout", 15, 1800, 600)

        self.status_label = ctk.CTkLabel(self, text="Введите IP-адрес ТВ и нажмите Подключиться", text_color="yellow", font=ctk.CTkFont(size=13))
        self.status_label.pack(side="bottom", fill="x", pady=15)

    def setup_crypto_keys(self):
        adbkey = "adbkey"
        if not os.path.exists(adbkey):
            keygen(adbkey)
        with open(adbkey, 'r') as f:
            priv = f.read()
        with open(adbkey + '.pub', 'r') as f:
            pub = f.read()
        return PythonRSASigner(pub, priv)

    def set_status(self, text, color="white"):
        self.status_label.configure(text=text, text_color=color)

    def start_connect(self):
        ip = self.ip_entry.get().strip()
        if not ip:
            self.set_status("Ошибка: Введите корректный IP!", "red")
            return
        self.set_status("Подключение... ВНИМАНИЕ: Включите отладку на ТВ и разрешите доступ в окне на экране ТВ!", "cyan")
        threading.Thread(target=self._connect_worker, args=(ip,), daemon=True).start()

    def _connect_worker(self, ip):
        try:
            self.device = AdbDeviceTcp(ip, 5555, default_transport_timeout_s=15)
            self.device.connect(rsa_keys=[self.signer], auth_timeout_s=10)
            self.set_status(f"Успешно подключено к ТВ ({ip})! Доступ открыт.", "green")
            self.apk_frame.pack(fill="x", padx=20, pady=10)
            self.pic_frame.pack(fill="x", padx=20, pady=10)
        except Exception:
            self.set_status("Ошибка подключения. Проверьте IP и включена ли отладка на ТВ.", "red")
            self.device = None

    def install_apk_flow(self):
        if not self.device: return
        file_path = filedialog.askopenfilename(filetypes=[("Android App", "*.apk")])
        if file_path:
            self.set_status(f"Установка {os.path.basename(file_path)}... Пожалуйста, подождите.", "yellow")
            threading.Thread(target=self._install_worker, args=(file_path,), daemon=True).start()

    def _install_worker(self, path):
        try:
            self.device.install(path)
            self.set_status("Программа успешно установлена на телевизор!", "green")
        except Exception as e:
            self.set_status(f"Ошибка при установке приложения: {str(e)}", "red")

    def add_slider_cmd(self, parent, label_text, setting_name, min_v, max_v, init_v):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(frame, text=label_text, width=150, anchor="w").pack(side="left")
        
        def on_slide(val):
            if self.device:
                threading.Thread(target=self.device.shell, args=(f"settings put system {setting_name} {int(float(val))}",), daemon=True).start()

        slider = ctk.CTkSlider(frame, from_=min_v, to=max_v, command=on_slide)
        slider.set(init_v)
        slider.pack(side="right", fill="x", expand=True, padx=10)

if __name__ == "__main__":
    TVAdminApp().mainloop()
