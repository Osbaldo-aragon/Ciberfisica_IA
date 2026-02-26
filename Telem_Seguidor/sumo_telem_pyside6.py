#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║       ZUMO LINE FOLLOWER — Telemetría en Tiempo Real            ║
║       PySide6 · pyqtgraph · QSerialPort                         ║
╚══════════════════════════════════════════════════════════════════╝

Instalación:
    pip install PySide6 pyqtgraph pyserial

Uso:
    python zumo_telemetry.py
"""

import json
import sys
from collections import deque

import pyqtgraph as pg
from PySide6.QtCore import (Qt, QIODeviceBase, QTimer, Slot, Signal, QObject)
from PySide6.QtGui import QFont, QColor, QPalette, QIcon
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QComboBox, QSpinBox,
    QDoubleSpinBox, QGroupBox, QSplitter, QStatusBar,
    QFrame, QLCDNumber, QSlider, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QTextEdit,
    QMessageBox,
)

# ─────────────────────────── Colores / Tema oscuro ─────────────────
DARK_BG      = "#0d0f14"
PANEL_BG     = "#13161e"
CARD_BG      = "#1a1e2a"
BORDER       = "#2a2f3e"
ACCENT_CYAN  = "#00e5ff"
ACCENT_GREEN = "#00e676"
ACCENT_AMBER = "#ffb300"
ACCENT_RED   = "#ff1744"
ACCENT_BLUE  = "#448aff"
TEXT_PRI     = "#e8eaf6"
TEXT_SEC     = "#7986cb"
TEXT_DIM     = "#3d4263"

PLOT_LINE    = "x"          # número máximo de puntos en la gráfica
MAX_POINTS   = 500

pg.setConfigOptions(antialias=True, background=DARK_BG, foreground=TEXT_PRI)


# ══════════════════════════════════════════════════════════════════
#  Estilos QSS
# ══════════════════════════════════════════════════════════════════
QSS = f"""
QMainWindow, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT_PRI};
    font-family: "Segoe UI", "Inter", "Roboto", sans-serif;
    font-size: 12px;
}}
QGroupBox {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding: 8px 6px 6px 6px;
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_SEC};
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}
QPushButton {{
    background-color: {CARD_BG};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: #222840;
    border-color: {ACCENT_CYAN};
    color: {ACCENT_CYAN};
}}
QPushButton:pressed {{
    background-color: #111520;
}}
QPushButton#btn_start {{
    background-color: #003320;
    border-color: {ACCENT_GREEN};
    color: {ACCENT_GREEN};
}}
QPushButton#btn_start:hover {{
    background-color: #005030;
}}
QPushButton#btn_stop {{
    background-color: #320010;
    border-color: {ACCENT_RED};
    color: {ACCENT_RED};
}}
QPushButton#btn_stop:hover {{
    background-color: #500020;
}}
QPushButton#btn_connect {{
    background-color: #00203a;
    border-color: {ACCENT_CYAN};
    color: {ACCENT_CYAN};
}}
QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {CARD_BG};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 4px 8px;
    selection-background-color: {ACCENT_CYAN};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {PANEL_BG};
    color: {TEXT_PRI};
    selection-background-color: #1e2540;
    border: 1px solid {BORDER};
}}
QScrollBar:vertical {{
    background: {PANEL_BG};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 20px;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {CARD_BG};
    border-radius: 0 8px 8px 8px;
}}
QTabBar::tab {{
    background: {PANEL_BG};
    color: {TEXT_SEC};
    border: 1px solid {BORDER};
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 6px 16px;
    margin-right: 2px;
    font-size: 11px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background: {CARD_BG};
    color: {ACCENT_CYAN};
    border-color: {ACCENT_CYAN};
}}
QTableWidget {{
    background-color: {CARD_BG};
    gridline-color: {BORDER};
    border: none;
    border-radius: 6px;
    alternate-background-color: #161a26;
}}
QTableWidget::item {{
    padding: 4px 8px;
    color: {TEXT_PRI};
}}
QHeaderView::section {{
    background-color: {PANEL_BG};
    color: {TEXT_SEC};
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    padding: 5px 8px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QTextEdit {{
    background-color: {PANEL_BG};
    color: #8bc34a;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 11px;
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px;
}}
QStatusBar {{
    background-color: {PANEL_BG};
    color: {TEXT_SEC};
    border-top: 1px solid {BORDER};
    font-size: 11px;
    padding: 2px 8px;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT_CYAN};
    border: 2px solid {ACCENT_CYAN};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT_CYAN};
    border-radius: 2px;
}}
QLCDNumber {{
    background-color: {PANEL_BG};
    color: {ACCENT_CYAN};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
"""


# ══════════════════════════════════════════════════════════════════
#  Widget métrica individual
# ══════════════════════════════════════════════════════════════════
class MetricCard(QFrame):
    def __init__(self, label: str, unit: str = "", accent: str = ACCENT_CYAN, parent=None):
        super().__init__(parent)
        self.accent = accent
        self.setObjectName("MetricCard")
        self.setStyleSheet(f"""
            QFrame#MetricCard {{
                background: {CARD_BG};
                border: 1px solid {BORDER};
                border-left: 3px solid {accent};
                border-radius: 8px;
                padding: 4px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(2)

        self.lbl_title = QLabel(label.upper())
        self.lbl_title.setStyleSheet(f"color:{TEXT_SEC}; font-size:10px; font-weight:700; letter-spacing:1px;")

        self.lbl_value = QLabel("—")
        font = QFont()
        font.setPointSize(22)
        font.setBold(True)
        self.lbl_value.setFont(font)
        self.lbl_value.setStyleSheet(f"color:{accent};")
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setStyleSheet(f"color:{TEXT_DIM}; font-size:10px;")

        lay.addWidget(self.lbl_title)
        lay.addWidget(self.lbl_value)
        lay.addWidget(self.lbl_unit)

    def set_value(self, val, fmt="{}", color: str = None):
        try:
            self.lbl_value.setText(fmt.format(val))
        except Exception:
            self.lbl_value.setText(str(val))
        c = color or self.accent
        self.lbl_value.setStyleSheet(f"color:{c};")


# ══════════════════════════════════════════════════════════════════
#  Barra de error centrada (canvas pyqtgraph)
# ══════════════════════════════════════════════════════════════════
class ErrorBar(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setYRange(-1.2, 1.2)
        self.setXRange(-1, 1)
        self.hideAxis("bottom")
        self.hideAxis("left")
        self.getPlotItem().setContentsMargins(0, 0, 0, 0)
        self.setBackground(PANEL_BG)

        # línea central
        self.addItem(pg.InfiniteLine(pos=0, angle=90,
                                      pen=pg.mkPen(TEXT_DIM, width=1, style=Qt.DashLine)))
        # barra de error
        self._bar = pg.BarGraphItem(x=[0], height=[0.7], width=0, brush=ACCENT_AMBER)
        self.addItem(self._bar)

    def update_error(self, error: float, max_err: float = 2500):
        norm = max(-1.0, min(1.0, error / max(max_err, 1)))
        color = ACCENT_RED if norm > 0 else ACCENT_BLUE
        w = abs(norm)
        x0 = norm / 2  # center of bar
        self._bar.setOpts(x=[x0], height=[0.7], width=w,
                           brush=pg.mkBrush(color))


# ══════════════════════════════════════════════════════════════════
#  Ventana principal
# ══════════════════════════════════════════════════════════════════
class ZumoTelemetry(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zumo Line Follower — Telemetría en Tiempo Real")
        self.setMinimumSize(1200, 780)

        # Estado
        self._port = QSerialPort(self)
        self._connected = False
        self._running   = False
        self._telem_count = 0
        self._packet_buf  = ""

        # Buffers de datos
        self._t_buf   = deque(maxlen=MAX_POINTS)
        self._pos_buf = deque(maxlen=MAX_POINTS)
        self._err_buf = deque(maxlen=MAX_POINTS)
        self._m1_buf  = deque(maxlen=MAX_POINTS)
        self._m2_buf  = deque(maxlen=MAX_POINTS)

        # Parámetros
        self._kp = 0.25
        self._kd = 6.0
        self._max_speed = 400
        self._interval  = 100

        self._build_ui()
        self._apply_theme()
        self._refresh_ports()

        # Serial data-ready signal
        self._port.readyRead.connect(self._on_ready_read)

        # Timer para refrescar lista de puertos
        self._port_timer = QTimer(self)
        self._port_timer.timeout.connect(self._refresh_ports)
        self._port_timer.start(3000)

    # ──────────────────────────────────────────────────────────────
    #  UI BUILD
    # ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 8, 10, 6)
        root.setSpacing(8)

        # ── Barra superior ────────────────────────────────────────
        root.addWidget(self._build_topbar())

        # ── Splitter principal ────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {BORDER}; }}")

        # Panel izquierdo: métricas + control
        left = QWidget()
        left.setFixedWidth(280)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 4, 0)
        left_lay.setSpacing(8)
        left_lay.addWidget(self._build_metrics())
        left_lay.addWidget(self._build_control())
        left_lay.addWidget(self._build_pid_panel())
        left_lay.addStretch()

        # Panel derecho: gráficas + log
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(4, 0, 0, 0)
        right_lay.setSpacing(8)

        # Error bar
        gb_err = QGroupBox("Error de Posición")
        gb_err_lay = QVBoxLayout(gb_err)
        gb_err_lay.setContentsMargins(6, 14, 6, 6)
        self._error_bar = ErrorBar()
        gb_err_lay.addWidget(self._error_bar)

        # Tabs: Gráficas / Log / Tabla
        tabs = QTabWidget()
        tabs.addTab(self._build_plots_tab(), "📈  Gráficas")
        tabs.addTab(self._build_log_tab(),   "📋  Log Serie")
        tabs.addTab(self._build_table_tab(), "📊  Historial")

        right_lay.addWidget(gb_err)
        right_lay.addWidget(tabs, stretch=1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._lbl_status = QLabel("  ●  Desconectado")
        self._lbl_status.setStyleSheet(f"color:{ACCENT_RED};")
        self._lbl_pkts = QLabel("Paquetes: 0")
        self._lbl_pkts.setStyleSheet(f"color:{TEXT_SEC};")
        self.status.addPermanentWidget(self._lbl_status)
        self.status.addPermanentWidget(QLabel("  |  "))
        self.status.addPermanentWidget(self._lbl_pkts)

    # ── Top bar ─────────────────────────────────────────────────
    def _build_topbar(self):
        bar = QFrame()
        bar.setStyleSheet(f"background:{PANEL_BG}; border-radius:8px; padding:4px;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(10)

        # Logo / título
        title = QLabel("⚡ ZUMO TELEMETRY")
        title.setStyleSheet(f"color:{ACCENT_CYAN}; font-size:16px; font-weight:800; letter-spacing:2px;")
        lay.addWidget(title)
        lay.addStretch()

        # Puerto
        lay.addWidget(QLabel("Puerto:"))
        self.cmb_port = QComboBox()
        self.cmb_port.setMinimumWidth(130)
        lay.addWidget(self.cmb_port)

        # Baud
        lay.addWidget(QLabel("Baud:"))
        self.cmb_baud = QComboBox()
        for b in ["9600", "19200", "38400", "57600", "115200", "230400"]:
            self.cmb_baud.addItem(b)
        self.cmb_baud.setCurrentText("115200")
        self.cmb_baud.setMinimumWidth(80)
        lay.addWidget(self.cmb_baud)

        # Botón refrescar puertos
        btn_refresh = QPushButton("⟳")
        btn_refresh.setFixedWidth(32)
        btn_refresh.setToolTip("Refrescar puertos")
        btn_refresh.clicked.connect(self._refresh_ports)
        lay.addWidget(btn_refresh)

        # Botón conectar/desconectar
        self.btn_connect = QPushButton("  Conectar  ")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.setFixedWidth(110)
        self.btn_connect.clicked.connect(self._toggle_connect)
        lay.addWidget(self.btn_connect)

        # Indicador LED
        self._led = QLabel("●")
        self._led.setStyleSheet(f"color:{ACCENT_RED}; font-size:20px;")
        lay.addWidget(self._led)

        return bar

    # ── Métricas ─────────────────────────────────────────────────
    def _build_metrics(self):
        gb = QGroupBox("Métricas en Tiempo Real")
        grid = QGridLayout(gb)
        grid.setSpacing(6)
        grid.setContentsMargins(6, 16, 6, 6)

        self.card_pos  = MetricCard("Posición", "", ACCENT_CYAN)
        self.card_err  = MetricCard("Error", "", ACCENT_AMBER)
        self.card_m1   = MetricCard("Motor 1", "PWM", ACCENT_GREEN)
        self.card_m2   = MetricCard("Motor 2", "PWM", ACCENT_BLUE)
        self.card_time = MetricCard("Tiempo", "ms", TEXT_SEC)

        grid.addWidget(self.card_pos,  0, 0)
        grid.addWidget(self.card_err,  0, 1)
        grid.addWidget(self.card_m1,   1, 0)
        grid.addWidget(self.card_m2,   1, 1)
        grid.addWidget(self.card_time, 2, 0, 1, 2)

        return gb

    # ── Control ───────────────────────────────────────────────────
    def _build_control(self):
        gb = QGroupBox("Control")
        lay = QHBoxLayout(gb)
        lay.setContentsMargins(8, 16, 8, 8)
        lay.setSpacing(8)

        self.btn_start = QPushButton("▶  START")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._send_start)

        self.btn_stop = QPushButton("■  STOP")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._send_stop)

        lay.addWidget(self.btn_start, stretch=1)
        lay.addWidget(self.btn_stop,  stretch=1)
        return gb

    # ── Panel PID + Speed + Interval ────────────────────────────
    def _build_pid_panel(self):
        gb = QGroupBox("Parámetros PID")
        lay = QVBoxLayout(gb)
        lay.setContentsMargins(8, 16, 8, 10)
        lay.setSpacing(10)

        # KP
        row_kp = QHBoxLayout()
        row_kp.addWidget(QLabel("Kp"))
        self.spin_kp = QDoubleSpinBox()
        self.spin_kp.setRange(0, 10)
        self.spin_kp.setSingleStep(0.05)
        self.spin_kp.setValue(0.25)
        self.spin_kp.setDecimals(3)
        row_kp.addWidget(self.spin_kp)
        lay.addLayout(row_kp)

        # KD
        row_kd = QHBoxLayout()
        row_kd.addWidget(QLabel("Kd"))
        self.spin_kd = QDoubleSpinBox()
        self.spin_kd.setRange(0, 100)
        self.spin_kd.setSingleStep(0.5)
        self.spin_kd.setValue(6.0)
        self.spin_kd.setDecimals(2)
        row_kd.addWidget(self.spin_kd)
        lay.addLayout(row_kd)

        btn_pid = QPushButton("Enviar PID")
        btn_pid.clicked.connect(self._send_pid)
        lay.addWidget(btn_pid)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{BORDER};")
        lay.addWidget(sep)

        # Speed
        row_spd = QHBoxLayout()
        row_spd.addWidget(QLabel("Speed"))
        self.spin_speed = QSpinBox()
        self.spin_speed.setRange(0, 400)
        self.spin_speed.setSingleStep(10)
        self.spin_speed.setValue(400)
        row_spd.addWidget(self.spin_speed)
        btn_spd = QPushButton("Set")
        btn_spd.setFixedWidth(40)
        btn_spd.clicked.connect(self._send_speed)
        row_spd.addWidget(btn_spd)
        lay.addLayout(row_spd)

        # Interval
        row_int = QHBoxLayout()
        row_int.addWidget(QLabel("Interval"))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(10, 10000)
        self.spin_interval.setSingleStep(10)
        self.spin_interval.setValue(100)
        self.spin_interval.setSuffix(" ms")
        row_int.addWidget(self.spin_interval)
        btn_int = QPushButton("Set")
        btn_int.setFixedWidth(40)
        btn_int.clicked.connect(self._send_interval)
        row_int.addWidget(btn_int)
        lay.addLayout(row_int)

        return gb

    # ── Tab Gráficas ─────────────────────────────────────────────
    def _build_plots_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        pen_pos  = pg.mkPen(ACCENT_CYAN,  width=2)
        pen_err  = pg.mkPen(ACCENT_AMBER, width=2)
        pen_m1   = pg.mkPen(ACCENT_GREEN, width=1.5)
        pen_m2   = pg.mkPen(ACCENT_BLUE,  width=1.5)

        def make_plot(title, ylabel, unit=""):
            pw = pg.PlotWidget(title=title)
            pw.setLabel("left", ylabel, units=unit)
            pw.setLabel("bottom", "Tiempo", units="ms")
            pw.showGrid(x=True, y=True, alpha=0.15)
            pw.getPlotItem().titleLabel.setAttr("color", TEXT_SEC)
            pw.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            return pw

        # Plot Posición
        self.plt_pos = make_plot("Posición del sensor", "Posición")
        self.crv_pos = self.plt_pos.plot(pen=pen_pos, name="Posición")
        self.plt_pos.addLegend()
        lay.addWidget(self.plt_pos)

        # Plot Error
        self.plt_err = make_plot("Error PD", "Error")
        self.crv_err = self.plt_err.plot(pen=pen_err, name="Error")
        # Relleno bajo cero
        self.plt_err.addLegend()
        lay.addWidget(self.plt_err)

        # Plot Motores
        self.plt_mot = make_plot("Velocidad Motores", "PWM")
        self.crv_m1  = self.plt_mot.plot(pen=pen_m1, name="Motor 1")
        self.crv_m2  = self.plt_mot.plot(pen=pen_m2, name="Motor 2")
        self.plt_mot.addLegend()
        lay.addWidget(self.plt_mot)

        return w

    # ── Tab Log ───────────────────────────────────────────────────
    def _build_log_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)

        row = QHBoxLayout()
        self.btn_clear_log = QPushButton("Limpiar")
        self.btn_clear_log.setFixedWidth(80)
        self.btn_pause_log = QPushButton("⏸ Pausar")
        self.btn_pause_log.setFixedWidth(90)
        self.btn_pause_log.setCheckable(True)
        self.chk_autoscroll = QPushButton("↓ Auto-scroll ON")
        self.chk_autoscroll.setCheckable(True)
        self.chk_autoscroll.setChecked(True)
        self.chk_autoscroll.setFixedWidth(130)
        row.addWidget(self.btn_clear_log)
        row.addWidget(self.btn_pause_log)
        row.addWidget(self.chk_autoscroll)
        row.addStretch()
        lay.addLayout(row)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        lay.addWidget(self.log_text)

        self.btn_clear_log.clicked.connect(self.log_text.clear)

        return w

    # ── Tab Historial ─────────────────────────────────────────────
    def _build_table_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)

        cols = ["#", "Tiempo (ms)", "Posición", "Error", "Motor 1", "Motor 2", "Estado"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        btn_clear_tbl = QPushButton("Limpiar tabla")
        btn_clear_tbl.setFixedWidth(120)
        btn_clear_tbl.clicked.connect(lambda: self.table.setRowCount(0))

        row = QHBoxLayout()
        row.addWidget(btn_clear_tbl)
        row.addStretch()
        lay.addLayout(row)
        lay.addWidget(self.table)

        return w

    def _apply_theme(self):
        self.setStyleSheet(QSS)

    # ──────────────────────────────────────────────────────────────
    #  Serial: conectar / desconectar
    # ──────────────────────────────────────────────────────────────
    @Slot()
    def _refresh_ports(self):
        current = self.cmb_port.currentText()
        self.cmb_port.clear()
        for info in QSerialPortInfo.availablePorts():
            self.cmb_port.addItem(info.portName())
        idx = self.cmb_port.findText(current)
        if idx >= 0:
            self.cmb_port.setCurrentIndex(idx)

    @Slot()
    def _toggle_connect(self):
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port_name = self.cmb_port.currentText()
        baud = int(self.cmb_baud.currentText())
        if not port_name:
            QMessageBox.warning(self, "Sin puerto", "Selecciona un puerto serial.")
            return

        self._port.setPortName(port_name)
        self._port.setBaudRate(baud)
        self._port.setDataBits(QSerialPort.DataBits.Data8)
        self._port.setParity(QSerialPort.Parity.NoParity)
        self._port.setStopBits(QSerialPort.StopBits.OneStop)
        self._port.setFlowControl(QSerialPort.FlowControl.NoFlowControl)

        if not self._port.open(QIODeviceBase.OpenModeFlag.ReadWrite):
            QMessageBox.critical(self, "Error", f"No se pudo abrir {port_name}:\n{self._port.errorString()}")
            return

        self._connected = True
        self._led.setStyleSheet(f"color:{ACCENT_GREEN}; font-size:20px;")
        self._lbl_status.setText(f"  ●  Conectado  —  {port_name} @ {baud}")
        self._lbl_status.setStyleSheet(f"color:{ACCENT_GREEN};")
        self.btn_connect.setText("  Desconectar  ")
        self.btn_connect.setStyleSheet(f"background:#200010; border-color:{ACCENT_RED}; color:{ACCENT_RED}; border-radius:6px; padding:6px 14px; font-weight:600;")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.cmb_port.setEnabled(False)
        self.cmb_baud.setEnabled(False)
        self._log(f"<span style='color:{ACCENT_GREEN}'>■ Conectado a {port_name} @ {baud} baud</span>")

    def _disconnect(self):
        if self._port.isOpen():
            self._port.write(b"STOP\n")
            self._port.close()
        self._connected = False
        self._running   = False
        self._led.setStyleSheet(f"color:{ACCENT_RED}; font-size:20px;")
        self._lbl_status.setText("  ●  Desconectado")
        self._lbl_status.setStyleSheet(f"color:{ACCENT_RED};")
        self.btn_connect.setText("  Conectar  ")
        self.btn_connect.setStyleSheet("")  # reset
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.cmb_port.setEnabled(True)
        self.cmb_baud.setEnabled(True)
        self._log(f"<span style='color:{ACCENT_RED}'>■ Desconectado</span>")

    # ──────────────────────────────────────────────────────────────
    #  Lectura serial
    # ──────────────────────────────────────────────────────────────
    @Slot()
    def _on_ready_read(self):
        raw = bytes(self._port.readAll()).decode("utf-8", errors="replace")
        self._packet_buf += raw
        while "\n" in self._packet_buf:
            line, self._packet_buf = self._packet_buf.split("\n", 1)
            line = line.strip()
            if line:
                self._handle_line(line)

    def _handle_line(self, line: str):
        if not self.btn_pause_log.isChecked():
            self._log(f"<span style='color:{TEXT_DIM}'>&gt;</span> {line}")

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return

        if data.get("telem"):
            self._process_telem(data)
            return

        if data.get("params"):
            self._sync_params(data)
            return

        status = data.get("status", "")
        msg    = data.get("msg", "")

        if status == "RUNNING":
            self._running = True
            self._log(f"<span style='color:{ACCENT_GREEN}'>▶ Robot INICIADO</span>")
        elif status == "STOPPED":
            self._running = False
            self._log(f"<span style='color:{ACCENT_AMBER}'>■ Robot DETENIDO</span>")
        elif status == "PID_OK":
            kp = data.get("kp", "")
            kd = data.get("kd", "")
            self._log(f"<span style='color:{ACCENT_CYAN}'>✔ PID actualizado  kp={kp}  kd={kd}</span>")
            self.spin_kp.setValue(float(kp) if kp != "" else self.spin_kp.value())
            self.spin_kd.setValue(float(kd) if kd != "" else self.spin_kd.value())
        elif status == "SPEED_OK":
            spd = data.get("max_speed", "")
            self._log(f"<span style='color:{ACCENT_CYAN}'>✔ Velocidad → {spd}</span>")
        elif status == "INTERVAL_OK":
            iv = data.get("interval_ms", "")
            self._log(f"<span style='color:{ACCENT_CYAN}'>✔ Intervalo → {iv} ms</span>")
        elif status == "ERROR":
            self._log(f"<span style='color:{ACCENT_RED}'>✖ Error: {msg}</span>")
        elif status == "READY":
            self._log(f"<span style='color:{ACCENT_GREEN}'>● Robot listo. {msg}</span>")
        elif status:
            self._log(f"<span style='color:{TEXT_SEC}'>[{status}] {msg}</span>")

    def _process_telem(self, d: dict):
        self._telem_count += 1
        t   = d.get("t", 0)
        pos = d.get("pos", 0)
        err = d.get("err", 0)
        m1  = d.get("m1", 0)
        m2  = d.get("m2", 0)
        spd = d.get("spd", self._max_speed)
        run = bool(d.get("run", 0))

        self._running = run

        # Buffers
        self._t_buf.append(t)
        self._pos_buf.append(pos)
        self._err_buf.append(err)
        self._m1_buf.append(m1)
        self._m2_buf.append(m2)

        t_list   = list(self._t_buf)
        pos_list = list(self._pos_buf)
        err_list = list(self._err_buf)
        m1_list  = list(self._m1_buf)
        m2_list  = list(self._m2_buf)

        # Actualizar curvas
        self.crv_pos.setData(t_list, pos_list)
        self.crv_err.setData(t_list, err_list)
        self.crv_m1.setData(t_list, m1_list)
        self.crv_m2.setData(t_list, m2_list)

        # Métricas
        self.card_pos.set_value(pos, "{:>5}")
        err_color = ACCENT_RED if err > 500 else (ACCENT_AMBER if err > 100 else ACCENT_GREEN)
        self.card_err.set_value(err, "{:>+5}", err_color)
        m1_color = ACCENT_GREEN if m1 < spd * 0.8 else ACCENT_AMBER
        m2_color = ACCENT_GREEN if m2 < spd * 0.8 else ACCENT_AMBER
        self.card_m1.set_value(m1, "{}", m1_color)
        self.card_m2.set_value(m2, "{}", m2_color)
        self.card_time.set_value(t, "{:,}")

        # Barra de error
        self._error_bar.update_error(err)

        # Contador
        self._lbl_pkts.setText(f"Paquetes: {self._telem_count}")

        # Status bar
        state_txt = f"RUN  kp={spd}" if run else "STOP"

        # Tabla historial (cada 5 paquetes para no saturar)
        if self._telem_count % 5 == 0:
            row = self.table.rowCount()
            self.table.insertRow(row)
            vals = [str(self._telem_count), str(t), str(pos),
                    f"{err:+}", str(m1), str(m2),
                    "RUN" if run else "STOP"]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 6:
                    item.setForeground(QColor(ACCENT_GREEN if run else ACCENT_RED))
                self.table.setItem(row, col, item)
            # Limitar a 200 filas
            if row > 200:
                self.table.removeRow(0)
            self.table.scrollToBottom()

    def _sync_params(self, d: dict):
        kp  = d.get("kp", self._kp)
        kd  = d.get("kd", self._kd)
        spd = d.get("max_speed", self._max_speed)
        iv  = d.get("interval_ms", self._interval)
        self._kp = kp;  self.spin_kp.setValue(kp)
        self._kd = kd;  self.spin_kd.setValue(kd)
        self._max_speed = spd; self.spin_speed.setValue(spd)
        self._interval  = iv;  self.spin_interval.setValue(iv)

    # ──────────────────────────────────────────────────────────────
    #  Enviar comandos
    # ──────────────────────────────────────────────────────────────
    def _send(self, cmd: str):
        if self._connected and self._port.isOpen():
            self._port.write((cmd + "\n").encode())
            self._log(f"<span style='color:{TEXT_DIM}'>◀ {cmd}</span>")
        else:
            self._log(f"<span style='color:{ACCENT_RED}'>✖ Sin conexión</span>")

    @Slot()
    def _send_start(self):
        self._send("START")

    @Slot()
    def _send_stop(self):
        self._send("STOP")

    @Slot()
    def _send_pid(self):
        kp = self.spin_kp.value()
        kd = self.spin_kd.value()
        self._send(f"PID:{kp},{kd}")

    @Slot()
    def _send_speed(self):
        self._send(f"SPEED:{self.spin_speed.value()}")

    @Slot()
    def _send_interval(self):
        self._send(f"INTERVAL:{self.spin_interval.value()}")

    # ──────────────────────────────────────────────────────────────
    #  Log helper
    # ──────────────────────────────────────────────────────────────
    def _log(self, html: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.append(
            f"<span style='color:{TEXT_DIM}'>[{ts}]</span> {html}"
        )
        if self.chk_autoscroll.isChecked():
            sb = self.log_text.verticalScrollBar()
            sb.setValue(sb.maximum())

    # ──────────────────────────────────────────────────────────────
    #  Cierre limpio
    # ──────────────────────────────────────────────────────────────
    def closeEvent(self, event):
        if self._connected:
            self._disconnect()
        event.accept()


# ══════════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Zumo Telemetry")

    # Paleta oscura base
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(DARK_BG))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRI))
    pal.setColor(QPalette.ColorRole.Base, QColor(CARD_BG))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(PANEL_BG))
    pal.setColor(QPalette.ColorRole.Text, QColor(TEXT_PRI))
    pal.setColor(QPalette.ColorRole.Button, QColor(CARD_BG))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT_PRI))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT_CYAN))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(DARK_BG))
    app.setPalette(pal)

    win = ZumoTelemetry()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()