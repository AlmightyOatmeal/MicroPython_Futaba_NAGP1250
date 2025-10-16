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

# Number of radial elements
count = 30
# Length of radial elements
length = 100
# Center point for radial elements
lx = 70
ly = 16

# Create blank bitmap
width = 140
height = 32
bitmap = [[0 for _ in range(width)] for _ in range(height)]

# Compute angle step (e.g. 360° / 12 = 30° per line)
step = 360 / count

# Draw each radial line and update the bitmap
for i in range(count):
    angle = i * step
    bitmap = vfd.draw_graphic_lines(bitmap=bitmap, lines=[(lx, ly, angle, length)], width=width, height=height)

    packed = vfd.pack_bitmap(bitmap=bitmap, width=width, height=height)
    vfd.display_graphic_image(image_data=packed, width=width, height=height)
