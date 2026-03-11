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
APP_TITLE = "FreakDeck"
APP_ICON_ICO = os.path.join("assets", "FreakDeck.ico")


class WebPadApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
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
        self.status_var = tk.StringVar(value="Ready")
        self.device_status_var = tk.StringVar(value="Not connected")
        self.volume_var = tk.StringVar(value="Volume: 50%")
        self.now_playing_var = tk.StringVar(value="Now Playing: Nothing active")

        self.entries = {}
        self.type_vars = {}
        self.port_choices = []
        self.port_dropdown = None
        self.type_dropdowns = {}

        self.configure_styles()
        self.build_ui()
        self.apply_icon()
        self.refresh_ports()
        self.load_config()

    # ----------------------------
    # General helpers
    # ----------------------------

    def resource_path(self, relative_path: str) -> str:
        base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
        return os.path.join(base_path, relative_path)

    def apply_icon(self) -> None:
        try:
            icon_path = self.resource_path(APP_ICON_ICO)
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

    def configure_styles(self) -> None:
        self.root.configure(bg="#0f172a")

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", background="#0f172a", foreground="#e5e7eb")
        style.configure("TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#111827")
        style.configure("TLabel", background="#0f172a", foreground="#e5e7eb", font=("Segoe UI", 11))
        style.configure("Muted.TLabel", background="#0f172a", foreground="#94a3b8", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#0f172a", foreground="#f8fafc", font=("Segoe UI", 24, "bold"))
        style.configure("Section.TLabel", background="#111827", foreground="#f8fafc", font=("Segoe UI", 11, "bold"))
        style.configure("Value.TLabel", background="#111827", foreground="#e5e7eb", font=("Segoe UI", 11))

        style.configure(
            "Accent.TButton",
            background="#2563eb",
            foreground="#ffffff",
            borderwidth=0,
            font=("Segoe UI", 11, "bold"),
            padding=(12, 8),
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#1d4ed8"), ("pressed", "#1e40af")],
            foreground=[("disabled", "#9ca3af")],
        )

        style.configure(
            "Secondary.TButton",
            background="#1f2937",
            foreground="#ffffff",
            borderwidth=1,
            font=("Segoe UI", 10),
            padding=(12, 8),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#374151"), ("pressed", "#4b5563")],
            foreground=[("disabled", "#9ca3af")],
        )

        style.configure(
            "Card.TLabelframe",
            background="#111827",
            foreground="#f8fafc",
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Card.TLabelframe.Label",
            background="#111827",
            foreground="#f8fafc",
            font=("Segoe UI", 11, "bold"),
        )

    def make_dropdown(self, parent, variable: tk.StringVar, width: int = 18):
        btn = tk.Menubutton(
            parent,
            textvariable=variable,
            indicatoron=True,
            direction="below",
            anchor="w",
            relief="solid",
            bd=1,
            bg="#ffffff",
            fg="#111827",
            activebackground="#f8fafc",
            activeforeground="#111827",
            highlightthickness=1,
            highlightbackground="#cbd5e1",
            highlightcolor="#2563eb",
            padx=10,
            pady=7,
            width=width,
            font=("Segoe UI", 10),
            cursor="hand2",
        )

        menu = tk.Menu(
            btn,
            tearoff=False,
            bg="#ffffff",
            fg="#111827",
            activebackground="#2563eb",
            activeforeground="#ffffff",
            bd=1,
            font=("Segoe UI", 10),
        )
        btn.configure(menu=menu)
        return btn

    def update_dropdown_choices(self, dropdown, variable: tk.StringVar, choices, preferred=None):
        menu = dropdown.nametowidget(dropdown["menu"])
        menu.delete(0, "end")

        if not choices:
            choices = [""]

        for choice in choices:
            menu.add_command(
                label=choice,
                command=lambda c=choice: variable.set(c)
            )

        current = variable.get().strip()
        if preferred and preferred in choices:
            variable.set(preferred)
        elif current in choices:
            variable.set(current)
        else:
            variable.set(choices[0])

    # ----------------------------
    # UI
    # ----------------------------

    def build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 14))

        ttk.Label(header, text="FreakDeck", style="Title.TLabel").pack(anchor="w")

        content = ttk.Frame(outer)
        content.pack(fill="both", expand=True)

        left_col = ttk.Frame(content)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right_col = ttk.Frame(content)
        right_col.pack(side="right", fill="both", expand=False)

        self.build_device_card(left_col)
        self.build_mappings_card(left_col)

        self.build_live_card(right_col)
        self.build_quick_actions_card(right_col)
        self.build_log_card(right_col)

        status_bar = ttk.Frame(outer)
        status_bar.pack(fill="x", pady=(12, 0))

        ttk.Label(status_bar, textvariable=self.status_var, style="Muted.TLabel").pack(anchor="w")

    def build_device_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text="Connection", style="Card.TLabelframe", padding=14)
        card.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(card, style="Card.TFrame")
        inner.pack(fill="x")

        row1 = ttk.Frame(inner, style="Card.TFrame")
        row1.pack(fill="x", pady=(0, 10))

        ttk.Label(row1, text="Serial port", style="Section.TLabel").pack(side="left")

        self.port_dropdown = self.make_dropdown(row1, self.port_var, width=28)
        self.port_dropdown.pack(side="left", padx=(10, 10))

        ttk.Button(row1, text="Rescan", style="Secondary.TButton", command=self.refresh_ports).pack(side="left", padx=(0, 8))
        ttk.Button(row1, text="Connect", style="Accent.TButton", command=self.start_listener).pack(side="left", padx=(0, 8))
        ttk.Button(row1, text="Disconnect", style="Secondary.TButton", command=self.stop_listener).pack(side="left")

        row2 = ttk.Frame(inner, style="Card.TFrame")
        row2.pack(fill="x")

        ttk.Label(row2, text="Device status", style="Section.TLabel").pack(side="left")
        ttk.Label(row2, textvariable=self.device_status_var, style="Value.TLabel").pack(side="left", padx=(10, 0))

    def build_mappings_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text="Button Mappings", style="Card.TLabelframe", padding=14)
        card.pack(fill="both", expand=True)

        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x", pady=(0, 12))

        ttk.Label(
            top,
            text="Buttons 1–9 are configurable. * / 0 / # remain Volume Down / Mute / Volume Up.",
            style="Value.TLabel",
        ).pack(side="left")

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.pack(fill="x", pady=(0, 12))

        ttk.Button(actions, text="Load", style="Secondary.TButton", command=self.load_config).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Save", style="Accent.TButton", command=self.save_config).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Starter Web Preset", style="Secondary.TButton", command=self.apply_web_preset).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Clear All", style="Secondary.TButton", command=self.clear_mappings).pack(side="left")

        table = ttk.Frame(card, style="Card.TFrame")
        table.pack(fill="both", expand=True)

        headers = ["Button", "Type", "Target", "Browse", "Test"]

        for col, header in enumerate(headers):
            ttk.Label(table, text=header, style="Section.TLabel").grid(row=0, column=col, sticky="w", padx=4, pady=(0, 8))

        for idx, btn in enumerate([f"BTN_{i}" for i in range(1, 10)], start=1):
            ttk.Label(table, text=btn, style="Value.TLabel").grid(row=idx, column=0, sticky="w", padx=4, pady=6)

            type_var = tk.StringVar(value="url")
            dropdown = self.make_dropdown(table, type_var, width=10)
            self.update_dropdown_choices(dropdown, type_var, ["url", "app", "path"])
            dropdown.grid(row=idx, column=1, sticky="ew", padx=4, pady=6)

            self.type_vars[btn] = type_var
            self.type_dropdowns[btn] = dropdown

            entry = tk.Entry(
                table,
                bg="#0b1220",
                fg="#ffffff",
                insertbackground="#ffffff",
                relief="solid",
                highlightthickness=1,
                highlightbackground="#475569",
                highlightcolor="#60a5fa",
                bd=0,
                font=("Segoe UI", 11),
            )
            entry.grid(row=idx, column=2, sticky="ew", padx=4, pady=6, ipady=8)
            self.entries[btn] = entry

            ttk.Button(table, text="Browse", style="Secondary.TButton", command=lambda b=btn: self.pick_value(b)).grid(
                row=idx, column=3, sticky="ew", padx=4, pady=6
            )
            ttk.Button(table, text="Test", style="Secondary.TButton", command=lambda b=btn: self.test_mapping(b)).grid(
                row=idx, column=4, sticky="ew", padx=4, pady=6
            )

        table.columnconfigure(2, weight=1)

    def build_live_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text="Live Status", style="Card.TLabelframe", padding=14)
        card.pack(fill="x", pady=(0, 10))

        grid = ttk.Frame(card, style="Card.TFrame")
        grid.pack(fill="x")

        self.add_live_row(grid, 0, "Connection", self.device_status_var)
        self.add_live_row(grid, 1, "Volume", self.volume_var)
        self.add_live_row(grid, 2, "Now Playing", self.now_playing_var, wraplength=320)

    def add_live_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, wraplength: int = 0) -> None:
        ttk.Label(parent, text=label, style="Section.TLabel").grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=6)
        value_label = ttk.Label(parent, textvariable=variable, style="Value.TLabel", justify="left")
        if wraplength:
            value_label.configure(wraplength=wraplength)
        value_label.grid(row=row, column=1, sticky="w", pady=6)

    def build_quick_actions_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text="Quick Actions", style="Card.TLabelframe", padding=14)
        card.pack(fill="x", pady=(0, 10))

        ttk.Button(card, text="Sync Volume from Windows", style="Secondary.TButton", command=self.sync_volume_from_system).pack(fill="x", pady=(0, 8))
        ttk.Button(card, text="Refresh Now Playing", style="Secondary.TButton", command=self.manual_refresh_now_playing).pack(fill="x", pady=(0, 8))
        ttk.Button(card, text="Open Config Folder", style="Secondary.TButton", command=self.open_config_folder).pack(fill="x")

    def build_log_card(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text="Log", style="Card.TLabelframe", padding=14)
        card.pack(fill="both", expand=True)

        container = ttk.Frame(card, style="Card.TFrame")
        container.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            container,
            height=22,
            bg="#0b1220",
            fg="#e5e7eb",
            insertbackground="#ffffff",
            relief="flat",
            wrap="word",
            font=("Consolas", 10),
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")

        self.log_text.configure(yscrollcommand=scrollbar.set, state="disabled")

    # ----------------------------
    # Logging
    # ----------------------------

    def append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ----------------------------
    # Presets and mapping actions
    # ----------------------------

    def apply_web_preset(self) -> None:
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

        self.set_status("Starter web preset loaded.")

    def clear_mappings(self) -> None:
        for btn in self.entries:
            self.type_vars[btn].set("url")
            self.entries[btn].delete(0, tk.END)
        self.set_status("All mappings cleared.")

    def pick_value(self, button_name: str) -> None:
        action_type = self.type_vars[button_name].get()

        if action_type == "app":
            path = filedialog.askopenfilename(filetypes=[("Programs", "*.exe"), ("All files", "*.*")])
        elif action_type == "path":
            path = filedialog.askdirectory()
        else:
            return

        if path:
            self.entries[button_name].delete(0, tk.END)
            self.entries[button_name].insert(0, path)

    def test_mapping(self, button_name: str) -> None:
        action_type = self.type_vars[button_name].get()
        value = self.entries[button_name].get().strip()
        self.execute_mapping(button_name, action_type, value)

    def execute_mapping(self, button_name: str, action_type: str, value: str) -> None:
        if not value:
            self.set_status(f"{button_name}: no target set")
            return

        try:
            if action_type == "url":
                ok = webbrowser.open(value)
                if not ok:
                    raise RuntimeError("Could not open URL")

            elif action_type == "app":
                if not os.path.exists(value):
                    raise FileNotFoundError(f"File not found: {value}")
                subprocess.Popen([value], shell=False)

            elif action_type == "path":
                if not os.path.exists(value):
                    raise FileNotFoundError(f"Path not found: {value}")
                os.startfile(value)

            self.set_status(f"{button_name} executed")
            self.append_log(f"[ACTION] {button_name} -> {action_type} -> {value}")
        except Exception as e:
            self.set_status(f"Error on {button_name}: {e}")
            self.append_log(f"[ERROR] {button_name}: {e}")

    # ----------------------------
    # Config
    # ----------------------------

    def get_config(self) -> dict:
        return {
            "serial_port": self.port_var.get().strip(),
            "buttons": {
                btn: {
                    "type": self.type_vars[btn].get(),
                    "value": self.entries[btn].get().strip(),
                }
                for btn in self.entries
            },
        }

    def save_config(self) -> None:
        config = self.get_config()
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        self.set_status("Configuration saved.")
        self.append_log("[INFO] Configuration saved.")

    def load_config(self) -> None:
        if not os.path.exists(CONFIG_FILE):
            self.set_status("No saved configuration yet.")
            self.update_volume_label()
            self.update_now_playing_label()
            return

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        saved_port = config.get("serial_port", "")
        if saved_port and saved_port in self.port_choices:
            self.port_var.set(saved_port)

        buttons = config.get("buttons", {})
        for btn, cfg in buttons.items():
            if btn in self.entries:
                self.type_vars[btn].set(cfg.get("type", "url"))
                self.entries[btn].delete(0, tk.END)
                self.entries[btn].insert(0, cfg.get("value", ""))

        self.set_status("Configuration loaded.")
        self.update_volume_label()
        self.update_now_playing_label()
        self.append_log("[INFO] Configuration loaded.")

    def open_config_folder(self) -> None:
        folder = os.path.abspath(".")
        try:
            os.startfile(folder)
        except Exception as e:
            self.set_status(f"Could not open folder: {e}")

    # ----------------------------
    # Serial / device
    # ----------------------------

    def refresh_ports(self) -> None:
        if list_ports is None:
            return

        ports = list(list_ports.comports())
        choices = [p.device for p in ports]
        self.port_choices = choices

        selected = self.auto_detect_port(ports)

        if self.port_dropdown is not None:
            self.update_dropdown_choices(self.port_dropdown, self.port_var, choices, preferred=selected)

        if selected:
            self.set_status(f"Port found: {selected}")
        elif choices and not self.port_var.get():
            self.port_var.set(choices[0])
            self.set_status(f"Using available port: {choices[0]}")
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

    def start_listener(self) -> None:
        if serial is None:
            messagebox.showerror(
                "Error",
                "pyserial is not installed.\n\nInstall it with:\npython -m pip install pyserial",
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
        self.append_log("[INFO] Connecting to device...")

    def stop_listener(self) -> None:
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

    def listener_loop(self) -> None:
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
                    self.root.after(0, lambda p=port: self.set_status(f"Device connected: {p}"))
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

                self.root.after(0, lambda err=str(e): self.device_status_var.set("Not connected"))
                self.root.after(0, lambda err=str(e): self.set_status(f"Connection error: {err}"))
                self.root.after(0, lambda err=str(e): self.append_log(f"[ERROR] {err}"))
                self.root.after(0, self.refresh_ports)
                time.sleep(2)

        with self.serial_lock:
            self.ser = None

    def send_to_device(self, line: str) -> bool:
        try:
            with self.serial_lock:
                if self.ser and self.ser.is_open:
                    self.ser.write((line + "\n").encode("utf-8"))
                    self.ser.flush()
                    self.append_log(f"-> {line}")
                    return True
        except Exception as e:
            self.set_status(f"Send error: {e}")
            self.append_log(f"[ERROR] {e}")
        return False

    # ----------------------------
    # Device events
    # ----------------------------

    def handle_serial_event(self, event_name: str) -> None:
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

        elif event_name == "MUTE_TOGGLE":
            ok, actual_volume, actual_muted, err = self.toggle_mute()

            if ok:
                self.current_volume = actual_volume
                self.is_muted = actual_muted
                self.update_volume_label()
                self.send_to_device(f"SET_VOL:{self.current_volume}")
                self.send_to_device(f"SET_MUTE:{1 if self.is_muted else 0}")
                self.set_status("Mute toggled")
            else:
                self.set_status(f"Mute error: {err}")

        elif event_name == "READY":
            self.set_status("Device ready")
            self.send_to_device("STATUS:Windows")
            self.sync_volume_from_system()
            self.send_to_device(f"NOW_PLAYING:{self.now_playing[:60]}")

        elif event_name.startswith("ACK:"):
            self.set_status(f"Device confirmed: {event_name[4:]}")

        else:
            self.set_status(f"Unknown event: {event_name}")

    # ----------------------------
    # Now playing
    # ----------------------------

    def now_playing_loop(self) -> None:
        while self.running:
            try:
                text = self.get_windows_now_playing()
                self.root.after(0, lambda t=text: self.update_now_playing(t))
            except Exception:
                pass

            time.sleep(2)

    def manual_refresh_now_playing(self) -> None:
        try:
            text = self.get_windows_now_playing()
            self.update_now_playing(text)
            self.set_status("Now Playing refreshed.")
        except Exception as e:
            self.set_status(f"Now Playing error: {e}")

    def get_windows_now_playing(self) -> str:
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

    # ----------------------------
    # Audio
    # ----------------------------

    def get_windows_endpoint(self):
        if AudioUtilities is None:
            raise RuntimeError("pycaw is not installed")
        device = AudioUtilities.GetSpeakers()
        if device is None:
            raise RuntimeError("No default audio output device found")
        return device.EndpointVolume

    def get_windows_audio_state(self):
        endpoint = self.get_windows_endpoint()
        volume = int(round(endpoint.GetMasterVolumeLevelScalar() * 100))
        muted = bool(endpoint.GetMute())
        return endpoint, volume, muted

    def sync_volume_from_system(self) -> None:
        try:
            _, self.current_volume, self.is_muted = self.get_windows_audio_state()
            self.update_volume_label()
            self.send_to_device(f"SET_VOL:{self.current_volume}")
            self.send_to_device(f"SET_MUTE:{1 if self.is_muted else 0}")
        except Exception as e:
            self.set_status(f"Sync error: {e}")

    def apply_volume(self, volume: int):
        volume = max(0, min(100, volume))

        try:
            endpoint, _, _ = self.get_windows_audio_state()
            endpoint.SetMasterVolumeLevelScalar(float(volume / 100.0), None)
            _, actual_volume, actual_muted = self.get_windows_audio_state()
            return True, actual_volume, actual_muted, None
        except Exception as e:
            return False, None, None, str(e)

    def toggle_mute(self):
        try:
            endpoint, _, actual_muted = self.get_windows_audio_state()
            endpoint.SetMute(0 if actual_muted else 1, None)
            _, new_volume, new_muted = self.get_windows_audio_state()
            return True, new_volume, new_muted, None
        except Exception as e:
            return False, None, None, str(e)

    # ----------------------------
    # UI state
    # ----------------------------

    def update_volume_label(self) -> None:
        if self.is_muted:
            self.volume_var.set(f"{self.current_volume}% (Muted)")
        else:
            self.volume_var.set(f"{self.current_volume}%")

    def update_now_playing(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            text = "Nothing active"

        if text != self.now_playing:
            self.now_playing = text
            self.update_now_playing_label()
            self.send_to_device(f"NOW_PLAYING:{text[:60]}")

    def update_now_playing_label(self) -> None:
        self.now_playing_var.set(self.now_playing)

    def set_status(self, text: str) -> None:
        self.status_var.set(text)


if __name__ == "__main__":
    root = tk.Tk()
    app = WebPadApp(root)
    root.mainloop()