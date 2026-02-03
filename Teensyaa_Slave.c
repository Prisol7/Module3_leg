#include <Wire.h>
#include <Servo.h>
#define SLAVE_ADDR 0x08

Servo servo_0;
Servo servo_1;
Servo servo_2;
Servo servo_3;

volatile bool dataReceived = false;
volatile byte dataSize = false;


// Values from Master
int angle_0 = 0;
int angle_1 = 0;
int angle_2 = 0;
int angle_3 = 0;

int adc_0 = 0;
int adc_1 = 0;
int adc_2 = 0;
int adc_3 = 0;

// Recieved Data
char temp[32] = "";

void setup() {

  //I2C Initialize
  Wire.begin(SLAVE_ADDR);
  // Recieve
  Wire.onReceive(receiveEvent);
  Serial.begin(9600);

  // Servo Pins

  servo_0.attach(0); //Left Joint
  servo_1.attach(1); // Left Leg
  servo_2.attach(2);
  servo_3.attach(3);
}

void receiveEvent(int howMany){

  for (int i = 0; i < howMany; i++) {
    temp[i] = Wire.read();
    temp[i + 1] = '\0'; //add null after ea. char
  }

  //RPi first byte is cmd byte so shift everything to the left 1 pos so temp contains our string
  for (int i = 0; i < howMany; ++i)
    temp[i] = temp[i + 1];
  Serial.println(temp);

  transform_to_adc(temp);
}


void transform_to_adc(char* original){
  char buffer[32];
  strcpy(buffer, original);

  char *token = strtok(buffer, "/");
  angle_0 = atoi(token);
  token = strtok(NULL, "/");
  angle_1 = atoi(token);
  token = strtok(NULL, "/");
  angle_2 = atoi(token);
  token = strtok(NULL, "/");
  angle_3 = atoi(token);

  Serial.println(angle_0);
  Serial.println(angle_1);
  Serial.println(angle_2);
  Serial.println(angle_3);
}

void loop() {
  // put your main code here, to run repeatedly:
  //Serial.print("Slave received: ");
  //Serial.print(receive);
  //Serial.println(receive);
  //transform_to_adc(receive);

  servo_0.write(angle_0);
  servo_1.write(angle_1);
  servo_2.write(angle_2);
  servo_3.write(angle_3);

  delay(10);
}
