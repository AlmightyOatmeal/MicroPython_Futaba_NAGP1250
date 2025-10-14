<!-- TOC -->
* [More Futaba NAGP1250 Examples](#more-futaba-nagp1250-examples)
  * [Advanced Examples](#advanced-examples)
    * [Merging graphics and text LIKE A BOSS](#merging-graphics-and-text-like-a-boss)
    * [Drawing Circles and Lines](#drawing-circles-and-lines)
    * [Merging Graphics, Text, and independent Dynamic Windows](#merging-graphics-text-and-independent-dynamic-windows)
    * [ESP32 Wi-Fi Clock](#esp32-wi-fi-clock)
    * [ESP32 Wi-Fi Clock with clock face](#esp32-wi-fi-clock-with-clock-face)
  * [Animated Graphics](#animated-graphics)
    * [Pixel Blocks](#pixel-blocks)
    * [Radial lines](#radial-lines)
    * [Filling in a circle](#filling-in-a-circle)
<!-- TOC -->

# More Futaba NAGP1250 Examples

## Advanced Examples

### Merging graphics and text LIKE A BOSS

**CODE**: [EXAMPLES/graphics_and_text_like_a_boss.py](EXAMPLES/graphics_and_text_like_a_boss.py)

![Display with lines and text LIKE A BOSS](_images/display_lines_text_LIKE_A_BOSS.jpg)

### Drawing Circles and Lines

**CODE**: [EXAMPLES/circles_lines_circuit_traces.py](EXAMPLES/circles_lines_circuit_traces.py)

![Display with circles and lines](_images/display_graphic_circles_lines.jpg)

### Merging Graphics, Text, and independent Dynamic Windows

**CODE**: [EXAMPLES/graphics_text_dynamic_windows.py](EXAMPLES/graphics_text_dynamic_windows.py)

![Display with lines, text, and dynamic windows](_images/display_lines_dynamic_windows.jpg)

### ESP32 Wi-Fi Clock

* Uses the ESP32's built-in Wi-Fi module to connect to a Wi-Fi network.
  * Leverages [Micropython WifiManager](https://github.com/mitchins/micropython-wifimanager).
* Synchronizes time with NTP
* Fetches timezone information from [WorldTimeAPI](https://worldtimeapi.org).
* Uses user-defined windows so only the portion of the display that needs updating is updated.

This example assumes `wifi_manager.py` and `networks.json` in the root directory of the ESP32 alongside the script.

**CODE**: [EXAMPLES/esp32_wifi_clock.py](EXAMPLES/esp32_wifi_clock.py)

![Example ESP32 wifi clock](_images/display_example_wifi_clock.jpg)

### ESP32 Wi-Fi Clock with clock face

Similar to the [ESP32 Wi-Fi Clock](#esp32-wi-fi-clock) example, but time-only with a clock face.

There are a couple of helper functions in the example code that can align the hour to the literal hour or move it closer to the next hour as a regular clock would.

**CODE**: [EXAMPLES/esp32_wifi_clock_clockface.py](EXAMPLES/esp32_wifi_clock_clockface.py)

![Example ESP32 wifi clock with clock face](_images/display_example_wifi_clock_clockface.jpg)

## Animated Graphics

### Pixel Blocks

This is a painfully inefficient way to generate 1x1, 2x2, and 4x4 blocks, but it works and totally gives the W.O.P.R. vibes (from the movie War Games).

**CODE**: [EXAMPLES/animated_pixel_blocks.py](EXAMPLES/animated_pixel_blocks.py)

![Display with graphic pixel blocks](_images/display_graphics_blocks.gif)

This is a much more efficient way of randomizing 1px blocks: 
```python
random_bytes = [[urandom.getrandbits(1) for _ in range(width)] for _ in range(height)]
```

### Radial lines

**CODE**: [EXAMPLES/animated_radial_lines.py](EXAMPLES/animated_radial_lines.py)

![Display with graphic radial lines](_images/display_radial_lines.gif)

(this GIF is slower than the actual example)

### Filling in a circle

**CODE**: [EXAMPLES/animated_circle_filling.py](EXAMPLES/animated_circle_filling.py)

![Display filling in a circle](_images/display_graphic_circle_filling.gif)

(this GIF is slower than the actual example)
