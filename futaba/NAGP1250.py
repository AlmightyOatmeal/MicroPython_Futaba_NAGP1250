# -*- coding: utf-8 -*-
"""
Pure MicroPython driver for the Futaba NAGP1250 VFD.
"""

__author__ = "Catlin Kintsugi"

from machine import Pin
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


# noinspection GrazieInspection
class NAGP1250:
    def __init__(self,
                 sin: Pin | int,
                 sck: Pin | int,
                 reset: Pin | int = None,
                 sbusy: Pin | int = None,
                 luminance: int = 4,
                 cursor_blink: int | None = None,
                 mode: str | None = None) -> None:
        """
        Initializes the display with specified pins and settings.

        :param sin: Serial pin for communication with the display.
        :type sin: Pin | int
        :param sck: Clock pin for communication with the display.
        :type sck: Pin | int
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

        :raises ValueError: If the provided mode is invalid.
        """
        # Check to see whether we have a pin object or a pin integer
        self.pin_sin = Pin(sin, Pin.OUT) if not isinstance(sin, Pin) else sin
        self.pin_sck = Pin(sck, Pin.OUT) if not isinstance(sck, Pin) else sck
        self.pin_reset = Pin(reset, Pin.OUT) if not isinstance(reset, Pin) else reset
        self.pin_sbusy = Pin(sbusy, Pin.IN) if not isinstance(sbusy, Pin) else sbusy

        # Set pin initial states
        self.pin_sck.value(0)
        self.pin_sin.value(0)

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

    def _write_byte(self, byte: int | bytes) -> None:
        """
        Writes a single byte to a hardware interface using bit-banging.

        The byte is written the least significant bit (LSB) first. Each bit is successively shifted and sent through the
        specified data pin (SIN) while clock pulses are generated on the clock pin (SCK).

        :param byte: The byte (as an integer or bytes) to be written bit-by-bit.
        :type byte: int or bytes
        :return: None
        """
        for i in range(8):  # LSB-first
            bit = (byte >> i) & 1
            self.pin_sin.value(bit)
            time.sleep_us(1)
            self.pin_sck.value(1)
            time.sleep_us(1)
            self.pin_sck.value(0)
            time.sleep_us(1)

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

    def send_byte(self, data: bytearray | list, wait_busy: bool = True) -> None:
        """
        Sends a sequence of bytes to a specific display and optionally waits
        until the device is no longer busy after sending.

        :param data: A sequence of bytes to be sent to the device. Each byte should fall within the range of 0-255.
        :type data: bytearray | list
        :param wait_busy: (optional) Wait until the busy signal pin goes low before sending more data. (default: True)
        :type wait_busy: bool
        :return: None
        """
        for byte in data:
            # print(f"Sending byte: 0x{byte:02X} → {byte:08b}")
            self._write_byte(byte)
        if wait_busy and self.pin_sbusy:
            self._wait_for_sbusy()

    def initialize(self) -> None:
        """
        Sends an initialization command to the connected display.

        :return: None
        """
        self.send_byte(data=[0x1B, 0x40])

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
            raise ValueError("Invalid font ID")
        self.send_byte(data=[0x1B, 0x52, font_id])

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
            raise ValueError("Invalid character code")
        self.send_byte(data=[0x1B, 0x74, code])

    def set_cursor_blink(self, mode: int) -> None:
        """
        Turns the cursor blink on or off. When the cursor blink is on, it blinks at about 1Hz.

        :param mode: The cursor blink mode to set. 0 to disable blinking, 1 to enable blinking.
        :type mode: int
        :return: None
        :raises ValueError: Invalid cursor blink mode.
        """
        if not (0 <= mode <= 1):
            raise ValueError("Cursor blink must be 0–1")
        self.send_byte([0x1F, 0x43, mode])

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
            raise ValueError("Horizontal scroll speed must be 0–31")
        self.send_byte([0x1F, 0x73, speed])

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
            raise ValueError("Luminance must be 1–8")

        self.send_byte([0x1F, 0x58, luminance])

    def set_overwrite_mode(self) -> None:
        """
        Sets overwrite mode.

        :return: None
        """
        self.send_byte([0x1F, 0x01])  # MD1: Overwrite mode

    # TODO: Test
    def set_vertical_scroll(self) -> None:
        """
        Sets the vertical scroll mode.

        :return: None
        """
        self.send_byte([0x1F, 0x02])  # MD2: Vertical scroll mode

    def set_horizontal_scroll(self) -> None:
        """
        Sets the display to horizontal scroll mode.

        :return: None
        """
        self.send_byte([0x1F, 0x03])  # MD3: Horizontal scroll mode

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
            raise ValueError("Font magnification horizontal param must be 1 through 4")
        if not (1 <= v <= 4):
            raise ValueError("Font magnification vertical param must be 1 through 4")

        self.send_byte([0x1F, 0x28, 0x67, 0x40, h, v])

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
            raise ValueError("Mode must be between 0 and 3")

        self.send_byte([0x1F, 0x28, 0x67, 0x03, mode])

    # TODO: Test
    def set_cursor_position(self, x: int, y: int) -> None:
        """
        Sets the cursor position on the display to the specified x and y coordinates.

        :param x: The horizontal position for the cursor. Must be in the range 0-280.
        :type x: int
        :param y: The vertical position for the cursor. Must be in the range 0-31.
        :type y: int
        :return: None
        :raises ValueError: If x or y are out of their allowed ranges.
        """
        if not (0 <= x <= 280):
            raise ValueError("X position out of range")
        if not (0 <= y <= 31):
            raise ValueError("Y position out of range")

        payload = [
            0x1F,  # Command header
            0x24,  # Set Cursor Position
            x & 0xFF,  # X low byte
            (x >> 8) & 0xFF,  # X high byte
            y & 0xFF,  # Y low byte
            (y >> 8) & 0xFF  # Y high byte
        ]
        self.send_byte(payload)

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
            raise ValueError("Mode must be either 0 or 1")

        self.send_byte([0x1F, 0x72, mode])

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
        self.send_byte([0x0C])

    def do_blink_display(self, pattern: int, normal_time: int, blink_time: int, repetition: int) -> None:
        """
        This method controls a blinking display based on the specified pattern, normal display time, blink display
        time, and the number of repetitions.

        The time unit is approximately t*14ms.

        +----------------------------------------------------------------------------------------------------------+
        | **SEIZURE WARNING:**                                                                                     |
        +==========================================================================================================+
        | It is possible to make this screen blink at a rate that could trigger photosensitive epileptic episodes. |
        +----------------------------------------------------------------------------------------------------------+

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
            raise ValueError("Pattern needs to be 0 through 2")

        if not (1 <= normal_time <= 255):
            raise ValueError("Normal time needs to be 1 through 255")

        if not (1 <= blink_time <= 255):
            raise ValueError("Blink time needs to be 1 through 255")

        if not (1 <= repetition <= 255):
            raise ValueError("Repetition needs to be 1 through 255")

        self.send_byte([0x1F, 0x28, 0x61, 0x11, pattern, normal_time, blink_time, repetition])

    def do_home(self) -> None:
        """
        Brings the cursor to the top left of the current window.

        :return: None
        """
        self.send_byte([0x0B])

    def do_line_feed(self) -> None:
        """
        Moves the cursor to the beginning of the next line.

        :return: None
        """
        self.send_byte([0x0A])

    def do_backspace(self) -> None:
        """
        Moves the cursor back one character position.

        :return: None
        """
        self.send_byte([0x08])

    def do_horizontal_tab(self) -> None:
        """
        Sends a horizontal tab.

        :return: None
        """
        self.send_byte([0x09])

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
            raise ValueError("Wait duration must be 0–255")
        self.send_byte([0x1F, 0x28, 0x61, 0x01, duration])

    def do_select_window(self, window_num: int) -> None:
        """
        Selects a specific window for operations.

        :param window_num: The window number to select must be in the range 0–4.
        :type window_num: int
        :return: None
        :raises ValueError: If the provided window number is not in the range 0–4.
        """
        if not (0 <= window_num <= 4):
            raise ValueError("Window number must be 0–4")
        self.send_byte([0x1F, 0x28, 0x77, 0x01, window_num])

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
            raise ValueError("Screen saver must be 0 through 4")
        self.send_byte([0x1F, 0x28, 0x61, 0x40, pattern])

    def do_carriage_return(self) -> None:
        """
        Sends a carriage return to the current cursor position to bring the cursor to the beginning of the current line.

        :return: None
        """
        self._write_byte(0x0D)

    def write_text(self, text: str | list) -> None:
        """
        Writes a given string or list of characters to the output.

        Each character in the input is processed individually and converted to its corresponding byte representation.

        :param text: The input text to be written. It can be either a string or a list of characters. Each character
                     will be converted to its byte equivalent before writing.
        :type text: str | list
        :return: None
        """
        for char in text:
            self._write_byte(ord(char))

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
            raise ValueError("Window number must be 1–4")
        if not (0 <= x <= 279 or 0 <= y <= 3):
            raise ValueError("Upper-left corner out of bounds")
        if not (1 <= w <= 280 or 1 <= h <= 4):
            raise ValueError("Window size out of bounds")

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

        self.send_byte(payload)

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
            raise ValueError("Window number must be 1–4")

        # Check to see if we should clear the window before deleting it.
        if clear:
            self.clear_window(window_num=window_num)

        self.send_byte([0x1F, 0x28, 0x77, 0x02, window_num, 0x00])

    def define_base_window(self, mode: int) -> None:
        """
        Defines Window 0’s size as either 140x32 (base) or 280x32 (extended)

        `mode` options are:

        - 0 = Base
        - 1 = Extended

        :param mode: The base window mode. Valid values are 0 or 1.
        :type mode: int
        :return: None
        :raises ValueError: If the mode is outside the allowed range (0 to 1).
        """
        if not (0 <= mode <= 1):
            raise ValueError("Mode must be between 0 and 1")

        self.send_byte([0x1F, 0x28, 0x77, 0x10, mode])

    # IMAGE STUFF, *NOT WORKING*
    # TODO: Make work lolz
    def write_image(self, image_data, width, height) -> None:
        """
        Writes image data to the device with specified dimensions.

        This method constructs a command packet header and sends image data in
        8-byte chunks to a connected device over a communication interface. The
        image dimensions and data length must conform to the constraints defined
        within the method.

        :param image_data: The image data to be sent, as a sequence of bytes.
        :param width: The width of the image in pixels. Must be between 1 and 280.
        :param height: The height of the image in blocks. Each block represents 8
                       rows of pixels, and height must be between 1 and 4.
        :return: None
        :raises ValueError: If the width is not between 1 and 280.
        :raises ValueError: If the height is not between 1 and 4.
        :raises ValueError: If the image_data length does not match the product of
                            the width and height.
        """
        if not (1 <= width <= 280):
            raise ValueError("Width must be between 1 and 280")
        if not (1 <= height <= 4):
            raise ValueError("Height must be between 1 and 4")

        expected_length = width * height
        if len(image_data) != expected_length:
            raise ValueError(f"Expected {expected_length} bytes of image data, got {len(image_data)}")

        # Construct command packet header
        header = [
            0x1F,  # Command header
            0x28,
            0x66,
            0x11,
            width & 0xFF,
            (width >> 8) & 0xFF,
            height & 0xFF,
            (height >> 8) & 0xFF,
            0x1  # fixed mode
        ]
        self.send_byte(header)
        time.sleep_us(100)

        # Send image data in 8-byte chunks
        for i in range(0, len(image_data), 8):
            chunk = image_data[i:i + 8]
            self.send_byte(chunk)
            time.sleep_us(100)
