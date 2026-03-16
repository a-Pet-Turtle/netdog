#!/usr/bin/env python3
"""
netdog v3 — multi-user LAN chat with file transfer and rejoin
No external libraries required.
"""

import sys
import os
import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import customtkinter as ctk
from PIL import Image
from datetime import datetime
import json
import base64
import struct

# ── Theme ──────────────────────────────────────────────────────────────────────
BG        = "#1a1a1a"
BG2       = "#242424"
BG3       = "#2e2e2e"
FG        = "#e8e8e8"
ACCENT    = "#00cc88"
ACCENT2   = "#88ccff"
DIM       = "#555555"
ERR       = "#ff6666"
YELLOW    = "#ffcc44"
FONT_MONO = ("Courier", 11)
FONT_UI   = ("Courier", 10)

# ── Config file ────────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.expanduser("~/.netdog_config.json")
SAVE_DIR    = os.path.expanduser("~/netdog_files")
LOGO_PATH = os.path.join(
    getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))),
    "netdoglogo.png"
)
def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f)
    except:
        pass


class StartupDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        self.title("netdog")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()

        try:
            _lp = LOGO_PATH
            self._startup_logo = ctk.CTkImage(
                light_image=Image.open(_lp),
                dark_image=Image.open(_lp),
                size=(120, 120)
            )
            ctk.CTkLabel(self, image=self._startup_logo, text="", bg_color=BG).pack(pady=(12, 0))
        except Exception as e:
            print(f"startup logo: {e}")
        tk.Label(self, text="netdog", font=("Courier", 16, "bold"),
                 bg=BG, fg=ACCENT).pack(pady=(16, 4))
        tk.Label(self, text="LAN chat — no internet required",
                 font=FONT_UI, bg=BG, fg=DIM).pack(pady=(0, 8))

        # Rejoin last session button
        cfg = load_config()
        if cfg.get("last_mode"):
            last_info = (f"{cfg.get('last_name','?')}  •  "
                         f"{'hosting' if cfg['last_mode']=='host' else cfg.get('last_host','?')}  •  "
                         f"room {cfg.get('last_port', '?')}")
            rejoin_frame = tk.Frame(self, bg=BG2, padx=10, pady=8)
            rejoin_frame.pack(fill=tk.X, padx=20, pady=(0, 8))
            tk.Label(rejoin_frame, text="↩ rejoin last session",
                     font=("Courier", 9), bg=BG2, fg=DIM).pack(anchor='w')
            tk.Label(rejoin_frame, text=last_info,
                     font=FONT_UI, bg=BG2, fg=ACCENT2).pack(anchor='w')
            tk.Button(rejoin_frame, text="reconnect", font=FONT_UI,
                      bg=ACCENT2, fg=BG, relief=tk.FLAT, padx=10,
                      cursor="hand2",
                      command=lambda: self._rejoin(cfg)).pack(anchor='e', pady=(4,0))

        # Mode selection
        mode_frame = tk.Frame(self, bg=BG)
        mode_frame.pack(pady=4)
        self.mode = tk.StringVar(value="host")
        tk.Radiobutton(mode_frame, text="Host a room", variable=self.mode,
                       value="host", bg=BG, fg=FG, selectcolor=BG2,
                       activebackground=BG, font=FONT_UI,
                       command=self._update_fields).pack(side=tk.LEFT, padx=8)
        tk.Radiobutton(mode_frame, text="Join a room", variable=self.mode,
                       value="join", bg=BG, fg=FG, selectcolor=BG2,
                       activebackground=BG, font=FONT_UI,
                       command=self._update_fields).pack(side=tk.LEFT, padx=8)

        # Fields
        fields = tk.Frame(self, bg=BG)
        fields.pack(pady=8, padx=24, fill=tk.X)

        tk.Label(fields, text="Your name:", font=FONT_UI, bg=BG, fg=FG,
                 width=14, anchor='w').grid(row=0, column=0, pady=3)
        self.name_var = tk.StringVar(value=cfg.get("last_name", ""))
        tk.Entry(fields, textvariable=self.name_var, font=FONT_MONO,
                 bg=BG2, fg=FG, insertbackground=ACCENT,
                 relief=tk.FLAT).grid(row=0, column=1, sticky='ew', padx=4)

        self.host_label = tk.Label(fields, text="Host IP:", font=FONT_UI,
                                   bg=BG, fg=DIM, width=14, anchor='w')
        self.host_label.grid(row=1, column=0, pady=3)
        self.host_var = tk.StringVar(value=cfg.get("last_host", ""))
        self.host_entry = tk.Entry(fields, textvariable=self.host_var,
                                   font=FONT_MONO, bg=BG3, fg=FG,
                                   insertbackground=ACCENT, relief=tk.FLAT,
                                   state=tk.DISABLED)
        self.host_entry.grid(row=1, column=1, sticky='ew', padx=4)

        tk.Label(fields, text="Room number:", font=FONT_UI, bg=BG, fg=FG,
                 width=14, anchor='w').grid(row=2, column=0, pady=3)
        self.port_var = tk.StringVar(value=str(cfg.get("last_port", "12345")))
        tk.Entry(fields, textvariable=self.port_var, font=FONT_MONO,
                 bg=BG2, fg=FG, insertbackground=ACCENT,
                 relief=tk.FLAT).grid(row=2, column=1, sticky='ew', padx=4)

        fields.columnconfigure(1, weight=1)

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            my_ip = s.getsockname()[0]
            s.close()
        except:
            my_ip = "unknown"
        self.my_ip = my_ip
        tk.Label(self, text=f"your IP: {my_ip} (share this if hosting)",
                 font=("Courier", 9), bg=BG, fg=ACCENT2).pack(pady=(0, 4))

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=(4, 16))
        tk.Button(btn_frame, text="connect", font=FONT_UI,
                  bg=ACCENT, fg=BG, relief=tk.FLAT, padx=16,
                  activebackground="#00aa66", cursor="hand2",
                  command=self._submit).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="quit", font=FONT_UI,
                  bg=BG3, fg=FG, relief=tk.FLAT, padx=16,
                  activebackground=BG2, cursor="hand2",
                  command=self.destroy).pack(side=tk.LEFT, padx=6)

        self.bind("<Return>", lambda e: self._submit())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._update_fields()

    def _rejoin(self, cfg):
        if cfg["last_mode"] == "join" and not cfg.get("last_host"):
            messagebox.showerror("netdog", "No host IP saved for last session.", parent=self)
            return
        self.result = {
            "mode": cfg["last_mode"],
            "name": cfg["last_name"],
            "host": cfg.get("last_host", ""),
            "port": cfg["last_port"],
            "_rejoin": True,
        }
        self.destroy()

    def _update_fields(self):
        if self.mode.get() == "host":
            self.host_entry.config(state=tk.DISABLED, bg=BG3)
            self.host_label.config(fg=DIM)
        else:
            self.host_entry.config(state=tk.NORMAL, bg=BG2)
            self.host_label.config(fg=FG)

    def _submit(self):
        name = self.name_var.get().strip()
        port = self.port_var.get().strip()
        host = self.host_var.get().strip()
        if not name:
            messagebox.showerror("netdog", "Please enter your name.", parent=self)
            return
        if not port.isdigit():
            messagebox.showerror("netdog", "Room number must be a number.", parent=self)
            return
        if self.mode.get() == "join" and not host:
            messagebox.showerror("netdog", "Please enter the host IP.", parent=self)
            return
        self.result = {"mode": self.mode.get(), "name": name,
                       "host": host, "port": int(port),
                       "my_ip": getattr(self, "my_ip", "")}
        self.destroy()


class NetdogApp:
    def __init__(self, root):
        self.root = root
        self.my_name = "me"
        self.mode = None
        self.clients = {}
        self.client_names = {}
        self.server_sock = None
        self.conn_sock = None
        self.running = False
        self._show_startup()

    def _show_startup(self):
        dlg = StartupDialog(self.root)
        self.root.wait_window(dlg)
        if dlg.result is None:
            self.root.destroy()
            return
        cfg = dlg.result
        self.my_name = cfg["name"]
        self.mode = cfg["mode"]
        # Save config for rejoin
        save_config({
            "last_mode": cfg["mode"],
            "last_name": cfg["name"],
            "last_host": cfg.get("host", ""),
            "last_port": cfg["port"],
        })
        if cfg["mode"] == "host":
            self._start_server(cfg["port"])
        else:
            self._start_client(cfg["host"], cfg["port"])

    # ── Server ────────────────────────────────────────────────────────────────

    def _start_server(self, port):
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind(("", port))
            self.server_sock.listen(10)
        except Exception as e:
            messagebox.showerror("netdog", f"Could not start server:\n{e}")
            self.root.destroy()
            return
        self.running = True
        self._build_ui(f"hosting  •  room {port}")
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_sock.accept()
                addr_str = f"{addr[0]}:{addr[1]}"
                self.clients[addr_str] = conn
                self.client_names[addr_str] = addr_str
                self.root.after(0, self._log, f"● {addr_str} joined\n", "meta")
                self.root.after(0, self._refresh_users)
                threading.Thread(target=self._recv_loop,
                                 args=(conn, addr_str), daemon=True).start()
            except:
                break

    def _broadcast(self, payload, exclude=None):
        dead = []
        for addr, sock in list(self.clients.items()):
            if addr == exclude:
                continue
            try:
                sock.sendall(payload)
            except:
                dead.append(addr)
        for addr in dead:
            self._drop_client(addr)

    def _drop_client(self, addr_str):
        name = self.client_names.get(addr_str, addr_str)
        self.clients.pop(addr_str, None)
        self.client_names.pop(addr_str, None)
        self.root.after(0, self._log, f"● {name} left\n", "meta")
        self.root.after(0, self._refresh_users)

    # ── Client ────────────────────────────────────────────────────────────────

    def _start_client(self, host, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            self.conn_sock = sock
        except Exception as e:
            messagebox.showerror("netdog", f"Could not connect:\n{e}")
            self._show_startup()
            return
        self.running = True
        self._build_ui(f"room {port}  •  host {host}")
        self._send_raw(self.conn_sock, f"__NAME__{self.my_name}\n<<<END>>>".encode())
        # Ask host to introduce themselves
        self._send_raw(self.conn_sock, f"__WHOAMI__\n<<<END>>>".encode())
        threading.Thread(target=self._recv_loop,
                         args=(self.conn_sock, host), daemon=True).start()

    # ── Low-level send/recv ───────────────────────────────────────────────────

    def _send_raw(self, sock, data: bytes):
        """Send length-prefixed bytes."""
        sock.sendall(struct.pack(">I", len(data)) + data)

    def _send_to_all(self, data: bytes, exclude=None):
        if self.mode == "host":
            self._broadcast(struct.pack(">I", len(data)) + data, exclude=exclude)
        else:
            self._send_raw(self.conn_sock, data)

    def _recv_exactly(self, sock, n):
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("disconnected")
            buf += chunk
        return buf

    # ── Receive loop ─────────────────────────────────────────────────────────

    def _recv_loop(self, sock, peer):
        while self.running:
            try:
                raw_len = self._recv_exactly(sock, 4)
                length = struct.unpack(">I", raw_len)[0]
                data = self._recv_exactly(sock, length).decode(errors="replace")

                if data.startswith("__WHOAMI__") and "<<<END>>>" in data:
                    # Client asking for host's name — send it back
                    if self.mode == "host":
                        reply = f"__HOSTINFO__{self.my_name}\n<<<END>>>".encode()
                        try:
                            self._send_raw(sock, reply)
                        except:
                            pass
                    continue

                if data.startswith("__HOSTINFO__") and "<<<END>>>" in data:
                    # Host introduced themselves — add to sidebar
                    host_name = data.replace("__HOSTINFO__", "").replace("\n<<<END>>>", "").strip()
                    self.client_names[peer] = f"{host_name} (host)"
                    self.root.after(0, self._refresh_users)
                    continue

                if data.startswith("__NAME__") and "<<<END>>>" in data:
                    name = data.replace("__NAME__", "").replace("\n<<<END>>>", "").strip()
                    if peer in self.client_names:
                        self.client_names[peer] = name
                        self.root.after(0, self._refresh_users)
                    if self.mode == "host":
                        relay = f"__NAME__{name}\n<<<END>>>".encode()
                        self._broadcast(struct.pack(">I", len(relay)) + relay, exclude=peer)
                    continue

                if data.startswith("__FILE__"):
                    # Format: __FILE__<filename>\n<<<SEP>>><base64data><<<END>>>
                    try:
                        _, rest = data.split("__FILE__", 1)
                        filename, b64data = rest.split("\n<<<SEP>>>", 1)
                        b64data = b64data.replace("<<<END>>>", "").strip()
                        file_bytes = base64.b64decode(b64data)
                        save_path = os.path.join(SAVE_DIR, filename)
                        with open(save_path, "wb") as f:
                            f.write(file_bytes)
                        sender = self.client_names.get(peer, peer)
                        size_kb = len(file_bytes) / 1024
                        self.root.after(0, self._log,
                            f"📎 {sender} sent {filename} ({size_kb:.1f} KB) → saved to {save_path}\n", "file")
                        if self.mode == "host":
                            raw_relay = data.encode()
                            self._broadcast(struct.pack(">I", len(raw_relay)) + raw_relay, exclude=peer)
                    except Exception as e:
                        self.root.after(0, self._log, f"file error: {e}\n", "err")
                    continue

                # Normal message
                if "<<<END>>>" in data:
                    msg = data.replace("<<<END>>>", "").strip()
                    if not msg:
                        continue
                    if self.mode == "host":
                        relay = data.encode()
                        self._broadcast(struct.pack(">I", len(relay)) + relay, exclude=peer)
                    ts = datetime.now().strftime("%H:%M")
                    if ": " in msg:
                        sender, body = msg.split(": ", 1)
                    else:
                        sender = self.client_names.get(peer, peer)
                        body = msg
                    self.root.after(0, self._log, f"[{ts}] {sender}\n", "them")
                    self.root.after(0, self._log, body + "\n\n")

            except Exception:
                break

        if self.mode == "host":
            self._drop_client(peer)
        else:
            self.root.after(0, self._on_disconnected)

    def _on_disconnected(self):
        self._log("\n● disconnected from host\n", "err")
        self.status.config(text="● disconnected", fg=ERR)

    # ── File sending ──────────────────────────────────────────────────────────

    def _send_file_from_path(self, path):
        filename = os.path.basename(path)
        try:
            with open(path, "rb") as f:
                file_bytes = f.read()
            b64 = base64.b64encode(file_bytes).decode()
            payload = f"__FILE__{filename}\n<<<SEP>>>{b64}<<<END>>>".encode()
            self._send_to_all(payload)
            size_kb = len(file_bytes) / 1024
            self._log(f"📎 you sent {filename} ({size_kb:.1f} KB)\n", "file")
        except Exception as e:
            self._log(f"file send error: {e}\n", "err")

    def send_file(self):
        path = filedialog.askopenfilename(
            title="Send a file",
            filetypes=[("All files", "*.*"),
                       ("Pickle files", "*.pkl"),
                       ("Images", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if not path:
            return
        self._send_file_from_path(path)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self, status_text):
        self.root.title("netdog")
        self.root.configure(bg=BG)
        self.root.geometry("720x560")
        self.root.minsize(500, 360)
        self.root.deiconify()
        try:
            if os.path.exists(LOGO_PATH):
                self._win_icon = tk.PhotoImage(file=LOGO_PATH)
                self.root.after(100, lambda: self.root.iconphoto(False, self._win_icon))
        except Exception as e:
            print(f"window icon: {e}")
        hdr = tk.Frame(self.root, bg=BG, pady=6)
        hdr.pack(fill=tk.X, padx=12)

        # Logo + title
        try:
            icon_path = LOGO_PATH
            if os.path.exists(icon_path):
                self._icon_img = ctk.CTkImage(
                    light_image=Image.open(icon_path),
                    dark_image=Image.open(icon_path),
                    size=(36, 36)
                )
                ctk.CTkLabel(hdr, image=self._icon_img, text="", bg_color=BG).pack(side=tk.LEFT)
        except Exception as e:
            print(f"icon load failed: {e}")
        tk.Label(hdr, text="netdog", font=("Courier", 14, "bold"),
                 bg=BG, fg=ACCENT).pack(side=tk.LEFT, padx=(4, 0))
        # Get local IP
        try:
            _s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            _s.connect(("8.8.8.8", 80))
            my_ip = _s.getsockname()[0]
            _s.close()
        except:
            my_ip = "unknown"
        tk.Label(hdr, text=f"ip: {my_ip}",
                 font=FONT_UI, bg=BG, fg=DIM).pack(side=tk.RIGHT, padx=(0, 10))
        self.status = tk.Label(hdr, text=f"● {status_text}",
                               font=FONT_UI, bg=BG, fg=ACCENT)
        self.status.pack(side=tk.RIGHT)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=12)

        sidebar = tk.Frame(body, bg=BG, width=150)
        sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="online", font=("Courier", 9),
                 bg=BG, fg=DIM).pack(anchor='w', pady=(0, 2))
        self.user_list = tk.Text(sidebar, bg=BG2, fg=FG, font=FONT_UI,
                                 relief=tk.FLAT, bd=0, padx=6, pady=4,
                                 state=tk.DISABLED)
        self.user_list.pack(fill=tk.BOTH, expand=True)
        self.user_list.tag_config("you",   foreground=ACCENT)
        self.user_list.tag_config("other", foreground=ACCENT2)

        self.history = scrolledtext.ScrolledText(
            body, bg=BG2, fg=FG, font=FONT_MONO,
            relief=tk.FLAT, bd=0, padx=10, pady=8,
            wrap=tk.WORD, state=tk.DISABLED,
        )
        self.history.pack(fill=tk.BOTH, expand=True)
        self.history.tag_config("you",  foreground=ACCENT)
        self.history.tag_config("them", foreground=ACCENT2)
        self.history.tag_config("meta", foreground=DIM)
        self.history.tag_config("err",  foreground=ERR)
        self.history.tag_config("file", foreground=YELLOW)

        inp_frame = tk.Frame(self.root, bg=BG)
        inp_frame.pack(fill=tk.X, padx=12, pady=(4, 2))
        self.input = tk.Text(
            inp_frame, bg=BG2, fg=FG, font=FONT_MONO,
            relief=tk.FLAT, bd=0, padx=10, pady=8,
            height=4, wrap=tk.WORD, insertbackground=ACCENT,
        )
        self.input.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.input.bind("<Return>", self._on_enter)
        self.input.bind("<Shift-Return>", self._on_shift_enter)

        btn_col = tk.Frame(inp_frame, bg=BG)
        btn_col.pack(side=tk.RIGHT, padx=(6, 0), fill=tk.Y)
        tk.Button(btn_col, text="send", font=FONT_UI,
                  bg=ACCENT, fg=BG, relief=tk.FLAT, padx=12,
                  activebackground="#00aa66", cursor="hand2",
                  command=self.send).pack(fill=tk.X)
        tk.Button(btn_col, text="📎 file", font=FONT_UI,
                  bg=BG3, fg=YELLOW, relief=tk.FLAT, padx=12,
                  activebackground=BG2, cursor="hand2",
                  command=self.send_file).pack(fill=tk.X, pady=(4, 0))

        tk.Label(self.root, text="Enter to send  •  Shift+Enter for newline  •  📎 to send files",
                 font=("Courier", 8), bg=BG, fg=DIM).pack(pady=(0, 6))

        self._log(f"● {status_text}\n", "meta")
        self._log(f"● files saved to {SAVE_DIR}\n", "meta")
        self._refresh_users()
        self.input.focus_set()
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

    def _refresh_users(self):
        self.user_list.config(state=tk.NORMAL)
        self.user_list.delete("1.0", tk.END)
        self.user_list.insert(tk.END, f"● {self.my_name} (you)\n", "you")
        for name in self.client_names.values():
            self.user_list.insert(tk.END, f"● {name}\n", "other")
        self.user_list.config(state=tk.DISABLED)

    def _log(self, text, tag=""):
        self.history.config(state=tk.NORMAL)
        self.history.insert(tk.END, text, tag)
        self.history.see(tk.END)
        self.history.config(state=tk.DISABLED)

    def send(self):
        msg = self.input.get("1.0", tk.END).rstrip("\n")
        if not msg.strip():
            return
        # F? prefix — send a file by path e.g. F?/home/sailas/Dumbbot/model.pkl
        if msg.strip().startswith("F?"):
            path = msg.strip()[2:].strip()
            self.input.delete("1.0", tk.END)
            if not os.path.isfile(path):
                self._log(f"file not found: {path}\n", "err")
                return
            self._send_file_from_path(path)
            return
        payload = f"{self.my_name}: {msg}\n<<<END>>>".encode()
        try:
            self._send_to_all(payload)
            ts = datetime.now().strftime("%H:%M")
            self._log(f"[{ts}] {self.my_name}\n", "you")
            self._log(msg + "\n\n")
            self.input.delete("1.0", tk.END)
        except Exception as e:
            self._log(f"send error: {e}\n", "err")

    def _on_enter(self, event):
        self.send()
        return "break"

    def _on_shift_enter(self, event):
        self.input.insert(tk.INSERT, "\n")
        return "break"

    def _quit(self):
        self.running = False
        try:
            if self.server_sock:
                self.server_sock.close()
            if self.conn_sock:
                self.conn_sock.close()
            for sock in self.clients.values():
                sock.close()
        except:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = NetdogApp(root)
    root.mainloop()