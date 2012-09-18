import sys
from PyQt4.QtGui import QApplication, QDialog, QMainWindow
from ui_freeimu_cal import Ui_FreeIMUCal
from PyQt4.QtCore import QObject, pyqtSlot, QThread, SIGNAL
import numpy as np
import serial, time
from struct import unpack
from binascii import unhexlify
from subprocess import call



class FreeIMUCal(QMainWindow, Ui_FreeIMUCal):
  def __init__(self):
    QMainWindow.__init__(self)

    # Set up the user interface from Designer.
    self.setupUi(self)

    # Connect up the buttons.
    self.connectButton.clicked.connect(self.serial_connect)
    self.samplingToggleButton.clicked.connect(self.sampling_start)
    
    
    # data storages
    self.acc_data = [[], [], []]
    

  def set_status(self, status):
    self.statusbar.showMessage(self.tr(status))

  def serial_connect(self):
    self.serial_port = str(self.serialPortEdit.text())
    print "connecting to " + self.serial_port
    
    # TODO: serial port field input validation!
    
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
      self.serialPortEdit.setReadOnly(True)
      
      self.samplingToggleButton.setEnabled(True)
    
  def serial_disconnect(self):
    print "Disconnecting from " + self.serial_port
    self.ser.close()
    self.set_status("Disconnected")
    self.serialPortEdit.setReadOnly(False)
      
      
  def sampling_start(self):
    self.serWorker = SerialWorker(ser = self.ser)
    self.connect(self.serWorker, SIGNAL("new_data(PyQt_PyObject)"), self.newData)
    self.serWorker.start()
    
  def sampling_end(self):
    self.serWorker.quit()

  def newData(self, data):
    print "new data!"
    print len(self.acc_data[0])
    for elem in data:
      print elem
      for i in range(3):
        self.acc_data[i].append(elem[i])
        
    self.accXY.plot(self.acc_data[0][:-25], self.acc_data[1][:-25]) #pen=None, symbol='t', symbolPen=None, symbolSize=10, symbolBrush=(100, 100, 255, 50))
    self.accYZ.plot(self.acc_data[1][:-25], self.acc_data[2][:-25]) #pen=None, symbol='t', symbolPen=None, symbolSize=10, symbolBrush=(100, 100, 255, 50))
    self.accZX.plot(self.acc_data[2][:-25], self.acc_data[0][:-25]) #pen=None, symbol='t', symbolPen=None, symbolSize=10, symbolBrush=(100, 100, 255, 50))


class SerialWorker(QThread):
  def __init__(self, parent = None, ser = None):
    QThread.__init__(self, parent)
    self.exiting = False
    self.ser = ser
    print "ciao"
    
  def run(self):
    print "sampling start.."
    count = 5
    in_values = 9
    delay = 0.5
    buff = []
    buff_line = [0.0 for i in range(in_values)]
    while not self.exiting:
      time.sleep(delay)
      self.ser.write('b')
      self.ser.write(chr(count))
      for j in range(count):
        for i in range(in_values):
          buff_line[i] = unpack('h', self.ser.read(2))[0]
        self.ser.read(2) # consumes remaining '\r\n'
        buff.append(list(buff_line))
      self.emit(SIGNAL("new_data(PyQt_PyObject)"), buff)
      #print buff
  
  def __del__(self):
    self.exiting = True
    self.wait()




app = QApplication(sys.argv)
window = FreeIMUCal()

window.show()
sys.exit(app.exec_())