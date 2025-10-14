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

# Remember to set your cursor position so the display knows where to start drawing.
vfd.set_cursor_position(x=0, y=0)

bitmap = vfd.draw_graphic_lines(bitmap=bitmap, lines=[
    (3, 3, 0, 13),  # Top L horizontal
    (16, 0, 270, 7),  # Top L pipe
    (50, 0, 270, 7),  # Top R pipe
    (50, 3, 0, 86),  # Top R horizontal

    (3, 3, 270, 25),  # L vertical
    (136, 3, 270, 25),  # R vertical

    (3, 27, 0, 134)  # Bottom horizontal
], width=width, height=height)

packed = vfd.pack_bitmap(bitmap=bitmap, width=width, height=height)
vfd.display_realtime_image(image_data=packed, width=width, height=height)

# Move the cursor to the first row (0) and the 20th column, in the middle of the vertical pipes
vfd.set_cursor_position(x=20, y=0)

vfd.write_text("Boxy")
