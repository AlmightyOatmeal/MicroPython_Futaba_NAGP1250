<!-- TOC -->
* [Helper Tools](#helper-tools)
  * [Convert SVG to PNG](#convert-svg-to-png)
  * [Convert PNG to Bitmap](#convert-png-to-bitmap)
<!-- TOC -->

# Helper Tools

## Convert SVG to PNG

This assumes the glyphs are black and white and to your liking.

```python
import os
from cairosvg import svg2png

svg_path = os.path.join(os.getcwd(), 'weather_glyphs')
png_path = os.path.join(os.getcwd(), 'weather_glyphs_png')
if not os.path.exists(png_path):
    os.mkdir(png_path)

for file in os.listdir(svg_path):
    print(file)
    if file.endswith(".svg"):
        svg2png(
            url=os.path.join(svg_path, file),
            write_to=os.path.join(png_path, file.replace('.svg', '.png')),
            background_color='white'
        )
```

## Convert PNG to Bitmap

This saves three different sizes of bitmap arrays, 32x32, 24x24, and 16x16. 

```python
import os
import json
from PIL import Image, ImageOps
import numpy


def json_min(data):
    """Converts Python dict or list/set/array objects to a minified JSON string.
    :param data: Python iter object like dict, list, set, array, tuple, etc.
    :type data: dict, list, set, array, tuple
    :param encoder: (optional) Custom JSON encoder class that's an extension of `json.JSONEncoder`.
                    (default: CustomJSONEncoder)
    :type encoder: json.JSONEncoder
    :return: Minified JSON string.
    :rtype: str
    """
    return json.dumps(data, separators=(',', ":"))


png_path = os.path.join(os.getcwd(), 'weather_glyphs_png')


for file in os.listdir(png_path):
    if file.endswith(".png"):
        print(f"file = {file}")

        for sz in [32, 24, 16]:
            if not os.path.exists(os.path.join(png_path, str(sz))):
                os.mkdir(os.path.join(png_path, str(sz)))

            print(f"\tsz = {sz}")
            img = Image.open(os.path.join(png_path, file)).convert("1")

            # Sampling filters: Image.NEAREST, Image.BOX, Image.BILINEAR, Image.HAMMING, Image.BICUBIC, Image.LANCZOS
            img = img.resize((sz, sz), Image.NEAREST)

            img_array = numpy.array(ImageOps.invert(img))
            # Binarize the image based on the threshold
            bitmap_array = img_array.astype(int)
            # Convert to a Python list for compatibility
            bitmap_list = bitmap_array.tolist()

            json_path = os.path.join(png_path, str(sz), file.replace('.png', '.json'))
            with open(json_path, 'w') as f:
                f.write(json_min(bitmap_list))
```
