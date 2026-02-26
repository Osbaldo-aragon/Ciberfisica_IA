#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║   ZUMO MISSION CONTROL — GUI Monitor                                 ║
║   Pololu Zumo Line Follower · tkinter + pyserial                     ║
╚══════════════════════════════════════════════════════════════════════╝

Requiere:  pip install pyserial
"""

import tkinter as tk
from tkinter import ttk, font as tkfont
import threading
import queue
import serial
import serial.tools.list_ports
import json
import time
import math
import argparse
from collections import deque
from datetime import datetime

# ═══════════════════════════ PALETA ════════════════════════════════
BG          = "#060A10"
BG2         = "#0C1018"
PANEL       = "#0F1520"
PANEL2      = "#141C28"
BORDER      = "#1E2D40"
BORDER_LIT  = "#2A4060"

CYAN        = "#00E5FF"
CYAN_DIM    = "#005566"
GREEN       = "#00FF88"
GREEN_DIM   = "#004422"
RED         = "#FF3355"
RED_DIM     = "#440011"
YELLOW      = "#FFD600"
YELLOW_DIM  = "#443800"
ORANGE      = "#FF7700"
BLUE        = "#4488FF"
WHITE       = "#E8F0F8"
DIM         = "#2A3848"
DIM2        = "#1A2535"
TXT         = "#B8C8D8"
TXT_DIM     = "#4A6070"

# Fuentes (monospace para estética de terminal)
MONO = "Courier"

# ═══════════════════════════ UTILIDADES ════════════════════════════

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def lerp_color(c1, c2, t):
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"

def clamp(v, lo, hi): return max(lo, min(hi, v))


# ═══════════════════════════ CANVAS WIDGETS ═════════════════════════

class GaugeCanvas(tk.Canvas):
    """Medidor semicircular tipo tacómetro."""

    def __init__(self, parent, label="", max_val=400, unit="", **kw):
        kw.setdefault("width", 140)
        kw.setdefault("height", 90)
        kw.setdefault("bg", PANEL)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        self.label   = label
        self.max_val = max_val
        self.unit    = unit
        self._value  = 0
        self._draw(0)

    def set(self, value):
        self._value = clamp(value, 0, self.max_val)
        self.delete("all")
        self._draw(self._value)

    def _draw(self, value):
        w, h   = int(self["width"]), int(self["height"])
        cx, cy = w // 2, h - 14
        r      = min(cx, cy) - 8
        ratio  = value / max(self.max_val, 1)

        # Arco de fondo
        self.create_arc(cx - r, cy - r, cx + r, cy + r,
                        start=0, extent=180,
                        outline=DIM, width=2, style="arc")

        # Arco de relleno
        if ratio > 0:
            color = lerp_color(GREEN, RED, ratio)
            self.create_arc(cx - r, cy - r, cx + r, cy + r,
                            start=180 - ratio * 180, extent=ratio * 180,
                            outline=color, width=4, style="arc")

        # Aguja
        angle  = math.radians(180 - ratio * 180)
        nx     = cx + (r - 6) * math.cos(angle)
        ny     = cy - (r - 6) * math.sin(angle)
        color  = lerp_color(GREEN, RED, ratio)
        self.create_line(cx, cy, nx, ny, fill=color, width=2)
        self.create_oval(cx - 4, cy - 4, cx + 4, cy + 4,
                         fill=PANEL2, outline=color)

        # Valor
        self.create_text(cx, cy - 20,
                         text=f"{int(value)}", font=(MONO, 14, "bold"),
                         fill=WHITE)
        self.create_text(cx, cy - 6,
                         text=self.unit, font=(MONO, 7),
                         fill=TXT_DIM)
        # Label
        self.create_text(cx, h - 4,
                         text=self.label, font=(MONO, 8, "bold"),
                         fill=TXT_DIM)


class LinePositionCanvas(tk.Canvas):
    """Visualizador de posición de línea (0–5000, centro=2500)."""

    def __init__(self, parent, **kw):
        kw.setdefault("width", 300)
        kw.setdefault("height", 48)
        kw.setdefault("bg", PANEL)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        self._pos = 2500
        self._draw(2500)

    def set(self, pos):
        self._pos = clamp(pos, 0, 5000)
        self.delete("all")
        self._draw(self._pos)

    def _draw(self, pos):
        w, h = int(self["width"]), int(self["height"])
        pad  = 18

        # Fondo del track
        self.create_rectangle(pad, h//2 - 4, w - pad, h//2 + 4,
                               fill=DIM2, outline=BORDER)

        # Ticks de sensores (6 sensores → posiciones 0, 1000, 2000, 3000, 4000, 5000)
        for i in range(6):
            tx = pad + (w - 2*pad) * i / 5
            self.create_line(tx, h//2 - 10, tx, h//2 + 10,
                             fill=BORDER_LIT, width=1)
            self.create_text(tx, h - 4,
                             text=str(i), font=(MONO, 6), fill=TXT_DIM)

        # Centro
        cx = pad + (w - 2*pad) / 2
        self.create_line(cx, 6, cx, h - 12, fill=CYAN_DIM, width=1, dash=(3, 3))

        # Marcador de posición
        px = pad + (w - 2*pad) * pos / 5000
        error = pos - 2500
        color = GREEN if abs(error) < 300 else (YELLOW if abs(error) < 800 else RED)

        self.create_oval(px - 8, h//2 - 8, px + 8, h//2 + 8,
                         fill=color, outline=WHITE, width=1)

        # Texto pos / error
        self.create_text(w - 4, 8,
                         text=f"pos:{pos}", font=(MONO, 7), fill=TXT_DIM, anchor="e")
        self.create_text(4, 8,
                         text=f"err:{error:+}", font=(MONO, 7),
                         fill=(GREEN if abs(error) < 300 else RED), anchor="w")


class SparklineCanvas(tk.Canvas):
    """Mini gráfica de historial."""

    def __init__(self, parent, color=CYAN, max_points=120, y_range=(-2500, 2500), **kw):
        kw.setdefault("width", 300)
        kw.setdefault("height", 80)
        kw.setdefault("bg", PANEL)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        self.color     = color
        self.max_pts   = max_points
        self.y_min, self.y_max = y_range
        self._data: deque = deque(maxlen=max_points)

    def push(self, value):
        self._data.append(value)
        self._redraw()

    def _redraw(self):
        self.delete("all")
        w, h = int(self["width"]), int(self["height"])
        pad  = 4

        # Línea cero
        zero_y = h - pad - (0 - self.y_min) / (self.y_max - self.y_min) * (h - 2*pad)
        self.create_line(pad, zero_y, w - pad, zero_y,
                         fill=DIM, width=1, dash=(4, 4))

        if len(self._data) < 2:
            return

        pts = list(self._data)
        coords = []
        for i, v in enumerate(pts):
            x = pad + (w - 2*pad) * i / (self.max_pts - 1)
            ratio = (v - self.y_min) / max(self.y_max - self.y_min, 1)
            y = h - pad - ratio * (h - 2*pad)
            coords += [x, y]

        self.create_line(*coords, fill=self.color, width=1, smooth=True)

        # Dot en el último punto
        if coords:
            lx, ly = coords[-2], coords[-1]
            self.create_oval(lx - 3, ly - 3, lx + 3, ly + 3,
                             fill=self.color, outline="")


class LEDIndicator(tk.Canvas):
    """LED circular con glow."""

    def __init__(self, parent, color=GREEN, size=14, **kw):
        kw["width"]  = size + 4
        kw["height"] = size + 4
        kw["bg"]     = PANEL
        kw["highlightthickness"] = 0
        super().__init__(parent, **kw)
        self._color  = color
        self._size   = size
        self._on     = False
        self._draw()

    def set(self, on: bool):
        if on != self._on:
            self._on = on
            self._draw()

    def _draw(self):
        self.delete("all")
        s  = self._size
        c  = s // 2 + 2
        if self._on:
            # Glow externo
            self.create_oval(c - s//2 - 2, c - s//2 - 2,
                             c + s//2 + 2, c + s//2 + 2,
                             fill="", outline=self._color + "44", width=3)
            self.create_oval(c - s//2, c - s//2, c + s//2, c + s//2,
                             fill=self._color, outline=WHITE, width=1)
        else:
            dim = lerp_color(self._color, "#111111", 0.8)
            self.create_oval(c - s//2, c - s//2, c + s//2, c + s//2,
                             fill=dim, outline=BORDER, width=1)


# ═══════════════════════════ PANEL PRINCIPAL ════════════════════════

class ZumoGUI(tk.Tk):

    def __init__(self, args):
        super().__init__()
        self.args = args
        self.title("ZUMO MISSION CONTROL")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(860, 620)

        # Estado
        self.ser: serial.Serial | None = None
        self.connected   = False
        self.running     = False
        self.kp          = 0.25
        self.kd          = 6.0
        self.max_speed   = 400
        self.interval_ms = 100
        self.telem_count = 0
        self.last_telem  = {}

        self._stop_event  = threading.Event()
        self._reader_th: threading.Thread | None = None
        self._cmd_buf     = ""
        self._msg_queue: queue.Queue = queue.Queue()   # hilo → UI

        # Historial para gráficas
        self._hist_error = deque(maxlen=120)
        self._hist_m1    = deque(maxlen=120)
        self._hist_m2    = deque(maxlen=120)

        self._log_lines: list[tuple[str, str]] = []   # (texto, color)
        self._blink_state = False

        self._build_ui()
        self._start_blink_loop()
        self._poll_queue()   # drena mensajes del hilo serial en el hilo principal

        # Auto-conectar si se dio puerto por CLI
        if args.port:
            self.port_var.set(args.port)
            self.after(600, self._connect)

    # ═══════════════════════ BUILD UI ═══════════════════════════
    def _build_ui(self):
        self._build_topbar()

        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # Columna izquierda: controles
        left = tk.Frame(main, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self._build_connection_panel(left)
        self._build_pid_panel(left)
        self._build_speed_panel(left)
        self._build_telem_settings(left)
        self._build_control_panel(left)

        # Columna derecha: monitoreo
        right = tk.Frame(main, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self._build_sensor_panel(right)
        self._build_charts_panel(right)
        self._build_log_panel(right)

    # ── Top bar ─────────────────────────────────────────────────
    def _build_topbar(self):
        bar = tk.Frame(self, bg=PANEL, height=42)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # Logo
        tk.Label(bar, text="◈ ZUMO MISSION CONTROL",
                 font=(MONO, 13, "bold"), fg=CYAN, bg=PANEL,
                 padx=16).pack(side="left", pady=8)

        tk.Label(bar, text="Pololu Zumo · Line Follower · PID",
                 font=(MONO, 8), fg=TXT_DIM, bg=PANEL).pack(side="left", pady=8)

        # Indicadores de estado (derecha)
        right = tk.Frame(bar, bg=PANEL)
        right.pack(side="right", padx=12, pady=6)

        self.led_conn = LEDIndicator(right, color=GREEN, size=12)
        self.led_conn.pack(side="left")
        self.lbl_conn_status = tk.Label(right, text="OFFLINE",
                                         font=(MONO, 9, "bold"), fg=RED, bg=PANEL)
        self.lbl_conn_status.pack(side="left", padx=(4, 16))

        self.led_run = LEDIndicator(right, color=YELLOW, size=12)
        self.led_run.pack(side="left")
        self.lbl_run_status = tk.Label(right, text="IDLE",
                                        font=(MONO, 9, "bold"), fg=TXT_DIM, bg=PANEL)
        self.lbl_run_status.pack(side="left", padx=(4, 16))

        self.lbl_pkt = tk.Label(right, text="PKT: 0",
                                 font=(MONO, 8), fg=TXT_DIM, bg=PANEL)
        self.lbl_pkt.pack(side="left", padx=(0, 8))

        # Separador
        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x")

    # ── Conexión ─────────────────────────────────────────────────
    def _build_connection_panel(self, parent):
        frm = self._panel(parent, "[ SERIAL ]")
        frm.pack(fill="x", pady=(0, 6))

        row = tk.Frame(frm, bg=PANEL)
        row.pack(fill="x", padx=8, pady=(4, 2))

        tk.Label(row, text="PORT", font=(MONO, 8), fg=TXT_DIM, bg=PANEL,
                 width=6, anchor="w").pack(side="left")

        self.port_var = tk.StringVar()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb = ttk.Combobox(row, textvariable=self.port_var,
                                     values=ports, width=12, state="readonly",
                                     font=(MONO, 9))
        if ports: self.port_cb.current(0)
        self.port_cb.pack(side="left", padx=4)

        self._icon_btn(row, "↺", self._refresh_ports).pack(side="left")

        row2 = tk.Frame(frm, bg=PANEL)
        row2.pack(fill="x", padx=8, pady=(2, 8))
        tk.Label(row2, text="BAUD", font=(MONO, 8), fg=TXT_DIM, bg=PANEL,
                 width=6, anchor="w").pack(side="left")
        self.baud_var = tk.StringVar(value=str(getattr(self.args, "baud", 115200)))
        baud_entry = tk.Entry(row2, textvariable=self.baud_var, width=8,
                              font=(MONO, 9), bg=PANEL2, fg=TXT,
                              insertbackground=CYAN, relief="flat",
                              highlightthickness=1, highlightcolor=BORDER,
                              highlightbackground=BORDER)
        baud_entry.pack(side="left", padx=4)

        self.btn_connect = self._action_btn(frm, "▶  CONNECT", self._toggle_connect, GREEN)
        self.btn_connect.pack(fill="x", padx=8, pady=(0, 8))

    # ── PID ──────────────────────────────────────────────────────
    def _build_pid_panel(self, parent):
        frm = self._panel(parent, "[ PID CONTROL ]")
        frm.pack(fill="x", pady=(0, 6))

        inner = tk.Frame(frm, bg=PANEL)
        inner.pack(fill="x", padx=8, pady=6)

        # KP
        self.kp_var = tk.DoubleVar(value=getattr(self.args, "kp", None) or 0.25)
        self._param_row(inner, "KP", self.kp_var, 0.0, 5.0, 0.05)

        # KD
        self.kd_var = tk.DoubleVar(value=getattr(self.args, "kd", None) or 6.0)
        self._param_row(inner, "KD", self.kd_var, 0.0, 50.0, 0.5)

        self._action_btn(frm, "APPLY PID", self._apply_pid, CYAN).pack(
            fill="x", padx=8, pady=(0, 8))

    def _param_row(self, parent, label, var, from_, to_, res):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, font=(MONO, 9, "bold"), fg=CYAN,
                 bg=PANEL, width=4, anchor="w").pack(side="left")
        lbl_val = tk.Label(row, textvariable=var, font=(MONO, 9),
                           fg=WHITE, bg=PANEL, width=6)
        lbl_val.pack(side="right")
        sc = tk.Scale(row, variable=var, from_=from_, to=to_,
                      resolution=res, orient="horizontal",
                      bg=PANEL, fg=TXT, troughcolor=DIM2,
                      highlightthickness=0, bd=0,
                      activebackground=CYAN, sliderrelief="flat",
                      showvalue=False, length=110)
        sc.pack(side="left", padx=4)

    # ── Velocidad ────────────────────────────────────────────────
    def _build_speed_panel(self, parent):
        frm = self._panel(parent, "[ MAX SPEED ]")
        frm.pack(fill="x", pady=(0, 6))

        inner = tk.Frame(frm, bg=PANEL)
        inner.pack(fill="x", padx=8, pady=6)

        self.speed_var = tk.IntVar(value=getattr(self.args, "speed", None) or 400)
        self._param_row(inner, "SPD", self.speed_var, 0, 400, 10)

        self._action_btn(frm, "APPLY SPEED", self._apply_speed, YELLOW).pack(
            fill="x", padx=8, pady=(0, 8))

    # ── Intervalo telemetría ────────────────────────────────────
    def _build_telem_settings(self, parent):
        frm = self._panel(parent, "[ TELEMETRY ]")
        frm.pack(fill="x", pady=(0, 6))

        inner = tk.Frame(frm, bg=PANEL)
        inner.pack(fill="x", padx=8, pady=6)

        self.interval_var = tk.IntVar(value=getattr(self.args, "interval", None) or 100)
        self._param_row(inner, "ms", self.interval_var, 20, 2000, 10)

        self._action_btn(frm, "SET INTERVAL", self._apply_interval, BLUE).pack(
            fill="x", padx=8, pady=(0, 8))

    # ── Botones de control ──────────────────────────────────────
    def _build_control_panel(self, parent):
        frm = self._panel(parent, "[ CONTROL ]")
        frm.pack(fill="x")

        row = tk.Frame(frm, bg=PANEL)
        row.pack(fill="x", padx=8, pady=8)

        self._action_btn(row, "▶  START", self._cmd_start, GREEN).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        self._action_btn(row, "■  STOP", self._cmd_stop, RED).pack(
            side="left", expand=True, fill="x")

    # ── Sensores / posición ─────────────────────────────────────
    def _build_sensor_panel(self, parent):
        frm = self._panel(parent, "[ SENSOR · LINE POSITION ]")
        frm.pack(fill="x", pady=(0, 6))

        inner = tk.Frame(frm, bg=PANEL)
        inner.pack(fill="x", padx=8, pady=8)

        # Barra de posición
        self.line_canvas = LinePositionCanvas(inner, width=460, height=48, bg=PANEL)
        self.line_canvas.pack(fill="x", pady=(0, 8))

        # Gauges
        gauges = tk.Frame(inner, bg=PANEL)
        gauges.pack(fill="x")

        self.gauge_m1 = GaugeCanvas(gauges, label="MOTOR L", max_val=400, unit="pwm",
                                     width=140, height=90, bg=PANEL)
        self.gauge_m1.pack(side="left", expand=True)

        # Error display (centro)
        center = tk.Frame(gauges, bg=PANEL)
        center.pack(side="left", expand=True)
        tk.Label(center, text="ERROR", font=(MONO, 8), fg=TXT_DIM, bg=PANEL).pack()
        self.lbl_error_big = tk.Label(center, text="+0000",
                                       font=(MONO, 24, "bold"), fg=CYAN, bg=PANEL)
        self.lbl_error_big.pack()
        tk.Label(center, text="position", font=(MONO, 7), fg=TXT_DIM, bg=PANEL).pack()
        self.lbl_pos_big = tk.Label(center, text="2500",
                                     font=(MONO, 14), fg=WHITE, bg=PANEL)
        self.lbl_pos_big.pack()

        self.gauge_m2 = GaugeCanvas(gauges, label="MOTOR R", max_val=400, unit="pwm",
                                     width=140, height=90, bg=PANEL)
        self.gauge_m2.pack(side="left", expand=True)

    # ── Gráficas sparkline ──────────────────────────────────────
    def _build_charts_panel(self, parent):
        frm = self._panel(parent, "[ REALTIME CHARTS ]")
        frm.pack(fill="x", pady=(0, 6))

        inner = tk.Frame(frm, bg=PANEL)
        inner.pack(fill="both", padx=8, pady=6)

        # Error
        tk.Label(inner, text="LINE ERROR", font=(MONO, 7, "bold"),
                 fg=TXT_DIM, bg=PANEL, anchor="w").pack(fill="x")
        self.spark_error = SparklineCanvas(inner, color=CYAN, y_range=(-2500, 2500),
                                            width=460, height=60, bg=PANEL2)
        self.spark_error.pack(fill="x", pady=(0, 4))

        # Motores
        motors_row = tk.Frame(inner, bg=PANEL)
        motors_row.pack(fill="x")

        lf = tk.Frame(motors_row, bg=PANEL)
        lf.pack(side="left", expand=True, fill="x")
        tk.Label(lf, text="MOTOR L", font=(MONO, 7, "bold"),
                 fg=TXT_DIM, bg=PANEL, anchor="w").pack(fill="x")
        self.spark_m1 = SparklineCanvas(lf, color=GREEN, y_range=(0, 400),
                                         width=220, height=50, bg=PANEL2)
        self.spark_m1.pack(fill="x")

        rf = tk.Frame(motors_row, bg=PANEL)
        rf.pack(side="left", expand=True, fill="x", padx=(4, 0))
        tk.Label(rf, text="MOTOR R", font=(MONO, 7, "bold"),
                 fg=TXT_DIM, bg=PANEL, anchor="w").pack(fill="x")
        self.spark_m2 = SparklineCanvas(rf, color=ORANGE, y_range=(0, 400),
                                         width=220, height=50, bg=PANEL2)
        self.spark_m2.pack(fill="x")

    # ── Log de eventos ───────────────────────────────────────────
    def _build_log_panel(self, parent):
        frm = self._panel(parent, "[ EVENT LOG ]")
        frm.pack(fill="both", expand=True)

        inner = tk.Frame(frm, bg=PANEL2)
        inner.pack(fill="both", expand=True, padx=8, pady=6)

        self.log_text = tk.Text(inner, font=(MONO, 8),
                                 bg=BG, fg=TXT, relief="flat",
                                 highlightthickness=0,
                                 wrap="word", state="disabled",
                                 height=6)
        self.log_text.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(inner, orient="vertical", command=self.log_text.yview)
        vsb.pack(side="right", fill="y")
        self.log_text["yscrollcommand"] = vsb.set

        # Tags de color
        self.log_text.tag_config("ok",   foreground=GREEN)
        self.log_text.tag_config("err",  foreground=RED)
        self.log_text.tag_config("warn", foreground=YELLOW)
        self.log_text.tag_config("info", foreground=CYAN)
        self.log_text.tag_config("dim",  foreground=TXT_DIM)
        self.log_text.tag_config("data", foreground=TXT)

        # Barra de comando
        cmd_row = tk.Frame(frm, bg=PANEL)
        cmd_row.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(cmd_row, text="CMD›", font=(MONO, 9, "bold"),
                 fg=CYAN, bg=PANEL).pack(side="left")
        self.cmd_var = tk.StringVar()
        cmd_entry = tk.Entry(cmd_row, textvariable=self.cmd_var,
                             font=(MONO, 9), bg=BG, fg=WHITE,
                             insertbackground=CYAN, relief="flat",
                             highlightthickness=1, highlightcolor=CYAN,
                             highlightbackground=BORDER)
        cmd_entry.pack(side="left", fill="x", expand=True, padx=(6, 4))
        cmd_entry.bind("<Return>", self._on_cmd_enter)
        self._icon_btn(cmd_row, "SEND", self._on_cmd_enter).pack(side="left")

    # ═══════════════════════ HELPERS UI ═════════════════════════
    def _panel(self, parent, title=""):
        outer = tk.Frame(parent, bg=BORDER, bd=0)
        outer.pack(fill="x")  # caller overrides pack options
        inner = tk.Frame(outer, bg=PANEL, bd=0)
        inner.pack(fill="both", padx=1, pady=1)
        if title:
            tk.Label(inner, text=title, font=(MONO, 8, "bold"),
                     fg=CYAN, bg=PANEL, anchor="w",
                     padx=8, pady=3).pack(fill="x")
            tk.Frame(inner, bg=BORDER, height=1).pack(fill="x")
        return inner

    def _action_btn(self, parent, text, cmd, color=CYAN):
        btn = tk.Button(parent, text=text, font=(MONO, 9, "bold"),
                        bg=PANEL2, fg=color, relief="flat", bd=0,
                        activebackground=color, activeforeground=BG,
                        pady=5, command=cmd,
                        highlightthickness=1,
                        highlightcolor=color,
                        highlightbackground=BORDER)
        btn.bind("<Enter>", lambda e: btn.configure(bg=lerp_color(PANEL2, color, 0.15)))
        btn.bind("<Leave>", lambda e: btn.configure(bg=PANEL2))
        return btn

    def _icon_btn(self, parent, text, cmd):
        return tk.Button(parent, text=text, font=(MONO, 8),
                         bg=PANEL2, fg=TXT, relief="flat", bd=0,
                         activebackground=BORDER_LIT, padx=6,
                         command=cmd)

    def _log(self, msg, tag="data"):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{ts}] {msg}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line, tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ═══════════════════════ SERIAL ══════════════════════════════
    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb["values"] = ports
        if ports: self.port_cb.current(0)

    def _toggle_connect(self):
        if self.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self.port_var.get()
        if not port:
            self._log("No port selected.", "err")
            return
        try:
            baud = int(self.baud_var.get())
        except ValueError:
            baud = 115200
        try:
            self.ser = serial.Serial(port, baud, timeout=0.1)
            time.sleep(2)
            self.connected = True
            self.btn_connect.configure(text="■  DISCONNECT", fg=RED)
            self.led_conn.set(True)
            self.lbl_conn_status.configure(text="ONLINE", fg=GREEN)
            self._log(f"Connected to {port} @ {baud} baud", "ok")
            self._start_reader()

            # Aplicar parámetros CLI si existen
            a = self.args
            if getattr(a, "kp", None) and getattr(a, "kd", None):
                self.after(800, lambda: self._send(f"PID:{a.kp},{a.kd}"))
            if getattr(a, "speed", None):
                self.after(1000, lambda: self._send(f"SPEED:{a.speed}"))
            if getattr(a, "interval", None):
                self.after(1200, lambda: self._send(f"INTERVAL:{a.interval}"))
            if getattr(a, "autostart", False):
                self.after(1500, lambda: self._send("START"))

        except serial.SerialException as e:
            self._log(f"Connection failed: {e}", "err")

    def _disconnect(self):
        self._stop_event.set()
        if self._reader_th:
            self._reader_th.join(timeout=2)
        if self.ser and self.ser.is_open:
            self._send("STOP")
            time.sleep(0.1)
            self.ser.close()
        self.connected = False
        self.running   = False
        self.btn_connect.configure(text="▶  CONNECT", fg=GREEN)
        self.led_conn.set(False)
        self.led_run.set(False)
        self.lbl_conn_status.configure(text="OFFLINE", fg=RED)
        self.lbl_run_status.configure(text="IDLE", fg=TXT_DIM)
        self._log("Disconnected.", "warn")

    def _send(self, cmd: str):
        if not self.connected or not self.ser:
            self._log("Not connected.", "err")
            return
        try:
            self.ser.write((cmd + "\n").encode())
        except serial.SerialException as e:
            self._log(f"Send error: {e}", "err")
            self.connected = False

    # ═══════════════════════ READER THREAD ═══════════════════════
    def _start_reader(self):
        self._stop_event.clear()
        self._cmd_buf = ""
        self._reader_th = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_th.start()

    def _read_loop(self):
        """Hilo secundario: solo lee bytes y pone strings en la queue."""
        buf = ""
        while not self._stop_event.is_set():
            try:
                if self.ser and self.ser.in_waiting:
                    chunk = self.ser.read(self.ser.in_waiting).decode("utf-8", errors="replace")
                    buf += chunk
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip()
                        if line:
                            self._msg_queue.put(line)
                else:
                    time.sleep(0.005)
            except (serial.SerialException, OSError):
                self._msg_queue.put("__SERIAL_LOST__")
                self.connected = False
                break

    def _poll_queue(self):
        """Hilo principal: drena la queue y procesa mensajes cada 40 ms."""
        try:
            while True:
                raw = self._msg_queue.get_nowait()
                if raw == "__SERIAL_LOST__":
                    self._log("Serial connection lost.", "err")
                else:
                    self._handle_message(raw)
        except queue.Empty:
            pass
        self.after(40, self._poll_queue)

    def _handle_message(self, raw: str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._log(raw, "dim")
            return

        if data.get("telem"):
            self._update_telem(data)
            return

        if data.get("params"):
            self.kp        = data.get("kp", self.kp)
            self.kd        = data.get("kd", self.kd)
            self.max_speed = data.get("max_speed", self.max_speed)
            self.interval_ms = data.get("interval_ms", self.interval_ms)
            self.kp_var.set(self.kp)
            self.kd_var.set(self.kd)
            self.speed_var.set(self.max_speed)
            self.interval_var.set(self.interval_ms)
            self._log(f"Params sync: kp={self.kp} kd={self.kd} spd={self.max_speed} iv={self.interval_ms}ms", "info")
            return

        status = data.get("status", "")
        msg    = data.get("msg", "")
        if status == "READY":
            self._log(f"Robot READY. {msg}", "ok")
        elif status == "RUNNING":
            self.running = True
            self.led_run.set(True)
            self.lbl_run_status.configure(text="RUNNING", fg=GREEN)
            self._log("▶ Robot STARTED", "ok")
        elif status == "STOPPED":
            self.running = False
            self.led_run.set(False)
            self.lbl_run_status.configure(text="STOPPED", fg=RED)
            self._log("■ Robot STOPPED", "warn")
        elif status == "CALIBRATING":
            self._log("⟳ Calibrating sensors…", "info")
        elif status == "CALIBRATION_DONE":
            self._log("✔ Calibration done", "ok")
        elif status == "PID_OK":
            self._log(f"PID updated  kp={data.get('kp')}  kd={data.get('kd')}", "ok")
        elif status == "SPEED_OK":
            self._log(f"Speed set → {data.get('max_speed')}", "ok")
        elif status == "INTERVAL_OK":
            self._log(f"Telem interval → {data.get('interval_ms')} ms", "ok")
        elif status == "ERROR":
            self._log(f"Robot error: {msg}", "err")
        else:
            self._log(str(data), "dim")

    def _update_telem(self, d: dict):
        self.telem_count += 1
        self.last_telem = d

        pos  = d.get("pos", 2500)
        err_ = d.get("err", 0)
        m1   = d.get("m1", 0)
        m2   = d.get("m2", 0)
        run  = bool(d.get("run", 0))

        # Estado corriendo
        if run != self.running:
            self.running = run
            self.led_run.set(run)
            self.lbl_run_status.configure(
                text="RUNNING" if run else "STOPPED",
                fg=GREEN if run else RED)

        # Gauges
        self.gauge_m1.set(m1)
        self.gauge_m2.set(m2)

        # Posición de línea
        self.line_canvas.set(pos)

        # Números grandes
        color = GREEN if abs(err_) < 300 else (YELLOW if abs(err_) < 800 else RED)
        self.lbl_error_big.configure(text=f"{err_:+05d}", fg=color)
        self.lbl_pos_big.configure(text=str(pos))

        # Sparklines
        self.spark_error.push(err_)
        self.spark_m1.push(m1)
        self.spark_m2.push(m2)

        # Contador paquetes
        self.lbl_pkt.configure(text=f"PKT: {self.telem_count}")

    # ═══════════════════════ COMANDOS ════════════════════════════
    def _cmd_start(self):
        self._send("START")
        self._log("→ START sent", "info")

    def _cmd_stop(self):
        self._send("STOP")
        self._log("→ STOP sent", "info")

    def _apply_pid(self):
        kp = round(float(self.kp_var.get()), 4)
        kd = round(float(self.kd_var.get()), 4)
        self._send(f"PID:{kp},{kd}")
        self._log(f"→ PID:{kp},{kd} sent", "info")

    def _apply_speed(self):
        spd = int(self.speed_var.get())
        self._send(f"SPEED:{spd}")
        self._log(f"→ SPEED:{spd} sent", "info")

    def _apply_interval(self):
        iv = int(self.interval_var.get())
        self._send(f"INTERVAL:{iv}")
        self._log(f"→ INTERVAL:{iv} sent", "info")

    def _on_cmd_enter(self, event=None):
        cmd = self.cmd_var.get().strip()
        if cmd:
            self._send(cmd)
            self._log(f"→ {cmd}", "info")
            self.cmd_var.set("")

    # ═══════════════════════ BLINK LOOP ══════════════════════════
    def _start_blink_loop(self):
        self._blink()

    def _blink(self):
        self._blink_state = not self._blink_state
        # Pulsar LED de run si está corriendo
        if self.running and self.connected:
            self.led_run.set(self._blink_state)
        self.after(500, self._blink)

    # ═══════════════════════ CIERRE ══════════════════════════════
    def on_close(self):
        self._disconnect()
        self.destroy()


# ═══════════════════════════ ESTILOS TTK ═══════════════════════════
def apply_ttk_styles():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("TCombobox",
                    fieldbackground=PANEL2, background=PANEL2,
                    foreground=TXT, selectbackground=BORDER_LIT,
                    bordercolor=BORDER, arrowcolor=CYAN,
                    insertcolor=CYAN)
    style.map("TCombobox",
              fieldbackground=[("readonly", PANEL2)],
              selectbackground=[("readonly", BORDER_LIT)])
    style.configure("Vertical.TScrollbar",
                    background=PANEL2, troughcolor=BG,
                    bordercolor=BORDER, arrowcolor=TXT_DIM,
                    relief="flat")


# ═══════════════════════════════ MAIN ══════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Zumo Mission Control GUI")
    parser.add_argument("--port",      "-p", default=None)
    parser.add_argument("--baud",      "-b", type=int, default=115200)
    parser.add_argument("--kp",               type=float, default=None)
    parser.add_argument("--kd",               type=float, default=None)
    parser.add_argument("--speed",     "-s", type=int,   default=None)
    parser.add_argument("--interval",  "-i", type=int,   default=None)
    parser.add_argument("--autostart", "-a", action="store_true")
    args = parser.parse_args()

    app = ZumoGUI(args)
    apply_ttk_styles()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()