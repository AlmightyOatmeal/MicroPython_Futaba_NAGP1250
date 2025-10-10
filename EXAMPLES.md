<!-- TOC -->
* [More Futaba NAGP1250 Examples](#more-futaba-nagp1250-examples)
  * [Animated Graphics](#animated-graphics)
    * [Pixel Blocks](#pixel-blocks)
<!-- TOC -->

# More Futaba NAGP1250 Examples

## Animated Graphics

### Pixel Blocks

This is a painfully inefficient way to generate 1x1, 2x2, and 4x4 blocks, but it works and totally gives the W.O.P.R. vibes (from the movie War Games).

```python
import random
from futaba import NAGP1250


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


vfd = NAGP1250(sin=33, sck=37, reset=39, sbusy=35)

while True:
    random_bytes = generate_block_bitmap(width=width, height=height, block_size=4)

    packed = vfd.pack_bitmap(bitmap=random_bytes, width=width, height=height)

    vfd.display_realtime_image(image_data=packed, width=width, height=height)
```

![Display with graphic pixel blocks](_images/display_graphics_blocks.gif)

This is a much more efficient way of randomizing 1px blocks: 
```python
random_bytes = [[urandom.getrandbits(1) for _ in range(width)] for _ in range(height)]
```