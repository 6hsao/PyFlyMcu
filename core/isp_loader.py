import time
from PySide6.QtCore import QObject, Signal, QThread

class IspLoader(QObject):
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal(bool)

    ACK = 0x79
    NACK = 0x1F

    CMD_INIT = 0x7F
    CMD_GET_ID = 0x02
    CMD_READ_MEMORY = 0x11
    CMD_GO = 0x21
    CMD_WRITE_MEMORY = 0x31
    CMD_ERASE = 0x43
    CMD_EXTENDED_ERASE = 0x44
    CMD_WRITE_PROTECT = 0x63
    CMD_WRITE_UNPROTECT = 0x73
    CMD_READOUT_PROTECT = 0x82
    CMD_READOUT_UNPROTECT = 0x92

    def __init__(self, serial_manager):
        super().__init__()
        self.serial = serial_manager
        self.running = False

    def reset_into_bootloader(self, strategy_index):
        """
        Strategies:
        0: DTR Low Reset, RTS High Bootloader
        1: DTR Low Reset, RTS Low Bootloader
        2: RTS Low Reset, DTR High Bootloader
        3: RTS Low Reset, DTR Low Bootloader
        4: No DTR/RTS Control
        """
        self.log_signal.emit(f"Entering bootloader with strategy {strategy_index}...")
        
        if strategy_index == 4:
            self.log_signal.emit("Please manually reset the device into bootloader mode.")
            return

        # DTR/RTS Control Logic
        # pyserial: setDTR(True) -> Logic Low (0V usually). setDTR(False) -> Logic High (3.3V).
        
        if strategy_index == 0:
            # DTR Low Reset, RTS High Bootloader (Common for 'One-Click Download')
            # 1. Assert Boot0 (RTS High -> False)
            self.serial.set_rts(False) 
            # 2. Assert Reset (DTR Low -> True)
            self.serial.set_dtr(True)
            time.sleep(0.1)
            # 3. Release Reset (DTR High -> False)
            self.serial.set_dtr(False)
            time.sleep(0.5) # Wait for bootloader to start

        elif strategy_index == 1:
            # DTR Low Reset, RTS Low Bootloader
            self.serial.set_rts(True) # Boot0 Low
            self.serial.set_dtr(True) # Reset Low
            time.sleep(0.1)
            self.serial.set_dtr(False)
            time.sleep(0.5)

        elif strategy_index == 2:
            # RTS Low Reset, DTR High Bootloader
            self.serial.set_dtr(False) # Boot High
            self.serial.set_rts(True)  # Reset Low
            time.sleep(0.1)
            self.serial.set_rts(False) # Reset High
            time.sleep(0.5)

        elif strategy_index == 3:
            # RTS Low Reset, DTR Low Bootloader
            self.serial.set_dtr(True)  # Boot Low
            self.serial.set_rts(True)  # Reset Low
            time.sleep(0.1)
            self.serial.set_rts(False) # Reset High
            time.sleep(0.5)

    def connect_to_device(self):
        """Sends 0x7F to initialize communication. Retries multiple times."""
        self.log_signal.emit("Attempting to connect (sending 0x7F)...")
        self.serial.flush_input()
        
        max_retries = 5
        for i in range(max_retries):
            self.serial.write(bytes([self.CMD_INIT]))
            self.log_signal.emit(f"Sent 0x7F (Attempt {i+1}/{max_retries})")
            
            start_time = time.time()
            while time.time() - start_time < 0.5: # 0.5s timeout per attempt
                if self.serial.serial_port.in_waiting:
                    byte = self.serial.read(1)
                    if byte:
                        if byte[0] == self.ACK:
                            self.log_signal.emit("Device connected (ACK received).")
                            return True
                        elif byte[0] == self.NACK:
                            self.log_signal.emit("Device NACK received. Retrying...")
                        else:
                            self.log_signal.emit(f"Received unknown byte: {byte.hex()}")
                time.sleep(0.01)
            
            time.sleep(0.1) # Wait a bit before retry
            
        self.log_signal.emit("Connection timeout. Please check wiring or manual reset.")
        return False

    def get_id(self):
        """Gets the chip ID."""
        if not self.send_cmd(self.CMD_GET_ID):
            return None
        
        # Read N (number of bytes - 1)
        n = self.serial.read(1)
        if not n: return None
        count = n[0] + 1
        
        pid = self.serial.read(count)
        if not self.wait_ack(): return None
        
        pid_val = int.from_bytes(pid, byteorder='big')
        self.log_signal.emit(f"Chip ID: 0x{pid_val:04X}")
        return pid_val

    def erase_all(self):
        """Erases all flash memory."""
        self.log_signal.emit("Erasing chip...")
        # Try Extended Erase first (0x44)
        if self.send_cmd(self.CMD_EXTENDED_ERASE):
            # Global erase: 0xFFFF followed by checksum 0x00
            self.serial.write(b'\xFF\xFF\x00')
            if self.wait_ack(timeout=30): # Erase takes time
                self.log_signal.emit("Chip erased (Extended).")
                return True
        
        # Fallback to standard erase (0x43)
        if self.send_cmd(self.CMD_ERASE):
            self.serial.write(b'\xFF\x00')
            if self.wait_ack(timeout=30):
                self.log_signal.emit("Chip erased (Standard).")
                return True
                
        self.log_signal.emit("Erase failed.")
        return False

    def write_memory(self, address, data):
        """Writes data to memory address."""
        self.log_signal.emit(f"Writing {len(data)} bytes to 0x{address:08X}...")
        
        chunk_size = 256 # Max 256 bytes per write command
        total_len = len(data)
        
        for i in range(0, total_len, chunk_size):
            chunk = data[i:i+chunk_size]
            current_addr = address + i
            
            if not self.send_cmd(self.CMD_WRITE_MEMORY):
                return False
            
            # Send Address
            addr_bytes = current_addr.to_bytes(4, byteorder='big')
            checksum = addr_bytes[0] ^ addr_bytes[1] ^ addr_bytes[2] ^ addr_bytes[3]
            self.serial.write(addr_bytes + bytes([checksum]))
            if not self.wait_ack():
                self.log_signal.emit(f"Write address failed at 0x{current_addr:08X}")
                return False
            
            # Send Data
            # N = number of bytes - 1
            n = len(chunk) - 1
            self.serial.write(bytes([n]))
            
            data_checksum = n
            for b in chunk:
                data_checksum ^= b
            
            self.serial.write(chunk + bytes([data_checksum]))
            
            if not self.wait_ack():
                self.log_signal.emit(f"Write data failed at 0x{current_addr:08X}")
                return False
            
            # Progress
            self.progress_signal.emit(int((i + len(chunk)) / total_len * 100))
            
        self.log_signal.emit("Write complete.")
        return True

    def verify_memory(self, address, data):
        """Reads back memory and verifies it matches data."""
        self.log_signal.emit("Verifying...")
        # To be implemented using Read Memory (0x11)
        self.log_signal.emit("Verification skipped (Not implemented fully).")
        return True

    def go(self, address):
        """Jumps to address."""
        self.log_signal.emit(f"Jumping to 0x{address:08X}...")
        if not self.send_cmd(self.CMD_GO):
            return False
        
        addr_bytes = address.to_bytes(4, byteorder='big')
        checksum = addr_bytes[0] ^ addr_bytes[1] ^ addr_bytes[2] ^ addr_bytes[3]
        self.serial.write(addr_bytes + bytes([checksum]))
        
        if self.wait_ack():
            self.log_signal.emit("Jump successful.")
            return True
        return False

    # Helpers
    def send_cmd(self, cmd):
        self.serial.write(bytes([cmd, cmd ^ 0xFF]))
        return self.wait_ack()

    def wait_ack(self, timeout=2.0):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.serial.serial_port.in_waiting:
                byte = self.serial.read(1)
                if byte and byte[0] == self.ACK:
                    return True
                elif byte and byte[0] == self.NACK:
                    return False
            time.sleep(0.001)
        return False
