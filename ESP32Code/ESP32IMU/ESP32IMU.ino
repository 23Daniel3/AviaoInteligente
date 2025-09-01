#include <WiFi.h>
#include <Wire.h>

#define MPU_ADDR 0x68  

// Rede criada pelo ESP32
const char* ssid = "WIFI_ESP";
const char* password = "12345678";

// Servidores TCP
WiFiServer gyroServer(8080);  
WiFiServer logServer(9090);   

WiFiClient gyroClient;
WiFiClient logClient;

// Variáveis de sensores
int16_t ax, ay, az, gx, gy, gz;
float AccX, AccY, AccZ;
float GyroX, GyroY, GyroZ;

// Filtro complementar
float angleX, angleY; 
float gyroAngleX, gyroAngleY;
float accAngleX, accAngleY;
float elapsedTime, currentTime, previousTime;
float alpha = 0.98; 

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22); // SDA=21, SCL=22

  // Inicia como Access Point
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);
  Serial.println("✅ Access Point iniciado!");
  Serial.print("SSID: "); Serial.println(ssid);
  Serial.print("Senha: "); Serial.println(password);
  Serial.print("IP do ESP32: "); Serial.println(WiFi.softAPIP());

  // Inicia servidores
  gyroServer.begin();
  logServer.begin();

  // Inicializa MPU
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);  
  Wire.write(0); 
  if (Wire.endTransmission(true) != 0) {
    sendLog("❌ Erro: não conseguiu iniciar MPU6500!");
  } else {
    sendLog("✅ MPU6500 iniciado com filtro complementar.");
  }
}

void loop() {
  // Aceitar conexões
  if (!gyroClient || !gyroClient.connected()) {
    gyroClient = gyroServer.available();
  }
  if (!logClient || !logClient.connected()) {
    logClient = logServer.available();
  }

  // Tempo
  currentTime = millis();
  elapsedTime = (currentTime - previousTime) / 1000.0;
  previousTime = currentTime;

  // Ler MPU
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);  
  if (Wire.endTransmission(false) != 0) {
    sendLog("⚠️ Erro lendo MPU6500!");
    delay(100);
    return;
  }

  Wire.requestFrom(MPU_ADDR, 14, true);
  if (Wire.available() < 14) {
    sendLog("⚠️ Dados incompletos do MPU6500!");
    delay(100);
    return;
  }

  ax = Wire.read() << 8 | Wire.read(); 
  ay = Wire.read() << 8 | Wire.read(); 
  az = Wire.read() << 8 | Wire.read(); 
  Wire.read(); Wire.read(); // descarta temp
  gx = Wire.read() << 8 | Wire.read(); 
  gy = Wire.read() << 8 | Wire.read(); 
  gz = Wire.read() << 8 | Wire.read(); 

  AccX = ax / 16384.0;  
  AccY = ay / 16384.0;  
  AccZ = az / 16384.0;  

  GyroX = gx / 131.0;   
  GyroY = gy / 131.0;   
  GyroZ = gz / 131.0;   

  accAngleX = atan2(AccY, AccZ) * 180 / PI;
  accAngleY = atan2(-AccX, sqrt(AccY*AccY + AccZ*AccZ)) * 180 / PI;

  gyroAngleX += GyroX * elapsedTime;
  gyroAngleY += GyroY * elapsedTime;

  angleX = alpha * (angleX + GyroX * elapsedTime) + (1 - alpha) * accAngleX;
  angleY = alpha * (angleY + GyroY * elapsedTime) + (1 - alpha) * accAngleY;

  // Enviar dados (roll, pitch, yaw)
  sendGyro(angleY, angleX, gyroAngleX);

  delay(2);
}

void sendGyro(float roll, float pitch, float yaw) {
  if (gyroClient && gyroClient.connected()) {
    gyroClient.printf("%f,%f,%f\n", roll, pitch, yaw);
  }
}

void sendLog(const char* msg) {
  if (logClient && logClient.connected()) {
    logClient.println(msg);
  }
  Serial.println(msg);
}
