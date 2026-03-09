from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QCheckBox, QGroupBox, 
                               QGridLayout, QWidget, QScrollArea)
from PySide6.QtCore import Qt, Signal

class OptionBytesDialog(QDialog):
    # Signal emitted when "Apply" is clicked, passing the dictionary of values
    applied = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Option Bytes Setting For STM32F -- www.mcuisp.com")
        self.resize(700, 500)
        
        main_layout = QVBoxLayout(self)
        
        # --- 1. Read Protection (RDP) ---
        rdp_group = QGroupBox("读保护字节:")
        rdp_layout = QHBoxLayout()
        rdp_layout.addWidget(QLabel("值:"))
        self.rdp_edit = QLineEdit("A5")
        self.rdp_edit.setFixedWidth(50)
        self.rdp_edit.setAlignment(Qt.AlignCenter)
        self.rdp_a5_btn = QPushButton("设成A5,允许读出")
        self.rdp_ff_btn = QPushButton("设成FF,阻止读出")
        
        self.rdp_desc = QLabel("当RDP值等于0xA5时，允许读出Flash存储器内容。\n任何其它的值阻止Flash内的内容被读出，并阻止对Flash前4K字节的擦写操作。")
        self.rdp_desc.setWordWrap(True)
        
        rdp_layout.addWidget(self.rdp_edit)
        rdp_layout.addWidget(self.rdp_a5_btn)
        rdp_layout.addWidget(self.rdp_ff_btn)
        
        rdp_wrapper = QVBoxLayout()
        rdp_wrapper.addLayout(rdp_layout)
        rdp_wrapper.addWidget(self.rdp_desc)
        rdp_group.setLayout(rdp_wrapper)
        main_layout.addWidget(rdp_group)
        
        # --- 2. Hardware Option Byte ---
        hw_group = QGroupBox("硬件选项字节:")
        hw_layout = QVBoxLayout()
        
        hw_top = QHBoxLayout()
        hw_top.addWidget(QLabel("值:"))
        self.hw_edit = QLineEdit("FF")
        self.hw_edit.setFixedWidth(50)
        self.hw_edit.setAlignment(Qt.AlignCenter)
        self.hw_ff_btn = QPushButton("设成FF(缺省值)")
        hw_top.addWidget(self.hw_edit)
        hw_top.addWidget(self.hw_ff_btn)
        hw_top.addStretch()
        hw_layout.addLayout(hw_top)
        
        self.hw_checks = []
        hw_grid = QGridLayout()
        # Bit0=1: WDG_SW (Software Watchdog) - Checked means Hardware Watchdog? No, usually 1=Software
        # FlyMcu says: "Bit0=1: 软狗(WDG须程序启动)"
        # Let's map bits to checkboxes.
        # Screenshot shows:
        # [ ] Bit0=1: 软狗(WDG须程序启动)
        # [ ] Bit1=1: 进入STOP模式时不产生复位
        # [ ] Bit2=1: 进入Standby模式时不产生复位
        # [ ] Bit3=1  [ ] Bit4=1 ...
        
        # Note: If checkbox is CHECKED, it usually means the bit is 1? 
        # But wait, default is FF (all 1s). The screenshot shows UNCHECKED boxes for FF.
        # This implies UNCHECKED = 1, CHECKED = 0?
        # Let's re-examine. If "Bit0=1: Soft WDG", and default is FF (11111111), then default is Soft WDG.
        # If I want Hardware WDG (Bit0=0), I should probably change the state.
        # Let's assume: Checkbox text says "BitX=1 ...". 
        # So if I check it, does it mean I force it to 1? Or does it mean the condition for 1 is active?
        # In FlyMcu screenshot: Value is FF. Checkboxes are unchecked.
        # This is confusing. If Value is FF, Bit0 is 1. If checkbox is unchecked, and it represents "Bit0=1", maybe it means "Unchecked = Default(1)"?
        # Or maybe the label is just descriptive: "Bit0=1 means Soft WDG".
        # Let's assume standard logic: Checkbox ON = Bit 0 (Active/Protected/Enabled feature that requires 0).
        # OR Checkbox ON = Bit 1.
        # Let's try to infer from a common tool behavior.
        # In STM32 ST-LINK Utility:
        # WDG_SW: Checked = Hardware Watchdog (0), Unchecked = Software Watchdog (1).
        # nRST_STOP: Checked = Reset generated (0), Unchecked = No reset (1).
        # FlyMcu labels are "Bit0=1: Soft WDG".
        # If Value FF -> Bit0=1 -> Soft WDG.
        # If checkbox is unchecked and value is FF, then Unchecked must mean 1?
        # Let's implement logic: Update Hex based on Checkboxes.
        # If I check "Bit0=1...", I probably want that feature.
        # But wait, "Bit0=1" is the feature description.
        # If I check it, I want Bit0=1.
        # If Value is FF, Bit0 is 1. So Checkbox should be CHECKED if it follows "Checked=1".
        # But screenshot shows FF and UNCHECKED.
        # This implies Checkbox means "Bit=0"?
        # Or maybe "Unchecked" simply means "Default state not modified" or "Feature disabled"?
        # Let's look at "Bit0=1: 软狗". If I want "Hard Dog (Bit0=0)", I should probably toggle it.
        # Let's implement generic bit toggles and see.
        # Actually, let's follow the screenshot labels literally.
        # "Bit0=1: ..."
        # If I click it, I toggle the bit.
        # Let's assume Checkbox State correlates to Bit Value 0. (Checked = 0).
        # Why? Because in Flash protection, 0 is Protected.
        # Let's stick to: Checkbox Checked = Bit 0. Unchecked = Bit 1.
        # Let's verify with RDP. RDP A5 is 10100101.
        # RDP FF is 11111111.
        # Let's look at WRP. WRP FF means no protection (all 1s). Checkboxes are unchecked.
        # So Unchecked = 1. Checked = 0.
        # This seems consistent.
        
        self.hw_labels = [
            "Bit0=1: 软狗(WDG须程序启动)",
            "Bit1=1: 进入STOP模式时不产生复位",
            "Bit2=1: 进入Standby模式时不产生复位",
            "Bit3=1", "Bit4=1", "Bit5=1", "Bit6=1", "Bit7=1"
        ]
        
        row, col = 0, 0
        for i, label in enumerate(self.hw_labels):
            cb = QCheckBox(label)
            # Default FF means all 1s. If Unchecked=1, then init unchecked.
            cb.setChecked(False) 
            cb.stateChanged.connect(self.update_hw_hex)
            self.hw_checks.append(cb)
            hw_grid.addWidget(cb, row, col)
            col += 1
            if col > 3: # 4 cols
                col = 0
                row += 1
        
        hw_grid.addWidget(QLabel("这5位,用户应该大概也许可以使用"), 0, 4, 2, 1) # Mimic the text
        hw_layout.addLayout(hw_grid)
        hw_group.setLayout(hw_layout)
        main_layout.addWidget(hw_group)

        # --- 3. User Data Bytes ---
        user_group = QGroupBox("用户数据字节:")
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("Data0(0x1FFFF804):"))
        self.user_data0 = QLineEdit("FF")
        self.user_data0.setFixedWidth(40)
        self.user_data0.setAlignment(Qt.AlignCenter)
        user_layout.addWidget(self.user_data0)
        
        user_layout.addWidget(QLabel("Data1(0x1FFFF806):"))
        self.user_data1 = QLineEdit("FF")
        self.user_data1.setFixedWidth(40)
        self.user_data1.setAlignment(Qt.AlignCenter)
        user_layout.addWidget(self.user_data1)
        
        user_layout.addWidget(QLabel("这两字节用户可自由使用"))
        user_layout.addStretch()
        user_group.setLayout(user_layout)
        main_layout.addWidget(user_group)
        
        # --- 4. Write Protection (WRP) ---
        wrp_group = QGroupBox("写保护字节:")
        wrp_layout = QVBoxLayout()
        
        self.wrp_rows = [] # Stores (LineEdit, [CheckBoxes])
        
        # WRP0 covers pages 0-31 (approx, depends on device). 
        # Screenshot shows WRP0: 0-3, 4-7, ... 28-31.
        # Each bit protects 4 pages?
        # Bit 0: Pages 0-3
        # Bit 1: Pages 4-7
        # ...
        # Bit 7: Pages 28-31
        
        # Labels for each bit in WRP0, WRP1, WRP2, WRP3
        wrp_labels_map = [
            ["0-3", "4-7", "8-11", "12-15", "16-19", "20-23", "24-27", "28-31"],
            ["32-35", "36-39", "40-43", "44-47", "48-51", "52-55", "56-59", "60-63"],
            ["64-67", "68-71", "72-75", "76-79", "80-83", "84-87", "88-91", "92-95"],
            ["96-99", "100-103", "104-107", "108-111", "112-115", "116-119", "120-123", "124-511"]
        ]
        
        for i in range(4):
            row_layout = QHBoxLayout()
            row_layout.addWidget(QLabel(f"WRP{i}:"))
            edit = QLineEdit("FF")
            edit.setFixedWidth(40)
            edit.setAlignment(Qt.AlignCenter)
            row_layout.addWidget(edit)
            
            checks = []
            for j in range(8):
                cb = QCheckBox(wrp_labels_map[i][j])
                cb.setChecked(False) # Default FF -> Unchecked (1)
                # Use a closure to capture i
                cb.stateChanged.connect(lambda state, idx=i: self.update_wrp_hex(idx))
                row_layout.addWidget(cb)
                checks.append(cb)
            
            self.wrp_rows.append((edit, checks))
            wrp_layout.addLayout(row_layout)
            
            # Connect edit to update checkboxes
            edit.editingFinished.connect(lambda idx=i: self.update_wrp_checks(idx))

        wrp_group.setLayout(wrp_layout)
        main_layout.addWidget(wrp_group)
        
        # --- 5. Bottom Buttons ---
        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("采用这个设置")
        self.cancel_btn = QPushButton("放弃此次设置")
        self.factory_btn = QPushButton("恢复出厂缺省值")
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.factory_btn)
        btn_layout.addStretch()
        
        main_layout.addLayout(btn_layout)

        # --- Connections ---
        self.rdp_a5_btn.clicked.connect(lambda: self.rdp_edit.setText("A5"))
        self.rdp_ff_btn.clicked.connect(lambda: self.rdp_edit.setText("FF"))
        self.hw_ff_btn.clicked.connect(lambda: self.set_hw_hex("FF"))
        self.hw_edit.editingFinished.connect(self.update_hw_checks)
        
        self.factory_btn.clicked.connect(self.restore_defaults)
        self.cancel_btn.clicked.connect(self.reject)
        self.apply_btn.clicked.connect(self.apply_settings)

    def set_hw_hex(self, value_str):
        self.hw_edit.setText(value_str)
        self.update_hw_checks()

    def update_hw_hex(self):
        # Checkboxes -> Hex
        # Checked = 0, Unchecked = 1
        val = 0
        for i, cb in enumerate(self.hw_checks):
            if not cb.isChecked():
                val |= (1 << i)
        self.hw_edit.setText(f"{val:02X}")

    def update_hw_checks(self):
        # Hex -> Checkboxes
        try:
            val = int(self.hw_edit.text(), 16)
            for i, cb in enumerate(self.hw_checks):
                # If bit is 1, Unchecked. If bit is 0, Checked.
                is_set = (val >> i) & 1
                cb.blockSignals(True)
                cb.setChecked(not is_set)
                cb.blockSignals(False)
        except ValueError:
            pass

    def update_wrp_hex(self, row_idx):
        # Checkboxes -> Hex for a specific row
        val = 0
        _, checks = self.wrp_rows[row_idx]
        for i, cb in enumerate(checks):
            if not cb.isChecked():
                val |= (1 << i)
        edit, _ = self.wrp_rows[row_idx]
        edit.setText(f"{val:02X}")

    def update_wrp_checks(self, row_idx):
        # Hex -> Checkboxes for a specific row
        edit, checks = self.wrp_rows[row_idx]
        try:
            val = int(edit.text(), 16)
            for i, cb in enumerate(checks):
                is_set = (val >> i) & 1
                cb.blockSignals(True)
                cb.setChecked(not is_set)
                cb.blockSignals(False)
        except ValueError:
            pass

    def restore_defaults(self):
        self.rdp_edit.setText("A5")
        self.set_hw_hex("FF")
        self.user_data0.setText("FF")
        self.user_data1.setText("FF")
        for i in range(4):
            self.wrp_rows[i][0].setText("FF")
            self.update_wrp_checks(i)

    def apply_settings(self):
        settings = {
            "RDP": self.rdp_edit.text(),
            "HW": self.hw_edit.text(),
            "Data0": self.user_data0.text(),
            "Data1": self.user_data1.text(),
            "WRP0": self.wrp_rows[0][0].text(),
            "WRP1": self.wrp_rows[1][0].text(),
            "WRP2": self.wrp_rows[2][0].text(),
            "WRP3": self.wrp_rows[3][0].text(),
        }
        self.applied.emit(settings)
        self.accept()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    dlg = OptionBytesDialog()
    dlg.show()
    sys.exit(app.exec())
