/**
 * FreeIMU library serial communication protocol
*/

#include <ADXL345.h>
#include <bma180.h>
#include <HMC58X3.h>
#include <ITG3200.h>
#include <MS561101BA.h>
#include "I2Cdev.h"
#include "MPU6050.h"

//#define DEBUG
#include "DebugUtils.h"
#include "CommunicationUtils.h"
#include "FreeIMU.h"
#include <Wire.h>


float q[4];
int raw_values[9];
float ypr[3]; // yaw pitch roll
char str[512];
float val[9];


// Set the FreeIMU object
FreeIMU my3IMU = FreeIMU();
//The command from the PC
char cmd;

void setup() {
  Serial.begin(115200);
  Wire.begin();
  my3IMU.init(true);
}


void loop() {
  if(Serial.available()) {
    cmd = Serial.read();
    if(cmd=='v') {
      sprintf(str, "FreeIMU library by %s, FREQ:%s, LIB_VERSION: %s, IMU: %s", FREEIMU_DEVELOPER, FREEIMU_FREQ, FREEIMU_LIB_VERSION, FREEIMU_ID);
      Serial.print(str);
      Serial.print('\n');
    }
    else if(cmd=='r') {
      uint8_t count = serial_busy_wait();
      for(uint8_t i=0; i<count; i++) {
        my3IMU.getRawValues(raw_values);
        sprintf(str, "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,", raw_values[0], raw_values[1], raw_values[2], raw_values[3], raw_values[4], raw_values[5], raw_values[6], raw_values[7], raw_values[8], raw_values[9], raw_values[10]);
        Serial.print(str);
        Serial.print('\n');
      }
    }
    else if(cmd=='b') {
      uint8_t count = serial_busy_wait();
      for(uint8_t i=0; i<count; i++) {
        my3IMU.accgyro.getMotion6(&raw_values[0], &raw_values[1], &raw_values[2], &raw_values[3], &raw_values[4], &raw_values[5]);
        writeArr(raw_values, 6, sizeof(int)); // writes accelerometer and gyro values
        my3IMU.magn.getValues(&raw_values[0], &raw_values[1], &raw_values[2]);
        writeArr(raw_values, 3, sizeof(int));
        Serial.println();
      }
    }
    else if(cmd=='b') {
      uint8_t count = serial_busy_wait();
      for(uint8_t i=0; i<count; i++) {
        my3IMU.accgyro.getMotion6(&raw_values[0], &raw_values[1], &raw_values[2], &raw_values[3], &raw_values[4], &raw_values[5]);
        writeArr(raw_values, 6, sizeof(int)); // writes accelerometer and gyro values
        my3IMU.magn.getValues(&raw_values[0], &raw_values[1], &raw_values[2]);
        writeArr(raw_values, 3, sizeof(int));
        Serial.println();
      }
    }
    else if(cmd=='q') {
      uint8_t count = serial_busy_wait();
      for(uint8_t i=0; i<count; i++) {
        my3IMU.getQ(q);
        serialPrintFloatArr(q, 4);
        Serial.println("");
      }
    }
  }
}

char serial_busy_wait() {
  while(!Serial.available()) {
    ; // do nothing until ready
  }
  Serial.read();
}

