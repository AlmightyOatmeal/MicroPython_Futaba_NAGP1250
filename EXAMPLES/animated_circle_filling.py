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

# Step degrees
step_deg = 5

# Center point for radial elements
cx = 70
cy = 12

# Create blank bitmap
width = 140
height = 32
bitmap = [[0 for _ in range(width)] for _ in range(height)]

angle = 0
while True:
    # Draw rotating line
    bitmap = vfd.draw_graphic_lines(bitmap=bitmap, lines=[(cx, cy, angle, 10)], width=width, height=height)

    # Pack the bitmap and get it ready for display
    packed = vfd.pack_bitmap(bitmap=bitmap, width=width, height=height)

    # Send the packed bitmap data to the display
    vfd.display_graphic_image(image_data=packed, width=width, height=height)

    # Advance angle
    angle = (angle + step_deg) % 360

    # Break the loop
    if angle == 355:
        break
