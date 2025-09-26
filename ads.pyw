from tkinter import *
from tkinter import messagebox
from customtkinter import *
import os
import time
import json
import sys                    # required for startup shortcut target detection
from pynput import mouse, keyboard

# store config in AppData to avoid permission issues
CONFIG_FILE = os.path.join(os.getenv("APPDATA", ""), "AutoShutdown", "autoshuwdown_config.json")
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

message_storage = {"default": "Welcome! Thank you for using Auto Shutdown. You can change this message in the settings anytime. The Default PIN is 0000"}
pin_storage = {"main": "0000", "lock": "1234"}
time_storage = {"shutdown": 20}
startup_state = {"enabled": False}
noise_detector_state = {"enabled": False}

window_width = 460
window_height = 320

class AutoShutdownApp:
    def __init__(self, ui):
        self.ui = ui

        # load settings first so UI switches/loaders read the saved values
        self.load_settings()

        # build UI (kept identical to your design)
        self.center_window(460, 315)
        self.ui.title("AutoShutdown")
        self.ui.attributes("-alpha", 0.96)
        self.ui.overrideredirect(True)
        self.ui.resizable(0, 0)
        self.ui.configure(background='#242424')
        self.ui.protocol("WM_DELETE_WINDOW", self.prevent_closing_app)
        self.info_text = message_storage["default"]
        self.shutdown_time_ms = time_storage["shutdown"] * 60 * 1000
        self.last_activity_time = time.time()

        # Prepare frames (persistent)
        self.main_frame = None
        self.login_frame = None
        self.settings_frame = None

        # Build UI (creates frames and widgets)
        self.create_main_ui()
        self.login_ui()
        self.settings_ui()

        # Show main frame initially
        self.show_frame(self.main_frame)

        # Drag handling
        self.drag_data = {'x': 0, 'y': 0}
        self.ui.bind("<ButtonPress-1>", self.start_drag)
        self.ui.bind("<B1-Motion>", self.do_drag)

        # Initialize runtime flags from loaded config
        self.startup_var.set(startup_state.get("enabled", False))
        self.noise_prevention_active = noise_detector_state.get("enabled", False)

        # Start listeners
        self.start_listeners()

    def start_listeners(self):
        # Use pynput global listeners so moving outside the window still resets timer
        self.mouse_listener = mouse.Listener(
            on_move=lambda *a: self.update_activity_time(),
            on_click=lambda *a: self.update_activity_time(),
            on_scroll=lambda *a: self.update_activity_time()
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=lambda *a: self.update_activity_time()
        )
        self.mouse_listener.start()
        self.keyboard_listener.start()
        self.check_if_active()

    def update_activity_time(self, *args, **kwargs):
        now = time.time()
        if now - self.last_activity_time > 0.5:  # only reset every 0.5s
            self.last_activity_time = now
            self.update_time_label()


    def load_settings(self):
        """
        Loads config from CONFIG_FILE. If file doesn't exist, creates one with defaults.
        Saved keys:
          - pin
          - message
          - timeout
          - startup_enabled
          - noise_detector_enabled
        """
        try:
            if not os.path.exists(CONFIG_FILE):
                # create default config on first run
                default_config = {
                    "pin": pin_storage["main"],
                    "message": message_storage["default"],
                    "timeout": time_storage["shutdown"],
                    "startup_enabled": startup_state["enabled"],
                    "noise_detector_enabled": noise_detector_state["enabled"]
                }
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(default_config, f, indent=4)
                # keep in-memory defaults, don't return early (we'll pick them up below)
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                pin_storage["main"] = config.get("pin", "0000")
                message_storage["default"] = config.get("message", self.info_text if hasattr(self, "info_text") else message_storage["default"])
                time_storage["shutdown"] = config.get("timeout", 10)
                startup_state["enabled"] = config.get("startup_enabled", False)
                noise_detector_state["enabled"] = config.get("noise_detector_enabled", False)

                # apply loaded values to runtime if UI exists already
                self.info_text = message_storage["default"]
                self.shutdown_time_ms = time_storage["shutdown"] * 60 * 1000
                # update UI fields if they are created later (UI creation uses startup_state when building)
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_settings(self):
        # protect if widgets do not yet exist
        pin_val = getattr(self, "entry_newpin", None)
        msg_widget = getattr(self, "new_info_label", None)
        time_widget = getattr(self, "entry_newtime", None)

        config = {
            "pin": pin_val.get() if pin_val else pin_storage["main"],
            "message": msg_widget.get("1.0", "end").strip() if msg_widget else message_storage["default"],
            "timeout": int(time_widget.get()) if time_widget and time_widget.get().isdigit() else time_storage["shutdown"],
            "startup_enabled": self.startup_var.get() if hasattr(self, 'startup_var') else startup_state.get("enabled", False),
            "noise_detector_enabled": getattr(self, 'noise_prevention_active', False)
        }

        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)

            # Hide file after saving (windows). If not windows, just ignore.
            if os.name == 'nt' and os.path.exists(CONFIG_FILE):
                try:
                    os.system(f'attrib +h "{CONFIG_FILE}"')
                except Exception as e:
                    print(f"Failed to hide config file: {e}")

        except Exception as e:
            print(f"Error saving config: {e}")

    def center_window(self, width, height):
        screen_width = self.ui.winfo_screenwidth()
        screen_height = self.ui.winfo_screenheight()
        x_pos = (screen_width // 2) - (width // 2)
        y_pos = (screen_height // 2) - (height // 2)
        self.ui.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

    def show_frame(self, frame):
        # Hide all frames and show only the requested one
        for f in (self.main_frame, self.login_frame, self.settings_frame):
            if f is not None:
                f.pack_forget()
        if frame is not None:
            frame.pack(fill="both", expand=True)

    def start_drag(self, event):
        self.drag_data['x'] = event.x
        self.drag_data['y'] = event.y

    def do_drag(self, event):
        dx = event.x - self.drag_data['x']
        dy = event.y - self.drag_data['y']
        new_x = self.ui.winfo_x() + dx
        new_y = self.ui.winfo_y() + dy
        self.ui.geometry(f"+{new_x}+{new_y}")

    def create_main_ui(self):
        # Create persistent main frame
        self.main_frame = CTkFrame(self.ui, fg_color="#242424")

        self.time_label = Label(self.main_frame, text="", font=("Segoe UI", 60, "bold"),
                              fg="#28a745", bg="#242424", borderwidth=2)
        self.time_label.place(x=window_width // 2 - 100, y=25)

        self.label = Label(self.main_frame, text="\n ATTENTION", font=("Segoe UI", 14,"bold"),
                         fg="white", bg="#242424")
        self.label.place(x=window_width // 2 - 60, y=-11)

        self.lbl = Label(self.main_frame, text="Time Remaining Until Shutdown.",
                        font=("Segoe UI", 14, "bold"), fg="#28a745", bg="#242424")
        self.lbl.place(x=window_width // 2 - 140, y=125)

        self.info_label = Text(
            self.main_frame,
            font=("Courier", 14, "bold"),
            bg="#242424",
            fg="white",
            width=35,
            height=5,
            wrap="word",
            state="normal"
        )
        self.info_label.place(x=window_width // 2 - 195, y=167)

        # Create a center tag
        self.info_label.tag_configure("center", justify="center")

        # Insert text with the "center" tag
        self.info_label.insert("1.0", self.info_text, "center")

        # Disable editing
        self.info_label.config(state="disabled")

        self.btn = CTkButton(self.main_frame, text="🛠", font=("Times", 25),
                           fg_color="#28a745", text_color="white",
                           hover_color="#218838", height=8, width=15,
                           corner_radius=18, command=lambda: self.show_frame(self.login_frame))
        self.btn.place(x=window_width - 50, y=10)

        self.footer_label = Label(self.main_frame, text="Smart Shutdown - v1.6",
                                font=("Segoe UI", 8), fg="white", bg="#242424")
        self.footer_label.place(x=10, y=300 - 14)

        self.footer_label1 = Label(self.main_frame, text="Developed by: BenjieCabajar",
                                 font=("Segoe UI", 8), fg="white", bg="#242424")
        self.footer_label1.place(x=292, y=300 - 14)

    def login_ui(self):
        # Create persistent login frame
        self.login_frame = CTkFrame(self.ui, fg_color="#242424")

        CTkLabel(
            self.login_frame,
            text="🔒 Enter PIN to Continue",
            font=("Segoe UI", 20, "bold")
        ).pack(pady=(90, 5))

        self.pin_input = CTkEntry(
            self.login_frame,
            font=("Segoe UI", 16),
            width=220,
            justify="center",
            show="*",
            placeholder_text="4-digit PIN"
        )
        self.pin_input.pack(pady=(5, 20))
        self.pin_input.bind("<Return>", lambda event: self.check_pin())

        btn_frame = CTkFrame(self.login_frame, fg_color="transparent")
        btn_frame.pack(pady=10)

        CTkButton(
            btn_frame,
            text="⮜ Go Back",
            font=("Segoe UI", 14, "bold"),
            fg_color="#6c757d",
            hover_color="#5a6268",
            width=100,
            command=lambda: self.show_frame(self.main_frame)
        ).pack(side="left", padx=5)

        CTkButton(
            btn_frame,
            text="Continue ⮞",
            font=("Segoe UI", 14, "bold"),
            fg_color="#28a745",
            hover_color="#218838",
            width=100,
            command=self.check_pin
        ).pack(side="left", padx=5)

    def settings_ui(self):
        # Create persistent settings frame
        self.settings_frame = CTkFrame(self.ui, fg_color="#242424")

        self.settings_label = CTkLabel(
            self.settings_frame,
            text="Settings",
            font=("Segoe UI", 26, "bold"),
            text_color="#28a745",
            fg_color="#242424"
        )
        self.settings_label.place(relx=0.5, y=18, anchor="n")

        entry_width = 180
        info_entry_width = 400
        button_width = 80

        CTkLabel(self.settings_frame, text="Change PIN", font=("Segoe UI", 14, "bold"), text_color="#cccccc", fg_color="#242424").place(x=window_width // 2 - entry_width // 2, y=55)
        self.entry_newpin = CTkEntry(self.settings_frame, placeholder_text="Enter new PIN", width=entry_width, justify="center", font=("Segoe UI", 14), height=20)
        self.entry_newpin.insert(0, pin_storage["main"])
        self.entry_newpin.place(x=window_width // 2 - entry_width // 2, y=80)

        CTkLabel(self.settings_frame, text="Shutdown Timeout (minutes)", font=("Segoe UI", 14, "bold"), text_color="#cccccc", fg_color="#242424").place(x=window_width // 2 - entry_width // 2, y=115)
        self.entry_newtime = CTkEntry(self.settings_frame, placeholder_text="Enter time in minutes", width=entry_width, justify="center", font=("Segoe UI", 14), height=20)
        self.entry_newtime.insert(0, str(time_storage["shutdown"]))
        self.entry_newtime.place(x=window_width // 2 - entry_width // 2, y=140)

        CTkLabel(self.settings_frame, text="Custom Message", font=("Segoe UI", 14, "bold"), text_color="#cccccc", fg_color="#242424").place(x=window_width // 2 - entry_width // 2, y=175)
        self.new_info_label = CTkTextbox(self.settings_frame, font=("Segoe UI", 14), width=info_entry_width, height=60, fg_color="#181818", text_color="white")
        self.new_info_label.place(x=window_width // 2 - info_entry_width // 2, y=200)
        self.new_info_label.insert("1.0", message_storage["default"])

        # Startup switch now loads its initial value from startup_state
        self.startup_var = BooleanVar(value=startup_state.get("enabled", False))
        self.startup_switch = CTkSwitch(self.settings_frame, text="Start with Windows", variable=self.startup_var, font=("Segoe UI", 13), onvalue=True, offvalue=False, fg_color="red", progress_color="#218838", button_color="#fff", button_hover_color="#28a745", text_color="white", command=self.toggle_startup)
        self.startup_switch.place(x=window_width // 2 - 90, y=275)

        def save():
            new_pin = self.entry_newpin.get()
            new_info = self.new_info_label.get("1.0", "end").strip()
            time_value = self.entry_newtime.get()

            if not all([new_pin, new_info, time_value]):
                messagebox.showerror("Error", "All fields must be filled out")
                return

            if not (new_pin.isdigit() and len(new_pin) == 4):
                messagebox.showerror("Error", "PIN must be 4 digits")
                return

            try:
                time_value = int(time_value)
                if time_value <= 0:
                    messagebox.showerror("Error", "Time must be positive")
                    return
            except ValueError:
                messagebox.showerror("Error", "Invalid time value")
                return

            pin_storage["main"] = new_pin
            message_storage["default"] = new_info
            time_storage["shutdown"] = time_value
            self.shutdown_time_ms = time_value * 60 * 1000
            self.info_text = new_info
            self.load_settings()

            # update main UI widgets (no destroying)
            if getattr(self, "info_label", None):
                self.info_label.config(state="normal")
                self.info_label.delete("1.0", "end")
                self.info_label.insert("1.0", self.info_text, "center")
                self.info_label.config(state="disabled")
            if getattr(self, "entry_newtime", None):
                self.entry_newtime.delete(0, "end")
                self.entry_newtime.insert(0, str(time_storage["shutdown"]))
            if getattr(self, "entry_newpin", None):
                self.entry_newpin.delete(0, "end")
                self.entry_newpin.insert(0, pin_storage["main"])

            # go back to main frame
            self.show_frame(self.main_frame)
            self.check_if_active()
            messagebox.showinfo("Success", "Settings saved successfully")

        def open_feedback_link():
            import webbrowser
            webbrowser.open("https://www.facebook.com/bnje.23")

        self.feedback_button = CTkButton(self.settings_frame, text="📩",
            font=("Segoe UI", 15, "bold"), fg_color="blue",
            text_color="white", hover_color="darkblue",
            height=25, width=7,
            command=open_feedback_link)
        self.feedback_button.place(x=820 // 2 - button_width // 2, y=275)

        def open_update_link():
            import webbrowser
            import requests

            # 👉 Your GitHub repo
            GITHUB_USER = "benjiecabajar"
            GITHUB_REPO = "pc-auto-shutdown-for-computer-cafe"
            BRANCH = "main"

            local_version = "1.6"  # update this when you release new versions

            try:
                url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    latest_release = response.json()
                    latest_version = latest_release.get("tag_name", "")
                    html_url = latest_release.get("html_url", f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}")

                    if latest_version and latest_version != local_version:
                        if messagebox.askyesno(
                            "Update Available",
                            f"A new version ({latest_version}) is available!\n\nDo you want to download it?"
                        ):
                            webbrowser.open(html_url)
                    else:
                        messagebox.showinfo("Update", "Your system is up to date!")
                else:
                    messagebox.showwarning("Update Check Failed", "Could not reach GitHub.")
            except Exception as e:
                messagebox.showerror("Error", f"Update check failed:\n{e}")

        self.update_button = CTkButton(self.settings_frame, text="🔄",
            font=("Segoe UI", 15, "bold"), fg_color="#007bff",
            text_color="white", hover_color="#0056b3",
            height=25, width=7,
            command=open_update_link)
        self.update_button.place(x=640 // 2 - button_width // 2 + 50, y=275)

        self.save_button = CTkButton(self.settings_frame, text="💾", font=("Segoe UI", 15),
                    fg_color="#28a745", text_color="white",
                    hover_color="#218838", height=25,width=7,
                    command=save)
        self.save_button.place(x=900 // 2 - button_width // 2, y=275)

        self.back_button = CTkButton(self.settings_frame, text="⮜ Go Back", font=("Segoe UI", 14, "bold"),
                                    fg_color="#6c757d", text_color="white",
                                    hover_color="#5a6268",width=60,command=lambda: self.show_frame(self.main_frame))
        self.back_button.place(y=12, x=20)

        self.exit_button = CTkButton(self.settings_frame, text="  Exit ⮞  ", font=("Segoe UI", 14, "bold"),
                                    fg_color="#28a745", text_color="white",
                                    hover_color="#218838", width=60,command=self.end_program)
        self.exit_button.place(y=12, x=370)

        self.prevention_button = CTkButton(self.settings_frame, text="🔇 OFF", font=("Segoe UI", 20, "bold"),
                        fg_color="#dc3545", text_color="white",
                        hover_color="#c82333", height=50, width=90,
                        corner_radius=4, command=self.toggle_noise_prevention)
        self.prevention_button.place(y=87, x=350)

    def toggle_noise_prevention(self):
        if not hasattr(self, 'noise_prevention_active'):
            self.noise_prevention_active = False
        if not self.noise_prevention_active:
            self.noise_prevention_active = True
            if getattr(self, "prevention_button", None):
                self.prevention_button.configure(text="🔇 ON", fg_color="#28a745", hover_color="#218838")
            self.start_noise_monitoring()
        else:
            self.noise_prevention_active = False
            if getattr(self, "prevention_button", None):
                self.prevention_button.configure(text="🔇 OFF", fg_color="#dc3545", hover_color="#c82333")
            self.stop_noise_monitoring()
        self.save_settings()

    def start_noise_monitoring(self):
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            from tkinter import messagebox
            messagebox.showerror("Missing Dependency", "Please install 'sounddevice' and 'numpy' to use noise prevention.\nRun: pip install sounddevice numpy")
            self.noise_prevention_active = False
            if getattr(self, "prevention_button", None):
                self.prevention_button.configure(text="🔇 OFF", fg_color="#dc3545", hover_color="#c82333")
            return
        self._noise_monitoring = True
        self._noise_monitor_loop(sd, np)

    def _noise_monitor_loop(self, sd, np):
        if not getattr(self, 'noise_prevention_active', False):
            return
        duration = 1
        threshold = 0.03
        fs = 44100
        try:
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float64')
            sd.wait()
            volume_max = np.max(np.abs(recording))
            print(f"[DEBUG] Noise monitor: max amplitude = {volume_max}")
            if volume_max > threshold:
                if not hasattr(self, '_noise_warning_shown') or not self._noise_warning_shown:
                    self._noise_warning_shown = True
                    from tkinter import messagebox
                    messagebox.showwarning("Noise Detected", "Loud noise detected! Please keep silence.")
                    self._noise_warning_shown = False
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Microphone error: {e}")
            self.noise_prevention_active = False
            if getattr(self, "prevention_button", None):
                self.prevention_button.configure(text="🔇 OFF", fg_color="#dc3545", hover_color="#c82333")
            return
        if getattr(self, 'noise_prevention_active', False):
            self.ui.after(1200, lambda: self._noise_monitor_loop(sd, np))

    def stop_noise_monitoring(self):
        self._noise_monitoring = False

    def toggle_startup(self):
        # Only Windows startup integration is supported here
        if os.name != 'nt':
            messagebox.showwarning("Unsupported", "Startup integration is only supported on Windows.")
            # revert to saved state if present
            self.startup_var.set(startup_state.get("enabled", False))
            return

        try:
            from win32com.client import Dispatch
        except ImportError:
            messagebox.showerror("Missing Dependency", "pywin32 is required for startup integration. Please install it with 'pip install pywin32'.")
            # revert switch to saved state to avoid confusion
            self.startup_var.set(startup_state.get("enabled", False))
            return

        startup_folder = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
        if not os.path.isdir(startup_folder):
            messagebox.showerror("Startup Error", f"Startup folder not found: {startup_folder}")
            self.startup_var.set(startup_state.get("enabled", False))
            return

        shortcut_path = os.path.join(startup_folder, "AutoShutdown.lnk")
        script_path = os.path.abspath(sys.argv[0])

        try:
            shell = Dispatch('WScript.Shell')
            if self.startup_var.get():
                shortcut = shell.CreateShortCut(shortcut_path)
                # If running a .py file, point to python executable and pass the script in Arguments
                if script_path.lower().endswith(".py"):
                    shortcut.Targetpath = sys.executable
                    shortcut.Arguments = f'"{script_path}"'
                    shortcut.WorkingDirectory = os.path.dirname(script_path)
                    shortcut.IconLocation = sys.executable
                else:
                    # assume exe or other executable
                    shortcut.Targetpath = script_path
                    shortcut.WorkingDirectory = os.path.dirname(script_path)
                    shortcut.IconLocation = script_path
                shortcut.save()
                messagebox.showinfo("Startup", "App will start with Windows.")
            else:
                if os.path.exists(shortcut_path):
                    try:
                        os.remove(shortcut_path)
                        messagebox.showinfo("Startup", "App will NOT start with Windows.")
                    except Exception as e:
                        messagebox.showerror("Startup", f"Failed to remove startup shortcut: {e}")
                else:
                    messagebox.showinfo("Startup", "App will NOT start with Windows.")
            # persist the change in memory and in config
            startup_state["enabled"] = self.startup_var.get()
            self.save_settings()
        except Exception as e:
            messagebox.showerror("Startup Error", f"Failed to update startup shortcut: {e}")
            # on failure revert the UI switch to previous state to avoid mismatches
            self.startup_var.set(startup_state.get("enabled", False))

    def end_program(self):
        try:
            self.mouse_listener.stop()
            self.keyboard_listener.stop()
        except Exception:
            pass
        self.ui.destroy()

    def check_pin(self):
        if self.pin_input.get() == pin_storage["main"]:
            # go to settings frame
            self.show_frame(self.settings_frame)
        else:
            messagebox.showerror("Smart Shutdown", "Invalid PIN.")

    def main_ui(self):
        self.show_frame(self.main_frame)
        self.check_if_active()

    def prevent_closing_app(self):
        messagebox.showinfo("You can't close this window!", "In Bisaya: Dili nimo pwede ma close salamat!")

    def update_time_label(self):
        remaining_time = self.shutdown_time_ms - (time.time() - self.last_activity_time) * 1000
        minutes, seconds = divmod(int(remaining_time // 1000), 60)
        # ensure time_label exists
        if getattr(self, "time_label", None):
            self.time_label.config(text=f"{minutes:02}:{seconds:02}\n")

    def check_if_active(self):
        current_time = time.time()
        if (current_time - self.last_activity_time) * 1000 > self.shutdown_time_ms:
            self.shutdown_computer()
        else:
            self.update_time_label()
            self.ui.after(1000, self.check_if_active)

    def shutdown_computer(self):
        os.system("shutdown /s /t 1")

if __name__ == "__main__":
    def main_entry():
        ui = Tk()
        app = AutoShutdownApp(ui)
        ui.mainloop()

    main_entry()
