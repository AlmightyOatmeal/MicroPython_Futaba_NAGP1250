from futaba import NAGP1250
from futaba.NAGP1250 import WRITE_MODE_NORMAL, WRITE_MODE_OR, WRITE_MODE_XOR
from machine import SPI
import math
import time

# SPI pins for the NAGP1250 display.
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

# Create blank bitmap
width = 140
height = 32
bitmap = [[0 for _ in range(width)] for _ in range(height)]

# In normal mode, the txt on top would erase some of the box outline so merge the data instead with OR <3
vfd.set_write_logic(mode=WRITE_MODE_OR)

# Create some buttons
box_with = 45
box_height = 10
box_radius = 5
bitmap = vfd.draw_graphic_box(bitmap=bitmap, x=0, y=0, width=box_with, height=box_height, radius=box_radius, fill=True)
bitmap = vfd.draw_graphic_box(bitmap=bitmap, x=47, y=0, width=box_with, height=box_height, radius=box_radius)
bitmap = vfd.draw_graphic_box(bitmap=bitmap, x=94, y=0, width=box_with, height=box_height, radius=box_radius)

packed = vfd.pack_bitmap(bitmap=bitmap, width=140, height=32)

vfd.display_graphic_image(image_data=packed, width=140, height=32)

# Invert the text on the filled-in button
vfd.set_write_logic(mode=WRITE_MODE_XOR)
vfd.set_cursor_position(x=8, y=0)
vfd.write_text("wave")
# Reset the write logic mode
vfd.set_write_logic(mode=WRITE_MODE_OR)

vfd.set_cursor_position(x=55, y=0)
vfd.write_text("freq")

vfd.set_cursor_position(x=107, y=0)
vfd.write_text("amp")

vfd.define_user_window(window_num=1, x=0, y=2, w=45, h=2)
vfd.define_user_window(window_num=2, x=54, y=2, w=76, h=2)

# Switch to normal mode to overwrite contents here:
vfd.set_write_logic(mode=WRITE_MODE_NORMAL)

while True:
    for form in ["sin", "sqr", "saw", "tri"]:
        vfd.do_select_window(window_num=1)
        vfd.clear_window(window_num=1)
        vfd.do_home()

        vfd.set_font_magnification(h=2, v=2)
        vfd.write_text(form.upper())

        g_width = 76
        g_height = 16
        if form == "sin":
            wave = SineWaveBitmapGenerator(width=g_width, height=g_height, frequency=4, amplitude=5, thickness=2)
        elif form == "sqr":
            wave = SquareWaveBitmapGenerator(width=g_width, height=g_height, frequency=4, amplitude=5, thickness=2)
        elif form == "saw":
            wave = SawtoothWaveBitmapGenerator(width=g_width, height=g_height, frequency=4, amplitude=5, thickness=2)
        elif form == "tri":
            wave = TriangleWaveBitmapGenerator(width=g_width, height=g_height, frequency=4, amplitude=4, thickness=2)

        frame = wave.next_frame()
        data = vfd.pack_bitmap(bitmap=frame, width=g_width, height=g_height)
        vfd.do_select_window(window_num=2)
        vfd.clear_window(window_num=2)
        vfd.do_home()
        time.sleep_ms(3)
        vfd.display_graphic_image(image_data=data, width=g_width, height=g_height)

        time.sleep(5)
