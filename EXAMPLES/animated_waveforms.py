from machine import SPI
import math
import time
from futaba import NAGP1250

# Tested on:
# - MicroPython v1.26.1; LOLIN_S2_MINI

PIN_SIN = 33
PIN_SCK = 37
PIN_RESET = 39
PIN_SBUSY = 35


class SineWaveBitmapGenerator:
    def __init__(self, width, height, frequency=2.0, amplitude=None, thickness=1):
        """
        Generates a sine wave waveform with incremental bitmaps that can be used to generate an animation.

        :param width: The width of the wave bitmap in pixels.
        :type width: int
        :param height: The height of the wave bitmap in pixels.
        :type height: int
        :param frequency: (optional) The frequency of the wave in cycles per unit width. (default: 2.0)
        :type frequency: float
        :param amplitude: (optional) The amplitude of the wave in pixels (defaults: (0.5 * height) - 1)
        :type amplitude: float
        :param thickness: (optional) The thickness of the wave line in pixels. (default: 1)
        :type thickness: int
        """
        self.width = width
        self.height = height
        self.frequency = frequency
        self.amplitude = amplitude if amplitude is not None else (height / 2 - 1)
        self.center_y = height // 2
        self.phase = 0.0
        self.phase_step = (2 * math.pi * frequency) / width  # advance by one pixel
        self.thickness = thickness

    # # Lines look a little weird
    def next_frame(self):
        bitmap = [[0 for _ in range(self.width)] for _ in range(self.height)]

        half = self.thickness // 2

        for x in range(self.width):
            # Use fractional phase to simulate continuous horizontal motion
            radians = self.phase + (x * 2 * math.pi * self.frequency / self.width)
            y_float = self.center_y + self.amplitude * math.sin(radians)

            # Use round to avoid truncation bias
            # y = round(y_float)
            # if 0 <= y < self.height:
            #     bitmap[y][x] = 1
            for i in range(-half, half + 1):
                y = round(y_float + i * 0.5)
                if 0 <= y < self.height:
                    bitmap[y][x] = 1

        # Advance phase by a small fraction to simulate smooth motion
        self.phase += 2 * math.pi * self.frequency / self.width
        return bitmap


class SquareWaveBitmapGenerator:
    def __init__(self, width, height, frequency=2.0, amplitude=None, thickness=1, duty_cycle=0.5):
        """
        Generates a square wave waveform with incremental bitmaps that can be used to generate an animation.

        :param width: The width of the wave bitmap in pixels.
        :type width: int
        :param height: The height of the wave bitmap in pixels.
        :type height: int
        :param frequency: (optional) The frequency of the wave in cycles per unit width. (default: 2.0)
        :type frequency: float
        :param amplitude: (optional) The amplitude of the wave in pixels (defaults: (0.5 * height) - 1)
        :type amplitude: float
        :param thickness: (optional) The thickness of the wave line in pixels. (default: 1)
        :type thickness: int
        :param duty_cycle: (optional) A value representing the active proportion of the wave cycle. (default: 0.5)
        :type duty_cycle: float
        """
        self.width = width
        self.height = height
        self.frequency = frequency
        self.amplitude = amplitude if amplitude is not None else (height / 2 - 1)
        self.center_y = height // 2
        self.phase = 0.0
        self.phase_step = (2 * math.pi * frequency) / width
        self.thickness = thickness
        self.duty_cycle = duty_cycle

    def next_frame(self):
        bitmap = [[0 for _ in range(self.width)] for _ in range(self.height)]
        half = self.thickness // 2

        prev_is_high = None

        for x in range(self.width):
            radians = self.phase + (x * 2 * math.pi * self.frequency / self.width)
            wave_pos = (radians % (2 * math.pi)) / (2 * math.pi)  # normalized cycle position

            is_high = wave_pos < self.duty_cycle
            y_base = self.center_y - self.amplitude if is_high else self.center_y + self.amplitude

            # Draw horizontal line
            for i in range(-half, half + 1):
                y = round(y_base + i * 0.5)
                if 0 <= y < self.height:
                    bitmap[y][x] = 1

            # Draw vertical transition if state changed
            if prev_is_high is not None and is_high != prev_is_high:
                y_start = round(self.center_y - self.amplitude)
                y_end = round(self.center_y + self.amplitude)
                for y in range(min(y_start, y_end), max(y_start, y_end) + 1):
                    if 0 <= y < self.height:
                        bitmap[y][x] = 1

            prev_is_high = is_high

        self.phase += self.phase_step
        return bitmap


class SawtoothWaveBitmapGenerator:
    def __init__(self, width, height, frequency=2.0, amplitude=None, thickness=1, invert=False):
        """
        Generates a sawtooth wave waveform with incremental bitmaps that can be used to generate an animation.

        :param width: The width of the wave bitmap in pixels.
        :type width: int
        :param height: The height of the wave bitmap in pixels.
        :type height: int
        :param frequency: (optional) The frequency of the wave in cycles per unit width. (default: 2.0)
        :type frequency: float
        :param amplitude: (optional) The amplitude of the wave in pixels (defaults: (0.5 * height) - 1)
        :type amplitude: float
        :param thickness: (optional) The thickness of the wave line in pixels. (default: 1)
        :type thickness: int
        :param invert: (optional) Whether the sine wave is inverted vertically. (default: False)
        :type invert: bool
        """
        self.width = width
        self.height = height
        self.frequency = frequency
        self.amplitude = amplitude if amplitude is not None else (height / 2 - 1)
        self.center_y = height // 2
        self.phase = 0.0
        self.phase_step = (2 * math.pi * frequency) / width
        self.thickness = thickness
        self.invert = invert

    def next_frame(self):
        bitmap = [[0 for _ in range(self.width)] for _ in range(self.height)]
        half = self.thickness // 2

        prev_wave_pos = None

        for x in range(self.width):
            radians = self.phase + (x * 2 * math.pi * self.frequency / self.width)
            wave_pos = (radians % (2 * math.pi)) / (2 * math.pi)  # normalized cycle position

            # Sawtooth ramp: upward or downward
            if self.invert:
                y_float = self.center_y + self.amplitude * (1.0 - wave_pos * 2)
            else:
                y_float = self.center_y - self.amplitude + self.amplitude * 2 * wave_pos

            # Draw the ramp line
            for i in range(-half, half + 1):
                y = round(y_float + i * 0.5)
                if 0 <= y < self.height:
                    bitmap[y][x] = 1

            # Draw vertical edge at cycle reset
            if prev_wave_pos is not None and wave_pos < prev_wave_pos:
                y_start = round(self.center_y - self.amplitude)
                y_end = round(self.center_y + self.amplitude)
                for y in range(min(y_start, y_end), max(y_start, y_end) + 1):
                    if 0 <= y < self.height:
                        bitmap[y][x] = 1

            prev_wave_pos = wave_pos

        self.phase += self.phase_step
        return bitmap


class TriangleWaveBitmapGenerator:
    def __init__(self, width, height, frequency=2.0, amplitude=None, thickness=1):
        """
        Generates a triangle wave waveform with incremental bitmaps that can be used to generate an animation.

        :param width: The width of the wave bitmap in pixels.
        :type width: int
        :param height: The height of the wave bitmap in pixels.
        :type height: int
        :param frequency: (optional) The frequency of the wave in cycles per unit width. (default: 2.0)
        :type frequency: float
        :param amplitude: (optional) The amplitude of the wave in pixels (defaults: (0.5 * height) - 1)
        :type amplitude: float
        :param thickness: (optional) The thickness of the wave line in pixels. (default: 1)
        :type thickness: int
        """
        self.width = width
        self.height = height
        self.frequency = frequency
        self.amplitude = amplitude if amplitude is not None else (height / 2 - 1)
        self.center_y = height // 2
        self.y_min = self.center_y - self.amplitude
        self.y_max = self.center_y + self.amplitude
        self.phase_px = 0.0
        self.thickness = max(1, int(thickness))  # ensure thickness is at least 1

        # Pixels per cycle
        self.cycle_px = self.width / self.frequency

    def next_frame(self):
        bitmap = [[0 for _ in range(self.width)] for _ in range(self.height)]
        half = self.thickness // 2

        for x in range(self.width):
            # Compute position within the current cycle
            pos_in_cycle = (self.phase_px + x) % self.cycle_px
            half_cycle = self.cycle_px / 2

            if pos_in_cycle < half_cycle:
                # Rising edge
                y_float = self.y_min + (pos_in_cycle / half_cycle) * (self.y_max - self.y_min)
            else:
                # Falling edge
                y_float = self.y_max - ((pos_in_cycle - half_cycle) / half_cycle) * (self.y_max - self.y_min)

            # Draw vertical band of pixels for thickness
            for i in range(-half, half + 1):
                y = round(y_float + i)
                if 0 <= y < self.height:
                    bitmap[y][x] = 1

        self.phase_px += 1  # advance by one pixel per frame
        return bitmap


spi = SPI(2, mosi=PIN_SIN, sck=PIN_SCK, baudrate=115200)
vfd = NAGP1250(spi=spi, reset=PIN_RESET, sbusy=PIN_SBUSY)

# Create blank bitmap for window 0
width = 140
height = 32
bitmap = [[0 for _ in range(width)] for _ in range(height)]

# A line every 35-ish pixels but ignore the first and last lines
lines = [
    (30, 8, 270, 32),
    (65, 8, 270, 32),
    (100, 8, 270, 32),
]

bitmap = vfd.draw_graphic_lines(bitmap=bitmap, lines=lines, width=width, height=height)
packed = vfd.pack_bitmap(bitmap=bitmap, width=width, height=height)
vfd.display_graphic_image(image_data=packed, width=width, height=height)

vfd.set_reverse_display(mode=1)
vfd.set_cursor_position(x=35, y=0)
vfd.write_text("waveforms")
vfd.set_reverse_display(mode=0)

vfd.set_cursor_position(x=0, y=1)
vfd.write_text("sine")
# Make positioning easy and grab the starting point of each vertical line and add 2px buffer lol, #cheating ;-)
vfd.set_cursor_position(x=lines[0][0] + 2, y=1)
vfd.write_text("sqr")
vfd.set_cursor_position(x=lines[1][0] + 2, y=1)
vfd.write_text("saw")
vfd.set_cursor_position(x=lines[2][0] + 2, y=1)
vfd.write_text("tri")

# for sine wave
vfd.define_user_window(window_num=1, x=0, y=2, w=35, h=2)
# for square wave
vfd.define_user_window(window_num=2, x=34, y=2, w=35, h=2)
# for sawtooth wave
vfd.define_user_window(window_num=3, x=69, y=2, w=35, h=2)
# for triangle wave
vfd.define_user_window(window_num=4, x=104, y=2, w=35, h=2)

# Let's make it easy on life lol
waveform_width = 28
waveform_height = 16

# Set up the generators
sin_wave = SineWaveBitmapGenerator(width=waveform_width, height=waveform_height, frequency=2, amplitude=5, thickness=4)
sqr_wave = SquareWaveBitmapGenerator(width=waveform_width, height=waveform_height, frequency=2, amplitude=5, thickness=2)
saw_wave = SawtoothWaveBitmapGenerator(width=waveform_width, height=waveform_height, frequency=2, amplitude=5, thickness=2)
tri_wave = TriangleWaveBitmapGenerator(width=waveform_width, height=waveform_height, frequency=2, amplitude=4, thickness=2)

while True:
    # Gather the data and pack the data
    sin_frame = sin_wave.next_frame()
    sin_data = vfd.pack_bitmap(bitmap=sin_frame, width=waveform_width, height=waveform_height)

    sqr_frame = sqr_wave.next_frame()
    sqr_data = vfd.pack_bitmap(bitmap=sqr_frame, width=waveform_width, height=waveform_height)

    saw_frame = saw_wave.next_frame()
    saw_data = vfd.pack_bitmap(bitmap=saw_frame, width=waveform_width, height=waveform_height)

    tri_frame = tri_wave.next_frame()
    tri_data = vfd.pack_bitmap(bitmap=tri_frame, width=waveform_width, height=waveform_height)

    # Display the data
    vfd.do_select_window(window_num=1)
    vfd.do_home()
    vfd.display_graphic_image(image_data=sin_data, width=waveform_width, height=waveform_height)

    # The screen has an absolute bitch-fit without this delay and having 4 windows on the same line *puzzled face*
    # I'm guessing the display's frame buffer needs a little time to process the window data, but IDK... Could be a
    # display firmware bug too. This may not happen if each waveform is drawn on the same bitmap, so the display only
    # has to redraw one bitmap on a window instead of multiple. However, that isn't nearly as fun, although it would
    # be more efficient.
    time.sleep_ms(3)

    vfd.do_select_window(window_num=2)
    vfd.do_home()
    vfd.display_graphic_image(image_data=sqr_data, width=waveform_width, height=waveform_height)

    time.sleep_ms(3)

    vfd.do_select_window(window_num=3)
    vfd.do_home()
    vfd.display_graphic_image(image_data=saw_data, width=waveform_width, height=waveform_height)

    time.sleep_ms(3)

    vfd.do_select_window(window_num=4)
    vfd.do_home()
    vfd.display_graphic_image(image_data=tri_data, width=waveform_width, height=waveform_height)
