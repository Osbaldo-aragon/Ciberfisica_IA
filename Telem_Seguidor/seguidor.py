#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║         ZUMO LINE FOLLOWER — Terminal Controller                 ║
║         Pololu Zumo Robot · Serial @ 115200                      ║
╚══════════════════════════════════════════════════════════════════╝

Uso:
    python zumo_terminal.py                      # menú interactivo de puertos
    python zumo_terminal.py --port COM3          # puerto directo
    python zumo_terminal.py --port /dev/ttyACM0 --baud 115200
    python zumo_terminal.py --port COM4 --kp 0.3 --kd 8 --speed 350 --interval 200

Requiere:  pip install pyserial
"""

import argparse
import json
import sys
import threading
import time
from collections import deque
from datetime import datetime

import serial
import serial.tools.list_ports

# ─────────────────────────── ANSI ──────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
BLUE   = "\033[94m"
MAGENTA= "\033[95m"

def clr(text, *codes): return "".join(codes) + str(text) + RESET
def ok (msg): print(clr(f"  ✔  {msg}", GREEN))
def err(msg): print(clr(f"  ✖  {msg}", RED, BOLD))
def inf(msg): print(clr(f"  ●  {msg}", CYAN))
def warn(msg): print(clr(f"  ▲  {msg}", YELLOW))
def hdr(msg): print(clr(f"\n{'─'*60}\n  {msg}\n{'─'*60}", CYAN, BOLD))

# ─────────────────────── Barra visual ──────────────────────────────
def bar(value, max_val, width=20, fill="█", empty="░"):
    filled = int(width * max(0, min(value, max_val)) / max(max_val, 1))
    ratio  = value / max(max_val, 1)
    color  = GREEN if ratio < 0.5 else (YELLOW if ratio < 0.8 else RED)
    return clr(fill * filled, color) + clr(empty * (width - filled), DIM)

def signed_bar(error, max_err=2500, width=21):
    """Barra centrada para mostrar el error de posición."""
    mid = width // 2
    norm = max(-1.0, min(1.0, error / max_err))
    pos  = int(norm * mid)
    buf  = [clr("░", DIM)] * width
    buf[mid] = clr("|", DIM)
    if pos != 0:
        start, end = (mid + pos, mid) if pos > 0 else (mid, mid + pos)
        color = RED if pos > 0 else BLUE
        for i in range(min(start, end), max(start, end) + 1):
            buf[i] = clr("█", color)
    return "".join(buf)

# ═══════════════════════════════════════════════════════════════════
class ZumoController:

    HELP = """
╔════════════════════════════════════════════════════╗
║  COMANDOS DISPONIBLES                              ║

╠════════════════════════════════════════════════════╣
║  start                → Iniciar seguimiento        ║
║  stop                 → Detener robot              ║
║  pid <kp> <kd>        → Ajustar PID               ║
║                         ej: pid 0.3 8.0           ║
║  speed <0-400>        → Velocidad máxima          ║
║                         ej: speed 300             ║
║  interval <ms>        → Telemetría cada N ms      ║
║                         ej: interval 50           ║
║  params               → Mostrar parámetros        ║
║  status               → Estado actual del robot   ║
║  log [n]              → Últimas N lecturas (def 10)║
║  clear                → Limpiar pantalla           ║
║  help                 → Esta ayuda                 ║
║  quit / exit / q      → Salir                     ║
╚════════════════════════════════════════════════════╝
"""

    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self.ser: serial.Serial | None = None
        self.running_robot = False
        self.connected = False

        # Parámetros actuales (sincronizados con el robot)
        self.kp        = 0.25
        self.kd        = 6.0
        self.max_speed = 400
        self.interval  = 100

        # Telemetría
        self.telem_log: deque = deque(maxlen=500)
        self.last_telem: dict = {}
        self.telem_count = 0

        self._reader_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ── Conexión ────────────────────────────────────────────────
    def connect(self) -> bool:
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            time.sleep(2)   # esperar reset del Arduino
            self.connected = True
            ok(f"Conectado a {self.port} @ {self.baud} baud")
            self._start_reader()
            return True
        except serial.SerialException as e:
            err(f"No se pudo conectar: {e}")
            return False

    def disconnect(self):
        self._stop_event.set()
        if self._reader_thread:
            self._reader_thread.join(timeout=2)
        if self.ser and self.ser.is_open:
            self.send_raw("STOP")
            self.ser.close()
        self.connected = False
        inf("Desconectado.")

    # ── Lector en hilo ──────────────────────────────────────────
    def _start_reader(self):
        self._stop_event.clear()
        self._reader_thread = threading.Thread(
            target=self._read_loop, daemon=True)
        self._reader_thread.start()

    def _read_loop(self):
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
                            self._handle_message(line)
                else:
                    time.sleep(0.005)
            except (serial.SerialException, OSError):
                self.connected = False
                err("Conexión serial perdida.")
                break

    def _handle_message(self, raw: str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Mensaje no-JSON: mostrar directamente
            print(f"\n  {clr('▶', DIM)} {raw}")
            return

        # Telemetría
        if data.get("telem"):
            self.last_telem = data
            self.telem_count += 1
            self.telem_log.append({**data, "_ts": datetime.now()})
            self.running_robot = bool(data.get("run", 0))
            # Sincronizar parámetros
            self.kp        = data.get("kp", self.kp)
            self.kd        = data.get("kd", self.kd)
            self.max_speed = data.get("spd", self.max_speed)
            self._print_telem(data)
            return

        # Parámetros
        if data.get("params"):
            self.kp        = data.get("kp", self.kp)
            self.kd        = data.get("kd", self.kd)
            self.max_speed = data.get("max_speed", self.max_speed)
            self.interval  = data.get("interval_ms", self.interval)
            self._print_params()
            return

        # Mensajes de estado
        status = data.get("status", "")
        msg    = data.get("msg", "")
        if status == "READY":
            ok(f"Robot listo. {msg}")
        elif status == "RUNNING":
            ok("▶  Robot INICIADO")
            self.running_robot = True
        elif status == "STOPPED":
            warn("■  Robot DETENIDO")
            self.running_robot = False
        elif status == "CALIBRATING":
            inf("⟳  Calibrando sensores…")
        elif status == "CALIBRATION_DONE":
            ok("Calibración completada")
        elif status == "PID_OK":
            ok(f"PID actualizado  kp={data.get('kp','')}  kd={data.get('kd','')}")
            self.kp = data.get("kp", self.kp)
            self.kd = data.get("kd", self.kd)
        elif status == "SPEED_OK":
            ok(f"Velocidad máxima → {data.get('max_speed','')}")
            self.max_speed = data.get("max_speed", self.max_speed)
        elif status == "INTERVAL_OK":
            ok(f"Intervalo telemetría → {data.get('interval_ms','')} ms")
            self.interval = data.get("interval_ms", self.interval)
        elif status == "ERROR":
            err(f"Error del robot: {msg}")
        elif status == "UNKNOWN":
            warn(f"Comando desconocido por el robot: {data.get('cmd','')}")
        else:
            print(f"  {clr('↳', DIM)} {data}")

    def _print_telem(self, d: dict):
        pos  = d.get("pos", 0)
        err_ = d.get("err", 0)
        m1   = d.get("m1", 0)
        m2   = d.get("m2", 0)
        spd  = d.get("spd", self.max_speed)
        t    = d.get("t", 0)
        run  = d.get("run", 0)

        state = clr("▶ RUN", GREEN, BOLD) if run else clr("■ STOP", RED)

        print(
            f"\r  {clr(f't={t:>7}ms', DIM)}  {state}"
            f"  pos={clr(f'{pos:>4}', CYAN)}  err={clr(f'{err_:>+5}', YELLOW)}"
            f"  {signed_bar(err_)}"
            f"  M1={bar(m1, spd, 8)} {m1:>3}"
            f"  M2={bar(m2, spd, 8)} {m2:>3}"
            f"  #{self.telem_count}",
            end="", flush=True
        )

    def _print_params(self):
        hdr("Parámetros actuales")
        print(f"    KP           = {clr(self.kp, CYAN, BOLD)}")
        print(f"    KD           = {clr(self.kd, CYAN, BOLD)}")
        print(f"    MAX_SPEED    = {clr(self.max_speed, YELLOW, BOLD)}  (0–400)")
        print(f"    INTERVAL     = {clr(self.interval, YELLOW, BOLD)} ms")
        print(f"    Estado       = {clr('RUNNING', GREEN, BOLD) if self.running_robot else clr('STOPPED', RED)}")

    # ── Enviar ──────────────────────────────────────────────────
    def send_raw(self, cmd: str):
        if not self.connected or not self.ser:
            err("No hay conexión serial.")
            return False
        try:
            self.ser.write((cmd + "\n").encode())
            return True
        except serial.SerialException as e:
            err(f"Error al enviar: {e}")
            self.connected = False
            return False

    # ── Comandos de alto nivel ──────────────────────────────────
    def cmd_start(self):
        if self.send_raw("START"):
            inf("Enviando START…")

    def cmd_stop(self):
        if self.send_raw("STOP"):
            inf("Enviando STOP…")

    def cmd_pid(self, kp: float, kd: float):
        if self.send_raw(f"PID:{kp},{kd}"):
            inf(f"Enviando PID:{kp},{kd}")

    def cmd_speed(self, speed: int):
        if self.send_raw(f"SPEED:{speed}"):
            inf(f"Enviando SPEED:{speed}")

    def cmd_interval(self, ms: int):
        if self.send_raw(f"INTERVAL:{ms}"):
            inf(f"Enviando INTERVAL:{ms}")

    def cmd_params(self):
        self.send_raw("PARAMS")

    def cmd_log(self, n: int = 10):
        entries = list(self.telem_log)[-n:]
        if not entries:
            warn("Sin datos de telemetría aún.")
            return
        hdr(f"Últimas {len(entries)} lecturas de telemetría")
        print(f"  {'#':<5} {'Tiempo':>8}  {'Pos':>5}  {'Error':>6}  {'M1':>4}  {'M2':>4}  {'Estado'}")
        print(f"  {'─'*5} {'─'*8}  {'─'*5}  {'─'*6}  {'─'*4}  {'─'*4}  {'─'*7}")
        for i, d in enumerate(entries, 1):
            ts   = d.get("_ts", datetime.now()).strftime("%H:%M:%S")
            pos  = d.get("pos", 0)
            e_   = d.get("err", 0)
            m1   = d.get("m1", 0)
            m2   = d.get("m2", 0)
            run  = d.get("run", 0)
            state= clr("RUN", GREEN) if run else clr("STOP", RED)
            print(f"  {i:<5} {ts:>8}  {pos:>5}  {e_:>+6}  {m1:>4}  {m2:>4}  {state}")

    def cmd_status(self):
        hdr("Estado del controlador")
        connected_txt = clr("CONECTADO", GREEN, BOLD) if self.connected else clr("DESCONECTADO", RED, BOLD)
        robot_txt     = clr("RUNNING", GREEN, BOLD) if self.running_robot else clr("STOPPED", RED)
        print(f"    Puerto          : {clr(self.port, CYAN)}")
        print(f"    Baud rate       : {clr(self.baud, CYAN)}")
        print(f"    Conexión        : {connected_txt}")
        print(f"    Robot           : {robot_txt}")
        print(f"    KP / KD         : {clr(self.kp, YELLOW)} / {clr(self.kd, YELLOW)}")
        print(f"    MAX_SPEED       : {clr(self.max_speed, YELLOW)}")
        print(f"    Intervalo telem : {clr(self.interval, YELLOW)} ms")
        print(f"    Paquetes recib. : {clr(self.telem_count, CYAN)}")
        if self.last_telem:
            d = self.last_telem
            print(f"    Última posición : {clr(d.get('pos','-'), CYAN)}")
            print(f"    Último error    : {clr(d.get('err','-'), CYAN)}")

    # ── Loop interactivo ────────────────────────────────────────
    def interactive_loop(self):
        print(self.HELP)
        inf("Escribe un comando (help para ayuda):")
        print()

        while True:
            try:
                prompt = (
                    f"\n  {clr('[', DIM)}"
                    f"{clr('RUN', GREEN, BOLD) if self.running_robot else clr('STOP', RED)}"
                    f"{clr(']', DIM)} "
                    f"{clr('zumo', CYAN, BOLD)} {clr('▶', DIM)} "
                )
                raw = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                warn("Saliendo…")
                self.disconnect()
                sys.exit(0)

            if not raw:
                continue

            parts = raw.split()
            cmd   = parts[0].lower()

            # ─── Dispatcher ────────────────────────────────────
            if cmd in ("quit", "exit", "q"):
                warn("Cerrando conexión…")
                self.disconnect()
                sys.exit(0)

            elif cmd == "help":
                print(self.HELP)

            elif cmd == "clear":
                print("\033[2J\033[H", end="")

            elif cmd == "start":
                self.cmd_start()

            elif cmd == "stop":
                self.cmd_stop()

            elif cmd == "pid":
                if len(parts) < 3:
                    err("Uso: pid <kp> <kd>     ej: pid 0.3 8.0")
                else:
                    try:
                        kp = float(parts[1])
                        kd = float(parts[2])
                        if not (0 <= kp <= 10 and 0 <= kd <= 100):
                            warn("Valores fuera de rango recomendado (kp: 0-10, kd: 0-100)")
                        self.cmd_pid(kp, kd)
                    except ValueError:
                        err("kp y kd deben ser números. ej: pid 0.25 6.0")

            elif cmd == "speed":
                if len(parts) < 2:
                    err("Uso: speed <0-400>     ej: speed 300")
                else:
                    try:
                        spd = int(parts[1])
                        if not (0 <= spd <= 400):
                            err("Velocidad debe ser 0-400")
                        else:
                            self.cmd_speed(spd)
                    except ValueError:
                        err("La velocidad debe ser un entero. ej: speed 300")

            elif cmd == "interval":
                if len(parts) < 2:
                    err("Uso: interval <ms>     ej: interval 100")
                else:
                    try:
                        ms = int(parts[1])
                        if not (10 <= ms <= 10000):
                            err("Intervalo debe ser 10-10000 ms")
                        else:
                            self.cmd_interval(ms)
                    except ValueError:
                        err("El intervalo debe ser un entero en ms. ej: interval 50")

            elif cmd == "params":
                self.cmd_params()

            elif cmd == "status":
                self.cmd_status()

            elif cmd == "log":
                n = 10
                if len(parts) > 1:
                    try: n = int(parts[1])
                    except ValueError: pass
                self.cmd_log(n)

            else:
                warn(f"Comando desconocido: '{cmd}'.  Escribe 'help' para ver los comandos.")


# ═══════════════════════════════════════════════════════════════════
def list_ports():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        err("No se encontraron puertos seriales.")
        return None
    hdr("Puertos seriales disponibles")
    for i, p in enumerate(ports):
        print(f"    [{clr(i, YELLOW, BOLD)}]  {clr(p.device, CYAN)}  —  {p.description}")
    print()
    while True:
        try:
            raw = input(f"  Selecciona número [{clr(0, YELLOW)}]: ").strip()
            if raw == "":
                return ports[0].device
            idx = int(raw)
            if 0 <= idx < len(ports):
                return ports[idx].device
            warn("Número fuera de rango.")
        except (ValueError, KeyboardInterrupt):
            return None


def print_banner():
    banner = f"""
{CYAN}{BOLD}
  ██████╗ ██╗   ██╗███╗   ███╗ ██████╗
  ╚════██╗██║   ██║████╗ ████║██╔═══██╗
   █████╔╝██║   ██║██╔████╔██║██║   ██║
  ██╔═══╝ ██║   ██║██║╚██╔╝██║██║   ██║
  ███████╗╚██████╔╝██║ ╚═╝ ██║╚██████╔╝
  ╚══════╝ ╚═════╝ ╚═╝     ╚═╝ ╚═════╝
{RESET}
  {DIM}Pololu Zumo Line Follower — Terminal Controller{RESET}
"""
    print(banner)


# ═══════════════════════════════════════════════════════════════════
def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="Control terminal para Zumo Line Follower",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--port",     "-p", default=None,
                        help="Puerto serial  (ej: COM3  /dev/ttyACM0)")
    parser.add_argument("--baud",     "-b", type=int, default=115200,
                        help="Baud rate (default: 115200)")
    parser.add_argument("--kp",             type=float, default=None,
                        help="Proporcional PID (default: 0.25)")
    parser.add_argument("--kd",             type=float, default=None,
                        help="Derivativo PID  (default: 6.0)")
    parser.add_argument("--speed",    "-s", type=int,   default=None,
                        help="Velocidad máxima 0-400 (default: 400)")
    parser.add_argument("--interval", "-i", type=int,   default=None,
                        help="Intervalo telemetría ms (default: 100)")
    parser.add_argument("--autostart","-a", action="store_true",
                        help="Enviar START automáticamente al conectar")
    args = parser.parse_args()

    # ── Seleccionar puerto ──────────────────────────────────────
    port = args.port
    if not port:
        port = list_ports()
        if not port:
            err("Sin puerto seleccionado. Saliendo.")
            sys.exit(1)

    # ── Conectar ────────────────────────────────────────────────
    ctrl = ZumoController(port, args.baud)
    if not ctrl.connect():
        sys.exit(1)

    time.sleep(0.5)  # esperar mensajes de bienvenida del robot

    # ── Aplicar parámetros de línea de comandos ─────────────────
    if args.kp is not None and args.kd is not None:
        inf(f"Aplicando PID desde CLI: kp={args.kp} kd={args.kd}")
        ctrl.cmd_pid(args.kp, args.kd)
        time.sleep(0.2)

    if args.speed is not None:
        inf(f"Aplicando velocidad desde CLI: {args.speed}")
        ctrl.cmd_speed(args.speed)
        time.sleep(0.2)

    if args.interval is not None:
        inf(f"Aplicando intervalo desde CLI: {args.interval} ms")
        ctrl.cmd_interval(args.interval)
        time.sleep(0.2)

    if args.autostart:
        inf("--autostart activado, enviando START…")
        ctrl.cmd_start()
        time.sleep(0.2)

    # ── Loop principal ──────────────────────────────────────────
    ctrl.interactive_loop()


if __name__ == "__main__":
    main()