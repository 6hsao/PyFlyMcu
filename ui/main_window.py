import sys
import serial.tools.list_ports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QComboBox, QPushButton, QTextEdit, QFileDialog, 
                               QGroupBox, QMessageBox, QTabWidget, QCheckBox, QSplitter, QFrame, QProgressBar)
from PySide6.QtCore import Qt, QTimer
from core.serial_manager import SerialManager

from ui.option_bytes_dialog import OptionBytesDialog
from core.isp_worker import IspWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyFlyMcu - STM32 ISP Tool")
        self.resize(800, 600)
        
        self.option_bytes = {} # Store settings
        self.worker = None # Worker thread
        
        self.serial_manager = SerialManager()
        self.serial_manager.connected.connect(self.on_connected)
        self.serial_manager.error_occurred.connect(self.log_error)

        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # --- 1. Top Control Bar (Port, Baud, etc.) ---
        top_bar_layout = QHBoxLayout()
        
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(200)
        
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
        self.baud_combo.setCurrentText("115200")
        
        self.refresh_btn = QPushButton("搜索串口")
        self.refresh_btn.clicked.connect(self.refresh_ports)

        self.connect_btn = QPushButton("打开串口") # Connect button acts like "Open Port"
        self.connect_btn.clicked.connect(self.toggle_connection)

        top_bar_layout.addWidget(QLabel("Port:"))
        top_bar_layout.addWidget(self.port_combo)
        top_bar_layout.addWidget(QLabel("Bps:"))
        top_bar_layout.addWidget(self.baud_combo)
        top_bar_layout.addWidget(self.refresh_btn)
        top_bar_layout.addWidget(self.connect_btn)
        top_bar_layout.addStretch()
        
        main_layout.addLayout(top_bar_layout)

        # --- 2. File Selection Area ---
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("程序文件:"))
        
        self.file_path_edit = QTextEdit()
        self.file_path_edit.setFixedHeight(28)
        self.file_path_edit.setReadOnly(True)
        
        self.select_file_btn = QPushButton("...")
        self.select_file_btn.setFixedWidth(30)
        self.select_file_btn.clicked.connect(self.select_file)
        
        self.reload_file_check = QCheckBox("编程前重装文件")
        self.reload_file_check.setChecked(True)

        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(self.select_file_btn)
        file_layout.addWidget(self.reload_file_check)
        
        main_layout.addLayout(file_layout)

        # --- 3. Central Area (Tabs + Log) ---
        # Using a splitter or just HBox for flexibility
        central_split_layout = QHBoxLayout()
        
        # Left: Tabs for specific ISP controls
        self.tabs = QTabWidget()
        self.setup_stmisp_tab()
        self.tabs.addTab(self.stmisp_tab, "STMISP")
        self.tabs.addTab(QWidget(), "手持万用编程器") # Placeholder
        self.tabs.addTab(QWidget(), "免费STMIAP") # Placeholder
        
        # Right: Log Output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        
        # Adjust proportions (Left ~40%, Right ~60%)
        central_split_layout.addWidget(self.tabs, 2)
        central_split_layout.addWidget(self.log_output, 3)
        
        main_layout.addLayout(central_split_layout)

        # --- 4. Bottom Control (DTR/RTS) ---
        bottom_layout = QHBoxLayout()
        self.dtr_rts_combo = QComboBox()
        self.dtr_rts_combo.addItems([
            "DTR的低电平复位,RTS高电平进BootLoader",
            "DTR的低电平复位,RTS低电平进BootLoader",
            "RTS的低电平复位,DTR高电平进BootLoader",
            "RTS的低电平复位,DTR低电平进BootLoader",
            "不使用DTR/RTS控制"
        ])
        bottom_layout.addWidget(self.dtr_rts_combo)
        main_layout.addLayout(bottom_layout)

        self.refresh_ports()
        self.log("Application started. Ready.")

    def setup_stmisp_tab(self):
        self.stmisp_tab = QWidget()
        layout = QVBoxLayout(self.stmisp_tab)
        
        # Start Programming Button
        self.start_btn = QPushButton("开始编程(P)")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setEnabled(False) # Enabled when file selected & port open
        self.start_btn.clicked.connect(self.start_programming)
        layout.addWidget(self.start_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Checkboxes
        check_layout = QVBoxLayout()
        self.verify_check = QCheckBox("校验")
        self.verify_check.setChecked(True)
        self.run_after_check = QCheckBox("编程后执行")
        self.run_after_check.setChecked(True)
        self.ram_isp_check = QCheckBox("使用RamIsp")
        
        check_layout.addWidget(self.verify_check)
        check_layout.addWidget(self.run_after_check)
        check_layout.addWidget(self.ram_isp_check)
        layout.addLayout(check_layout)
        
        # Action Buttons
        btn_grid = QHBoxLayout()
        self.read_info_btn = QPushButton("读器件信息(R)")
        self.read_info_btn.clicked.connect(self.read_chip_info)
        self.erase_btn = QPushButton("清除芯片(Z)")
        self.erase_btn.clicked.connect(self.erase_chip)
        self.read_flash_btn = QPushButton("读FLASH")
        self.read_flash_btn.clicked.connect(self.read_flash)
        
        btn_grid.addWidget(self.read_info_btn)
        btn_grid.addWidget(self.erase_btn)
        btn_grid.addWidget(self.read_flash_btn)
        layout.addLayout(btn_grid)
        
        # Option Bytes Group
        opt_group = QGroupBox("选项字节区")
        opt_layout = QVBoxLayout()
        self.write_opt_check = QCheckBox("编程到FLASH时写选项字节")
        self.set_opt_btn = QPushButton("设定选项字节等")
        self.set_opt_btn.clicked.connect(self.open_option_bytes_dialog)
        opt_layout.addWidget(self.write_opt_check)
        opt_layout.addWidget(self.set_opt_btn)
        opt_group.setLayout(opt_layout)
        layout.addWidget(opt_group)
        
        layout.addStretch()

    def log(self, message):
        self.log_output.append(message)
        # Scroll to bottom
        sb = self.log_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def log_error(self, message):
        self.log(f"Error: {message}")

    def select_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Firmware File", "", "Binary/Hex Files (*.bin *.hex);;All Files (*)")
        if file_name:
            self.file_path_edit.setText(file_name)
            self.log(f"Selected file: {file_name}")
            self.check_ready_to_program()

    def refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device}", port.device) # Simplied display
        self.log(f"Found {len(ports)} ports.")

    def toggle_connection(self):
        if self.connect_btn.text() == "打开串口":
            port = self.port_combo.currentData()
            if not port:
                self.log("No port selected.")
                return
            baud = int(self.baud_combo.currentText())
            if self.serial_manager.connect(port, baud):
                self.connect_btn.setText("关闭串口")
                self.port_combo.setEnabled(False)
                self.baud_combo.setEnabled(False)
                self.refresh_btn.setEnabled(False)
                self.log(f"Connected to {port} at {baud} baud.")
                self.check_ready_to_program()
        else:
            self.serial_manager.disconnect()
            self.connect_btn.setText("打开串口")
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.log("Disconnected.")
            self.start_btn.setEnabled(False)

    def on_connected(self, connected):
        pass

    def check_ready_to_program(self):
        # Program button depends on: Connected + File Selected
        is_connected = (self.connect_btn.text() == "关闭串口")
        has_file = bool(self.file_path_edit.toPlainText())
        self.start_btn.setEnabled(is_connected and has_file)
        
        # Other buttons depend on: Connected
        self.read_info_btn.setEnabled(is_connected)
        self.erase_btn.setEnabled(is_connected)
        self.read_flash_btn.setEnabled(is_connected)

    def open_option_bytes_dialog(self):
        dlg = OptionBytesDialog(self)
        dlg.applied.connect(self.save_option_bytes)
        dlg.exec()

    def save_option_bytes(self, settings):
        self.option_bytes = settings
        self.log(f"Option Bytes Configured: {settings}")

    def start_task(self, task_type):
        if self.worker and self.worker.isRunning():
            return

        port = self.port_combo.currentData()
        if not port:
            self.log("Error: No port selected.")
            return

        # Check file only for programming task
        file_path = self.file_path_edit.toPlainText()
        if task_type == IspWorker.TASK_PROGRAM and not file_path:
            self.log("Error: No file selected.")
            return

        # Gather configuration
        config = {
            'port': port,
            'baud': int(self.baud_combo.currentText()),
            'file_path': file_path,
            'dtr_rts_strategy': self.dtr_rts_combo.currentIndex(),
            'verify': self.verify_check.isChecked(),
            'run_after': self.run_after_check.isChecked(),
            'option_bytes': self.option_bytes if self.write_opt_check.isChecked() else None
        }

        self.log(f"Starting {task_type}...")
        self.set_ui_enabled(False)

        # Create and start worker
        self.worker = IspWorker(self.serial_manager, config, task_type)
        self.worker.log_message.connect(self.log)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.finished_task.connect(self.on_programming_finished)
        self.worker.start()

    def start_programming(self):
        self.start_task(IspWorker.TASK_PROGRAM)

    def read_chip_info(self):
        self.start_task(IspWorker.TASK_READ_INFO)

    def erase_chip(self):
        self.start_task(IspWorker.TASK_ERASE)

    def read_flash(self):
        self.start_task(IspWorker.TASK_READ_FLASH)


    def set_ui_enabled(self, enabled):
        self.connect_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
        self.select_file_btn.setEnabled(enabled)
        self.read_info_btn.setEnabled(enabled)
        self.erase_btn.setEnabled(enabled)
        self.read_flash_btn.setEnabled(enabled)
        
        if enabled:
            self.check_ready_to_program()
        else:
            self.start_btn.setEnabled(False)
        # self.tabs.setEnabled(enabled)

    def on_programming_finished(self, success):
        self.set_ui_enabled(True)
        if success:
            self.log("Task process completed successfully.")
            QMessageBox.information(self, "Success", "Task completed successfully!")
        else:
            self.log("Task process failed.")
            # Don't show modal popup on failure to avoid annoyance, just log
            # QMessageBox.warning(self, "Failed", "Task failed. Check log for details.")

    def update_progress(self, value):
        self.progress_bar.setValue(value)
