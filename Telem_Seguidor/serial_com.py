"""
╔══════════════════════════════════════════════════════╗
║  LLANERO - Control Bluetooth GUI                     ║
║  Gabriel Carrizales · Bryam Muñiz · Kevyn Delgado    ║
║  ESP32 · TB6612FNG · 7.4v  —  Futbol Sumo 2025       ║
╚══════════════════════════════════════════════════════╝

Requiere:  pip install pyserial
Bluetooth: Empareja el dispositivo "01_LLANERO" primero.
           Windows → COM# / Linux → /dev/rfcomm0
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import serial
import serial.tools.list_ports
import time

# ─────────────────────── Paleta ────────────────────────
BG        = "#0d0f14"
PANEL     = "#161b24"
ACCENT    = "#00e5ff"
ACCENT2   = "#ff4060"
BTN_IDLE  = "#1e2533"
BTN_HOVER = "#263040"
BTN_ACT   = "#00e5ff"
TXT       = "#e0e8f0"
TXT_DIM   = "#4a5568"
GREEN     = "#00ff88"
ORANGE    = "#ff9900"

FONT_TITLE = ("Courier", 18, "bold")
FONT_SUB   = ("Courier", 9)
FONT_BTN   = ("Courier", 22, "bold")
FONT_LABEL = ("Courier", 10, "bold")
FONT_STATUS= ("Courier", 10)

# ─────────── Mapeo comando → caracteres BT ──────────────
CMD = {
    "F": b"F",  # adelante
    "B": b"B",  # atrás
    "L": b"L",  # girar izquierda
    "R": b"R",  # girar derecha
    "G": b"G",  # diagonal adelante-izq
    "I": b"I",  # diagonal adelante-der
    "H": b"H",  # diagonal atrás-izq
    "J": b"J",  # diagonal atrás-der
    "S": b"S",  # stop
}

# Teclas del teclado → comando
KEY_MAP = {
    "w": "F", "Up":    "F",
    "s": "B", "Down":  "B",
    "a": "L", "Left":  "L",
    "d": "R", "Right": "R",
}


class RobotController(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("01_LLANERO — Futbol Sumo 2025")
        self.configure(bg=BG)
        self.resizable(False, False)

        self.serial_conn: serial.Serial | None = None
        self.connected   = False
        self.speed_level = 9          # Q = 100 %
        self._active_btns: set = set()
        self._pressed_keys: set = set()
        self._last_cmd = "S"

        self._build_ui()
        self._bind_keys()
        self._refresh_ports()

    # ═══════════════════════ UI ═══════════════════════
    def _build_ui(self):
        # ── Encabezado ─────────────────────────────────
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=20, pady=(18, 0))

        tk.Label(hdr, text="◈  LLANERO", font=FONT_TITLE,
                 fg=ACCENT, bg=BG).pack(side="left")

        self.lbl_conn = tk.Label(hdr, text="● DESCONECTADO",
                                 font=FONT_STATUS, fg=ACCENT2, bg=BG)
        self.lbl_conn.pack(side="right", padx=4)

        tk.Label(self, text="Futbol Sumo 2025  ·  ESP32 · TB6612FNG · 7.4 V",
                 font=FONT_SUB, fg=TXT_DIM, bg=BG).pack(anchor="w", padx=22)

        sep = tk.Frame(self, height=1, bg=ACCENT); sep.pack(fill="x", padx=20, pady=8)

        # ── Cuerpo principal ───────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(padx=20, pady=6)

        # Col izquierda: conexión + velocidad
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", padx=(0, 20), anchor="n")

        self._build_connection_panel(left)
        self._build_speed_panel(left)
        self._build_cmd_log(left)

        # Col derecha: dpad
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", anchor="n")
        self._build_dpad(right)

        # ── Footer ─────────────────────────────────────
        sep2 = tk.Frame(self, height=1, bg=TXT_DIM); sep2.pack(fill="x", padx=20, pady=(8,0))
        tk.Label(self, text="W A S D / Flechas · Mantén presionado · Q = velocidad máx",
                 font=FONT_SUB, fg=TXT_DIM, bg=BG).pack(pady=(4, 14))

    # ── Panel conexión ──────────────────────────────────
    def _build_connection_panel(self, parent):
        frm = tk.LabelFrame(parent, text=" CONEXIÓN BLUETOOTH ",
                             font=FONT_SUB, fg=ACCENT, bg=PANEL,
                             bd=1, relief="solid")
        frm.pack(fill="x", pady=(0, 10))

        row1 = tk.Frame(frm, bg=PANEL); row1.pack(fill="x", padx=10, pady=(8,4))
        tk.Label(row1, text="Puerto:", font=FONT_LABEL, fg=TXT, bg=PANEL).pack(side="left")

        self.port_var = tk.StringVar()
        self.port_cb  = ttk.Combobox(row1, textvariable=self.port_var, width=14,
                                     state="readonly")
        self.port_cb.pack(side="left", padx=6)

        self._icon_btn(row1, "↺", self._refresh_ports, ACCENT).pack(side="left")

        row2 = tk.Frame(frm, bg=PANEL); row2.pack(fill="x", padx=10, pady=(0,10))
        self.btn_connect = self._styled_btn(row2, "CONECTAR", self._toggle_connect,
                                            color=GREEN, width=18)
        self.btn_connect.pack()

    # ── Panel velocidad ─────────────────────────────────
    def _build_speed_panel(self, parent):
        frm = tk.LabelFrame(parent, text=" VELOCIDAD ",
                             font=FONT_SUB, fg=ACCENT, bg=PANEL,
                             bd=1, relief="solid")
        frm.pack(fill="x", pady=(0, 10))

        inner = tk.Frame(frm, bg=PANEL); inner.pack(padx=10, pady=8)

        self.lbl_speed = tk.Label(inner, text="100 %", font=("Courier", 24, "bold"),
                                  fg=ACCENT, bg=PANEL, width=6)
        self.lbl_speed.grid(row=0, column=0, rowspan=2, padx=(0, 10))

        tk.Label(inner, text="MAX", font=FONT_LABEL, fg=TXT_DIM, bg=PANEL).grid(row=0, column=2, sticky="w")

        self.speed_scale = tk.Scale(inner, from_=0, to=100, orient="horizontal",
                                    length=170, bg=PANEL, fg=TXT, troughcolor=BTN_IDLE,
                                    highlightthickness=0, bd=0,
                                    activebackground=ACCENT, sliderrelief="flat",
                                    command=self._on_speed_change)
        self.speed_scale.set(100)
        self.speed_scale.grid(row=0, column=1, columnspan=2)

        # Botones rápidos
        qrow = tk.Frame(inner, bg=PANEL); qrow.grid(row=1, column=1, columnspan=2, pady=(4,0))
        for pct, label in [(25,"25%"),(50,"50%"),(75,"75%"),(100,"MAX")]:
            b = tk.Button(qrow, text=label, font=FONT_SUB,
                          bg=BTN_IDLE, fg=TXT, relief="flat", bd=0,
                          activebackground=ACCENT, activeforeground=BG, padx=4,
                          command=lambda p=pct: self._set_speed_pct(p))
            b.pack(side="left", padx=2)

    # ── Log de comandos ─────────────────────────────────
    def _build_cmd_log(self, parent):
        frm = tk.LabelFrame(parent, text=" ÚLTIMO COMANDO ",
                             font=FONT_SUB, fg=ACCENT, bg=PANEL,
                             bd=1, relief="solid")
        frm.pack(fill="x")

        self.lbl_cmd = tk.Label(frm, text="—", font=("Courier", 26, "bold"),
                                fg=ACCENT2, bg=PANEL, width=12)
        self.lbl_cmd.pack(pady=8)

        self.lbl_cmd_name = tk.Label(frm, text="EN ESPERA", font=FONT_LABEL,
                                     fg=TXT_DIM, bg=PANEL)
        self.lbl_cmd_name.pack(pady=(0, 10))

    # ── D-Pad ───────────────────────────────────────────
    def _build_dpad(self, parent):
        tk.Label(parent, text="CONTROL DIRECCIONAL", font=FONT_LABEL,
                 fg=TXT_DIM, bg=BG).pack(pady=(0, 8))

        grid = tk.Frame(parent, bg=BG)
        grid.pack()

        # Disposición:  G  F  I
        #               L  S  R
        #               H  B  J
        layout = [
            [("G","↖", 0,0), ("F","▲", 0,1), ("I","↗", 0,2)],
            [("L","◀", 1,0), ("S","■", 1,1), ("R","▶", 1,2)],
            [("H","↙", 2,0), ("B","▼", 2,1), ("J","↘", 2,2)],
        ]
        self._dpad_btns = {}

        for row in layout:
            for cmd, sym, r, c in row:
                is_center = (cmd == "S")
                is_arrow  = cmd in ("F","B","L","R")
                color = ACCENT2 if is_center else (ACCENT if is_arrow else TXT)
                btn = self._dpad_button(grid, sym, cmd, color)
                btn.grid(row=r, column=c, padx=4, pady=4)
                self._dpad_btns[cmd] = btn

    def _dpad_button(self, parent, symbol, cmd, color):
        btn = tk.Label(parent, text=symbol, font=FONT_BTN,
                       fg=color, bg=BTN_IDLE,
                       width=3, height=1, relief="flat", bd=0)
        btn.bind("<ButtonPress-1>",   lambda e, c=cmd: self._dpad_press(c))
        btn.bind("<ButtonRelease-1>", lambda e, c=cmd: self._dpad_release(c))
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=BTN_HOVER))
        btn.bind("<Leave>", lambda e, b=btn, c=cmd: b.configure(
            bg=BTN_ACT if c in self._active_btns else BTN_IDLE))
        return btn

    # ═══════════════════════ Helpers UI ════════════════
    def _styled_btn(self, parent, text, cmd, color=ACCENT, width=12):
        b = tk.Button(parent, text=text, font=FONT_LABEL,
                      bg=BTN_IDLE, fg=color, relief="flat", bd=0,
                      activebackground=color, activeforeground=BG,
                      width=width, pady=6, command=cmd)
        b.bind("<Enter>", lambda e: b.configure(bg=BTN_HOVER))
        b.bind("<Leave>", lambda e: b.configure(bg=BTN_IDLE))
        return b

    def _icon_btn(self, parent, text, cmd, color=TXT):
        return tk.Button(parent, text=text, font=FONT_LABEL,
                         bg=BTN_IDLE, fg=color, relief="flat", bd=0,
                         activebackground=BTN_HOVER, padx=6,
                         command=cmd)

    # ═══════════════════════ Lógica ════════════════════
    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb["values"] = ports
        if ports:
            self.port_cb.current(0)

    def _toggle_connect(self):
        if self.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("Sin puerto", "Selecciona un puerto COM.")
            return
        try:
            self.serial_conn = serial.Serial(port, baudrate=9600, timeout=1)
            time.sleep(1.5)
            self.connected = True
            self.lbl_conn.configure(text="● CONECTADO", fg=GREEN)
            self.btn_connect.configure(text="DESCONECTAR", fg=ACCENT2)
        except Exception as e:
            messagebox.showerror("Error de conexión", str(e))

    def _disconnect(self):
        self._send("S")
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.connected = False
        self.lbl_conn.configure(text="● DESCONECTADO", fg=ACCENT2)
        self.btn_connect.configure(text="CONECTAR", fg=GREEN)

    def _send(self, cmd: str):
        """Envía un byte al robot por Bluetooth/Serial."""
        if not self.connected or not self.serial_conn:
            return
        try:
            self.serial_conn.write(CMD.get(cmd, b"S"))
        except Exception:
            self._disconnect()

    def _update_cmd_label(self, cmd: str):
        names = {
            "F":"ADELANTE","B":"ATRÁS","L":"IZQ.","R":"DER.",
            "G":"ADELANTE-IZQ","I":"ADELANTE-DER",
            "H":"ATRÁS-IZQ","J":"ATRÁS-DER","S":"STOP",
        }
        self.lbl_cmd.configure(text=cmd)
        self.lbl_cmd_name.configure(text=names.get(cmd,"—"))

    # ── Velocidad ───────────────────────────────────────
    def _on_speed_change(self, val):
        pct = int(float(val))
        self.lbl_speed.configure(text=f"{pct} %")
        # Enviar dígito de velocidad al robot
        level = round(pct / 10)        # 0..10
        if level == 10:
            self._send_raw(b"Q")
        else:
            self._send_raw(str(level).encode())

    def _set_speed_pct(self, pct):
        self.speed_scale.set(pct)

    def _send_raw(self, data: bytes):
        if not self.connected or not self.serial_conn:
            return
        try:
            self.serial_conn.write(data)
        except Exception:
            self._disconnect()

    # ── D-Pad eventos ───────────────────────────────────
    def _dpad_press(self, cmd):
        self._active_btns.add(cmd)
        btn = self._dpad_btns.get(cmd)
        if btn:
            btn.configure(bg=BTN_ACT, fg=BG)
        self._send(cmd)
        self._update_cmd_label(cmd)

    def _dpad_release(self, cmd):
        self._active_btns.discard(cmd)
        btn = self._dpad_btns.get(cmd)
        color = ACCENT2 if cmd == "S" else (ACCENT if cmd in "FBLR" else TXT)
        if btn:
            btn.configure(bg=BTN_IDLE, fg=color)
        # Solo para y si no hay otra tecla activa
        if not self._active_btns and not self._pressed_keys:
            self._send("S")
            self._update_cmd_label("S")

    # ── Teclado ─────────────────────────────────────────
    def _bind_keys(self):
        self.bind("<KeyPress>",   self._on_key_press)
        self.bind("<KeyRelease>", self._on_key_release)

    def _on_key_press(self, event):
        key = event.keysym
        if key in self._pressed_keys:
            return   # auto-repeat
        cmd = KEY_MAP.get(key)
        if cmd:
            self._pressed_keys.add(key)
            # Resaltar botón dpad
            btn = self._dpad_btns.get(cmd)
            if btn:
                btn.configure(bg=BTN_ACT, fg=BG)
            self._send(cmd)
            self._update_cmd_label(cmd)

    def _on_key_release(self, event):
        key = event.keysym
        self._pressed_keys.discard(key)
        cmd = KEY_MAP.get(key)
        if cmd:
            btn = self._dpad_btns.get(cmd)
            color = ACCENT if cmd in "FBLR" else TXT
            if btn:
                btn.configure(bg=BTN_IDLE, fg=color)
        # Detener si no queda ninguna tecla activa
        if not self._pressed_keys and not self._active_btns:
            self._send("S")
            self._update_cmd_label("S")

    # ── Cierre limpio ───────────────────────────────────
    def on_close(self):
        self._disconnect()
        self.destroy()


# ═══════════════════════════ Main ══════════════════════
if __name__ == "__main__":
    app = RobotController()
    app.protocol("WM_DELETE_WINDOW", app.on_close)

    # Estilo ttk para el Combobox
    style = ttk.Style()
    style.theme_use("default")
    style.configure("TCombobox",
                    fieldbackground=BTN_IDLE, background=BTN_IDLE,
                    foreground=TXT, selectbackground=BTN_HOVER,
                    bordercolor=TXT_DIM, arrowcolor=ACCENT)

    app.mainloop()