//                                 Gabriel Carrizales García - - - - Bryam Muñiz Galvan - - - - Kevyn David Delgado Gomez
//                                                                    Futbol Sumo 2025
//                                                                ESP32 - TB6612FNG - 7.4v
//                VERSIÓN 2.4 - Sin Serial / Giros corregidos (según prueba real) / Anti-picos mejorado

#include "BluetoothSerial.h"
BluetoothSerial SerialBT;

// ===================== Pines TB6612FNG =====================
#define AIN1   14 // 14
#define AIN2   12 // 12
#define BIN1   18 //
#define BIN2   32 //
#define PWMA   25 
#define PWMB   13
#define STBY   27
#define LED_BT 33

// ===================== Configuración PWM =====================
#define PWM_FREQ 15000     // antes 20000, se baja un poco para probar estabilidad
#define PWM_RES  8         // rango 0..255
#define MAX_PWM  255       // límite para evitar picos fuertes (prueba 220-230)

// ===================== Variables globales =====================
int speedLevel  = MAX_PWM;
int currentPWMA = 0;
int currentPWMB = 0;
char currentDir = 'S';

// ===================== Anti-pico de corriente =====================
#define RAMP_STEP  4       // antes 8 (más suave)
#define RAMP_DELAY 8      // antes 10 (más suave)

// Delay corto al invertir sentido directo (F<->B, etc.)
#define DIR_CHANGE_BRAKE_MS 60

// ================================================================
void setup() {
  // Sin Serial.begin(); // no se usará monitor serial

  SerialBT.begin("01_LLANERO");

  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);
  pinMode(STBY, OUTPUT);
  pinMode(LED_BT, OUTPUT);

  ledcAttach(PWMA, PWM_FREQ, PWM_RES);
  ledcAttach(PWMB, PWM_FREQ, PWM_RES);

  digitalWrite(LED_BT, LOW);
  digitalWrite(STBY, HIGH);

  Stop();
}

// ================================================================
void loop() {
  if (SerialBT.available()) {
    char value = SerialBT.read();

    // Normaliza a mayúscula
    if (value >= 'a' && value <= 'z') value = value - 32;

    // ── Control de velocidad (0..9 = 0..90%, Q = 100% del MAX_PWM) ──────────
    if (value >= '0' && value <= '9') {
      int pct = (value - '0') * 10;
      speedLevel = map(pct, 0, 100, 0, MAX_PWM);
      applyCurrentDir();   // reaplica dirección actual con nueva velocidad
      return;
    }

    if (value == 'Q') {
      speedLevel = MAX_PWM;
      applyCurrentDir();
      return;
    }

    // ── Comandos de movimiento ────────────────────────────────────────────────
    switch (value) {
      case 'F': commandMove('F'); break;
      case 'B': commandMove('B'); break;
      case 'S': commandMove('S'); break;
      case 'L': commandMove('L'); break;
      case 'R': commandMove('R'); break;
      case 'G': commandMove('G'); break; // adelante-izquierda
      case 'I': commandMove('I'); break; // adelante-derecha
      case 'H': commandMove('H'); break; // atrás-izquierda
      case 'J': commandMove('J'); break; // atrás-derecha
      default: /* ignorar */ break;
    }
  }

  // LED encendido cuando hay cliente BT conectado
  digitalWrite(LED_BT, SerialBT.hasClient() ? HIGH : LOW);
}

// ================================================================
// Ejecuta movimiento con una pequeña protección al cambiar de sentido
void commandMove(char newDir) {
  // Si cambia entre avance y reversa (o diagonales de sentido opuesto), frena breve
  if (isOppositeSense(currentDir, newDir)) {
    Stop();
    delay(DIR_CHANGE_BRAKE_MS);
  }

  currentDir = newDir;
  applyCurrentDir();
}

// ================================================================
bool isForwardSense(char d) {
  return (d == 'F' || d == 'G' || d == 'I');
}

bool isBackwardSense(char d) {
  return (d == 'B' || d == 'H' || d == 'J');
}

bool isOppositeSense(char oldDir, char newDir) {
  if (oldDir == 'S' || newDir == 'S') return false;
  return (isForwardSense(oldDir) && isBackwardSense(newDir)) ||
         (isBackwardSense(oldDir) && isForwardSense(newDir));
}

// ================================================================
void applyCurrentDir() {
  switch (currentDir) {
    case 'F': Forward();      break;
    case 'B': Backward();     break;
    case 'L': Left();         break;
    case 'R': Right();        break;
    case 'G': ForwardLeft();  break;
    case 'I': ForwardRight(); break;
    case 'H': BackLeft();     break;
    case 'J': BackRight();    break;
    default:  Stop();         break;
  }
}

// ================================================================
// targetA = PWM motor A
// targetB = PWM motor B
//
// Direcciones asumidas por driver:
// A: HIGH/LOW = adelante, LOW/HIGH = atrás
// B: HIGH/LOW = adelante, LOW/HIGH = atrás
// ================================================================
void setMotors(int targetA, int targetB,
               bool ain1, bool ain2,
               bool bin1, bool bin2) {

  targetA = constrain(targetA, 0, MAX_PWM);
  targetB = constrain(targetB, 0, MAX_PWM);

  digitalWrite(AIN1, ain1);
  digitalWrite(AIN2, ain2);
  digitalWrite(BIN1, bin1);
  digitalWrite(BIN2, bin2);

  while (currentPWMA != targetA || currentPWMB != targetB) {
    if      (currentPWMA < targetA) currentPWMA = min(currentPWMA + RAMP_STEP, targetA);
    else if (currentPWMA > targetA) currentPWMA = max(currentPWMA - RAMP_STEP, targetA);

    if      (currentPWMB < targetB) currentPWMB = min(currentPWMB + RAMP_STEP, targetB);
    else if (currentPWMB > targetB) currentPWMB = max(currentPWMB - RAMP_STEP, targetB);

    ledcWrite(PWMA, currentPWMA);
    ledcWrite(PWMB, currentPWMB);
    delay(RAMP_DELAY);
  }
}

// ================================================================
// MOVIMIENTOS
// NOTA IMPORTANTE:
// Adelante y atrás están correctos en tu robot.
// Como reportaste giros invertidos, aquí se corrigen L/R y diagonales.
// ================================================================

void Forward() {
  // Ambos adelante
  setMotors(speedLevel, speedLevel, HIGH, LOW, HIGH, LOW);
}

void Backward() {
  // Ambos atrás
  setMotors(speedLevel, speedLevel, LOW, HIGH, LOW, HIGH);
}

void Stop() {
  currentPWMA = 0;
  currentPWMB = 0;

  ledcWrite(PWMA, 0);
  ledcWrite(PWMB, 0);

  digitalWrite(AIN1, LOW); digitalWrite(AIN2, LOW);
  digitalWrite(BIN1, LOW); digitalWrite(BIN2, LOW);
}

// ===================== GIROS CORREGIDOS (INVERTIDOS RESPECTO A LA VERSIÓN ANTERIOR) =====================

// Giro izquierda en sitio (corregido según tu prueba)
void Left() {
  int turn = (speedLevel * 85) / 100;   // reduce pico en giro
  // (ANTES estaba al revés para tu robot)
  setMotors(turn, turn, HIGH, LOW, LOW, HIGH);
}

// Giro derecha en sitio (corregido según tu prueba)
void Right() {
  int turn = (speedLevel * 85) / 100;
  // (ANTES estaba al revés para tu robot)
  setMotors(turn, turn, LOW, HIGH, HIGH, LOW);
}

// Curva adelante-izquierda (corregida para tu robot)
// Si antes giraba a la derecha con G, aquí se invierte la lógica de velocidades
void ForwardLeft() {
  int slow = speedLevel / 2;
  setMotors(slow, speedLevel, HIGH, LOW, HIGH, LOW);
}

// Curva adelante-derecha (corregida para tu robot)
void ForwardRight() {
  int slow = speedLevel / 2;
  setMotors(speedLevel, slow, HIGH, LOW, HIGH, LOW);
}

// Curva atrás-izquierda (corregida para tu robot)
void BackLeft() {
  int slow = speedLevel / 2;
  setMotors(slow,speedLevel, LOW, HIGH, LOW, HIGH);
}

// Curva atrás-derecha (corregida para tu robot)
void BackRight() {
  int slow = speedLevel / 2;
  setMotors(speedLevel, slow, LOW, HIGH, LOW, HIGH);
}