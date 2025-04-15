//Created on Mon Feb  3 09:41:59 2025
//@author: Dr. Gianmario Sorrentino
// RSSA Software - Arduino Sketch
// For research use, please cite:
// "Rooted Soil Shear Apparatus: A low-cost, direct shear apparatus for measuring the influence of plant roots on soil shear strength", HardwareX, 2025, DOI: xxxx
// GitHub: https://github.com/GM1710/RSSA_ShearDevice

//Preamble
#include "HX711.h"        //Library to read LoadCell 

//Pins for sensors
const int LVDT = A0;
const int LC_Signal = 10;
const int LC_Sck = 11;

//Pins for controlling stepper motor
const int stepPin = 6;
const int dirPin = 5;
const int enPin = 3;

//LoadCell Setup
HX711 LoadCell;          //Object creation

//Defining Timing variables for sensors
unsigned long lastLVDTReadTime = 0;
unsigned long lastLCReadTime = 0;
const unsigned LVDT_dt_Interval = 1000;   //LVDT read interval
const unsigned LC_dt_Interval = 1000;     //LoadCell read interval 

//Defining Timing variables for stepper motor
int period = 100; 

void setup() {
  Serial.begin(9600);    //Initialize Serial communication

  //SetUp LoadCell
  LoadCell.begin(LC_Signal, LC_Sck);
  LoadCell.set_gain(32);
  LoadCell.tare();

  //Set LVDT pin
  pinMode(LVDT, INPUT);

  //Setup Motor pins
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  pinMode(enPin, OUTPUT);
  digitalWrite(enPin, LOW);

  //Instructions for user
  Serial.println("Use a command letter followed by an optional number:");
  Serial.println("  p<number>  - Set step delay period (e.g., p20 → 20 ms delay)");
  Serial.println("  f          - Move motor forward continuously");
  Serial.println("  r          - Move motor in reverse continuously");
  Serial.println("  s          - Stop the motor immediately");

}

//Loop to read sensors and handle commands
void loop () {

  //Read sensors
  readSensors();

  //Check for motor commands
  if (Serial.available()){
    char command = Serial.read();
    int number = Serial.parseInt();

    if (command == 'p'){
      period = number;
    }
    else if (command == 'f'){
      stepForward(period);
    }
    else if (command == 'r'){
      stepReverse(period);
    }
  }

}

//Sensors Reading functions

void readSensors() {
  static float lastLVDT_volt = 0;
  static long lastLC_value = 0;

  bool dataUpdated = false;

  //Check and read LVDT
  if (millis() - lastLVDTReadTime >= LVDT_dt_Interval) {
    float LVDT_value = analogRead(LVDT);
    lastLVDT_volt = LVDT_value * 5.00 / 1023;
    lastLVDTReadTime = millis();
    dataUpdated = true;
  }

  //Check and read LoadCell
  if (millis() - lastLCReadTime >= LC_dt_Interval) {
    lastLC_value = LoadCell.read();
    lastLCReadTime = millis();
    dataUpdated = true;
  }

  //Print only if data has been updated
  if (dataUpdated) {
    Serial.println(String(lastLVDT_volt) + "," +
                   String(lastLC_value) + "," +
                   String(millis())); 
  }
}


//Motor Controls Functions

void stepForward(int period) {
  digitalWrite(dirPin, HIGH);
  bool stepPinState = LOW;
  unsigned long lastStepTime = 0;
  unsigned long lastPulseTime = 0;

  while (true) {
    readSensors();
    unsigned long currentMillis = millis();
    unsigned long currentMicros = micros();

    //Step the motor based on the defined period
    if (currentMillis - lastStepTime >= period) {
      if (currentMicros - lastPulseTime >= 500){
        if (stepPinState == LOW) {
          digitalWrite(stepPin, HIGH);
          stepPinState = HIGH;
        } else {
          digitalWrite(stepPin, LOW);
          stepPinState = LOW;
        }
        lastPulseTime = currentMicros;
      }
      lastStepTime = currentMillis;
    }
    if (Serial.available() && Serial.read() == 's') {
      break;
    }
    //delay(1);  // Optional: short delay to allow the microcontroller to process other tasks
  }
}

void stepReverse(int period) {
  digitalWrite(dirPin, LOW);
  bool stepPinState = LOW;
  unsigned long lastStepTime = 0;
  unsigned long lastPulseTime = 0;

  while (true) {
    readSensors();
    unsigned long currentMillis = millis();
    unsigned long currentMicros = micros();

    //Step the motor based on the defined period
    if (currentMillis - lastStepTime >= period) {
      if (currentMicros - lastPulseTime >= 500){
        if (stepPinState == LOW) {
          digitalWrite(stepPin, HIGH);
          stepPinState = HIGH;
        } else {
          digitalWrite(stepPin, LOW);
          stepPinState = LOW;
        }
        lastPulseTime = currentMicros;
      }
      lastStepTime = currentMillis;
    }
    if (Serial.available() && Serial.read() == 's') {
      break;
    }
    //delay(1);  // Optional: short delay to allow the microcontroller to process other tasks
  }
}


