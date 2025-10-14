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
    (3, 3, 0, 13),      # Top left horizontal
    (16, 0, 270, 7),    # Top left pipe
    (50, 0, 270, 7),    # Top right pipe
    (50, 3, 0, 86),     # Top right horizontal

    (3, 3, 270, 25),    # Left vertical
    (136, 3, 270, 25),  # Right vertical

    (3, 27, 0, 134)     # Bottom horizontal
], width=width, height=height)

packed = vfd.pack_bitmap(bitmap=bitmap, width=width, height=height)
vfd.display_realtime_image(image_data=packed, width=width, height=height)

# Move the cursor to the first row (0) and the 20th column, in the middle of the vertical pipes
vfd.set_cursor_position(x=20, y=0)

vfd.write_text("Boxy")

# Move the cursor to the second row (1) and the 6th column, the beginning of the open area
vfd.set_cursor_position(x=6, y=1)

# Set the font magnification to 2 rows and 2 columns
vfd.set_font_magnification(h=2, v=2)

vfd.write_text("Enhanced")
