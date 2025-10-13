# -*- coding: utf-8 -*-
"""
Pure MicroPython driver for the Futaba NAGP1250 VFD.
"""

__author__ = "Catlin Kintsugi"

from machine import Pin, SPI
import micropython
import math
import time


FONT_AMERICA = 0x00
FONT_FRANCE = 0x01
FONT_GERMANY = 0x02
FONT_ENGLAND = 0x03
FONT_DENMARK_1 = 0x04
FONT_SWEDEN = 0x05
FONT_ITALY = 0x06
FONT_SPAIN_1 = 0x07
FONT_JAPAN = 0x08
FONT_NORWAY = 0x09
FONT_DENMARK_2 = 0x0A
FONT_SPAIN_2 = 0x0B
FONT_LATIN_AMERICA = 0x0C
FONT_KOREA = 0x0D

CHAR_CODE_PC437 = 0x00
CHAR_CODE_KATAKANA = 0x01
CHAR_CODE_PC850 = 0x02
CHAR_CODE_PC860 = 0x03
CHAR_CODE_PC863 = 0x04
CHAR_CODE_PC865_NORDIC = 0x05
CHAR_CODE_WPC1252 = 0x10
CHAR_CODE_PC866 = 0x11
CHAR_CODE_PC852 = 0x12
CHAR_CODE_PC858 = 0x13

WRITE_MODE_NORMAL = 0
WRITE_MODE_OR = 1
WRITE_MODE_AND = 2
WRITE_MODE_XOR = 3

BASE_WINDOW_MODE_DEFAULT = 0
BASE_WINDOW_MODE_EXTENDED = 1


# Create a lookup table to reverse the bits of every possible 8-bit value (0–255)
REVERSE_TABLE = bytearray(256)  # Allocate space for 256 reversed bytes

# Loop through all 8-bit values
for bit_i in range(256):
    original_byte = bit_i  # Original byte value
    result = 0  # Will hold the reversed result

    # Reverse the bits of `original_bytes` by shifting and masking
    for _ in range(8):  # Process each of the 8 bits
        result = (result << 1) | (original_byte & 1)  # Shift `result` left and add the least significant bit of `original_bytes`
        original_byte >>= 1  # Shift `original_bytes` right to move to the next bit

    # Store the reversed byte in the lookup table
    REVERSE_TABLE[bit_i] = result


# noinspection GrazieInspection
class NAGP1250:
    def __init__(self, spi: SPI, reset: Pin | int = None, sbusy: Pin | int = None,
                 luminance: int = 4, cursor_blink: int | None = None, mode: str | None = None,
                 base_window_mode: int = 0, debug: bool = False) -> None:
        """
        Initializes the display with specified pins and settings.

        :param spi: Serial peripheral interface object for the display.
        :type spi: machine.SPI
        :param reset: (optional) Reset pin for the display. (default: None)
        :type reset: Pin | int
        :param sbusy: (optional) Busy signal pin for the display. (default: None)
        :type sbusy: Pin | int
        :param luminance: (optional) Luminance level of the display. (default: 4 (50%)
        :type luminance: int
        :param cursor_blink: (optional) Enable/disable cursor blink. (default: None)
        :type cursor_blink: int | None
        :param mode: (optional) Initial mode of the display. Expects "MD1", "MD2", or "MD3". (default: None)
        :type mode: str | None
        :param base_window_mode: (optional) Base window is 0=140x32 (default) or 1=256x32. (default: 0)
        :type base_window_mode: int
        :param debug: (optional) Enable/disable debug mode. (default: False)
        :type debug: bool
        :raises ValueError: If the provided mode is invalid.
        :raises ValueError: If the provided base window mode is invalid.
        """
        self.debug = debug

        # Check to see whether we have a pin object or a pin integer
        self.pin_reset = Pin(reset, Pin.OUT) if not isinstance(reset, Pin) else reset
        self.pin_sbusy = Pin(sbusy, Pin.IN) if not isinstance(sbusy, Pin) else sbusy

        # Leverage hardware-specific optimizations at a consistent baud rate. This display supports a
        # maximum baud rate of 115,200.
        self.spi = spi

        if base_window_mode == 0:
            self.width = 140
            self.height = 32
        elif base_window_mode == 1:
            self.width = 256
            self.height = 32
        else:
            raise ValueError(f"Invalid base window mode: {base_window_mode}")

        # Initialize the display
        self.reset_display()
        self.initialize()

        # Set the display initial state
        self.set_luminance(luminance=luminance)

        if cursor_blink is not None:
            self.set_cursor_blink(mode=cursor_blink)

        if mode is not None:
            mode = mode.upper()
            if mode == "MD1":
                self.set_mode_md1()
            elif mode == "MD2":
                self.set_mode_md2()
            elif mode == "MD3":
                self.set_mode_md3()
            else:
                raise ValueError("Invalid mode")

    def _wait_for_sbusy(self, timeout_us: int = 10000) -> None:
        """
        Waits for the SBUSY signal to become inactive or until the timeout is reached.

        :param timeout_us: (optional) Maximum duration to wait for the SBUSY signal to become inactive, specified in
                           microseconds (default: 10000).
        :type timeout_us: int
        :return: None
        """
        # If `pin_sbusy` is None, then we can't wait for it to become False so return immediately.
        if not self.pin_sbusy:
            return None

        start = time.ticks_us()
        while self.pin_sbusy.value():
            if time.ticks_diff(time.ticks_us(), start) > timeout_us:
                print("WARNING: SBUSY timeout")
                break
            time.sleep_us(10)
        return None

    @micropython.native
    def send_bytes(self, data: bytearray | list, wait_busy: bool = True) -> None:
        """
        Sends a sequence of bytes to a specific display and optionally waits
        until the device is no longer busy after sending.

        :param data: A sequence of bytes to be sent to the device. Each byte should fall within the range of 0-255.
        :type data: bytearray | list
        :param wait_busy: (optional) Wait until the busy signal pin goes low before sending more data. (default: True)
        :type wait_busy: bool
        :return: None
        """
        # MicroPython's SPI implementation doesn't support LSB so we need to pre-flip
        # the data and handle both 8-bit and 16-bit values.

        out = bytearray()

        for item in data:
            if item < 0 or item > 0xFFFF:
                raise ValueError("Data item out of range (must be 0–65535)")

            if item <= 0xFF:
                # 8-bit value: reverse bits, keep as single byte
                out.append(REVERSE_TABLE[item])
            else:
                # 16-bit value: reverse each byte, preserve 2-byte structure
                high = (item >> 8) & 0xFF
                low = item & 0xFF
                out.append(REVERSE_TABLE[low])  # LSB becomes MSB
                out.append(REVERSE_TABLE[high])  # MSB becomes LSB

        if self.debug:
            print(f"Sending {len(out)} bytes: {out}")
        self.spi.write(out)

        if wait_busy and self.pin_sbusy:
            self._wait_for_sbusy()

    def initialize(self) -> None:
        """
        Sends an initialization command to the connected display.

        :return: None
        """
        self.send_bytes(data=[0x1B, 0x40])

    def reset_display(self) -> None:
        """
        Resets the display via reset pin.

        :return: None
        :raises TypeError: If the `pin_reset` attribute is not set as expected.
        """
        if not self.pin_reset:
            return None

        self.pin_reset.value(1)
        if self.pin_reset:
            self.pin_reset.value(0)
            time.sleep_ms(100)
            self.pin_reset.value(1)
            time.sleep_ms(100)
        return None

    # TODO: Why doesn't this seem to work?
    def set_font(self, font_id: int) -> None:
        """
        Sets the font table for the display for characters 20h and 7Fh.

        `font_id` options are:

        - 0x00 = America
        - 0x01 = France
        - 0x02 = Germany
        - 0x03 = England
        - 0x04 = Denmark 1
        - 0x05 = Sweden
        - 0x06 = Italy
        - 0x07 = Spain 1
        - 0x08 = Japan
        - 0x09 = Norway
        - 0x0A = Denmark 2
        - 0x0B = Spain 2
        - 0x0C = Latin America
        - 0x0D = Korea

        :param font_id: The identifier for the font to be selected.
        :type font_id: int
        :return: None
        :raises ValueError: Invalid font ID.
        """
        if not (0 <= font_id <= 13):
            raise ValueError(f"Invalid font ID: {font_id}")
        self.send_bytes(data=[0x1B, 0x52, font_id])

    def set_character_code(self, code: int) -> None:
        """
        Sets the character code for the display for characters 0x80 - 0xFF.

        `code` options are:

        - 0x00 = PC437 (US – European)
        - 0x01 = Katakana – Japanese
        - 0x02 = PC850 (Multilingual)
        - 0x03 = PC860 (Portuguese)
        - 0x04 = PC863 (Canadian – French)
        - 0x05 = PC865 Nordic
        - 0x10 = WPC1252
        - 0x11 = PC866 (Cyrillic #2)
        - 0x12 = PC852 (Latin #2)
        - 0x13 = PC858

        :param code: The identifier for the font to be selected.
        :type code: int
        :return: None
        :raises ValueError: Invalid character code.
        """
        if not (0 <= code <= 13):
            raise ValueError(f"Invalid character code: {code}")
        self.send_bytes(data=[0x1B, 0x74, code])

    def set_cursor_blink(self, mode: int) -> None:
        """
        Turns the cursor blink on or off. When the cursor blink is on, it blinks at about 1Hz.

        :param mode: The cursor blink mode to set. 0 to disable blinking, 1 to enable blinking.
        :type mode: int
        :return: None
        :raises ValueError: Invalid cursor blink mode.
        """
        if not (0 <= mode <= 1):
            raise ValueError(f"Cursor blink {mode} must be 0–1")
        self.send_bytes([0x1F, 0x43, mode])

    def set_write_logic(self, mode: int) -> None:
        """
        This three-byte command selects the Write Logic Mode. As character data or graphic data is written, it is
        logically combined with the data already in the Display Memory.

        `mode` options are:

        - 0 = Normal (overwrites existing data)
        - 1 = OR (combines new and existing data)
        - 2 = AND (masks existing data)
        - 3 = XOR (inverts existing data when new data is 0xFF)

        :param mode: The write logic mode.
        :type mode: int
        :return: None
        :raises ValueError: Invalid write logic mode.
        """
        if not (0 <= mode <= 3):
            raise ValueError(f"Write logic mode {mode} must be 0–3")
        self.send_bytes([0x1F, 0x77, mode])

    def set_horizontal_scroll_speed(self, speed: int) -> None:
        """
        Sets the Horizontal Scroll Speed for the MD3 mode.

        Horizontal Scroll Speed is approximately: S * 14ms per column, maximum speed of 31.

        :param speed: Speed level.
        :type speed: int
        :return: None
        :raises ValueError: Invalid speed level.
        """
        if not (0 <= speed <= 31):
            raise ValueError(f"Horizontal scroll speed {speed} must be 0–31")
        self.send_bytes([0x1F, 0x73, speed])

    def set_luminance(self, luminance: int) -> None:
        """Set display brightness.

        `luminance` options are:

        - 1 = 12.5%
        - 2 = 25%
        - 3 = 37.5%
        - 4 = 50%
        - 5 = 62.5%
        - 6 = 75%
        - 7 = 87.5%
        - 8 = 100%

        :param luminance: Luminance level.
        :type luminance: int
        :return: None
        :raises ValueError: Invalid luminance level.
        """
        if not (1 <= luminance <= 8):
            raise ValueError(f"Luminance {luminance} must be 1–8")

        self.send_bytes([0x1F, 0x58, luminance])

    def set_overwrite_mode(self) -> None:
        """
        Sets overwrite mode.

        :return: None
        """
        self.send_bytes([0x1F, 0x01])  # MD1: Overwrite mode

    # TODO: Test
    def set_vertical_scroll(self) -> None:
        """
        Sets the vertical scroll mode.

        :return: None
        """
        self.send_bytes([0x1F, 0x02])  # MD2: Vertical scroll mode

    def set_horizontal_scroll(self) -> None:
        """
        Sets the display to horizontal scroll mode.

        :return: None
        """
        self.send_bytes([0x1F, 0x03])  # MD3: Horizontal scroll mode

    def set_mode_md1(self) -> None:
        """
        Alias for overwrite mode.

        :return: None
        """
        self.set_overwrite_mode()

    def set_mode_md2(self) -> None:
        """
        Alias for vertical scrolling mode.

        :return: None
        """
        self.set_vertical_scroll()

    def set_mode_md3(self) -> None:
        """
        Alias for horizontal scroll mode.

        :return: None
        """
        self.set_horizontal_scroll()

    def set_font_magnification(self, h: int, v: int) -> None:
        """
        Sets the font magnification by specifying horizontal and vertical
        scaling factors.

        Not all displays support all magnification factors.

        :param h: Horizontal magnification value must be an integer between 1 and 4 inclusive.
        :type h: int
        :param v: Vertical magnification value must be an integer between 1 and 4 inclusive.
        :type v: int
        :return: None
        :raises ValueError: If the horizontal or vertical magnification is outside the range 1 to 4.
        """
        if not (1 <= h <= 4):
            raise ValueError(f"Font magnification horizontal param {h} must be 1 through 4")
        if not (1 <= v <= 4):
            raise ValueError(f"Font magnification vertical param {v} must be 1 through 4")

        self.send_bytes([0x1F, 0x28, 0x67, 0x40, h, v])

    def set_character_spacing(self, mode: int) -> None:
        """
        Sets the character spacing mode.

        0 = Fixed width, space on right
        1 = Fixed width, space on left and right
        2 = Proportional width, space on right
        3 = Proportional width, space on left and right

        :param mode: The character spacing mode to set. Must be an integer between 0 and 3, inclusive.
        :type mode: int
        :return: None
        :raises ValueError: If the mode is not within the range 0 to 3.
        """
        if not (0 <= mode <= 3):
            raise ValueError(f"Mode {mode} must be between 0 and 3")

        self.send_bytes([0x1F, 0x28, 0x67, 0x03, mode])

    def set_cursor_position(self, x: int, y: int) -> None:
        """
        Sets the cursor position on the display to the specified x and y coordinates on a given window.

        :param x: The horizontal position for the cursor. Must be in the range 0-255 (1 pixel per column).
        :type x: int
        :param y: The vertical position for the cursor. Must be in the range 0-3 (8 pixel units per row).
        :type y: int
        :return: None
        :raises ValueError: If x or y are out of their allowed ranges.
        """
        if not (0 <= x <= 255):
            raise ValueError(f"X position {x} out of range")
        if not (0 <= y <= 3):
            raise ValueError(f"Y position {y} out of range")

        payload = [
            0x1F,  # Command header
            0x24,  # Set Cursor Position
            x & 0xFF,  # X low byte
            (x >> 8) & 0xFF,  # X high byte
            y & 0xFF,  # Y low byte
            (y >> 8) & 0xFF  # Y high byte
        ]
        self.send_bytes(payload)

    def set_reverse_display(self, mode: int) -> None:
        """
        Specify or Cancel Reverse Display

        This only applies to new data, existing data on the display will not be affected.

        0 = Cancel Reverse Display
        1 = Reverse Display

        :param mode: The reverse display mode to set, 1 reverses the display and 0 returns to normal.
        :type mode: int
        :return: None
        :raises ValueError: If the mode is not 0 or 1.
        """
        if not (0 <= mode <= 1):
            raise ValueError(f"Mode {mode} must be either 0 or 1")

        self.send_bytes([0x1F, 0x72, mode])

    def clear_window(self, window_num: int = 0) -> None:
        """
        Clears the content of a specific window.

        :param window_num: (optional) Window number to be cleared. (default: 0)
        :type window_num: int
        :return: None
        :raises ValueError: Invalid window number.
        """
        if not (0 <= window_num <= 4):
            raise ValueError(f"Invalid window number {window_num}")

        self.do_select_window(window_num)
        self.send_bytes([0x0C])

    def do_blink_display(self, pattern: int, normal_time: int, blink_time: int, repetition: int) -> None:
        """
        This method controls a blinking display based on the specified pattern, normal display time, blink display
        time, and the number of repetitions.

        The time unit is approximately t*14ms.

        .. list-table::
         :header-rows: 1

         * - **SEIZURE WARNING:**
         * - It is possible to make this screen blink at a rate that could trigger photosensitive epileptic episodes.

        `pattern` options are:

        - 0 = Normal display
        - 1 = Repeat blink display with normal and Blank display
        - 2 = Repeat blink display with normal and Reverse display

        :param pattern: The blinking pattern to be applied.
        :type pattern: int
        :param normal_time: The duration for which the display remains visible in the normal state.
        :type normal_time: int
        :param blink_time: The duration for which the display remains visible in the blinking/blank state.
        :type blink_time: int
        :param repetition: The number of repetitions for the blinking sequence before returning to normal.
        :type repetition: int
        :return: None
        :raises ValueError: If any of the arguments fall outside their respective allowed ranges.
        """
        if not (0 <= pattern <= 2):
            raise ValueError(f"Pattern {pattern} needs to be 0 through 2")

        if not (1 <= normal_time <= 255):
            raise ValueError(f"Normal time {normal_time} needs to be 1 through 255")

        if not (1 <= blink_time <= 255):
            raise ValueError(f"Blink time {blink_time} needs to be 1 through 255")

        if not (1 <= repetition <= 255):
            raise ValueError(f"Repetition {repetition} needs to be 1 through 255")

        self.send_bytes([0x1F, 0x28, 0x61, 0x11, pattern, normal_time, blink_time, repetition])

    def do_home(self) -> None:
        """
        Brings the cursor to the top left of the current window.

        :return: None
        """
        self.send_bytes([0x0B])

    def do_line_feed(self) -> None:
        """
        Moves the cursor to the beginning of the next line.

        :return: None
        """
        self.send_bytes([0x0A])

    def do_backspace(self) -> None:
        """
        Moves the cursor back one character position.

        :return: None
        """
        self.send_bytes([0x08])

    def do_horizontal_tab(self) -> None:
        """
        Sends a horizontal tab.

        :return: None
        """
        self.send_bytes([0x09])

    def do_wait(self, duration: int) -> None:
        """
        Waits for a specified duration in the range 0–255, allowing the system to pause.

        Wait Time is approximately: 0.5s * `duration`

        :param duration: The duration to wait for, specified as an integer between 0 and 255 inclusive.
        :type duration: int
        :return: None
        :raises ValueError: If the provided duration is not within the allowed range of 0–255.
        """
        if not (0 <= duration <= 255):
            raise ValueError(f"Wait duration {duration} must be 0–255")
        self.send_bytes([0x1F, 0x28, 0x61, 0x01, duration])

    def do_select_window(self, window_num: int) -> None:
        """
        Selects a specific window for operations.

        :param window_num: The window number to select must be in the range 0–4.
        :type window_num: int
        :return: None
        :raises ValueError: If the provided window number is not in the range 0–4.
        """
        if not (0 <= window_num <= 4):
            raise ValueError(f"Window number {window_num} must be 0–4")
        self.send_bytes([0x1F, 0x28, 0x77, 0x01, window_num])

    def do_screen_saver(self, pattern: int) -> None:
        """
        Sets the screen saver mode.

        `pattern` options are:

        - 0 = Turns off module’s internal switching power supply.
        - 1 = Turns on module’s internal switching power supply.
        - 2 = Turns all display dots off (Display Memory is not affected).
        - 3 = Turns on all display dots (Display Memory is not affected).
        - 4 = Alternates between all dots on and reverse video display patterns every 2 seconds.

        :param pattern: An integer representing the screen saver pattern. Valid values are from 0 to 4.
        :type pattern: int
        :return: None
        :raises ValueError: Invalid pattern.
        """
        if not (0 <= pattern <= 4):
            raise ValueError(f"Screen saver {pattern} must be 0 through 4")
        self.send_bytes([0x1F, 0x28, 0x61, 0x40, pattern])

    def do_carriage_return(self) -> None:
        """
        Sends a carriage return to the current cursor position to bring the cursor to the beginning of the current line.

        :return: None
        """
        self.send_bytes([0x0D])

    def do_display_scroll(self, shift_bytes: int, repeat_count: int, speed: int = 1) -> None:
        """
        Scroll the display using the Scroll Display Action command. This only applies when using the additional
        hidden/extended 116 pixels for a display resolution of 256px wide.

        :param shift_bytes: The number of bytes (0–1023) to shift in the display.
        :param repeat_count: The number of times (1–65535) the scrolling action will repeat.
        :param speed: The speed of scrolling (0–255), where 0 is the slowest and 255 is the fastest.
        :return: None
        """
        if not (0 <= shift_bytes <= 1023):
            raise ValueError("shift_bytes must be between 0 and 1023")
        if not (1 <= repeat_count <= 65535):
            raise ValueError("repeat_count must be between 1 and 65535")
        if not (0 <= speed <= 255):
            raise ValueError("speed must be between 0 and 255")

        # Split values into low/high bytes
        wl = shift_bytes & 0xFF
        wh = (shift_bytes >> 8) & 0xFF
        cl = repeat_count & 0xFF
        ch = (repeat_count >> 8) & 0xFF

        # Construct command packet
        payload = bytearray([
            0x1F, 0x28, 0x61, 0x10,  # Command header
            wl, wh,  # Shift amount
            cl, ch,  # Repeat count
            speed  # Speed
        ])

        self.send_bytes(data=payload, wait_busy=True)

    def write_text(self, text: str | list) -> None:
        """
        Writes a given string or list of characters to the output.

        Each character in the input is processed individually and converted to its corresponding byte representation.

        :param text: The input text to be written. It can be either a string or a list of characters. Each character
                     will be converted to its byte equivalent before writing.
        :type text: str | list
        :return: None
        """
        self.send_bytes([ord(char) for char in text])

    def define_user_window(self, window_num: int, x: int, y: int, w: int, h: int) -> None:
        """
        Defines or deletes a user window (1–4).

        :param window_num: The identifier of the user window. Must be an integer between 1 and 4 inclusive.
        :type window_num: int
        :param x: The x-coordinate of the upper-left corner. Must be an integer between 0 and 279.
        :type x: int
        :param y: The y-coordinate of the upper-left corner. Must be an integer between 0 and 3.
        :type y: int
        :param w: The width of the window. Must be an integer between 1 and 280.
        :type w: int
        :param h: The height of the window. Must be an integer between 1 and 4.
        :type h: int
        :return: None
        :raises ValueError: If the window number, position coordinates, or size are outside their allowable bounds.
        """
        if not (1 <= window_num <= 4):
            raise ValueError(f"Window {window_num} number must be 1–4")
        if not (0 <= x <= 279 or 0 <= y <= 3):
            raise ValueError(f"Upper-left corner {x} out of bounds")
        if not (1 <= w <= 280 or 1 <= h <= 4):
            raise ValueError(f"Window size {w} out of bounds")

        # Command header
        # noinspection PyListCreation
        payload = [0x1F, 0x28, 0x77, 0x02]

        # Window number
        payload.append(window_num)

        # Define byte
        payload.append(0x01)

        # Upper-left X
        payload.append(x & 0xFF)  # Low byte
        payload.append((x >> 8) & 0xFF)  # High byte

        # Upper-left Y
        payload.append(y & 0xFF)
        payload.append((y >> 8) & 0xFF)

        # Window size X
        payload.append(w & 0xFF)
        payload.append((w >> 8) & 0xFF)

        # Window size Y
        payload.append(h & 0xFF)
        payload.append((h >> 8) & 0xFF)

        self.send_bytes(payload)

    def delete_user_window(self, window_num: int, clear: bool = True) -> None:
        """
        Deletes a user-defined window.

        :param window_num: The number of the window to delete. Must be between 1 and 4.
        :type window_num: int
        :param clear: (optional) Clear the contents of the window before deletion. (default: True)
        :type clear: bool
        :return: None
        :raises ValueError: Invalid user-defined window number.
        """
        if not (1 <= window_num <= 4):
            raise ValueError(f"Window {window_num} number must be 1–4")

        # Check to see if we should clear the window before deleting it.
        if clear:
            self.clear_window(window_num=window_num)

        self.send_bytes([0x1F, 0x28, 0x77, 0x02, window_num, 0x00])

    def define_base_window(self, mode: int) -> None:
        """
        Defines Window 0’s size as either 140x32 (base) or 140+116 of hidden pixels (extended) to give the full 256x32.

        `mode` options are:

        - 0 = Base
        - 1 = Extended

        :param mode: The base window mode. Valid values are 0 or 1.
        :type mode: int
        :return: None
        :raises ValueError: If the mode is outside the allowed range (0 to 1).
        """
        if not (0 <= mode <= 1):
            raise ValueError(f"Mode {mode} must be between 0 and 1")

        if mode == 0:
            self.width = 140
            self.height = 32
        elif mode == 1:
            self.width = 256
            self.height = 32

        self.send_bytes([0x1F, 0x28, 0x77, 0x10, mode])

    @staticmethod
    @micropython.native
    def pack_bitmap(bitmap: list | tuple[list | tuple[int]], width: int, height: int) -> bytearray:
        """
        Pack bitmap into column-major format

        The bitmap list/tuple where each inner list/tuple corresponds to a row in the bitmap, where each element is an
        integer (either 0 or 1) representing the state of the pixel. Columns are processed sequentially, and the
        packed data is returned as a bytearray.

        :param bitmap: The list representing the bitmap.
        :type bitmap: list | tuple[list | tuple[int]]
        :param width: The width of the bitmap, representing the number of columns.
        :type width: int
        :param height: The height of the bitmap, representing the number of rows.
        :type height: int
        :return: A bytearray where each byte represents a packed column of the bitmap.
        :rtype: bytearray
        """
        packed = bytearray()
        for x in range(width):
            for byte_row in range(0, height, 8):
                byte = 0
                for bit in range(8):
                    y = byte_row + bit
                    if bitmap[y][x]:
                        byte |= (1 << (7 - bit))
                packed.append(byte)
        return packed

    @micropython.native
    def display_realtime_image(self, image_data: list | bytearray, width: int, height: int) -> None:
        """
        Display a bit image at the current cursor position in real-time.

        :param image_data: The image data to be sent, as a sequence of bytes (column-major).
        :type image_data: list | bytearray
        :param width: The width of the image in pixels (columns are 1 pixel wide).
        :type width: int
        :param height: The height of the image that must be divisible of 8 (rows are blocks of 8 pixels high).
        :type height: int
        :return: None
        """
        if not (1 <= width <= 256):
            raise ValueError(f"Width {width} must be between 1 and 256")

        if height % 8 != 0 or not (1 <= height <= 32):
            raise ValueError(f"Height {height} must be divisible by 8 and ≤ 32")

        byte_rows = height // 8  # height is represented in number of rows that are 8 pixels high.
        expected_length = width * byte_rows  # width is represented in columns that are 1 pixel wide.

        if len(image_data) != expected_length:
            raise ValueError(f"Expected {expected_length} bytes of image data, got {len(image_data)}")

        payload = [
            0x1F, 0x28, 0x66, 0x11,  # Command
            width & 0xFF,  # X low byte
            (width >> 8) & 0xFF,  # X high byte
            byte_rows & 0xFF,  # Y low byte
            (byte_rows >> 8) & 0xFF,  # Y high byte
            1  # Mode (fixed)
        ]
        payload.extend(image_data)

        if self.debug:
            print()
            print(f"debug: graphics payload: {payload}")
        self.send_bytes(payload)

    @staticmethod
    def draw_graphic_lines(bitmap: list[list[int]], lines: list | tuple[list | tuple[int]], width: int = 140,
                           height: int = 32) -> list[list[int]]:
        """
        Draws lines based on [x, y, angle_deg, length] specs and sends the packed image to the display.

        *Make sure to set your cursor position before drawing so the display knows where to start.*

        This method takes a list of lines, where each line is defined by its starting coordinates, angle (measured
        counter-clockwise from the positive x-axis), and length (number of pixels). The method computes the pixel
        representation of the lines in a bitmap and calls `pack_bitmap` to pack the column-major format. Finally, it
        sends the processed data to the display for rendering.

        .. list-table::
          :param bitmap:
          :header-rows: 1

          * - **IMPORTANT:**
          * - Degrees is measured counter-clockwise from the positive x-axis. This means 90 degrees from left to right is actually 0 and 180 degrees top to bottom is actually 270.

        :param bitmap: A 2D list or tuple representing the bitmap to draw on.
        :type bitmap: list[list[int]]
        :param lines: A list or tuple of lines to be drawn.
        :type lines: list | tuple[list | tuple[int]]
        :param width: (optional) The width of the bitmap to draw on. (default: 140)
        :type width: int
        :param height: (optional) The height of the bitmap to draw on. (default: 32)
        :type height: int
        :return: None
        """
        # Modify the bitmap for each line:
        for x0, y0, angle_deg, length in lines:
            angle_rad = math.radians(angle_deg)
            deg_x = math.cos(angle_rad)
            deg_y = -math.sin(angle_rad)  # negative because y increases downward

            for i in range(length):
                x = int(round(x0 + deg_x * i))
                y = int(round(y0 + deg_y * i))
                if 0 <= x < width and 0 <= y < height:
                    bitmap[y][x] = 1

        return bitmap

    @staticmethod
    def draw_graphic_circle(bitmap: list[list[int]], cx: int, cy: int, radius: int, width: int = 140,
                            height: int = 32) -> list[list[int]]:
        """
        Draw a circle on a bitmap using the midpoint circle algorithm.

        This method modifies the given bitmap to draw a circle centered at the specified coordinates (x, y) with the
        specified radius. The algorithm calculates the circle's points for only one octant and uses symmetry to
        replicate the points across the other octants. The algorithm takes into account the constraints of the
        display dimensions (width and height) to ensure that the circle does not exceed the bitmap's boundaries.

        :param bitmap: The list representing the bitmap.
        :type bitmap: list[list[int]]
        :param cx: Integer coordinate for the x-center of the circle.
        :type cx: int
        :param cy: Integer coordinate for the y-center of the circle.
        :type cy: int
        :param radius: Radius of the circle, specified as an integer.
        :type radius: int
        :param width: (optional) Width of the bitmap, specified as an integer. (default: 140).
        :type width: int
        :param height: (optional) Height of the bitmap, specified as an integer. (default: 32).
        :type height: int
        :return: A modified 2D list representing the bitmap with the circle drawn on it.
        :rtype: list[list[int]]
        """
        x = radius  # Start at the far right of the circle
        y = 0  # Start at the top
        d = 1 - radius  # Decision variable to determine when to step x

        def plot(px, py):
            # Plot a pixel if it's within display bounds
            if 0 <= px < width and 0 <= py < height:
                bitmap[py][px] = 1

        while x >= y:
            # Plot all 8 symmetrical points around the center
            plot(cx + x, cy + y)  # Octant 1
            plot(cx + y, cy + x)  # Octant 2
            plot(cx - y, cy + x)  # Octant 3
            plot(cx - x, cy + y)  # Octant 4
            plot(cx - x, cy - y)  # Octant 5
            plot(cx - y, cy - x)  # Octant 6
            plot(cx + y, cy - x)  # Octant 7
            plot(cx + x, cy - y)  # Octant 8

            y += 1  # Move one step down

            if d < 0:
                # Midpoint is inside the circle — keep x the same
                d += 2 * y + 1
            else:
                # Midpoint is outside — move x inward
                x -= 1
                d += 2 * (y - x) + 1

        return bitmap

    @staticmethod
    def draw_graphic_circle_filled(bitmap: list[list[int]], cx: int, cy: int, radius: int, width: int = 140,
                                   height: int = 32) -> list[list[int]]:
        """
        Draw a filled circle on a bitmap using the midpoint circle algorithm.

        This method modifies the given bitmap to draw a circle centered at the specified coordinates (x, y) with the
        specified radius. The algorithm calculates the circle's points for only one octant and uses symmetry to
        replicate the points across the other octants. The algorithm takes into account the constraints of the
        display dimensions (width and height) to ensure that the circle does not exceed the bitmap's boundaries.

        :param bitmap: The list representing the bitmap.
        :type bitmap: list[list[int]]
        :param cx: Integer coordinate for the x-center of the circle.
        :type cx: int
        :param cy: Integer coordinate for the y-center of the circle.
        :type cy: int
        :param radius: Radius of the circle, specified as an integer.
        :type radius: int
        :param width: (optional) Width of the bitmap, specified as an integer. (default: 140).
        :type width: int
        :param height: (optional) Height of the bitmap, specified as an integer. (default: 32).
        :type height: int
        :return: A modified 2D list representing the bitmap with the circle drawn on it.
        :rtype: list[list[int]]
        """
        x = radius          # Start at the far right edge of the circle
        y = 0               # Start at the top
        d = 1 - radius      # Decision variable for midpoint algorithm

        def draw_span(y_offset: int, x_left: int, x_right: int):
            """
            Draws a horizontal span of pixels on a bitmap at a specified vertical offset relative to a central point
            with defined left and right horizontal lengths.

            :param y_offset: Vertical offset, relative to the center `cy`, where the span should be drawn.
            :type y_offset: int
            :param x_left: Number of pixels to extend to the left of the center `cx`.
            :type x_left: int
            :param x_right: Number of pixels to extend to the right of the center `cx`.
            :type x_right: int
            :return: Nothing. This nested function directly modifies the bitmap from the outer scope.
            """
            y_pos = cy + y_offset
            if 0 <= y_pos < height:  # Check vertical bounds
                for x_pos in range(cx - x_left, cx + x_right + 1):
                    if 0 <= x_pos < width:  # Check horizontal bounds
                        bitmap[y_pos][x_pos] = 1  # Set pixel ON

        # Loop through each vertical slice of the circle
        while x >= y:
            # Draw horizontal spans for each symmetrical row
            draw_span(+y, x, x)  # Top half
            draw_span(-y, x, x)  # Bottom half
            draw_span(+x, y, y)  # Right half
            draw_span(-x, y, y)  # Left half

            y += 1  # Move down one row

            # Update decision variable to determine whether to shrink x
            if d < 0:
                d += 2 * y + 1
            else:
                x -= 1
                d += 2 * (y - x) + 1

        return bitmap

    def draw_graphic_circles(self, bitmap: list[list[int]], circles: list | tuple[list | tuple[int]],
                             width: int = 140, height: int = 32) -> list[list[int]]:
        """
        Draws one or more circles on the given bitmap.

        This method iterates through a given list or tuple of circle definitions (each defined by x-coordinate,
        y-coordinate, and radius) and draws them on the provided bitmap.

        :param bitmap: The list representing the bitmap.
        :type bitmap: list[list[int]]
        :param circles: A list or tuple containing the definitions of circles.
        type circles: list | tuple[list | tuple[int]]
        :param width: (optional) Width of the bitmap, specified as an integer. (default: 140).
        :type width: int
        :param height: (optional) Height of the bitmap, specified as an integer. (default: 32).
        :type height: int
        :return: The updated bitmap after drawing the specified circles.
        :rtype: list[list[int]]
        """
        for cx, cy, radius, filled in circles:
            if not filled:
                bitmap = self.draw_graphic_circle(bitmap=bitmap, cx=cx, cy=cy, radius=radius, width=width,
                                                  height=height)
            else:
                bitmap = self.draw_graphic_circle_filled(bitmap=bitmap, cx=cx, cy=cy, radius=radius, width=width,
                                                         height=height)

        return bitmap
