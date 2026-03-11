import ctypes
import json
import os
import sys
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
        self.root.title("FreakDeck")
        self.root.geometry("1180x760")
        self.root.minsize(1080, 700)

        self.listener_thread = None
        self.now_playing_thread = None
        self.running = False

        self.current_volume = 50
        self.is_muted = False
        self.now_playing = "Nothing active"

        self.ser = None
        self.serial_lock = threading.Lock()

        self.port_var = tk.StringVar(value="")
        self.platform_var = tk.StringVar(value="windows")

        self.status_var = tk.StringVar(value="Ready")
        self.device_status_var = tk.StringVar(value="Not connected")
        self.volume_var = tk.StringVar(value="Volume: 50%")
        self.now_playing_var = tk.StringVar(value="Now Playing: Nothing active")

        self.entries = {}
        self.type_vars = {}

        self._icon_image = None

        self.configure_theme()
        self.apply_app_icon()
        self.build_ui()
        self.refresh_ports()
        self.load_config()

    @staticmethod
    def resource_path(relative_path):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def apply_app_icon(self):
        png_candidates = [
            self.resource_path(os.path.join("assets", "FreakDeck.png")),
            self.resource_path("FreakDeck.png"),
        ]

        for png_path in png_candidates:
            if os.path.exists(png_path):
                try:
                    self._icon_image = tk.PhotoImage(file=png_path)
                    self.root.iconphoto(True, self._icon_image)
                    return
                except Exception:
                    pass

        ico_candidates = [
            self.resource_path(os.path.join("assets", "FreakDeck.ico")),
            self.resource_path("FreakDeck.ico"),
        ]

        for ico_path in ico_candidates:
            if os.path.exists(ico_path):
                try:
                    self.root.iconbitmap(default=ico_path)
                    return
                except Exception:
                    try:
                        self.root.iconbitmap(ico_path)
                        return
                    except Exception:
                        pass

    def set_status(self, text):
        self.status_var.set(text)

    def append_log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def configure_theme(self):
        self.root.configure(bg="#0f172a")

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#111827")
        style.configure("Header.TFrame", background="#111827")

        style.configure(
            "Title.TLabel",
            background="#111827",
            foreground="#f8fafc",
            font=("Segoe UI", 20, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background="#111827",
            foreground="#94a3b8",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Section.TLabel",
            background="#111827",
            foreground="#e2e8f0",
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "Muted.TLabel",
            background="#111827",
            foreground="#94a3b8",
            font=("Segoe UI", 10),
        )
        style.configure(
            "LiveValue.TLabel",
            background="#111827",
            foreground="#f8fafc",
            font=("Segoe UI", 11, "bold"),
        )

        style.configure(
            "Card.TLabelframe",
            background="#111827",
            foreground="#e2e8f0",
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Card.TLabelframe.Label",
            background="#111827",
            foreground="#e2e8f0",
            font=("Segoe UI", 10, "bold"),
        )

        style.configure(
            "TLabel",
            background="#0f172a",
            foreground="#e2e8f0",
        )

        style.configure(
            "TButton",
            background="#2563eb",
            foreground="#ffffff",
            borderwidth=0,
            focusthickness=0,
            padding=(10, 8),
        )
        style.map(
            "TButton",
            background=[("active", "#1d4ed8"), ("pressed", "#1e40af")],
            foreground=[("disabled", "#94a3b8")],
        )

        style.configure(
            "Secondary.TButton",
            background="#334155",
            foreground="#ffffff",
            padding=(10, 8),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#475569"), ("pressed", "#1f2937")],
        )

        style.configure(
            "Danger.TButton",
            background="#b91c1c",
            foreground="#ffffff",
            padding=(10, 8),
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#dc2626"), ("pressed", "#991b1b")],
        )

        style.configure(
            "TEntry",
            fieldbackground="#0b1220",
            foreground="#f8fafc",
            bordercolor="#334155",
            insertcolor="#f8fafc",
            padding=6,
        )
        style.configure(
            "TCombobox",
            fieldbackground="#0b1220",
            foreground="#f8fafc",
            arrowcolor="#f8fafc",
            padding=6,
        )

    def build_ui(self):
        main = ttk.Frame(self.root, padding=16, style="TFrame")
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main, padding=16, style="Header.TFrame")
        header.pack(fill="x", pady=(0, 14))

        ttk.Label(header, text="FreakDeck", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Windows-focused control app with live device sync, media title, and hardware volume control",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(main, style="TFrame")
        body.pack(fill="both", expand=True)

        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, style="TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        right = ttk.Frame(body, style="TFrame")
        right.grid(row=0, column=1, sticky="nsew")

        self.build_device_card(left)
        self.build_mappings_card(left)

        self.build_live_status_card(right)
        self.build_quick_actions_card(right)
        self.build_log_card(right)

        footer = ttk.Frame(main, padding=(12, 10), style="Header.TFrame")
        footer.pack(fill="x", pady=(14, 0))

        ttk.Label(footer, textvariable=self.status_var, style="Subtitle.TLabel").pack(side="left")

    def build_device_card(self, parent):
        card = ttk.LabelFrame(parent, text="Device & platform", padding=14, style="Card.TLabelframe")
        card.pack(fill="x", pady=(0, 10))

        card.columnconfigure(1, weight=1)
        card.columnconfigure(3, weight=1)

        ttk.Label(card, text="Serial port").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        self.port_combo = ttk.Combobox(card, textvariable=self.port_var, state="readonly", width=24)
        self.port_combo.grid(row=0, column=1, sticky="ew", pady=6)

        ttk.Label(card, text="Platform").grid(row=0, column=2, sticky="w", padx=(14, 10), pady=6)
        self.platform_combo = ttk.Combobox(
            card,
            textvariable=self.platform_var,
            values=["windows", "macos"],
            state="readonly",
            width=16,
        )
        self.platform_combo.grid(row=0, column=3, sticky="ew", pady=6)

        buttons = ttk.Frame(card, style="Card.TFrame")
        buttons.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        buttons.columnconfigure((0, 1, 2, 3, 4), weight=1)

        ttk.Button(buttons, text="Rescan", style="Secondary.TButton", command=self.refresh_ports).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(buttons, text="Connect", command=self.start_listener).grid(
            row=0, column=1, sticky="ew", padx=6
        )
        ttk.Button(buttons, text="Disconnect", style="Danger.TButton", command=self.stop_listener).grid(
            row=0, column=2, sticky="ew", padx=6
        )
        ttk.Button(buttons, text="Load config", style="Secondary.TButton", command=self.load_config).grid(
            row=0, column=3, sticky="ew", padx=6
        )
        ttk.Button(buttons, text="Save config", style="Secondary.TButton", command=self.save_config).grid(
            row=0, column=4, sticky="ew", padx=(6, 0)
        )

        note = ttk.Label(
            card,
            text="Reserved device keys: * = volume down, 0 = mute / unmute, # = volume up",
            style="Muted.TLabel",
        )
        note.grid(row=2, column=0, columnspan=4, sticky="w", pady=(12, 0))

    def build_mappings_card(self, parent):
        card = ttk.LabelFrame(parent, text="Button mappings", padding=14, style="Card.TLabelframe")
        card.pack(fill="both", expand=True)

        topbar = ttk.Frame(card, style="Card.TFrame")
        topbar.pack(fill="x", pady=(0, 10))

        ttk.Label(
            topbar,
            text="Configure BTN_1 to BTN_9. Keep the functionality, just map what each button should launch.",
            style="Muted.TLabel",
        ).pack(side="left")

        action_bar = ttk.Frame(card, style="Card.TFrame")
        action_bar.pack(fill="x", pady=(0, 10))

        ttk.Button(action_bar, text="Starter preset", style="Secondary.TButton", command=self.apply_web_preset).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(action_bar, text="Clear all", style="Secondary.TButton", command=self.clear_mappings).pack(
            side="left"
        )

        grid = ttk.Frame(card, style="Card.TFrame")
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(2, weight=1)

        headers = ["Button", "Type", "Value", "", ""]
        for col, title in enumerate(headers):
            ttk.Label(grid, text=title, style="Section.TLabel").grid(
                row=0, column=col, sticky="w", padx=4, pady=(0, 8)
            )

        for idx, btn in enumerate([f"BTN_{i}" for i in range(1, 10)], start=1):
            ttk.Label(grid, text=btn).grid(row=idx, column=0, sticky="w", padx=4, pady=6)

            type_var = tk.StringVar(value="url")
            combo = ttk.Combobox(
                grid,
                textvariable=type_var,
                values=["url", "app", "path"],
                state="readonly",
                width=10,
            )
            combo.grid(row=idx, column=1, sticky="w", padx=4, pady=6)
            self.type_vars[btn] = type_var

            entry = ttk.Entry(grid)
            entry.grid(row=idx, column=2, sticky="ew", padx=4, pady=6)
            self.entries[btn] = entry

            ttk.Button(
                grid,
                text="Browse",
                style="Secondary.TButton",
                command=lambda b=btn: self.pick_value(b),
            ).grid(row=idx, column=3, sticky="ew", padx=4, pady=6)

            ttk.Button(
                grid,
                text="Test",
                style="Secondary.TButton",
                command=lambda b=btn: self.test_mapping(b),
            ).grid(row=idx, column=4, sticky="ew", padx=4, pady=6)

    def build_live_status_card(self, parent):
        card = ttk.LabelFrame(parent, text="Live status", padding=14, style="Card.TLabelframe")
        card.pack(fill="x", pady=(0, 10))

        ttk.Label(card, text="Device", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=self.device_status_var, style="LiveValue.TLabel").pack(anchor="w", pady=(2, 10))

        ttk.Label(card, text="Volume", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=self.volume_var, style="LiveValue.TLabel").pack(anchor="w", pady=(2, 10))

        ttk.Label(card, text="Now playing", style="Muted.TLabel").pack(anchor="w")
        self.now_playing_label = ttk.Label(
            card,
            textvariable=self.now_playing_var,
            style="LiveValue.TLabel",
            wraplength=360,
            justify="left",
        )
        self.now_playing_label.pack(anchor="w", pady=(2, 0))

    def build_quick_actions_card(self, parent):
        card = ttk.LabelFrame(parent, text="Quick actions", padding=14, style="Card.TLabelframe")
        card.pack(fill="x", pady=(0, 10))

        ttk.Button(card, text="Sync volume from system", command=self.sync_volume_from_system).pack(
            fill="x", pady=(0, 8)
        )
        ttk.Button(card, text="Refresh now playing", style="Secondary.TButton", command=self.manual_refresh_now_playing).pack(
            fill="x", pady=(0, 8)
        )
        ttk.Button(card, text="Rescan ports", style="Secondary.TButton", command=self.refresh_ports).pack(
            fill="x", pady=(0, 8)
        )
        ttk.Button(card, text="Save config", style="Secondary.TButton", command=self.save_config).pack(
            fill="x"
        )

    def build_log_card(self, parent):
        card = ttk.LabelFrame(parent, text="Live log", padding=14, style="Card.TLabelframe")
        card.pack(fill="both", expand=True)

        text_frame = ttk.Frame(card, style="Card.TFrame")
        text_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            text_frame,
            bg="#0b1220",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            relief="flat",
            borderwidth=0,
            wrap="word",
            font=("Consolas", 10),
            yscrollcommand=scrollbar.set,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_text.configure(state="disabled")

        scrollbar.config(command=self.log_text.yview)

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
        self.set_status("Configuration saved.")
        self.append_log("[INFO] Configuration saved.")

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self.set_status("No saved configuration found yet.")
            self.update_volume_label()
            self.update_now_playing_label()
            return

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        saved_port = config.get("serial_port", "")
        saved_platform = config.get("platform", "")

        if saved_port and hasattr(self, "port_combo") and saved_port in self.port_combo["values"]:
            self.port_var.set(saved_port)

        if saved_platform in ["windows", "macos"]:
            self.platform_var.set(saved_platform)

        buttons = config.get("buttons", {})
        for btn, cfg in buttons.items():
            if btn in self.entries:
                self.type_vars[btn].set(cfg.get("type", "url"))
                self.entries[btn].delete(0, tk.END)
                self.entries[btn].insert(0, cfg.get("value", ""))

        self.set_status("Configuration loaded.")
        self.append_log("[INFO] Configuration loaded.")
        self.update_volume_label()
        self.update_now_playing_label()

    def apply_web_preset(self):
        preset = {
            "BTN_1": ("url", "https://www.google.com"),
            "BTN_2": ("url", "https://www.youtube.com"),
            "BTN_3": ("url", "https://chatgpt.com"),
            "BTN_4": ("url", "https://mail.google.com"),
            "BTN_5": ("url", "https://calendar.google.com"),
            "BTN_6": ("url", "https://github.com"),
            "BTN_7": ("url", "https://www.wikipedia.org"),
            "BTN_8": ("url", "https://open.spotify.com"),
            "BTN_9": ("url", "https://www.linkedin.com"),
        }

        for btn, (kind, value) in preset.items():
            self.type_vars[btn].set(kind)
            self.entries[btn].delete(0, tk.END)
            self.entries[btn].insert(0, value)

        self.set_status("Starter preset applied.")
        self.append_log("[INFO] Starter preset applied.")

    def clear_mappings(self):
        for btn in self.entries:
            self.type_vars[btn].set("url")
            self.entries[btn].delete(0, tk.END)

        self.set_status("All mappings cleared.")
        self.append_log("[INFO] All mappings cleared.")

    def pick_value(self, button_name):
        action_type = self.type_vars[button_name].get()

        if action_type == "app":
            if self.platform_var.get() == "windows":
                path = filedialog.askopenfilename(
                    filetypes=[("Applications", "*.exe"), ("All files", "*.*")]
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

    def test_mapping(self, button_name):
        if button_name not in self.entries:
            return

        action_type = self.type_vars[button_name].get()
        value = self.entries[button_name].get().strip()
        self.execute_mapping(button_name, action_type, value)

    def execute_mapping(self, button_name, action_type, value):
        target_platform = self.platform_var.get()

        if not value:
            self.set_status(f"{button_name}: no value set.")
            return

        try:
            if action_type == "url":
                ok = webbrowser.open(value)
                if not ok:
                    raise RuntimeError("URL could not be opened.")

            elif action_type == "app":
                if not os.path.exists(value):
                    raise FileNotFoundError(f"File not found: {value}")

                if target_platform == "windows":
                    subprocess.Popen([value], shell=False)
                elif target_platform == "macos":
                    subprocess.Popen(["open", value])
                else:
                    raise RuntimeError(f"Unknown platform: {target_platform}")

            elif action_type == "path":
                if not os.path.exists(value):
                    raise FileNotFoundError(f"Path not found: {value}")

                if target_platform == "windows":
                    os.startfile(value)
                elif target_platform == "macos":
                    subprocess.Popen(["open", value])
                else:
                    raise RuntimeError(f"Unknown platform: {target_platform}")

            self.set_status(f"{button_name} executed.")
            self.append_log(f"[ACTION] {button_name} -> {action_type}: {value}")
        except Exception as e:
            self.set_status(f"Error on {button_name}: {e}")
            self.append_log(f"[ERROR] {button_name}: {e}")

    def refresh_ports(self):
        if list_ports is None:
            return

        ports = list(list_ports.comports())
        choices = [p.device for p in ports]
        self.port_combo["values"] = choices

        selected = self.auto_detect_port(ports)

        if selected:
            self.port_var.set(selected)
            self.set_status(f"Port found: {selected}")
        elif choices and not self.port_var.get():
            self.port_var.set(choices[0])
            self.set_status(f"No clear ESP32 match, using: {choices[0]}")
        elif not choices:
            self.port_var.set("")
            self.set_status("No serial ports found.")

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

    def start_listener(self):
        if serial is None:
            messagebox.showerror(
                "Error",
                "pyserial is not installed.\n\nInstall it with:\npip install pyserial",
            )
            return

        if self.running:
            self.set_status("Listener already running.")
            return

        if not self.port_var.get().strip():
            self.refresh_ports()

        if not self.port_var.get().strip():
            messagebox.showerror("Error", "No serial port found.")
            return

        self.running = True
        self.listener_thread = threading.Thread(target=self.listener_loop, daemon=True)
        self.listener_thread.start()

        if self.now_playing_thread is None or not self.now_playing_thread.is_alive():
            self.now_playing_thread = threading.Thread(target=self.now_playing_loop, daemon=True)
            self.now_playing_thread.start()

        self.set_status("Connecting...")
        self.append_log("[INFO] Starting listener...")

    def stop_listener(self):
        self.running = False
        with self.serial_lock:
            try:
                if self.ser and self.ser.is_open:
                    self.ser.close()
            except Exception:
                pass
            self.ser = None

        self.device_status_var.set("Not connected")
        self.set_status("Disconnected.")
        self.append_log("[INFO] Disconnected.")

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

                    self.root.after(0, lambda p=port: self.device_status_var.set(f"Connected: {p}"))
                    self.root.after(0, lambda p=port: self.set_status(f"Connected to {p}."))
                    self.root.after(0, lambda p=port: self.append_log(f"[INFO] Connected to {p}"))

                    while self.running:
                        try:
                            line = ser.readline().decode("utf-8", errors="ignore").strip()
                        except Exception:
                            line = ""

                        if not line:
                            continue

                        self.root.after(0, lambda l=line: self.append_log(f"<- {l}"))
                        self.root.after(0, lambda l=line: self.handle_serial_event(l))

            except Exception as e:
                with self.serial_lock:
                    self.ser = None

                self.root.after(0, lambda: self.device_status_var.set("Not connected"))
                self.root.after(0, lambda err=str(e): self.set_status(f"Connection error: {err}"))
                self.root.after(0, lambda err=str(e): self.append_log(f"[ERROR] {err}"))
                self.root.after(0, self.refresh_ports)
                time.sleep(2)

        with self.serial_lock:
            self.ser = None

    def send_to_device(self, line):
        try:
            with self.serial_lock:
                if self.ser and self.ser.is_open:
                    self.ser.write((line + "\n").encode("utf-8"))
                    self.ser.flush()
                    self.append_log(f"-> {line}")
                    return True
        except Exception as e:
            self.set_status(f"Send error: {e}")
            self.append_log(f"[ERROR] Send failed: {e}")
        return False

    def now_playing_loop(self):
        while self.running:
            try:
                if self.platform_var.get() == "macos":
                    text = self.get_macos_now_playing()
                elif self.platform_var.get() == "windows":
                    text = self.get_windows_now_playing()
                else:
                    text = "Nothing active"

                self.root.after(0, lambda t=text: self.update_now_playing(t))
            except Exception:
                pass

            time.sleep(2)

    def manual_refresh_now_playing(self):
        try:
            if self.platform_var.get() == "macos":
                text = self.get_macos_now_playing()
            elif self.platform_var.get() == "windows":
                text = self.get_windows_now_playing()
            else:
                text = "Nothing active"

            self.update_now_playing(text)
            self.set_status("Now playing refreshed.")
            self.append_log("[INFO] Now playing refreshed.")
        except Exception as e:
            self.set_status(f"Now playing error: {e}")
            self.append_log(f"[ERROR] Now playing refresh failed: {e}")

    def get_windows_now_playing(self):
        if gw is None:
            return "PyGetWindow not installed"

        try:
            win = gw.getActiveWindow()
            if win is None:
                return "Nothing active"

            title = (win.title or "").strip()
            if not title:
                return "Nothing active"

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
                return "Nothing active"

            return title
        except Exception as e:
            return f"Error: {e}"

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

        return "Nothing active"

    def handle_serial_event(self, event_name):
        if event_name.startswith("BTN_"):
            if event_name in self.entries:
                action_type = self.type_vars[event_name].get()
                value = self.entries[event_name].get().strip()
                self.execute_mapping(event_name, action_type, value)

        elif event_name == "VOL_UP":
            requested = min(100, self.current_volume + 5)
            ok, actual_volume, actual_muted, err = self.apply_volume(requested)

            if ok:
                self.current_volume = actual_volume
                self.is_muted = actual_muted
                self.update_volume_label()
                self.send_to_device(f"SET_VOL:{self.current_volume}")
                self.send_to_device(f"SET_MUTE:{1 if self.is_muted else 0}")
                self.set_status(f"Volume up -> {self.current_volume}%")
            else:
                self.set_status(f"Volume error: {err}")
                self.append_log(f"[ERROR] Volume up failed: {err}")

        elif event_name == "VOL_DOWN":
            requested = max(0, self.current_volume - 5)
            ok, actual_volume, actual_muted, err = self.apply_volume(requested)

            if ok:
                self.current_volume = actual_volume
                self.is_muted = actual_muted
                self.update_volume_label()
                self.send_to_device(f"SET_VOL:{self.current_volume}")
                self.send_to_device(f"SET_MUTE:{1 if self.is_muted else 0}")
                self.set_status(f"Volume down -> {self.current_volume}%")
            else:
                self.set_status(f"Volume error: {err}")
                self.append_log(f"[ERROR] Volume down failed: {err}")

        elif event_name == "MUTE_TOGGLE":
            ok, actual_volume, actual_muted, err = self.toggle_mute()

            if ok:
                self.current_volume = actual_volume
                self.is_muted = actual_muted
                self.update_volume_label()
                self.send_to_device(f"SET_VOL:{self.current_volume}")
                self.send_to_device(f"SET_MUTE:{1 if self.is_muted else 0}")
                self.set_status("Mute toggled.")
            else:
                self.set_status(f"Mute error: {err}")
                self.append_log(f"[ERROR] Mute toggle failed: {err}")

        elif event_name == "READY":
            self.set_status("Device ready.")
            self.send_to_device(f"STATUS:{self.platform_var.get()}")
            self.sync_volume_from_system()
            self.send_to_device(f"NOW_PLAYING:{self.now_playing[:60]}")

        elif event_name.startswith("ACK:"):
            self.set_status(f"Device confirmed: {event_name[4:]}")

        else:
            self.set_status(f"Unknown event: {event_name}")

    def get_windows_endpoint(self):
        if AudioUtilities is None:
            raise RuntimeError("pycaw is not installed")
        device = AudioUtilities.GetSpeakers()
        if device is None:
            raise RuntimeError("No default output device found")
        return device.EndpointVolume

    def get_windows_audio_state(self):
        endpoint = self.get_windows_endpoint()
        volume = int(round(endpoint.GetMasterVolumeLevelScalar() * 100))
        muted = bool(endpoint.GetMute())
        return endpoint, volume, muted

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

    def sync_volume_from_system(self):
        try:
            if self.platform_var.get() == "windows":
                _, self.current_volume, self.is_muted = self.get_windows_audio_state()
            elif self.platform_var.get() == "macos":
                self.current_volume, self.is_muted = self.get_macos_audio_state()

            self.update_volume_label()
            self.send_to_device(f"SET_VOL:{self.current_volume}")
            self.send_to_device(f"SET_MUTE:{1 if self.is_muted else 0}")
            self.append_log("[INFO] Synced volume from system.")
        except Exception as e:
            self.set_status(f"Sync error: {e}")
            self.append_log(f"[ERROR] Volume sync failed: {e}")

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

        return False, None, None, f"Unknown platform: {target_platform}"

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

        return False, None, None, f"Unknown platform: {target_platform}"

    def update_volume_label(self):
        if self.is_muted:
            self.volume_var.set(f"Volume: {self.current_volume}% (Muted)")
        else:
            self.volume_var.set(f"Volume: {self.current_volume}%")

    def update_now_playing(self, text):
        text = (text or "").strip()
        if not text:
            text = "Nothing active"

        if text != self.now_playing:
            self.now_playing = text
            self.update_now_playing_label()
            self.send_to_device(f"NOW_PLAYING:{text[:60]}")

    def update_now_playing_label(self):
        self.now_playing_var.set(f"Now Playing: {self.now_playing}")


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FreakDeck.App")
        except Exception:
            pass

    root = tk.Tk()
    app = WebPadApp(root)
    root.mainloop()