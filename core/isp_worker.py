from PySide6.QtCore import QThread, Signal
import time
import serial
from core.isp_loader import IspLoader
from core.firmware_parser import FirmwareParser

class IspWorker(QThread):
    log_message = Signal(str)
    progress_update = Signal(int)
    finished_task = Signal(bool)

    # Task Types
    TASK_PROGRAM = "program"
    TASK_READ_INFO = "read_info"
    TASK_ERASE = "erase"
    TASK_READ_FLASH = "read_flash"

    def __init__(self, serial_manager, config, task_type=TASK_PROGRAM):
        super().__init__()
        self.serial_manager = serial_manager
        self.config = config
        self.task_type = task_type
        self.loader = IspLoader(serial_manager)
        
        # Connect loader signals to worker signals
        self.loader.log_signal.connect(self.log_message)
        self.loader.progress_signal.connect(self.progress_update)

    def run(self):
        try:
            self.log_message.emit(f"Starting task: {self.task_type}...")
            
            # Re-configure port for ISP (8E1)
            port = self.config.get('port')
            baud = self.config.get('baud')
            
            self.log_message.emit("Configuring serial for ISP (8E1)...")
            self.serial_manager.disconnect()
            time.sleep(0.1)
            if not self.serial_manager.connect(port, baud, parity=serial.PARITY_EVEN):
                self.log_message.emit("Failed to open serial port.")
                self.finished_task.emit(False)
                return

            # Common Step: Reset into Bootloader
            strategy = self.config.get('dtr_rts_strategy', 0)
            self.loader.reset_into_bootloader(strategy)
            
            # Common Step: Connect
            if not self.loader.connect_to_device():
                self.log_message.emit("Failed to connect to device.")
                # Restore 8N1 before exiting
                self.serial_manager.disconnect()
                self.serial_manager.connect(port, baud, parity=serial.PARITY_NONE)
                self.finished_task.emit(False)
                return
            
            success = False
            
            if self.task_type == self.TASK_PROGRAM:
                success = self.run_program_task()
            elif self.task_type == self.TASK_READ_INFO:
                success = self.run_read_info_task()
            elif self.task_type == self.TASK_ERASE:
                success = self.run_erase_task()
            elif self.task_type == self.TASK_READ_FLASH:
                success = self.run_read_flash_task()
            
            if success:
                self.log_message.emit("Task completed successfully.")
            else:
                self.log_message.emit("Task failed.")
            
            # Restore 8N1
            self.serial_manager.disconnect()
            self.serial_manager.connect(port, baud, parity=serial.PARITY_NONE)
                
            self.finished_task.emit(success)

        except Exception as e:
            self.log_message.emit(f"Unexpected error: {str(e)}")
            import traceback
            self.log_message.emit(traceback.format_exc())
            self.finished_task.emit(False)

    def run_program_task(self):
        # 1. Parse File
        file_path = self.config.get('file_path')
        try:
            start_addr, data = FirmwareParser.parse(file_path)
            self.log_message.emit(f"File loaded. Size: {len(data)} bytes. Start Addr: 0x{start_addr:08X}")
        except Exception as e:
            self.log_message.emit(f"Error loading file: {str(e)}")
            return False

        # 2. Get ID
        chip_id = self.loader.get_id()
        if chip_id:
            self.log_message.emit(f"Chip ID detected: 0x{chip_id:04X}")
        
        # 3. Erase
        if not self.loader.erase_all():
            return False

        # 4. Write
        if not self.loader.write_memory(start_addr, data):
            return False

        # 5. Verify
        if self.config.get('verify', True):
            if not self.loader.verify_memory(start_addr, data):
                return False

        # 6. Run After
        if self.config.get('run_after', True):
            self.loader.go(start_addr)
            self.reset_to_run_mode()

        return True

    def run_read_info_task(self):
        chip_id = self.loader.get_id()
        if chip_id:
            self.log_message.emit(f"Chip ID: 0x{chip_id:04X}")
            # Could add more info reading like bootloader version, etc.
            return True
        return False

    def run_erase_task(self):
        return self.loader.erase_all()

    def run_read_flash_task(self):
        self.log_message.emit("Read Flash not implemented yet.")
        return True

    def reset_to_run_mode(self):
        self.log_message.emit("Resetting to Run mode...")
        # Strategy 0: RTS=High(False) for Boot0=1. We want Boot0=0 (Low, RTS=True).
        # And toggle DTR (Reset).
        self.serial_manager.set_rts(True) # Boot0 = 0 (Low)
        self.serial_manager.set_dtr(True) # Reset Low
        time.sleep(0.1)
        self.serial_manager.set_dtr(False) # Reset High
