from machine import SPI
from futaba import NAGP1250

# Tested on:
# - MicroPython v1.26.1; LOLIN_S2_MINI

PIN_SIN = 33
PIN_SCK = 37
PIN_RESET = 39
PIN_SBUSY = 35

spi = SPI(2, mosi=PIN_SIN, sck=PIN_SCK, baudrate=115200)
vfd = NAGP1250(spi=spi, reset=PIN_RESET, sbusy=PIN_SBUSY)

# Create blank bitmap
width = 140
height = 32
bitmap = [[0 for _ in range(width)] for _ in range(height)]

# (x, y, radius, filled[boolean])
bitmap = vfd.draw_graphic_circles(bitmap=bitmap, circles=[
    (10, 8, 2, False),    # S1
    (10, 16, 2, False),   # S2
    (10, 24, 2, False),   # S3
    (50, 20, 2, False),   # S4
    (90, 10, 2, False),   # S5
    (130, 3, 2, False),   # E1
    (130, 10, 2, False),  # E2
    (130, 18, 2, False),  # E3
    (130, 25, 2, False),  # E4
    (130, 25, 2, False),  # E4
], width=width, height=height)

# Use the first updated bitmap to add lines to

# (x, y, angle_deg, length)
bitmap = vfd.draw_graphic_lines(bitmap=bitmap, lines=[
    # S1
    (13, 8, 0, 20),
    (33, 8, 45, 8),
    (39, 3, 0, 90),

    # S4-S5
    (53, 20, 0, 15),
    (68, 20, 45, 15),
    (79, 10, 0, 10),

    # S4-S5-E3
    (93, 10, 0, 10),
    (103, 10, 315, 12),
    (112, 18, 0, 17),

    # S2-E2
    (13, 16, 0, 50),
    (63, 16, 45, 15),
    (73, 6, 0, 33),
    (105, 6, 315, 5),
    (109, 10, 0, 19),

    # S3-E4
    (13, 24, 0, 30),
    (43, 24, 315, 3),
    (45, 25, 0, 83),
], width=width, height=height)

packed = vfd.pack_bitmap(bitmap=bitmap, width=width, height=height)
vfd.display_realtime_image(image_data=packed, width=width, height=height)
