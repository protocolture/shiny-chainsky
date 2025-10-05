from PiicoDev_Potentiometer import PiicoDev_Potentiometer
from PiicoDev_RGB import PiicoDev_RGB
from PiicoDev_Unified import sleep_ms

# Initialize devices (auto address detection)
pot = PiicoDev_Potentiometer()
leds = PiicoDev_RGB()

# Define base color gradient (you can expand or reorder as needed)
colors = [
    [255, 0, 0],     # red
    [255, 255, 0],   # yellow
    [0, 255, 0],     # green
    [0, 255, 255],   # cyan
    [0, 0, 255],     # blue
    [255, 0, 255],   # magenta
    [255, 255, 255]  # white
]

# Interpolate between two colors
def blend(c1, c2, t):
    return [
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t)
    ]

while True:
    val = pot.value  # 0.0 to 100.0
    num_zones = len(colors) - 1
    scaled = val / 100 * num_zones
    index = int(scaled)
    t = scaled - index

    if index >= num_zones:
        color = colors[-1]
    else:
        color = blend(colors[index], colors[index + 1], t)

    for i in range(3):
        leds.setPixel(i, color)
    leds.show()

    print(f"Pot: {val:.2f} → color: {color}")
    sleep_ms(50)

