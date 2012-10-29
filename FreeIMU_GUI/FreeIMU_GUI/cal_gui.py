import sys, os
from PyQt4.QtGui import QApplication, QDialog, QMainWindow, QCursor, QFileDialog
from ui_freeimu_cal import Ui_FreeIMUCal
from PyQt4.QtCore import Qt,QObject, pyqtSlot, QThread, QSettings, SIGNAL
import numpy as np
import serial, time
from struct import unpack
from binascii import unhexlify
from subprocess import call
import pyqtgraph.opengl as gl
import cal_lib, numpy

acc_file_name = "acc.txt"
magn_file_name = "magn.txt"
calibration_h_file_name = "calibration.h"

acc_range = 15000
magn_range = 1000

class FreeIMUCal(QMainWindow, Ui_FreeIMUCal):
  def __init__(self):
    QMainWindow.__init__(self)

    # Set up the user interface from Designer.
    self.setupUi(self)
    
    # load user settings
    self.settings = QSettings("FreeIMU Calibration Application", "Fabio Varesano")
    # restore previous serial port used
    self.serialPortEdit.setText(self.settings.value("calgui/serialPortEdit", "").toString())
    
    # when user hits enter, we generate the clicked signal to the button so that connection starts
    self.connect(self.serialPortEdit, SIGNAL("returnPressed()"), self.connectButton, SIGNAL("clicked()"))
    
    # Connect up the buttons to their functions
    self.connectButton.clicked.connect(self.serial_connect)
    self.samplingToggleButton.clicked.connect(self.sampling_start)
    self.set_status("Disconnected")
    
    # data storages
    self.acc_data = [[], [], []]
    self.magn_data = [[], [], []]
    
    self.accXY.setXRange(-acc_range, acc_range)
    self.accXY.setYRange(-acc_range, acc_range)
    self.accYZ.setXRange(-acc_range, acc_range)
    self.accYZ.setYRange(-acc_range, acc_range)
    self.accZX.setXRange(-acc_range, acc_range)
    self.accZX.setYRange(-acc_range, acc_range)
    
    self.accXY.setAspectLocked()
    self.accYZ.setAspectLocked()
    self.accZX.setAspectLocked()
    
    self.magnXY.setXRange(-magn_range, magn_range)
    self.magnXY.setYRange(-magn_range, magn_range)
    self.magnYZ.setXRange(-magn_range, magn_range)
    self.magnYZ.setYRange(-magn_range, magn_range)
    self.magnZX.setXRange(-magn_range, magn_range)
    self.magnZX.setYRange(-magn_range, magn_range)
    
    self.magnXY.setAspectLocked()
    self.magnYZ.setAspectLocked()
    self.magnZX.setAspectLocked()
    
    self.accXY_cal.setXRange(-1.5, 1.5)
    self.accXY_cal.setYRange(-1.5, 1.5)
    self.accYZ_cal.setXRange(-1.5, 1.5)
    self.accYZ_cal.setYRange(-1.5, 1.5)
    self.accZX_cal.setXRange(-1.5, 1.5)
    self.accZX_cal.setYRange(-1.5, 1.5)
    
    self.accXY_cal.setAspectLocked()
    self.accYZ_cal.setAspectLocked()
    self.accZX_cal.setAspectLocked()
    
    self.magnXY_cal.setXRange(-1.5, 1.5)
    self.magnXY_cal.setYRange(-1.5, 1.5)
    self.magnYZ_cal.setXRange(-1.5, 1.5)
    self.magnYZ_cal.setYRange(-1.5, 1.5)
    self.magnZX_cal.setXRange(-1.5, 1.5)
    self.magnZX_cal.setYRange(-1.5, 1.5)
    
    self.magnXY_cal.setAspectLocked()
    self.magnYZ_cal.setAspectLocked()
    self.magnZX_cal.setAspectLocked()
    
    self.acc3D.opts['distance'] = 20
    self.acc3D.show()

    ax = gl.GLAxisItem()
    ax.setSize(5,5,5)
    self.acc3D.addItem(ax)

    self.sp = gl.GLScatterPlotItem(pos = [], color = (1.0, 0.0, 0.0, 0.5), size = 0.5)
    self.acc3D.addItem(self.sp)
    
    #b = gl.GLBoxItem()
    #self.acc3D.addItem(b)

    #ax2 = gl.GLAxisItem()
    #ax2.setParentItem(b)

    #b.translate(1,1,1)
    

  def set_status(self, status):
    self.statusbar.showMessage(self.tr(status))

  def serial_connect(self):
    self.serial_port = str(self.serialPortEdit.text())
    # save serial value to user settings
    self.settings.setValue("calgui/serialPortEdit", self.serial_port)
    
    self.connectButton.setEnabled(False)
    # waiting mouse cursor
    QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
    self.set_status("Connecting to " + self.serial_port + " ...")
    
    # TODO: serial port field input validation!
    
    try:
      self.ser = serial.Serial(
        port= self.serial_port,
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS
      )
      
      if self.ser.isOpen():
        print "Arduino serial port opened correctly"
        self.set_status("Connection Successfull. Awaiting for Arduino reset...")

        # wait for arduino reset on serial open
        time.sleep(3)
        
        self.ser.write('v') # ask version
        self.set_status("Connected to: " + self.ser.readline())
        
        self.connectButton.setText("Disconnect")
        self.connectButton.clicked.connect(self.serial_disconnect)
        self.serialPortEdit.setEnabled(False)
        self.serialProtocol.setEnabled(False)
        
        self.samplingToggleButton.setEnabled(True)
    except serial.serialutil.SerialException, e:
      self.connectButton.setEnabled(True)
      self.set_status("Impossible to connect: " + str(e))
      
    # restore mouse cursor
    QApplication.restoreOverrideCursor()
    self.connectButton.setEnabled(True)

    
  def serial_disconnect(self):
    print "Disconnecting from " + self.serial_port
    self.ser.close()
    self.set_status("Disconnected")
    self.serialPortEdit.setEnabled(True)
    self.serialProtocol.setEnabled(True)
    
    self.connectButton.setText("Connect")
    self.connectButton.clicked.disconnect(self.serial_disconnect)
    self.connectButton.clicked.connect(self.serial_connect)
    
    self.samplingToggleButton.setEnabled(False)
      
  def sampling_start(self):
    self.acc_file = open(acc_file_name, 'w')
    self.magn_file = open(magn_file_name, 'w')
    
    self.serWorker = SerialWorker(ser = self.ser)
    self.connect(self.serWorker, SIGNAL("new_data(PyQt_PyObject)"), self.newData)
    self.serWorker.start()
    print "Starting SerialWorker"
    self.samplingToggleButton.setText("Stop Sampling")
    
    self.samplingToggleButton.clicked.disconnect(self.sampling_start)
    self.samplingToggleButton.clicked.connect(self.sampling_end)
    
  def sampling_end(self):
    self.serWorker.exiting = True
    self.serWorker.quit()
    self.serWorker.wait()
    self.samplingToggleButton.setText("Start Sampling")
    self.samplingToggleButton.clicked.disconnect(self.sampling_end)
    self.samplingToggleButton.clicked.connect(self.sampling_start)
    
    # closing open logging files
    self.acc_file.close()
    self.magn_file.close()
    
    self.calibrateButton.setEnabled(True)
    self.calAlgorithmComboBox.setEnabled(True)
    self.calibrateButton.clicked.connect(self.calibrate)
    
  
  def calibrate(self):
    # read file and run calibration algorithm
    (self.acc_offset, self.acc_scale) = cal_lib.calibrate_from_file(acc_file_name)
    (self.magn_offset, self.magn_scale) = cal_lib.calibrate_from_file(magn_file_name)
    
    # show calibrated tab
    self.tabWidget.setCurrentIndex(1)
    
    #populate acc calibration output on gui
    self.calRes_acc_OSx.setText(str(self.acc_offset[0]))
    self.calRes_acc_OSy.setText(str(self.acc_offset[1]))
    self.calRes_acc_OSz.setText(str(self.acc_offset[2]))
    
    self.calRes_acc_SCx.setText(str(self.acc_scale[0]))
    self.calRes_acc_SCy.setText(str(self.acc_scale[1]))
    self.calRes_acc_SCz.setText(str(self.acc_scale[2]))
    
    #populate acc calibration output on gui
    self.calRes_magn_OSx.setText(str(self.magn_offset[0]))
    self.calRes_magn_OSy.setText(str(self.magn_offset[1]))
    self.calRes_magn_OSz.setText(str(self.magn_offset[2]))
    
    self.calRes_magn_SCx.setText(str(self.magn_scale[0]))
    self.calRes_magn_SCy.setText(str(self.magn_scale[1]))
    self.calRes_magn_SCz.setText(str(self.magn_scale[2]))
    
    self.acc_cal_data = cal_lib.compute_calibrate_data(self.acc_data, self.acc_offset, self.acc_scale)
    self.magn_cal_data = cal_lib.compute_calibrate_data(self.magn_data, self.magn_offset, self.magn_scale)
    
    self.accXY_cal.plot(x = self.acc_cal_data[0], y = self.acc_cal_data[1], clear = True, pen='r')
    self.accYZ_cal.plot(x = self.acc_cal_data[1], y = self.acc_cal_data[2], clear = True, pen='g')
    self.accZX_cal.plot(x = self.acc_cal_data[2], y = self.acc_cal_data[0], clear = True, pen='b')
    
    self.magnXY_cal.plot(x = self.magn_cal_data[0], y = self.magn_cal_data[1], clear = True, pen='r')
    self.magnYZ_cal.plot(x = self.magn_cal_data[1], y = self.magn_cal_data[2], clear = True, pen='g')
    self.magnZX_cal.plot(x = self.magn_cal_data[2], y = self.magn_cal_data[0], clear = True, pen='b')
    
    #enable calibration buttons to activate calibration storing functions
    self.saveCalibrationHeaderButton.setEnabled(True)
    self.saveCalibrationHeaderButton.clicked.connect(self.save_calibration_header)
    
    self.saveCalibrationEEPROMButton.setEnabled(True)
    self.saveCalibrationEEPROMButton.clicked.connect(self.save_calibration_eeprom)
    
    
  def save_calibration_header(self):
    text = """
/**
 * FreeIMU calibration header. Automatically generated by octave AccMagnCalib.m.
 * Do not edit manually unless you know what you are doing.
*/


#define CALIBRATION_H

const int acc_off_x = %d;
const int acc_off_y = %d;
const int acc_off_z = %d;
const float acc_scale_x = %f;
const float acc_scale_y = %f;
const float acc_scale_z = %f;

const int magn_off_x = %d;
const int magn_off_y = %d;
const int magn_off_z = %d;
const float magn_scale_x = %f;
const float magn_scale_y = %f;
const float magn_scale_z = %f;
"""
    calibration_h_text = text % (self.acc_offset[0], self.acc_offset[1], self.acc_offset[2], self.acc_scale[0], self.acc_scale[1], self.acc_scale[2], self.magn_offset[0], self.magn_offset[1], self.magn_offset[2], self.magn_scale[0], self.magn_scale[1], self.magn_scale[2])
    
    calibration_h_folder = QFileDialog.getExistingDirectory(self, "Select the Folder to which save the calibration.h file")
    calibration_h_file = open(os.path.join(str(calibration_h_folder), calibration_h_file_name), "w")
    calibration_h_file.write(calibration_h_text)
    calibration_h_file.close()
    
    self.set_status("Calibration saved to: " + str(calibration_h_folder) + calibration_h_file_name + " .\nRecompile and upload the program using the FreeIMU library to your microcontroller.")
  
  def save_calibration_eeprom(self):
    print "gatto"

  def newData(self, data):
    for reading in data:
      acc_readings_line = "%d %d %d\r\n" % (reading[0], reading[1], reading[2])
      self.acc_file.write(acc_readings_line)
      
      magn_readings_line = "%d %d %d\r\n" % (reading[6], reading[7], reading[8])
      self.magn_file.write(magn_readings_line)
    
    # only display last reading in burst
    self.acc_data[0].append(reading[0])
    self.acc_data[1].append(reading[1])
    self.acc_data[2].append(reading[2])
    
    self.magn_data[0].append(reading[6])
    self.magn_data[1].append(reading[7])
    self.magn_data[2].append(reading[8])
    
    
    self.accXY.plot(x = self.acc_data[0], y = self.acc_data[1], clear = True, pen='r')
    self.accYZ.plot(x = self.acc_data[1], y = self.acc_data[2], clear = True, pen='g')
    self.accZX.plot(x = self.acc_data[2], y = self.acc_data[0], clear = True, pen='b')
    
    self.magnXY.plot(x = self.magn_data[0], y = self.magn_data[1], clear = True, pen='r')
    self.magnYZ.plot(x = self.magn_data[1], y = self.magn_data[2], clear = True, pen='g')
    self.magnZX.plot(x = self.magn_data[2], y = self.magn_data[0], clear = True, pen='b')
    
    #point3D = [{'pos': (self.acc_data[0],self.acc_data[1],self.acc_data[2]), 'size':0.5, 'color':(1.0, 0.0, 0.0, 0.5)}]
    
    #points = numpy.array([self.acc_data[0],self.acc_data[1],self.acc_data[2]])
    #points = numpy.transpose(points)
    #print points
    
    #print numpy.array(self.acc_data)
    
    #poss = (numpy.random.random(size=(100000,3)) * 10) - 5
    
    #poss = [[1, 1, 1]]
    
    #self.sp.setData(pos = poss)
    

class SerialWorker(QThread):
  def __init__(self, parent = None, ser = None):
    QThread.__init__(self, parent)
    self.exiting = False
    self.ser = ser
    
  def run(self):
    print "sampling start.."
    count = 50
    in_values = 9
    buff = []
    buff_line = [0.0 for i in range(in_values)]
    while not self.exiting:
      self.ser.write('b')
      self.ser.write(chr(count))
      for j in range(count):
        for i in range(in_values):
          buff_line[i] = unpack('h', self.ser.read(2))[0]
        self.ser.read(2) # consumes remaining '\r\n'
        buff.append(list(buff_line))
      self.emit(SIGNAL("new_data(PyQt_PyObject)"), buff)
      buff = []
      print ".",
    return 
  
  def __del__(self):
    self.exiting = True
    self.wait()
    print "SerialWorker exits.."
  
  #def quit(self):
    #self.exiting = True


app = QApplication(sys.argv)
window = FreeIMUCal()

window.show()
sys.exit(app.exec_())