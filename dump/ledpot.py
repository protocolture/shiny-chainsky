from PiicoDev_Potentiometer import PiicoDev_Potentiometer
from PiicoDev_RGB import PiicoDev_RGB, wheel
from PiicoDev_Unified import sleep_ms

# Initialise modules (auto address detection)
pot = PiicoDev_Potentiometer()
leds = PiicoDev_RGB()

while True:
    val = pot.value  # 0.0 to 100.0
    hue = int(val / 100 * 255)
    color = wheel(hue)

    for i in range(3):
        leds.setPixel(i, color)
    leds.show()

    print(f"Potentiometer: {val:.2f} → Hue: {hue}")
    sleep_ms(50)
