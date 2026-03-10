import json
import os
import threading
import time
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

try:
    from pycaw.pycaw import AudioUtilities
except ImportError:
    AudioUtilities = None

try:
    import pygetwindow as gw
except ImportError:
    gw = None

CONFIG_FILE = "webpad_config.json"


class WebPadApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FreakDeck Config")
        self.root.geometry("900x620")

        self.listener_thread = None
        self.now_playing_thread = None
        self.running = False

        self.current_volume = 50
        self.is_muted = False
        self.now_playing = "Nichts aktiv"

        self.ser = None
        self.serial_lock = threading.Lock()

        self.port_var = tk.StringVar(value="")
        self.platform_var = tk.StringVar(value="windows")

        self.entries = {}
        self.type_vars = {}

        self.build_ui()
        self.refresh_ports()
        self.load_config()

    def build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.grid(sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(2, weight=1)

        ttk.Label(main, text="Serial Port:").grid(row=0, column=0, sticky="w")

        self.port_combo = ttk.Combobox(
            main,
            textvariable=self.port_var,
            state="readonly",
            width=42,
        )
        self.port_combo.grid(row=0, column=1, columnspan=2, sticky="ew", pady=4)

        ttk.Button(main, text="Neu scannen", command=self.refresh_ports).grid(
            row=0, column=3, padx=(6, 0), sticky="ew"
        )

        ttk.Label(main, text="Zielsystem:").grid(row=1, column=0, sticky="w", pady=(8, 4))

        self.platform_combo = ttk.Combobox(
            main,
            textvariable=self.platform_var,
            values=["windows", "macos"],
            state="readonly",
            width=15,
        )
        self.platform_combo.grid(row=1, column=1, sticky="w", pady=(8, 4))

        ttk.Label(main, text="Taste").grid(row=2, column=0, sticky="w", pady=(10, 4))
        ttk.Label(main, text="Typ").grid(row=2, column=1, sticky="w", pady=(10, 4))
        ttk.Label(main, text="Wert").grid(row=2, column=2, sticky="w", pady=(10, 4))

        button_names = [f"BTN_{i}" for i in range(1, 10)]

        for idx, btn in enumerate(button_names, start=3):
            ttk.Label(main, text=btn).grid(row=idx, column=0, sticky="w", pady=2)

            type_var = tk.StringVar(value="url")
            combo = ttk.Combobox(
                main,
                textvariable=type_var,
                values=["url", "app", "path"],
                width=10,
                state="readonly",
            )
            combo.grid(row=idx, column=1, sticky="w", padx=(0, 8))
            self.type_vars[btn] = type_var

            entry = ttk.Entry(main, width=50)
            entry.grid(row=idx, column=2, sticky="ew", pady=2)
            self.entries[btn] = entry

            ttk.Button(main, text="Wählen", command=lambda b=btn: self.pick_value(b)).grid(
                row=idx, column=3, padx=(6, 0)
            )

        info_row = 12
        ttk.Separator(main, orient="horizontal").grid(
            row=info_row, column=0, columnspan=4, sticky="ew", pady=12
        )

        ttk.Label(
            main,
            text="Fest belegt: * = Volume Down, 0 = Mute/Unmute, # = Volume Up",
        ).grid(row=info_row + 1, column=0, columnspan=4, sticky="w")

        ttk.Label(
            main,
            text="ESP32-Events: VOL_DOWN / MUTE_TOGGLE / VOL_UP",
        ).grid(row=info_row + 2, column=0, columnspan=4, sticky="w", pady=(2, 10))

        button_row = info_row + 3
        ttk.Button(main, text="Laden", command=self.load_config).grid(
            row=button_row, column=0, pady=12, sticky="ew"
        )
        ttk.Button(main, text="Speichern", command=self.save_config).grid(
            row=button_row, column=1, pady=12, sticky="ew"
        )
        ttk.Button(main, text="Start", command=self.start_listener).grid(
            row=button_row, column=2, pady=12, sticky="ew"
        )
        ttk.Button(main, text="Stop", command=self.stop_listener).grid(
            row=button_row, column=3, pady=12, sticky="ew"
        )

        self.status_label = ttk.Label(main, text="Bereit")
        self.status_label.grid(row=button_row + 1, column=0, columnspan=4, sticky="w")

        self.volume_label = ttk.Label(main, text="Volume: 50%")
        self.volume_label.grid(row=button_row + 2, column=0, columnspan=4, sticky="w", pady=(6, 0))

        self.now_playing_label = ttk.Label(main, text="Now Playing: Nichts aktiv")
        self.now_playing_label.grid(row=button_row + 3, column=0, columnspan=4, sticky="w", pady=(6, 0))

    def refresh_ports(self):
        if list_ports is None:
            return

        ports = list(list_ports.comports())
        choices = [p.device for p in ports]
        self.port_combo["values"] = choices

        selected = self.auto_detect_port(ports)

        if selected:
            self.port_var.set(selected)
            self.set_status(f"Port gefunden: {selected}")
        elif choices and not self.port_var.get():
            self.port_var.set(choices[0])
            self.set_status(f"Kein ESP32 eindeutig erkannt, nutze: {choices[0]}")
        elif not choices:
            self.port_var.set("")
            self.set_status("Keine seriellen Ports gefunden")

    def auto_detect_port(self, ports):
        preferred_keywords = [
            "usbserial",
            "wch",
            "cp210",
            "silicon labs",
            "ch340",
            "uart",
            "esp32",
            "serial",
        ]

        for p in ports:
            text = f"{p.device} {p.description} {p.manufacturer} {p.hwid}".lower()
            if any(keyword in text for keyword in preferred_keywords):
                return p.device

        return None

    def pick_value(self, button_name):
        action_type = self.type_vars[button_name].get()

        if action_type == "app":
            if self.platform_var.get() == "windows":
                path = filedialog.askopenfilename(
                    filetypes=[("Programme", "*.exe"), ("Alle Dateien", "*.*")]
                )
            else:
                path = filedialog.askopenfilename()
        elif action_type == "path":
            path = filedialog.askdirectory()
        else:
            return

        if path:
            self.entries[button_name].delete(0, tk.END)
            self.entries[button_name].insert(0, path)

    def get_config(self):
        return {
            "serial_port": self.port_var.get().strip(),
            "platform": self.platform_var.get().strip(),
            "buttons": {
                btn: {
                    "type": self.type_vars[btn].get(),
                    "value": self.entries[btn].get().strip(),
                }
                for btn in self.entries
            },
        }

    def save_config(self):
        config = self.get_config()
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        self.set_status("Konfiguration gespeichert")

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self.set_status("Noch keine Konfiguration gespeichert")
            self.update_volume_label()
            self.update_now_playing_label()
            return

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        saved_port = config.get("serial_port", "")
        saved_platform = config.get("platform", "")

        if saved_port and saved_port in self.port_combo["values"]:
            self.port_var.set(saved_port)

        if saved_platform in ["windows", "macos"]:
            self.platform_var.set(saved_platform)

        buttons = config.get("buttons", {})
        for btn, cfg in buttons.items():
            if btn in self.entries:
                self.type_vars[btn].set(cfg.get("type", "url"))
                self.entries[btn].delete(0, tk.END)
                self.entries[btn].insert(0, cfg.get("value", ""))

        self.set_status("Konfiguration geladen")
        self.update_volume_label()
        self.update_now_playing_label()

    def start_listener(self):
        if serial is None:
            messagebox.showerror(
                "Fehler",
                "pyserial ist nicht installiert.\n\nInstalliere es mit:\npip install pyserial",
            )
            return

        if self.running:
            self.set_status("Listener läuft bereits")
            return

        if not self.port_var.get().strip():
            self.refresh_ports()

        if not self.port_var.get().strip():
            messagebox.showerror("Fehler", "Kein serieller Port gefunden.")
            return

        self.running = True
        self.listener_thread = threading.Thread(target=self.listener_loop, daemon=True)
        self.listener_thread.start()

        if self.now_playing_thread is None or not self.now_playing_thread.is_alive():
            self.now_playing_thread = threading.Thread(target=self.now_playing_loop, daemon=True)
            self.now_playing_thread.start()

        self.set_status("Listener gestartet")

    def stop_listener(self):
        self.running = False
        with self.serial_lock:
            try:
                if self.ser and self.ser.is_open:
                    self.ser.close()
            except Exception:
                pass
            self.ser = None
        self.set_status("Listener gestoppt")

    def listener_loop(self):
        while self.running:
            port = self.port_var.get().strip()

            if not port:
                self.root.after(0, self.refresh_ports)
                time.sleep(2)
                port = self.port_var.get().strip()

            try:
                with serial.Serial(port, 115200, timeout=0.2, write_timeout=1) as ser:
                    with self.serial_lock:
                        self.ser = ser

                    time.sleep(2)

                    self.root.after(0, lambda p=port: self.set_status(f"Verbunden: {p}"))

                    while self.running:
                        try:
                            line = ser.readline().decode("utf-8", errors="ignore").strip()
                        except Exception:
                            line = ""

                        if not line:
                            continue

                        print("<- ESP32:", line)
                        self.root.after(0, lambda l=line: self.handle_serial_event(l))

            except Exception as e:
                with self.serial_lock:
                    self.ser = None
                self.root.after(0, lambda err=str(e): self.set_status(f"Verbindungsfehler: {err}"))
                self.root.after(0, self.refresh_ports)
                time.sleep(2)

        with self.serial_lock:
            self.ser = None

    def now_playing_loop(self):
        while self.running:
            try:
                if self.platform_var.get() == "macos":
                    text = self.get_macos_now_playing()
                elif self.platform_var.get() == "windows":
                    text = self.get_windows_now_playing()
                else:
                    text = "Nichts aktiv"

                self.root.after(0, lambda t=text: self.update_now_playing(t))
            except Exception:
                pass

            time.sleep(2)

    def send_to_device(self, line):
        try:
            with self.serial_lock:
                if self.ser and self.ser.is_open:
                    self.ser.write((line + "\n").encode("utf-8"))
                    self.ser.flush()
                    print("-> ESP32:", line)
                    return True
        except Exception as e:
            self.set_status(f"Sende-Fehler: {e}")
        return False

    def handle_serial_event(self, event_name):
        if event_name.startswith("BTN_"):
            self.handle_button(event_name)

        elif event_name == "VOL_UP":
            requested = min(100, self.current_volume + 5)
            ok, actual_volume, actual_muted, err = self.apply_volume(requested)

            if ok:
                self.current_volume = actual_volume
                self.is_muted = actual_muted
                self.update_volume_label()
                self.send_to_device(f"SET_VOL:{self.current_volume}")
                self.send_to_device(f"SET_MUTE:{1 if self.is_muted else 0}")
                self.set_status(f"Volume Up -> {self.current_volume}%")
            else:
                self.set_status(f"Lautstärke-Fehler: {err}")

        elif event_name == "VOL_DOWN":
            requested = max(0, self.current_volume - 5)
            ok, actual_volume, actual_muted, err = self.apply_volume(requested)

            if ok:
                self.current_volume = actual_volume
                self.is_muted = actual_muted
                self.update_volume_label()
                self.send_to_device(f"SET_VOL:{self.current_volume}")
                self.send_to_device(f"SET_MUTE:{1 if self.is_muted else 0}")
                self.set_status(f"Volume Down -> {self.current_volume}%")
            else:
                self.set_status(f"Lautstärke-Fehler: {err}")

        elif event_name == "MUTE_TOGGLE":
            ok, actual_volume, actual_muted, err = self.toggle_mute()

            if ok:
                self.current_volume = actual_volume
                self.is_muted = actual_muted
                self.update_volume_label()
                self.send_to_device(f"SET_VOL:{self.current_volume}")
                self.send_to_device(f"SET_MUTE:{1 if self.is_muted else 0}")
                self.set_status("Mute umgeschaltet")
            else:
                self.set_status(f"Mute-Fehler: {err}")

        elif event_name == "READY":
            self.set_status("ESP32 bereit")
            self.send_to_device(f"STATUS:{self.platform_var.get()}")
            self.sync_volume_from_system()
            self.send_to_device(f"NOW_PLAYING:{self.now_playing[:60]}")

        elif event_name.startswith("ACK:"):
            self.set_status(f"ESP32 bestätigt: {event_name[4:]}")

        else:
            self.set_status(f"Unbekanntes Event: {event_name}")

    def handle_button(self, button_name):
        if button_name not in self.entries:
            self.set_status(f"{button_name}: nicht in GUI konfiguriert")
            return

        action_type = self.type_vars[button_name].get()
        value = self.entries[button_name].get().strip()
        target_platform = self.platform_var.get()

        if not value:
            self.set_status(f"{button_name}: kein Wert gesetzt")
            return

        try:
            if action_type == "url":
                ok = webbrowser.open(value)
                if not ok:
                    raise RuntimeError("URL konnte nicht geöffnet werden")

            elif action_type == "app":
                if not os.path.exists(value):
                    raise FileNotFoundError(f"Datei nicht gefunden: {value}")

                if target_platform == "windows":
                    subprocess.Popen([value], shell=False)
                elif target_platform == "macos":
                    subprocess.Popen(["open", value])
                else:
                    raise RuntimeError(f"Unbekanntes Zielsystem: {target_platform}")

            elif action_type == "path":
                if not os.path.exists(value):
                    raise FileNotFoundError(f"Pfad nicht gefunden: {value}")

                if target_platform == "windows":
                    os.startfile(value)
                elif target_platform == "macos":
                    subprocess.Popen(["open", value])
                else:
                    raise RuntimeError(f"Unbekanntes Zielsystem: {target_platform}")

            self.set_status(f"{button_name} ausgeführt: {value}")

        except Exception as e:
            self.set_status(f"Fehler bei {button_name}: {e}")

    def get_windows_endpoint(self):
        if AudioUtilities is None:
            raise RuntimeError("pycaw ist nicht installiert")
        device = AudioUtilities.GetSpeakers()
        if device is None:
            raise RuntimeError("Kein Standard-Ausgabegerät gefunden")
        return device.EndpointVolume

    def get_windows_audio_state(self):
        endpoint = self.get_windows_endpoint()
        volume = int(round(endpoint.GetMasterVolumeLevelScalar() * 100))
        muted = bool(endpoint.GetMute())
        return endpoint, volume, muted

    def get_windows_now_playing(self):
        if gw is None:
            return "PyGetWindow fehlt"

        try:
            win = gw.getActiveWindow()
            if win is None:
                return "Nichts aktiv"

            title = (win.title or "").strip()
            if not title:
                return "Nichts aktiv"

            suffixes = [
                " - Google Chrome",
                " - Microsoft Edge",
                " - Mozilla Firefox",
                " - Brave",
                " - Opera",
            ]

            for suffix in suffixes:
                if title.endswith(suffix):
                    title = title[:-len(suffix)].strip()
                    break

            if not title:
                return "Nichts aktiv"

            return title
        except Exception as e:
            return f"Fehler: {e}"

    def get_macos_audio_state(self):
        vol_result = subprocess.run(
            ["osascript", "-e", "output volume of (get volume settings)"],
            capture_output=True,
            text=True,
            check=True,
        )
        mute_result = subprocess.run(
            ["osascript", "-e", "output muted of (get volume settings)"],
            capture_output=True,
            text=True,
            check=True,
        )

        volume = int(vol_result.stdout.strip())
        muted = mute_result.stdout.strip().lower() == "true"
        return volume, muted

    def get_macos_now_playing(self):
        scripts = [
            '''
            tell application "Spotify"
                if it is running and player state is playing then
                    return artist of current track & " - " & name of current track
                end if
            end tell
            ''',
            '''
            tell application "Music"
                if it is running and player state is playing then
                    return artist of current track & " - " & name of current track
                end if
            end tell
            '''
        ]

        for script in scripts:
            try:
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                text = result.stdout.strip()
                if text:
                    return text
            except Exception:
                pass

        return "Nichts aktiv"

    def sync_volume_from_system(self):
        try:
            if self.platform_var.get() == "windows":
                _, self.current_volume, self.is_muted = self.get_windows_audio_state()
            elif self.platform_var.get() == "macos":
                self.current_volume, self.is_muted = self.get_macos_audio_state()

            self.update_volume_label()
            self.send_to_device(f"SET_VOL:{self.current_volume}")
            self.send_to_device(f"SET_MUTE:{1 if self.is_muted else 0}")

        except Exception as e:
            self.set_status(f"Sync-Fehler: {e}")

    def apply_volume(self, volume):
        volume = max(0, min(100, volume))
        target_platform = self.platform_var.get()

        if target_platform == "macos":
            try:
                subprocess.run(
                    ["osascript", "-e", f"set volume output volume {volume}"],
                    check=True,
                )
                actual_volume, actual_muted = self.get_macos_audio_state()
                return True, actual_volume, actual_muted, None
            except Exception as e:
                return False, None, None, str(e)

        elif target_platform == "windows":
            try:
                endpoint, _, _ = self.get_windows_audio_state()
                endpoint.SetMasterVolumeLevelScalar(float(volume / 100.0), None)
                _, actual_volume, actual_muted = self.get_windows_audio_state()
                return True, actual_volume, actual_muted, None
            except Exception as e:
                return False, None, None, str(e)

        return False, None, None, f"Unbekanntes Zielsystem: {target_platform}"

    def toggle_mute(self):
        target_platform = self.platform_var.get()

        if target_platform == "macos":
            try:
                _, muted = self.get_macos_audio_state()
                if muted:
                    subprocess.run(["osascript", "-e", "set volume without output muted"], check=True)
                else:
                    subprocess.run(["osascript", "-e", "set volume with output muted"], check=True)

                actual_volume, actual_muted = self.get_macos_audio_state()
                return True, actual_volume, actual_muted, None
            except Exception as e:
                return False, None, None, str(e)

        elif target_platform == "windows":
            try:
                endpoint, actual_volume, actual_muted = self.get_windows_audio_state()
                endpoint.SetMute(0 if actual_muted else 1, None)
                _, new_volume, new_muted = self.get_windows_audio_state()
                return True, new_volume, new_muted, None
            except Exception as e:
                return False, None, None, str(e)

        return False, None, None, f"Unbekanntes Zielsystem: {target_platform}"

    def update_volume_label(self):
        if self.is_muted:
            self.volume_label.config(text=f"Volume: {self.current_volume}% (Muted)")
        else:
            self.volume_label.config(text=f"Volume: {self.current_volume}%")

    def update_now_playing(self, text):
        text = (text or "").strip()
        if not text:
            text = "Nichts aktiv"

        if text != self.now_playing:
            self.now_playing = text
            self.update_now_playing_label()
            self.send_to_device(f"NOW_PLAYING:{text[:60]}")

    def update_now_playing_label(self):
        self.now_playing_label.config(text=f"Now Playing: {self.now_playing}")

    def set_status(self, text):
        self.status_label.config(text=text)


if __name__ == "__main__":
    root = tk.Tk()
    app = WebPadApp(root)
    root.mainloop()