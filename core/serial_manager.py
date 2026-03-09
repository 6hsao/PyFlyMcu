import serial
import serial.tools.list_ports
from PySide6.QtCore import QObject, Signal

class SerialManager(QObject):
    connected = Signal(bool)
    error_occurred = Signal(str)
    data_received = Signal(bytes)

    def __init__(self):
        super().__init__()
        self.serial_port = None

    def list_ports(self):
        """Returns a list of available serial ports."""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def connect(self, port_name, baud_rate, parity=serial.PARITY_NONE):
        """Connects to the specified serial port."""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=parity,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1  # Non-blocking read with timeout
            )
            self.connected.emit(True)
            return True
        except serial.SerialException as e:
            self.error_occurred.emit(str(e))
            return False

    def disconnect(self):
        """Disconnects the serial port."""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.serial_port = None
        self.connected.emit(False)

    def write(self, data):
        """Writes data to the serial port."""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(data)
                return True
            except serial.SerialException as e:
                self.error_occurred.emit(str(e))
                return False
        return False

    def read(self, size=1):
        """Reads data from the serial port."""
        if self.serial_port and self.serial_port.is_open:
            try:
                return self.serial_port.read(size)
            except serial.SerialException as e:
                self.error_occurred.emit(str(e))
        return b''
    
    def set_dtr(self, level):
        """Sets DTR line level (True=High/1, False=Low/0)."""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.dtr = level
            
    def set_rts(self, level):
        """Sets RTS line level (True=High/1, False=Low/0)."""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.rts = level

    def flush_input(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.reset_input_buffer()
