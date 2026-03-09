# PyFlyMcu - STM32 ISP 烧录工具

一个基于PySide6开发的STM32系列单片机ISP（In-System Programming）烧录工具。

## 功能特性

- 串口自动搜索与连接
- 支持 .bin 和 .hex 固件文件解析
- 多种DTR/RTS复位策略
- Flash擦除、写入、校验
- 编程后自动运行
- 实时日志输出
- 进度条显示

## 环境要求

- Python 3.8+
- Windows/Linux/MacOS

## 依赖安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 项目结构

```
Upper Computer/
├── core/                    # 核心功能模块
│   ├── firmware_parser.py  # 固件文件解析器
│   ├── isp_loader.py       # ISP协议实现
│   ├── isp_worker.py       # 后台工作线程
│   └── serial_manager.py  # 串口管理
├── ui/                     # UI界面
│   ├── main_window.py      # 主窗口
│   └── option_bytes_dialog.py  # 选项字节对话框
├── main.py                 # 程序入口
└── requirements.txt        # 依赖列表
```

## 使用说明

1. **连接设备**：选择串口和波特率，点击"打开串口"
2. **选择固件**：点击"..."按钮选择 .bin 或 .hex 文件
3. **配置选项**：
   - 选择DTR/RTS复位策略
   - 设置是否校验、是否编程后执行
4. **开始编程**：点击"开始编程(P)"按钮

### DTR/RTS复位策略说明

| 策略 | 说明 |
|------|------|
| 策略0 | DTR低电平复位，RTS高电平进BootLoader |
| 策略1 | DTR低电平复位，RTS低电平进BootLoader |
| 策略2 | RTS低电平复位，DTR高电平进BootLoader |
| 策略3 | RTS低电平复位，DTR低电平进BootLoader |
| 策略4 | 手动复位 |

## 技术细节

### 支持的芯片

本工具基于STM32标准ISP协议开发，理论上支持所有支持串口烧录的STM32芯片。

### ISP协议命令

- `0x7F` - 初始化通信
- `0x02` - 获取芯片ID
- `0x11` - 读取内存
- `0x21` - 跳转到指定地址
- `0x31` - 写入内存
- `0x43/0x44` - 擦除Flash
- `0x82` - 读保护
- `0x92` - 读解除保护

### 波特率支持

9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600

## 许可证

MIT License
