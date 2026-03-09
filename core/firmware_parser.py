import os

class FirmwareParser:
    @staticmethod
    def parse(file_path):
        """
        Parses .bin or .hex files.
        Returns: (start_address, data_bytes)
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.bin':
            with open(file_path, 'rb') as f:
                data = f.read()
            # Default start address for STM32 Flash is usually 0x08000000
            return 0x08000000, data
            
        elif ext == '.hex':
            # Simple Intel Hex parser
            data_map = {} # addr -> byte
            min_addr = 0xFFFFFFFF
            max_addr = 0
            
            with open(file_path, 'r') as f:
                base_addr = 0
                for line in f:
                    line = line.strip()
                    if not line.startswith(':'): continue
                    
                    byte_count = int(line[1:3], 16)
                    addr_offset = int(line[3:7], 16)
                    record_type = int(line[7:9], 16)
                    data_str = line[9:9+2*byte_count]
                    # checksum = line[9+2*byte_count:]
                    
                    if record_type == 0: # Data
                        addr = base_addr + addr_offset
                        for i in range(byte_count):
                            byte = int(data_str[i*2:i*2+2], 16)
                            data_map[addr + i] = byte
                            if addr + i < min_addr: min_addr = addr + i
                            if addr + i > max_addr: max_addr = addr + i
                            
                    elif record_type == 1: # EOF
                        break
                    elif record_type == 2: # Extended Segment Address
                        base_addr = int(data_str, 16) * 16
                    elif record_type == 4: # Extended Linear Address
                        base_addr = int(data_str, 16) * 65536
            
            if not data_map:
                return 0, b''
                
            # Convert map to contiguous bytes (filling gaps with 0xFF)
            size = max_addr - min_addr + 1
            data = bytearray([0xFF] * size)
            for addr, byte in data_map.items():
                data[addr - min_addr] = byte
                
            return min_addr, data
            
        else:
            raise ValueError("Unsupported file format")
