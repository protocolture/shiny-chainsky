import smbus2
import time

def sleep_ms(ms): time.sleep(ms / 1000)

def print_i2c_bus_scan(bus=1):
    print("Scanning I2C bus", bus)
    scan_bus = smbus2.SMBus(bus)
    for addr in range(0x03, 0x78):
        try:
            scan_bus.write_quick(addr)
            print(f"Device found at address 0x{addr:02X}")
        except:
            pass
    scan_bus.close()

# PiicoDev Potentiometer at address 0x35
class PiicoDev_Potentiometer:
    def __init__(self, address=0x35, bus=1):
        self.addr = address
        self.bus = smbus2.SMBus(bus)

    def read_raw(self):
        try:
            raw = self.bus.read_word_data(self.addr, 0x00)
            return ((raw & 0xFF) << 8) | ((raw >> 8) & 0xFF)
        except Exception as e:
            print(f"read_raw() error: {e}")
            return 0

    def read(self):
        return self.read_raw() / 1023

# Main
if __name__ == "__main__":
    pot = PiicoDev_Potentiometer()

    print("Scanning I2C bus...")
    print_i2c_bus_scan()

    try:
        while True:
            val = pot.read()
            print(f"Potentiometer: {val:.2f}")
            sleep_ms(200)

    except KeyboardInterrupt:
        print("Exited.")
