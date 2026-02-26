/*
 * Zumo Line Follower — Control via Serial
 * ─────────────────────────────────────────────────────────────────
 * Comandos recibidos por Serial (115200 baud):
 *
 *   START              → Inicia seguimiento de línea
 *   STOP               → Detiene el robot
 *   PID:<kp>,<kd>      → Ajusta constantes PID  ej: PID:0.25,6.0
 *   SPEED:<max>        → Ajusta velocidad máxima (0-400) ej: SPEED:300
 *   INTERVAL:<ms>      → Intervalo de telemetría en ms  ej: INTERVAL:100
 *
 * Datos enviados por Serial (JSON):
 *   {"pos":<pos>,"err":<err>,"m1":<m1>,"m2":<m2>,"kp":<kp>,"kd":<kd>,"spd":<max>,"run":<0|1>}
 *
 * ─────────────────────────────────────────────────────────────────
 */

#include <Wire.h>
#include <ZumoShield.h>

// ── Hardware ──────────────────────────────────────────────────────
ZumoReflectanceSensorArray reflectanceSensors;
ZumoMotors motors;

// ── Parámetros PID (ajustables via serial) ────────────────────────
float KP         = 0.25f;
float KD         = 6.0f;
int   MAX_SPEED  = 400;

// ── Telemetría ────────────────────────────────────────────────────
unsigned long TELEM_INTERVAL_MS = 100;   // cada cuántos ms enviar datos
unsigned long lastTelemTime     = 0;

// ── Estado ────────────────────────────────────────────────────────
bool  running   = false;
int   lastError = 0;

// Últimos valores para telemetría
int lastPosition = 0;
int lastM1 = 0, lastM2 = 0;

// ── Buffer de comandos serial ─────────────────────────────────────
String cmdBuffer = "";

// ═══════════════════════════════════════════════════════════════════
void setup()
{
  Serial.begin(115200);

  reflectanceSensors.init();
  motors.setSpeeds(0, 0);

  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);

  // Calibración automática al encender
  calibrate();

  Serial.println(F("{\"status\":\"READY\",\"msg\":\"Enviar START para comenzar\"}"));
  sendParams();
}

// ═══════════════════════════════════════════════════════════════════
void loop()
{
  // ── Leer comandos serial ──────────────────────────────────────
  while (Serial.available())
  {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r')
    {
      cmdBuffer.trim();
      if (cmdBuffer.length() > 0)
      {
        processCommand(cmdBuffer);
        cmdBuffer = "";
      }
    }
    else
    {
      cmdBuffer += c;
    }
  }

  // ── Control de línea ─────────────────────────────────────────
  if (running)
  {
    unsigned int sensors[6];
    int position = reflectanceSensors.readLine(sensors);
    int error    = position - 2500;

    int speedDiff = (int)(KP * error) + (int)(KD * (error - lastError));
    lastError = error;

    int m1Speed = constrain(MAX_SPEED + speedDiff, 0, MAX_SPEED);
    int m2Speed = constrain(MAX_SPEED - speedDiff, 0, MAX_SPEED);

    motors.setSpeeds(m1Speed, m2Speed);

    lastPosition = position;
    lastM1 = m1Speed;
    lastM2 = m2Speed;
  }

  // ── Telemetría periódica ──────────────────────────────────────
  unsigned long now = millis();
  if (now - lastTelemTime >= TELEM_INTERVAL_MS)
  {
    lastTelemTime = now;
    sendTelemetry();
  }
}

// ═══════════════════════════════════════════════════════════════════
void processCommand(const String& cmd)
{
  if (cmd == "START")
  {
    running   = true;
    lastError = 0;
    digitalWrite(13, HIGH);
    Serial.println(F("{\"status\":\"RUNNING\"}"));
  }
  else if (cmd == "STOP")
  {
    running = false;
    motors.setSpeeds(0, 0);
    digitalWrite(13, LOW);
    Serial.println(F("{\"status\":\"STOPPED\"}"));
  }
  else if (cmd.startsWith("PID:"))
  {
    // Formato: PID:kp,kd
    String params = cmd.substring(4);
    int comma = params.indexOf(',');
    if (comma > 0)
    {
      KP = params.substring(0, comma).toFloat();
      KD = params.substring(comma + 1).toFloat();
      Serial.print(F("{\"status\":\"PID_OK\",\"kp\":"));
      Serial.print(KP, 4);
      Serial.print(F(",\"kd\":"));
      Serial.print(KD, 4);
      Serial.println(F("}"));
    }
    else
    {
      Serial.println(F("{\"status\":\"ERROR\",\"msg\":\"Formato: PID:kp,kd\"}"));
    }
  }
  else if (cmd.startsWith("SPEED:"))
  {
    int spd = cmd.substring(6).toInt();
    if (spd >= 0 && spd <= 400)
    {
      MAX_SPEED = spd;
      Serial.print(F("{\"status\":\"SPEED_OK\",\"max_speed\":"));
      Serial.print(MAX_SPEED);
      Serial.println(F("}"));
    }
    else
    {
      Serial.println(F("{\"status\":\"ERROR\",\"msg\":\"SPEED debe ser 0-400\"}"));
    }
  }
  else if (cmd.startsWith("INTERVAL:"))
  {
    unsigned long iv = cmd.substring(9).toInt();
    if (iv >= 10 && iv <= 10000)
    {
      TELEM_INTERVAL_MS = iv;
      Serial.print(F("{\"status\":\"INTERVAL_OK\",\"interval_ms\":"));
      Serial.print(TELEM_INTERVAL_MS);
      Serial.println(F("}"));
    }
    else
    {
      Serial.println(F("{\"status\":\"ERROR\",\"msg\":\"INTERVAL debe ser 10-10000 ms\"}"));
    }
  }
  else if (cmd == "PARAMS")
  {
    sendParams();
  }
  else
  {
    Serial.print(F("{\"status\":\"UNKNOWN\",\"cmd\":\""));
    Serial.print(cmd);
    Serial.println(F("\"}"));
  }
}

// ═══════════════════════════════════════════════════════════════════
void sendTelemetry()
{
  Serial.print(F("{\"telem\":1,\"pos\":"));
  Serial.print(lastPosition);
  Serial.print(F(",\"err\":"));
  Serial.print(lastPosition - 2500);
  Serial.print(F(",\"m1\":"));
  Serial.print(lastM1);
  Serial.print(F(",\"m2\":"));
  Serial.print(lastM2);
  Serial.print(F(",\"kp\":"));
  Serial.print(KP, 4);
  Serial.print(F(",\"kd\":"));
  Serial.print(KD, 4);
  Serial.print(F(",\"spd\":"));
  Serial.print(MAX_SPEED);
  Serial.print(F(",\"run\":"));
  Serial.print(running ? 1 : 0);
  Serial.print(F(",\"t\":"));
  Serial.print(millis());
  Serial.println(F("}"));
}

// ═══════════════════════════════════════════════════════════════════
void sendParams()
{
  Serial.print(F("{\"params\":1,\"kp\":"));
  Serial.print(KP, 4);
  Serial.print(F(",\"kd\":"));
  Serial.print(KD, 4);
  Serial.print(F(",\"max_speed\":"));
  Serial.print(MAX_SPEED);
  Serial.print(F(",\"interval_ms\":"));
  Serial.print(TELEM_INTERVAL_MS);
  Serial.println(F("}"));
}

// ═══════════════════════════════════════════════════════════════════
void calibrate()
{
  Serial.println(F("{\"status\":\"CALIBRATING\"}"));
  digitalWrite(13, HIGH);
  delay(500);

  for (int i = 0; i < 80; i++)
  {
    if ((i > 10 && i <= 30) || (i > 50 && i <= 70))
      motors.setSpeeds(-200, 200);
    else
      motors.setSpeeds(200, -200);

    reflectanceSensors.calibrate();
    delay(20);
  }

  motors.setSpeeds(0, 0);
  digitalWrite(13, LOW);
  Serial.println(F("{\"status\":\"CALIBRATION_DONE\"}"));
}
