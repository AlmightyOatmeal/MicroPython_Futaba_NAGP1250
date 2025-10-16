import random
from machine import SPI
from futaba import NAGP1250

# Tested on:
# - MicroPython v1.26.1; LOLIN_S2_MINI

def generate_block_bitmap(width: int = 140, height: int = 32, block_size: int = 1) -> list[list[int]]:
    """
    Generate a 2D bitmap representation of binary blocks.

    This function generates a bitmap where each "block" is composed of square grids (block_size x block_size) filled
    with either 1s or 0s. The size of the bitmap is defined by the width and height parameters, while the granularity
    of blocks is controlled by the block_size parameter.

    :param width: The total width of the resulting bitmap in pixels.
    :type width: int
    :param height: The total height of the resulting bitmap in pixels.
    :type height: int
    :param block_size: The size of each block in pixels. Possible values are 1, 2, or 4.
    :type block_size: int
    :return: A 2D list where each element represents a single pixel value (0 or 1).
    :raises ValueError: If block_size is not one of the valid options (1, 2, 4).
    """
    if block_size not in [1, 2, 4]:
        raise ValueError("block_size must be 1, 2 or 4")

    block_w = width // block_size
    block_h = height // block_size
    bitmap = []

    for _ in range(block_h):
        # Create block_size rows per block row
        block_rows = [[] for _ in range(block_size)]
        for _ in range(block_w):
            bit = random.getrandbits(1)
            # Fill block_size × block_size pixels with the same bit
            for row in block_rows:
                row.extend([bit] * block_size)
        bitmap.extend(block_rows)

    return bitmap


PIN_SIN = 33
PIN_SCK = 37
PIN_RESET = 39
PIN_SBUSY = 35

spi = SPI(2, mosi=PIN_SIN, sck=PIN_SCK, baudrate=115200)
vfd = NAGP1250(spi=spi, reset=PIN_RESET, sbusy=PIN_SBUSY)

width = 140
height = 32

block_size = 1
loop = 0
while True:
    # random_bytes = generate_block_bitmap(width=width, height=height, block_size=4)
    random_bytes = generate_block_bitmap(width=width, height=height, block_size=block_size)

    packed = vfd.pack_bitmap(bitmap=random_bytes, width=width, height=height)

    vfd.display_graphic_image(image_data=packed, width=width, height=height)

    if loop >= 5:
        loop = 0

        if block_size == 1:
            block_size = 2
        elif block_size == 2:
            block_size = 4
        else:
            block_size = 1

    loop += 1
