import random, string, time, json, os, threading
from collections import deque
from tkinter import (Tk, Frame, Label, Entry, Button, Text, Scrollbar, END,
                     DISABLED, NORMAL, StringVar, BooleanVar, Checkbutton, messagebox, ttk)
from tkinter.ttk import Style, Notebook

# --- Third‑party ---
try:
    import requests
    from requests.exceptions import (ProxyError, SSLError, ConnectTimeout, ReadTimeout, ConnectionError as ReqConnErr)
except ImportError:
    raise SystemExit("Install requests: pip install requests")

try:
    import socks  # noqa: F811
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False

# --- Constants ---
CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789_.'
API1 = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
API2 = "https://discord.com/api/v9/auth/register"
HEADERS = {"Content-Type": "application/json"}

def center_window(win, w, h):
    ws = win.winfo_screenwidth()
    hs = win.winfo_screenheight()
    win.geometry(f'{w}x{h}+{(ws-w)//2}+{(hs-h)//2}')

def random_string(length):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))

def gen_register_payload(username):
    return {
        "fingerprint": f"{random.randint(10**16, 10**17)}.{random_string(20)}",
        "email": f"{random_string(10)}@gmail.com",
        "username": username,
        "global_name": random_string(8),
        "password": random_string(12),
        "invite": None,
        "consent": True,
        "date_of_birth": "2000-01-01",
        "gift_code_sku_id": None,
        "promotional_email_opt_in": False
    }

def is_taken(data):
    if "taken" in data:
        return data["taken"]
    errors = data.get("errors", {}).get("username", {}).get("_errors", [])
    return any(e.get("code") == "USERNAME_ALREADY_TAKEN" for e in errors)

# --- Sniper Thread ---
class SniperThread(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        self.running = False
        self.cycle = 0
        self.checked = 0
        self.available = 0

    def run(self):
        self.running = True
        try:
            delay = float(self.app.delay_var.get())
        except:
            delay = 5.0
        try:
            length = int(self.app.length_var.get())
        except:
            length = 5

        verify_ssl = not self.app.no_verify_var.get()
        zero_delay = self.app.zero_delay_var.get()
        proxy_available = bool(self.app.proxy_list)
        if zero_delay and proxy_available:
            delay = 0.0
        else:
            min_delay = 2 if proxy_available else 5
            if delay < min_delay:
                self.app.log(f"Delay too low — forced to {min_delay}s", "yellow")
                delay = min_delay

        while self.running:
            try:
                time.sleep(delay)
            except:
                break

            username = ''.join(random.choice(CHARS) for _ in range(length))
            self.checked += 1
            self.app.update_counter_checked()

            # --- Try a request with proxy, auto‑purge on failure ---
            success = False
            attempts = 0
            max_attempts = len(self.app.proxy_list) if proxy_available else 1

            while not success and attempts < max_attempts and self.running:
                attempts += 1
                proxy = self.app.get_next_proxy() if proxy_available else None
                try:
                    if self.cycle == 0:
                        resp = requests.post(API1, json={"username": username},
                                             headers=HEADERS, proxies={"http": proxy, "https": proxy} if proxy else None,
                                             timeout=8, verify=verify_ssl)
                    else:
                        resp = requests.post(API2, json=gen_register_payload(username),
                                             headers=HEADERS, proxies={"http": proxy, "https": proxy} if proxy else None,
                                             timeout=8, verify=verify_ssl)

                    # HTTP errors that indicate a dead proxy → remove instantly
                    if resp.status_code in (400, 403, 502, 503, 504):
                        self.app.log(f"[{self.checked}] {username} — Proxy dead (HTTP {resp.status_code})", "yellow")
                        if proxy:
                            self.app.remove_proxy(proxy)
                        continue

                    if resp.status_code == 429:
                        self.app.log(f"[{self.checked}] {username} — RATE LIMITED, switching API", "yellow")
                        self.cycle = 1 - self.cycle
                        continue

                    if resp.status_code != 200:
                        self.app.log(f"[{self.checked}] {username} — HTTP {resp.status_code}", "red")
                        continue

                    data = resp.json()
                    taken = is_taken(data)
                    success = True

                    if taken:
                        self.app.log(f"[{self.checked}] {username} TAKEN", "red")
                        self.app.add_taken(username)
                    else:
                        self.available += 1
                        self.app.log(f"[{self.checked}] {username} AVAILABLE !!!", "green")
                        self.app.save_valid(username)
                        if self.app.webhook_var.get().strip():
                            self.send_webhook(self.app.webhook_var.get().strip(), username)

                except (SSLError, ProxyError, ConnectTimeout, ReadTimeout, ReqConnErr) as e:
                    self.app.log(f"[{self.checked}] {username} — Proxy/connection error: {e}", "red")
                    if proxy:
                        self.app.remove_proxy(proxy)
                except Exception as e:
                    self.app.log(f"[{self.checked}] {username} — Unexpected error: {e}", "red")
                    continue

            if not success:
                self.app.log(f"[{self.checked}] {username} — FAILED after {attempts} attempts", "yellow")

        self.app.log("Sniping stopped.")
        self.app.root.after(0, self.app.update_status, "Stopped.")

    def send_webhook(self, url, username):
        try:
            requests.post(url, json={
                "embeds": [{
                    "title": "Username Available!",
                    "description": f"`{username}` is free to claim.",
                    "color": 3066993,
                    "footer": {"text": "ODUS Sniper by OnajLikezz"}
                }]
            }, timeout=10)
        except:
            pass

    def stop(self):
        self.running = False

# --- GUI ---
class ODUSApp:
    def __init__(self):
        self.root = Tk()
        self.root.title("ODUS v3 – OnajLikezz Username Sniper")
        self.root.resizable(False, False)
        center_window(self.root, 680, 540)

        # Dark theme with modern colors
        self.style = Style()
        self.style.theme_use('clam')
        self._set_dark_theme()

        # Variables
        self.delay_var = StringVar(value="5")
        self.length_var = StringVar(value="5")
        self.webhook_var = StringVar()
        self.no_verify_var = BooleanVar(value=False)
        self.zero_delay_var = BooleanVar(value=False)
        self.proxy_list = []          # list of proxy URLs
        self.proxy_index = -1
        self.sniper = None
        self.taken_queue = deque(maxlen=50)

        # Files
        self.proxies_file = "proxies.txt"
        self.valid_file = "valid.txt"

        self._build_ui()
        self.load_proxies_from_file()
        self.load_valid_usernames()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _set_dark_theme(self):
        self.style.configure('.', background='#1e1e2e', foreground='#cdd6f4',
                             fieldbackground='#313244')
        self.style.map('TButton', background=[('active', '#45475a')])
        self.style.configure('TNotebook', background='#1e1e2e', borderwidth=0)
        self.style.configure('TNotebook.Tab', background='#313244', foreground='#cdd6f4', padding=[12, 4])
        self.style.map('TNotebook.Tab', background=[('selected', '#585b70')])
        self.style.configure('TFrame', background='#1e1e2e')
        self.style.configure('TLabel', background='#1e1e2e', foreground='#cdd6f4', font=('Segoe UI', 9))
        self.style.configure('TEntry', fieldbackground='#313244', foreground='#cdd6f4',
                             insertcolor='#cdd6f4', font=('Consolas', 9))
        self.style.configure('Green.TButton', background='#a6e3a1', foreground='#1e1e2e',
                             font=('Segoe UI', 9, 'bold'), borderwidth=0, focusthickness=0)
        self.style.map('Green.TButton', background=[('active', '#94e2d5')])
        self.style.configure('Red.TButton', background='#f38ba8', foreground='#1e1e2e',
                             font=('Segoe UI', 9, 'bold'), borderwidth=0, focusthickness=0)
        self.style.map('Red.TButton', background=[('active', '#fab387')])

    def _build_ui(self):
        notebook = Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=8, pady=8)

        # --- Config Tab ---
        cfg = Frame(notebook)
        notebook.add(cfg, text="⚙️ Config & Control")

        s = Frame(cfg)
        s.pack(pady=10)
        ttk.Label(s, text="Delay (s):").grid(row=0, column=0, sticky='w', padx=5)
        ttk.Entry(s, textvariable=self.delay_var, width=8).grid(row=0, column=1, padx=5)
        ttk.Label(s, text="Length:").grid(row=0, column=2, sticky='w', padx=5)
        ttk.Entry(s, textvariable=self.length_var, width=8).grid(row=0, column=3, padx=5)

        ttk.Label(s, text="Webhook URL:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        ttk.Entry(s, textvariable=self.webhook_var, width=45).grid(row=1, column=1, columnspan=3, padx=5)

        ttk.Checkbutton(s, text="Disable SSL verification (self‑signed certs)", variable=self.no_verify_var).grid(
            row=2, column=0, columnspan=4, pady=5, sticky='w')
        ttk.Checkbutton(s, text="Zero delay when proxies loaded (use at own risk!)", variable=self.zero_delay_var).grid(
            row=3, column=0, columnspan=4, pady=2, sticky='w')

        # Start/Stop buttons with style
        btnf = Frame(cfg)
        btnf.pack(pady=15)
        self.start_btn = ttk.Button(btnf, text="▶ START", style='Green.TButton', command=self.start_sniper, width=12)
        self.start_btn.pack(side='left', padx=8)
        self.stop_btn = ttk.Button(btnf, text="⏹ STOP", style='Red.TButton', command=self.stop_sniper, width=12, state=DISABLED)
        self.stop_btn.pack(side='left', padx=8)

        cnt = Frame(cfg)
        cnt.pack(pady=10)
        self.checked_lbl = ttk.Label(cnt, text="Checked: 0", font=('Segoe UI', 10, 'bold'))
        self.checked_lbl.pack(side='left', padx=15)
        self.avail_lbl = ttk.Label(cnt, text="Available: 0", font=('Segoe UI', 10, 'bold'))
        self.avail_lbl.pack(side='left', padx=15)

        self.status_lbl = ttk.Label(cfg, text="Ready.", foreground="#a6adc8", font=('Segoe UI', 9))
        self.status_lbl.pack(pady=8)

        # --- Proxies Tab ---
        pxy = Frame(notebook)
        notebook.add(pxy, text="🌐 Proxies")
        ttk.Label(pxy, text="One proxy per line (ip:port or socks5://ip:port):").pack(anchor='w', padx=8, pady=5)
        self.proxy_text = Text(pxy, height=8, bg="#181825", fg="#cdd6f4", insertbackground="white",
                               font=('Consolas', 9), relief='flat', borderwidth=2)
        self.proxy_text.pack(fill='both', expand=True, padx=8, pady=4)
        bpf = Frame(pxy)
        bpf.pack(pady=5)
        ttk.Button(bpf, text="📂 Load from file", command=self.load_proxies_from_file).pack(side='left', padx=4)
        ttk.Button(bpf, text="💾 Save to file", command=self.save_proxies_to_file).pack(side='left', padx=4)
        self.proxy_cnt = ttk.Label(pxy, text="Proxies: 0 loaded", font=('Segoe UI', 9, 'italic'))
        self.proxy_cnt.pack(pady=6)

        # --- Log Tab ---
        log = Frame(notebook)
        notebook.add(log, text="📋 Log")
        self.log_text = Text(log, bg="#181825", fg="#cdd6f4", insertbackground="white",
                             font=('Consolas', 9), state=DISABLED, relief='flat', borderwidth=2)
        scroll = Scrollbar(log, command=self.log_text.yview, bg='#313244')
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side='left', fill='both', expand=True, padx=8, pady=5)
        scroll.pack(side='right', fill='y')
        self.log_text.tag_configure("red", foreground="#f38ba8")
        self.log_text.tag_configure("green", foreground="#a6e3a1")
        self.log_text.tag_configure("yellow", foreground="#f9e2af")
        ttk.Button(log, text="Clear log", command=self.clear_log).pack(pady=5)

        # --- Results Tab ---
        res = Frame(notebook)
        notebook.add(res, text="📊 Results")
        ttk.Label(res, text="Found (saved to valid.txt):", font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=8, pady=2)
        self.found_box = Text(res, height=7, bg="#1e1e2e", fg="#a6e3a1", font=('Consolas', 9),
                              state=DISABLED, relief='flat', borderwidth=2)
        self.found_box.pack(fill='both', expand=True, padx=8, pady=2)

        ttk.Label(res, text="Last 50 taken:", font=('Segoe UI', 9, 'bold')).pack(anchor='w', padx=8, pady=2)
        self.taken_box = Text(res, height=7, bg="#1e1e2e", fg="#f38ba8", font=('Consolas', 9),
                              state=DISABLED, relief='flat', borderwidth=2)
        self.taken_box.pack(fill='both', expand=True, padx=8, pady=2)

    # --- Thread‑safe UI updates ---
    def log(self, msg, color="white"):
        self.root.after(0, lambda: self._log(msg, color))

    def _log(self, msg, color):
        self.log_text.config(state=NORMAL)
        self.log_text.insert(END, msg + "\n", color)
        self.log_text.see(END)
        self.log_text.config(state=DISABLED)

    def clear_log(self):
        self.log_text.config(state=NORMAL)
        self.log_text.delete(1.0, END)
        self.log_text.config(state=DISABLED)

    def add_taken(self, name):
        self.taken_queue.append(name)
        self.root.after(0, self._update_taken)

    def _update_taken(self):
        self.taken_box.config(state=NORMAL)
        self.taken_box.delete(1.0, END)
        for n in reversed(self.taken_queue):
            self.taken_box.insert(END, n + "\n")
        self.taken_box.see(END)
        self.taken_box.config(state=DISABLED)

    def save_valid(self, name):
        with open(self.valid_file, "a") as f:
            f.write(name + "\n")
        self.root.after(0, self._show_found, name)

    def _show_found(self, name):
        self.found_box.config(state=NORMAL)
        self.found_box.insert(END, name + "\n")
        self.found_box.see(END)
        self.found_box.config(state=DISABLED)
        if self.sniper:
            self.avail_lbl.config(text=f"Available: {self.sniper.available}")

    def load_valid_usernames(self):
        if os.path.exists(self.valid_file):
            with open(self.valid_file) as f:
                names = f.read().splitlines()
            self.found_box.config(state=NORMAL)
            self.found_box.insert(END, "\n".join(names) + "\n")
            self.found_box.config(state=DISABLED)

    # --- Proxy management ---
    def _sanitise_proxy(self, raw):
        raw = raw.strip()
        if not raw:
            return None
        if raw.startswith("socks"):
            if not SOCKS_AVAILABLE:
                self.log(f"SOCKS proxy ignored (pysocks not installed): {raw}", "yellow")
                return None
            return raw
        if not raw.startswith(("http://", "https://")):
            raw = "http://" + raw
        return raw

    def load_proxies(self, from_file=False):
        if from_file and os.path.exists(self.proxies_file):
            with open(self.proxies_file) as f:
                self.proxy_text.delete(1.0, END)
                self.proxy_text.insert(END, f.read())
        raw_lines = self.proxy_text.get(1.0, END).splitlines()
        self.proxy_list = []
        for line in raw_lines:
            p = self._sanitise_proxy(line)
            if p:
                self.proxy_list.append(p)
        self.proxy_index = -1
        self.proxy_cnt.config(text=f"Proxies: {len(self.proxy_list)} loaded")

    def load_proxies_from_file(self):
        self.load_proxies(from_file=True)
        self.log(f"Loaded {len(self.proxy_list)} proxies.")

    def save_proxies_to_file(self):
        self.load_proxies(from_file=False)  # refresh from UI
        with open(self.proxies_file, "w") as f:
            for p in self.proxy_list:
                f.write(p + "\n")
        self.log(f"Saved {len(self.proxy_list)} proxies to {self.proxies_file}")

    def get_next_proxy(self):
        if not self.proxy_list:
            return None
        self.proxy_index = (self.proxy_index + 1) % len(self.proxy_list)
        return self.proxy_list[self.proxy_index]

    def remove_proxy(self, proxy_url):
        """Thread‑safe removal of a dead proxy."""
        if proxy_url in self.proxy_list:
            self.proxy_list.remove(proxy_url)
            self.log(f"Removed dead proxy: {proxy_url}", "yellow")
            self.root.after(0, self._refresh_proxy_display)

    def _refresh_proxy_display(self):
        self.proxy_text.delete(1.0, END)
        self.proxy_text.insert(END, "\n".join(self.proxy_list))
        self.proxy_cnt.config(text=f"Proxies: {len(self.proxy_list)} loaded")

    # --- Start / Stop ---
    def start_sniper(self):
        try:
            delay = float(self.delay_var.get())
            if delay < 0:
                raise ValueError
        except:
            messagebox.showerror("Error", "Invalid delay (positive number required)")
            return
        try:
            length = int(self.length_var.get())
            if not 1 <= length <= 32:
                raise ValueError
        except:
            messagebox.showerror("Error", "Invalid length (1-32)")
            return

        self.load_proxies(from_file=False)  # refresh proxy list from UI
        self.start_btn.config(state=DISABLED)
        self.stop_btn.config(state=NORMAL)
        self.status_lbl.config(text="Running...")
        self.checked_lbl.config(text="Checked: 0")
        self.avail_lbl.config(text="Available: 0")

        self.sniper = SniperThread(self)
        self.sniper.start()
        self._update_counters()

    def stop_sniper(self):
        if self.sniper:
            self.sniper.stop()
        self.start_btn.config(state=NORMAL)
        self.stop_btn.config(state=DISABLED)
        self.status_lbl.config(text="Stopped by user.")

    def update_counter_checked(self):
        if self.sniper:
            self.root.after(0, lambda: self.checked_lbl.config(text=f"Checked: {self.sniper.checked}"))

    def _update_counters(self):
        if self.sniper and self.sniper.running:
            self.checked_lbl.config(text=f"Checked: {self.sniper.checked}")
            self.root.after(1000, self._update_counters)

    def update_status(self, text):
        self.status_lbl.config(text=text)

    def on_close(self):
        if self.sniper:
            self.sniper.stop()
        self.root.destroy()

# --- Entry point ---
if __name__ == "__main__":
    app = ODUSApp()
    app.root.mainloop()   # <--- FIXED
