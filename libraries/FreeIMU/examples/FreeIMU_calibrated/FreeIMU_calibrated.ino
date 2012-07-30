#include <ADXL345.h>
#include <bma180.h>
#include <HMC58X3.h>
#include <ITG3200.h>
#include <MS561101BA.h>
#include "I2Cdev.h"
#include "MPU6050.h"

//#define DEBUG
#include "DebugUtils.h"


#include "FreeIMU.h"
#include <Wire.h>

float val[11];


// Set the default object
FreeIMU my3IMU = FreeIMU();

void setup() { 
  Serial.begin(115200);
  Wire.begin();
  
  delay(500);
  my3IMU.init(true); // the parameter enable or disable fast mode
  delay(500);
}

void loop() {
  my3IMU.getValues(val);
  for(int i=0; i<9; i++) {
    Serial.print(val[i], 4);
    Serial.print('\t');
  }
  #if HAS_MS5611() 
    // with baro
    Serial.print(val[9]);
    Serial.print('\t');
    Serial.print(val[10]);
  #endif
  Serial.print('\n');
  
  /*
  my3IMU.getValues(val);
  sprintf(str, "%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d", int(val[0]), int(val[1]), int(val[2]), int(val[3]), int(val[4]), int(val[5]), int(val[6]), int(val[7]), int(val[8]));  
  Serial.print(str);
  Serial.print(10, BYTE);
  */
}

