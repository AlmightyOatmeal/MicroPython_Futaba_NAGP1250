from machine import SPI
from futaba import NAGP1250
from futaba.NAGP1250 import WRITE_MODE_OR

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

# Set the logic mode to merge images
vfd.set_write_logic(mode=WRITE_MODE_OR)

# Remember to set your cursor position so the display knows where to start drawing.
vfd.set_cursor_position(x=0, y=0)

# (x, y, angle_deg, length)
# Tuples
bitmap = vfd.draw_graphic_lines(bitmap=bitmap, lines=[
    (70, 16, 0, 30),  # Horizontal right
    (70, 16, 90, 15),  # Up
    (70, 16, 180, 30),  # Left
    (70, 16, 270, 15),  # Down
    (70, 16, 45, 20),  # Diagonal up-right
    (70, 16, 135, 20),  # Diagonal up-left
    (70, 16, 315, 20),  # Diagonal down-right
    (70, 16, 225, 20)  # Diagonal down-left
], width=width, height=height)

# (x, y, angle_deg, length)
# Lists
bitmap = vfd.draw_graphic_lines(bitmap=bitmap, lines=[
    [35, 16, 0, 30],  # Horizontal right
    [35, 16, 90, 15],  # Up
    [35, 16, 180, 30],  # Left
    [35, 16, 270, 15],  # Down
    [35, 16, 45, 20],  # Diagonal up-right
    [35, 16, 135, 20],  # Diagonal up-left
    [35, 16, 315, 20],  # Diagonal down-right
    [35, 16, 225, 20]  # Diagonal down-left
], width=width, height=height)

packed = vfd.pack_bitmap(bitmap=bitmap, width=width, height=height)
vfd.display_realtime_image(image_data=packed, width=width, height=height)
