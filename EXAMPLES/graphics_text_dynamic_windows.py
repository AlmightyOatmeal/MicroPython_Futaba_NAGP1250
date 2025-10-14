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

# Text to be used at the top
text = "Fancy Box"
# How far the top text should be indented from the left
left_indent = 14

# Create blank bitmap
width = 140
height = 32
bitmap = [[0 for _ in range(width)] for _ in range(height)]

# Assigning starting positions to variables for readability
start_x = 0
start_y = 0
# Assigning directions to variables for readability
hor_l_to_r = 0
vert_t_to_b = 270

# Text is 5x7 so 5*L
empty_width = (len(text) * 7) + 4

vfd.set_cursor_position(x=0, y=0)

# (x, y, angle_deg, length)
bitmap = vfd.draw_graphic_lines(bitmap=bitmap, lines=[
    # Outer
    (start_x, start_y, hor_l_to_r, left_indent),                                                     # Top left horizontal
    (left_indent + empty_width + 1, hor_l_to_r, hor_l_to_r, width - 1 - empty_width - left_indent),  # Top right horizontal
    (start_x, 1, vert_t_to_b, height - 2),                                                           # Left vertical
    (width - 1, hor_l_to_r, vert_t_to_b, height),                                                    # Right vertical
    (start_x, height - 1, hor_l_to_r, width),                                                        # Bottom horizontal

    # Inner 1
    (start_x + 2, start_y + 2, hor_l_to_r, left_indent - 2),                                          # Top left horizontal
    (left_indent + empty_width + 1, start_y + 2, hor_l_to_r, width - 3 - empty_width - left_indent),  # Top right horizontal
    (start_x + 2, start_y + 2, vert_t_to_b, height - 6),                                              # Left vertical
    (width - 3, start_y + 2, vert_t_to_b, height - 4),                                                # Right vertical
    (start_x + 2, height - 3, hor_l_to_r, width - 4),                                                 # Bottom horizontal

    # Inner 2
    (start_x + 4, start_y + 4, hor_l_to_r, left_indent - 4),                                          # Top left horizontal
    (left_indent + empty_width + 1, start_y + 4, hor_l_to_r, width - 5 - empty_width - left_indent),  # Top right horizontal
    (start_x + 4, start_y + 4, vert_t_to_b, height - 9),                                              # Left vertical
    (width - 5, start_y + 4, vert_t_to_b, height - 8),                                                # Right vertical
    (start_x + 4, height - 5, hor_l_to_r, width - 8),                                                 # Bottom horizontal

    # Inner 3
    (start_x + 6, start_x + 6, hor_l_to_r, left_indent - 6),                                          # Top left horizontal
    (left_indent + empty_width + 1, start_y + 6, hor_l_to_r, width - 7 - empty_width - left_indent),  # Top right horizontal
    (start_x + 6, start_y + 6, vert_t_to_b, height - 13),                                             # Left vertical
    (width - 7, start_y + 6, vert_t_to_b, height - 12),                                               # Right vertical
    (start_x + 6, height - 7, hor_l_to_r, width - 12),                                                # Bottom horizontal

    (left_indent, start_y, vert_t_to_b, 7),                    # Top left pipe
    (left_indent + empty_width + 1, start_y, vert_t_to_b, 7),  # Top right pipe
], width=width, height=height)

packed = vfd.pack_bitmap(bitmap=bitmap, width=width, height=height)
vfd.display_realtime_image(image_data=packed, width=width, height=height)

vfd.define_user_window(window_num=1, x=left_indent + 3, y=0, w=empty_width, h=1)
vfd.define_user_window(window_num=2, x=8, y=1, w=123, h=2)

# Move the cursor inside the vertical pipes, make sure there is a 2px buffer
vfd.do_select_window(window_num=1)
vfd.do_home()

vfd.write_text(text)

vfd.do_select_window(window_num=2)
vfd.do_home()

vfd.set_font_magnification(h=2, v=2)
vfd.write_text("Enhanced")
