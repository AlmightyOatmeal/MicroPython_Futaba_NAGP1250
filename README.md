<!-- TOC -->
* [MicroPython Futaba NAGP1250 VFD display driver](#micropython-futaba-nagp1250-vfd-display-driver)
  * [Datasheets](#datasheets)
  * [Display Configuration](#display-configuration)
    * [Jumpers](#jumpers)
    * [Interface](#interface)
  * [Example Wiring for an ESP32 S2 Mini](#example-wiring-for-an-esp32-s2-mini)
  * [Example Code](#example-code)
    * [Basic Text](#basic-text)
    * [International Text](#international-text)
    * [Font Magnification](#font-magnification)
      * [BIG](#big)
      * [Horizontal span 2, Vertical span 1](#horizontal-span-2-vertical-span-1)
      * [Horizontal span 1, Vertical span 2](#horizontal-span-1-vertical-span-2)
    * [Horizontal Scrolling](#horizontal-scrolling)
    * [Horizontal Scroll Speed](#horizontal-scroll-speed)
    * [User-Defined Windows](#user-defined-windows)
    * [User-Defined Windows with Mixed Magnifications](#user-defined-windows-with-mixed-magnifications)
    * [User-Defined Windows with Scrolling](#user-defined-windows-with-scrolling)
* [TODO](#todo)
* [Thank You <3](#thank-you-3)
<!-- TOC -->

# MicroPython Futaba NAGP1250 VFD display driver

**Built on MicroPython 1.25.0.**

This is a relatively quick driver I wrote for the NAGP1250-BA display that I have using synchronous serial communications based off its datasheet and then supplemented with the correct datasheet lol.

This is my first driver, so please be gentle with me. :^)

There are some minor differences between the various submodels (AA, AB, BA, BB), and I started writing this driver using features that my display didn't currently support. This driver doesn't differentiate, so if a feature doesn't work correctly, then it's possible the display does not support the feature or the code might need updating.

## Datasheets

Each datasheet provides a different perspective on the display, aside from command differences, so both are worth looking at even if you're using the slightly less feature-rich -BA display like I am.

* [Futaba-04-20-2020-NAGP1250AB-0-1839372.pdf](_datasheets/Futaba-04-20-2020-NAGP1250AB-0-1839372.pdf)
* [dbFutaba_MFD-M_NAGP1250_EN.pdf](_datasheets/dbFutaba_MFD-M_NAGP1250_EN.pdf)

## Display Configuration

For my example, I'm using the synchronous serial interface which needs only JP2 shorted (this is the default for how my display came) that uses the 6-pin CN2 header located at the bottom of the board. While you can solder wires directly to these holes, I do not recommend it and would suggest soldering a 6-pin header.

CN2 pin 1 is located at the far right when looking at the back, which is indicated by a mark right by the CN2 label.

[![Futaba Display Back](_images/display-marked.jpg)](_images/display-marked.jpg)

### Jumpers

Mine are configured for synchronous serial with J2 shorted, and that is how I designed this driver with that in mind.

| J0      | J1      | J2      | J3      | Function                                                                                                                                                         |
|---------|---------|---------|---------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| open    | open    | open    | X       | Asynchronous serial at 38400 baud                                                                                                                                |
| shorted | open    | open    | X       | Asynchronous serial at 19200 baud                                                                                                                                |
| open    | shorted | open    | X       | Asynchronous serial at 9600 baud                                                                                                                                 |
| shorted | shorted | open    | X       | Asynchronous serial at 115200 baud                                                                                                                               |
| x       | x       | shorted | X       | Synchronous serial                                                                                                                                               |
| x       | x       | x       | shorted | Self-test image displayed at power-up and after a reset for about 4 seconds before the all dots on screen saver is displayed. (image includes software revision) |

(x = ignored)

### Interface

Keep in mind the display itself uses 5v logic and some MCU's, like the ESP32 and Raspberry Pi Pico, use 3.3v logic, so a bi-directional level shifter is needed.

My Arduino's use 5v logic, so no level shifter is needed, but you should check your MCU specifications/datasheet to make sure you whether you need a level shifter.

For synchronous serial, four of the six pins are used for communication and control, two of them are +5v and GROUND. Using SBUSY and RESET lines is optional, but I would recommend using them.

| Pin | Signal       |
|-----|--------------|
| 1   | VCC (+5v DC) |
| 2   | SIN          |
| 3   | GROUND       |
| 4   | SBUSY        |
| 5   | SCK          |
| 6   | /RESET       |

The maximum SCK frequency is 2.45mhz; my MCU has a theoretical SCK speed of 44mhz, so I tried to adjust timings to slow down that speed, but your MCU might be different and timings adjusted. If you would like to test your SCK frequency, you can use this MicroPython code:

```python
import time
from futaba import NAGP1250

vfd = NAGP1250(sin=33, sck=37, reset=39, sbusy=35)

pulses = 1000

# Warm-up
vfd.pin_sck.value(0)
time.sleep_ms(10)

# Start timing
start = time.ticks_us()
for _ in range(pulses):
    vfd.pin_sck.value(1)
    time.sleep_us(100)
    vfd.pin_sck.value(0)
    time.sleep_us(100)
end = time.ticks_us()

elapsed_us = time.ticks_diff(end, start)
freq = pulses / (elapsed_us / 1_000_000)  # Hz

print(f"SCK pulses: {pulses}")
print(f"Elapsed time: {elapsed_us} µs")
print(f"Estimated SCK frequency: {freq:.2f} Hz")
```

## Example Wiring for an ESP32 S2 Mini

I used the ESP32 S2 Mini because the dev board because it's pretty but has a built-in voltage regulator. This dev board can be powered from +5v DC through the VBUS-pin, or it can supply +5v DC through the VBUS pin when the dev board is powered via USB.

This MCU does use 3.3v logic, so a level shifter is needed; I used a simple 4-channel bidirectional shifter from HiLetgo. While any level shifter should work, some have different wiring and/or have an enable-pin, so please refer to your level shifter's documentation and wire accordingly.

Remember to load MicroPython on your MCU! ;-)

[![Futaba Display ESP32 S2 Mini wiring diagram](_images/futaba_esp32_wiring.png)](_images/futaba_esp32_wiring.png)

## Example Code

I tried to document the code as much as possible while including some key details from the datasheets. 

### Basic Text

```python
from futaba import NAGP1250

vfd = NAGP1250(sin=33, sck=37, reset=39, sbusy=35)
n = [chr(i) for i in range(128)]
vfd.write_text(text=n)
```

![Display with alphabet](_images/display_alphabet.jpg)

### International Text

The datasheets will be delightfully confusing, but this helps test some of the character maps.

```python
from futaba import NAGP1250
from futaba.NAGP1250 import CHAR_CODE_KATAKANA

vfd = NAGP1250(sin=33, sck=37, reset=39, sbusy=35)
vfd.set_character_code(code=CHAR_CODE_KATAKANA)

chars = list(range(0x80, 0xFF))
vfd.send_byte(data=chars)
```

![Display with japanese letters](_images/display_international.jpg)

### Font Magnification

You can have characters occupy up to two columns and up to two rows to give each character a 4x4 area. 

#### BIG

```python
from futaba import NAGP1250

vfd = NAGP1250(sin=33, sck=37, reset=39, sbusy=35)
vfd.set_font_magnification(h=2, v=2)
vfd.write_text(text="Hello, World!")
```

![Display with large letters](_images/display_big_letters.jpg)

#### Horizontal span 2, Vertical span 1

```python
from futaba import NAGP1250

vfd = NAGP1250(sin=33, sck=37, reset=39, sbusy=35)
vfd.set_font_magnification(h=2, v=1)
vfd.write_text(text="Hello, World!")
```

![Display with letters h2 v1](_images/display_h2_v1.jpg)

(my camera shutter speed didn't capture the whole image)

#### Horizontal span 1, Vertical span 2

```python
from futaba import NAGP1250

vfd = NAGP1250(sin=33, sck=37, reset=39, sbusy=35)
vfd.set_font_magnification(h=1, v=2)
vfd.write_text(text="Hello, World!")
```

![Display with letters h1 v2](_images/display_h1_v2.jpg)

### Horizontal Scrolling

It's a little hard to demonstrate it in still photos, but trust me, it works. ;-)

```python
from futaba import NAGP1250

vfd = NAGP1250(sin=33, sck=37, reset=39, sbusy=35)
vfd.set_horizontal_scroll()
vfd.set_font_magnification(h=2, v=2)
vfd.write_text(text="Hello, World!")
```

![Display with after horizontal scrolling](_images/display_scroll.jpg)

### Horizontal Scroll Speed

Scroll speed is approximately `S * 14ms per column` and the speed settings range from 1 to 31; 1 seems plenty fast, so maybe I need to slow the clock rate down. 

```python
from futaba import NAGP1250

vfd = NAGP1250(sin=33, sck=37, reset=39, sbusy=35)
vfd.set_horizontal_scroll()
vfd.set_horizontal_scroll_speed(speed=1)
vfd.set_font_magnification(h=2, v=2)
vfd.write_text(text="Hello, World!")
```

It's like the above but much more calm.

### User-Defined Windows

```python
from futaba import NAGP1250

vfd = NAGP1250(sin=33, sck=37, reset=39, sbusy=35)

vfd.define_user_window(window_num=1, x=0, y=0, w=140, h=3)
vfd.define_user_window(window_num=2, x=0, y=3, w=140, h=1)

vfd.do_select_window(window_num=1)
vfd.set_font_magnification(h=2, v=2)
vfd.write_text("( . )( . )")

vfd.do_select_window(window_num=2)
vfd.set_font_magnification(h=1, v=1)
vfd.write_text("    Hello, World!")
```

![Display with windows and mixed font sizes](_images/display_user_windows_mixed_font.jpg)


### User-Defined Windows with Mixed Magnifications

```python
from futaba import NAGP1250

vfd = NAGP1250(sin=33, sck=37, reset=39, sbusy=35)

vfd.define_user_window(window_num=1, x=0, y=0, w=140, h=2)
vfd.define_user_window(window_num=2, x=0, y=2, w=140, h=2)

vfd.do_select_window(window_num=1)
vfd.set_font_magnification(h=2, v=2)
vfd.write_text("Hello")

vfd.do_select_window(window_num=2)
vfd.set_font_magnification(h=1, v=2)
vfd.write_text("Hello, World!")
```

![Display with windows and mixed font magnifications](_images/display_user_windows_mixed_mag.jpg)

### User-Defined Windows with Scrolling

```python
from futaba import NAGP1250

vfd = NAGP1250(sin=33, sck=37, reset=39, sbusy=35)

vfd.define_user_window(window_num=1, x=0, y=0, w=140, h=3)
vfd.define_user_window(window_num=2, x=0, y=3, w=140, h=1)

vfd.do_select_window(window_num=1)
vfd.set_font_magnification(h=2, v=2)
vfd.write_text("( . )( . )")

vfd.do_select_window(window_num=2)
vfd.set_font_magnification(h=1, v=1)
vfd.set_horizontal_scroll()
vfd.set_horizontal_scroll_speed(speed=1)
vfd.write_text("Hello, World! Hello, World! Hello, World! Hello, World!")
```

![Display with windows and window scrolling](_images/display_user_window_scrolling.jpg)

# TODO

* [ ] Automatically build code documentation from in-code rST docstrings.
* [ ] Add support for more commands.
* [ ] Add support for graphics.
* [ ] Add additional examples.
* [ ] Add abstractions for doing cool things.
* [ ] Add framebuffer support.
* [ ] Add specific delays in writing data for various speeds of MCU.
* [ ] Optimize code so it has a smaller footprint.

# Thank You <3

A special thanks to [Murphy's Surplus](https://murphyjunk.net) for providing these beautiful displays at an incredible price and for having next level customer service!

![Display showing Murphy's Surplus](_images/display_murphys_surplus.jpg)
