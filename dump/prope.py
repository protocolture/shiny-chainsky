import smbus2

bus = smbus2.SMBus(1)
address = 0x08

try:
    for reg in range(0x00, 0x10):
        val = bus.read_byte_data(address, reg)
        print(f"Register 0x{reg:02X}: 0x{val:02X}")
except Exception as e:
    print("Error:", e)
