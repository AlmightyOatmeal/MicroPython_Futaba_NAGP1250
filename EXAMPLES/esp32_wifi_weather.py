from futaba import NAGP1250
from futaba.NAGP1250 import WRITE_MODE_NORMAL, WRITE_MODE_XOR
import json
from machine import SPI
import ntptime
import time
import urequests
from wifi_manager import WifiManager

# Tested on:
# - MicroPython v1.26.1; LOLIN_S2_MINI

#
# Basic Setup
#

# Sign up for a free account at https://openweathermap.org/ to get your API key. It took about a half hour for my
# API key to become active, which was a small annoyance, but it was worth the wait.
OPENWEATHER_API_KEY = "<API KEY>"

# https://openweathermap.org/current#name
WX_CITY = "Milwaukee,US"
WX_LANG = "EN"
WX_UNITS = "metric"
# WX_UNITS = "imperial"

# Time timezone from https://worldtimeapi.org/api/timezone/
TIMEZONE = "America/Chicago"

# SPI pins for the NAGP1250 display.
PIN_SIN = 33
PIN_SCK = 37
PIN_RESET = 39
PIN_SBUSY = 35

#
# Core setup, you shouldn't have to touch this unless you want to change the names to match your language.
#
UTC_OFFSET_SEC = 0
# Set up the initial state as None until we get a valid value from the API
UPDATED_OFFSET = False

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]

# https://openweathermap.org/weather-conditions
#
# I downloaded SVGs and converted them to PNGs (in Python using `cairosvg`) and then resized them to 32px and converted
# those to bitmap arrays (in Python using `Pillow` and `numpy`) then stored the bitmap arrays in .json files. I copied
# the .json files do the ESP32 filesystem under `/weather/32` (I created directories for multiple sizes); for example,
# the icon `forecast-weather-sun-sunny-hot-summer` is stored in `/weather/32/forecast-weather-sun-sunny-hot-summer.json`.
ICON_MAP = {
    "01": {  # clear sky
        "d": "forecast-weather-sun-sunny-hot-summer",
        "n": "moon-night-stars"
    },
    "02": {  # few clouds
        "d": "forecast-weather-sun-cloud",
        "n": "forecast-weather-night-cloud-moon"
    },
    "03": {  # scattered clouds
        "d": "forecast-weather-sun-cloud",
        "n": "forecast-weather-night-cloud-moon"
    },
    "04": {  # broken clouds
        "d": "forecast-weather-sun-cloud",
        "n": "forecast-weather-night-cloud-moon"
    },
    "09": {  # shower rain
        "d": "forecast-weather-day-rain-sun-cloud",
        "n": "forecast-weather-night-rain-moon-cloud"
    },
    "10": {  # rain
        "d": "forecast-weather-day-rain-sun-cloud",
        "n": "forecast-weather-night-rain-moon-cloud"
    },
    "11": {  # thunderstorm
        "d": "forecast-weather-day-storm-lightning-bolt-cloud-sun",
        "n": "forecast-weather-night-storm-lightning-bolt"
    },
    "13": {  # snow
        "d": "forecast-weather-snow-cloud-winter-cold-day",
        "n": "forecast-weather-snow-cloud-winter-cold-night"
    },
    "50": {  # mist
        "d": "forecast-cloud-fog-foggy-weather",
        "n": "forecast-fog-foggy-night"
    }
}


#
# Weather Logic
#
def get_raw_weather_data(city: str, lang: str = "EN", units: str = "metric") -> dict:
    """
    Fetches raw weather data for a specified city using the OpenWeather API.

    If the API fails to respond successfully, the function enters a retry loop with a delay of 10 seconds between
    each attempt.

    :param city: The name of the city for which to retrieve weather data.
    :type city: str
    :param lang: (optional) A two-letter language code. (default: "EN")
    :type lang: str
    :param units: (optional) The measurement units to use for output. (default is "metric")
    :type units: str
    :return: A dictionary containing the raw weather data in JSON format.
    :rtype: dict
    """
    params_dict = {
        "q": city,
        "APPID": OPENWEATHER_API_KEY,
        "lang": lang,
        "units": units
    }
    # This turns the above dict into a parameterized string like:
    # >>> 'q=Chicago,US&APPID=tacocat&lang=EN&units=METRIC'
    params_str = '&'.join([f"{k}={v}" for k, v in params_dict.items()])

    url = f"https://api.openweathermap.org/data/2.5/weather?{params_str}"
    while True:
        response = urequests.get(url=url)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"[ERROR] Failed to get weather data: HTTP {response.status_code}, retrying in 10 seconds...")
            print(f"[DEBUG] URL: {url}")
            time.sleep(10)


def get_weather_data(city: str, lang: str = "EN", units: str = "metric") -> tuple[str, float, int]:
    """
    Fetches and processes weather data from an external API.

    :param city: The name of the city for which to retrieve weather data.
    :type city: str
    :param lang: (optional) A two-letter language code. (default: "EN")
    :type lang: str
    :param units: (optional) The measurement units to use for output. (default is "metric")
    :type units: str
    :return: A tuple containing the processed weather icon, the temperature, and the humidity level.
    :rtype: tuple[str, float, int]
    """
    raw_data = get_raw_weather_data(city=city, lang=lang, units=units)
    # Raw data from the API looks like this: https://openweathermap.org/current#example_JSON

    # Pro-tip when working with nested dicts/lists, if you chain calls together like this, then set the default value
    # to an empty data structure that you expect to see in the next call to prevent it from erroring out.
    # `<dict>.get()` returns `None` by default, but you can specify what to return if the key is not found.
    wx = raw_data.get("weather", [{}])[0]
    # Because the above returned an array, calling `[0]` to get the first element is value and returns an empty dict.
    # When the below call is made on that empty dict, `None` is returned, and we can deal with that later in the code.
    wx_icon = wx.get("icon")

    wx_main = raw_data.get("main", {})
    wx_temp = wx_main.get("temp")
    print(f"[DEBUG] wx_temp: {wx_temp}")
    wx_humidity = wx_main.get("humidity")
    print(f"[DEBUG] wx_humidity: {wx_humidity}")

    # icon prefix and day/night
    icon_sel = None
    dn = None
    wx_display_icon = None
    if wx_icon is not None:
        # Get the first two characters of the icon string to know what weather icon to use from the `ICON_MAP` dict.
        icon_sel = wx_icon[:2]
        # Get the last character of the icon string to know what day/night icon to use from the `ICON_MAP` dict.
        dn = wx_icon[-1]

        print(f"[DEBUG] icon: {icon_sel} ({dn})")

        # Finally, select the appropriate icon from the `ICON_MAP` dict and select the appropriate day (d) or night (n) icon.
        wx_display_icon = ICON_MAP.get(icon_sel, {}).get(dn)

    return wx_display_icon, wx_temp, wx_humidity


#
# NTP Logic
#
def get_timezone_offset(timezone):
    """
    Retrieve the timezone offset in seconds for a given timezone using the World Time API.

    This function connects to the external World Time API to fetch information about the given timezone. If
    successful, it calculates the offset in seconds by summing the raw offset and the Daylight Saving Time (DST)
    offset, if applicable.

    The function returns the offset in seconds if the operation is successful or `False` if the API request fails.

    :param timezone: The name of the timezone to fetch data for.
    :type timezone: str
    :return: Timezone offset in seconds if successful, or `False` if the request fails.
    :rtype: Union[int, bool]
    """
    # Get timezone offset from worldtimeapi.org
    print(f"[INFO] Getting timezone offset for {timezone}...")

    # This API also supports HTTP if HTTPS is not working correctly.
    response = urequests.get(f"https://worldtimeapi.org/api/timezone/{timezone}")

    if response.status_code == 200:
        response_data = response.json()

        # Get offset in seconds
        utc_offset_seconds = response_data['raw_offset'] + response_data.get('dst_offset', 0)
        utc_offset_hours = utc_offset_seconds / 3600

        print(f"[INFO] Timezone offset: {utc_offset_hours} hours ({utc_offset_seconds} seconds)")
        print(f"[INFO] DST active: {response_data.get('dst', False)}")

        return utc_offset_seconds
    else:
        print(f"[ERROR] Failed to get timezone data: HTTP {response.status_code}")
        return False


def set_ntp_time_utc(ntp_host="pool.ntp.org"):
    """
    Sets the system time to UTC using an NTP server.

    This function configures the NTP host and continuously attempts, until successful, to fetch and set the
    current UTC time from the provided or default NTP server. In the event of failure due to network issues
    or other errors, a retry will occur after a 5-second delay until a successful time synchronization is achieved.

    :param ntp_host: The host address of the NTP server to synchronize
        the time from. Defaults to "pool.ntp.org".
    :type ntp_host: str
    :return: None
    """
    ntptime.host = ntp_host

    while True:
        try:
            # Get UTC time from NTP
            print(f"[INFO] Fetching time from NTP server: {ntp_host}...")
            ntptime.settime()

            # Get current UTC time
            utc_time = time.gmtime()
            print(f"[INFO] UTC time: {utc_time}")
            break
        except Exception as e:
            print(f"[ERROR] Failed to get NTP time: {e}")
            print("[INFO] Retrying NTP time setting in 5 seconds...")
            time.sleep(5)


def get_local_time(utc_offset_seconds=0):
    """Fetches the local time adjusted by the supplied UTC offset in seconds.

    :param utc_offset_seconds: (optional) Number of seconds to shift the UTC time to get the local time. (default: 0)
    :type utc_offset_seconds: int
    :return: The local time adjusted by the specified UTC offset as a time.struct_time object.
    :rtype: time.struct_time
    """
    utc_time = time.gmtime()
    utc_timestamp = time.mktime(utc_time)
    local_timestamp = utc_timestamp + utc_offset_seconds
    return time.localtime(local_timestamp)


#
# Setup Micropython WifiManager
# https://github.com/mitchins/micropython-wifimanager
#

# Set up a connection handler to update NTP once Wi-Fi is connected
def my_connection_handler(event, **kwargs):
    """
    Handles WiFiManager connection events and processes associated tasks such as updating the time and timezone offset
    based on the event type. This function supports different event types including 'connected', 'disconnected',
    'ap_started', and 'connection_failed', performing actions accordingly.

    :param event: The type of connection event.
    :type event: str
    :param kwargs: Arbitrary keyword arguments that provide additional context based on the event type. For example,
                   this may include parameters such as `ssid`, `ip`, `essid`, and `attempted_networks`.
    :type kwargs: dict
    :return: None
    """
    global UPDATED_OFFSET
    global UTC_OFFSET_SEC

    if event == 'connected':
        print(f"[INFO] Connected to {kwargs.get('ssid')} with IP {kwargs.get('ip')}")
        # Settle time to avoid connection issues
        time.sleep(5)

        # When we're connected, trigger getting the timezone offset and NTP time

        # Enter a loop trying to get the current timezone offset until we have a valid value
        while not UPDATED_OFFSET:
            UTC_OFFSET_SEC = get_timezone_offset(timezone="America/Chicago")
            if UTC_OFFSET_SEC is not False:
                UPDATED_OFFSET = True
            time.sleep(5)

        # Set microcontroller time via NTP
        set_ntp_time_utc()
        # We will use the offset later to display localtime.

        # Example of printing the local time tuple
        local = get_local_time(utc_offset_seconds=UTC_OFFSET_SEC)
        print(f"[INFO] Using stored offset: {local}")

    elif event == 'disconnected':
        print("[INFO] Lost WiFi connection")

    elif event == 'ap_started':
        print(f"[INFO] Started access point: {kwargs.get('essid')}")

    elif event == 'connection_failed':
        print(f"[INFO] Failed to connect to: {kwargs.get('attempted_networks')}")


# Add the connection handler to WifiManager
WifiManager.on_connection_change(my_connection_handler)


#
# Display Logic
#

# Leverage hardware-specific optimizations at a consistent baud rate. This display supports a
# maximum baud rate of 115,200.
spi = SPI(2, mosi=PIN_SIN, sck=PIN_SCK, baudrate=115200)

vfd = NAGP1250(spi=spi, reset=PIN_RESET, sbusy=PIN_SBUSY)

# Set up an initial "waiting for Wi-Fi" message, then clear once the offset has been updated.
# But first, an adorable icon is displayed along with the text, uwu.
bitmap = [
    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0],
    [0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    [0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
]

data = vfd.pack_bitmap(bitmap=bitmap, width=45, height=32)

vfd.define_user_window(window_num=1, x=0, y=0, w=46, h=2)
vfd.define_user_window(window_num=2, x=50, y=1, w=93, h=2)

vfd.do_select_window(window_num=1)
vfd.do_home()
vfd.display_graphic_image(image_data=data, width=45, height=32)

vfd.do_select_window(window_num=2)
# vfd.do_home()
vfd.set_font_magnification(h=1, v=1)
vfd.write_text('WAITING')
vfd.do_line_feed()
vfd.do_carriage_return()
vfd.write_text('FOR WIFI')

# Try to connect to Wi-Fi after setting the initial display message.
WifiManager.setup_network()

# Initialize core logic variables
# If we cleared the base display after Wi-Fi is connected, the initial state is false.
did_clear = False

# Only read from the filesystem if the icon changes
last_icon = ''

# Only update the weather every 5 minutes to save on API calls.
wx_update_counter = 0
wx_initial_load = False
while True:
    if UPDATED_OFFSET:
        # Clear the base window only once
        if not did_clear:
            # Remove the user-defined windows from the "waiting for Wi-Fi" message
            vfd.delete_user_window(window_num=1, clear=True)
            vfd.delete_user_window(window_num=2, clear=True)
            vfd.clear_window(window_num=0)
            did_clear = True

            # Set up a window for the time display since that will be updated frequently, and we don't want to
            # re-draw the base display every time.
            vfd.define_user_window(window_num=1, x=32, y=2, w=75, h=2)
            # Window for the humidity box
            vfd.define_user_window(window_num=2, x=110, y=0, w=29, h=1)

        # Only update the weather every 5 minutes to save on API calls.
        wx_update_counter += 1
        if wx_update_counter >= 5 or not wx_initial_load:
            vfd.do_select_window(window_num=0)

            print("[INFO] updating weather data...")
            # Create a bitmap big enough for the humidity box
            humidity_width = 29
            humidity_height = 8
            bitmap = [[0 for _ in range(humidity_width)] for _ in range(humidity_height)]
            bitmap = vfd.draw_graphic_box(bitmap=bitmap, x=0, y=0, width=humidity_width, height=humidity_height, radius=5, fill=True)
            packed = vfd.pack_bitmap(bitmap=bitmap, width=humidity_width, height=humidity_height)
            vfd.do_select_window(window_num=2)
            vfd.clear_window(window_num=2)
            vfd.display_graphic_image(image_data=packed, width=humidity_width, height=humidity_height)

            # Give the display some processing time.
            time.sleep_ms(3)

            vfd.do_select_window(window_num=0)

            if not wx_initial_load:
                wx_initial_load = True

            display_icon, temp, humidity = get_weather_data(city=WX_CITY, units=WX_UNITS)
            wx_update_counter = 0

            # Load the icon bitmap from the filesystem and display it, but only if it's different from the previous
            # iteration and a valid value was returned.
            if display_icon != last_icon and display_icon is not None:
                print(f"[INFO] updating weather icon: {display_icon}")
                with open(f"/weather/32/{display_icon}.json", 'r') as f:
                    icon_bitmap = json.loads(f.read())
                last_icon = display_icon

                icon_data = vfd.pack_bitmap(bitmap=icon_bitmap, width=32, height=32)
                vfd.do_select_window(window_num=0)
                vfd.do_home()
                vfd.display_graphic_image(image_data=icon_data, width=32, height=32)

            # Give the display some processing time.
            time.sleep_ms(3)

            vfd.do_select_window(window_num=0)
            vfd.set_cursor_position(x=32, y=0)
            vfd.set_font_magnification(h=2, v=2)
            # Assign the formatted string to a variable, so we call it multiple times without going through the
            # extra steps of string formatting.
            temp_formatted = f"{temp:.1f}"
            # Write the temp to the display
            vfd.write_text(temp_formatted)

            # Set the string length to a variable so we don't have to waste cpu cycles calculating the length
            # multiple times
            temp_formatted_len = len(temp_formatted)

            # Set the spacing for the degrees and units based on the length of the temperature string.
            deg_cursor_pos = 75  # defaults if temp is like <int>.<int> (3 characters)
            if temp_formatted_len == 4:  # if temp is <int><int>.<int> (4 characters)
                deg_cursor_pos = 88
            elif temp_formatted_len == 5:  # mmmm, toasty (5 characters)
                deg_cursor_pos = 103

            # Add the degree symbol on row 0 and the temp unit on row 1 below it.
            vfd.set_font_magnification(h=1, v=1)
            vfd.set_cursor_position(x=deg_cursor_pos, y=0)
            # This is the degree symbol 0xF8 based on the international character code set as outlined in
            # the datasheet.
            vfd.write_text(chr(248))

            unit = "?"  # default unit to ? for the weather API "standard" unit -- I didn't research to what it was.
            if WX_UNITS == "metric":
                unit = "C"
            elif WX_UNITS == "imperial":
                unit = "F"
            # Align the unit right below the degree symbol.
            vfd.set_cursor_position(x=deg_cursor_pos, y=1)
            vfd.write_text(f"{unit}")

            # Give the display some processing time.
            time.sleep_ms(3)

            # Add the humidity to the beveled box but switch mode to XOR so the text will appear inverted! Cool, huh? ;-)
            vfd.do_select_window(window_num=2)
            # Set cursor relative to the active window ;-)
            vfd.set_cursor_position(x=4, y=0)
            vfd.set_write_logic(mode=WRITE_MODE_XOR)
            vfd.set_font_magnification(h=1, v=1)
            vfd.write_text(f"{humidity}%")
            vfd.set_write_logic(mode=WRITE_MODE_NORMAL)

            # Give the display some processing time.
            time.sleep_ms(3)

        # Update the time in the user-defined window to prevent the flicker of a full display update.
        vfd.do_select_window(window_num=1)
        vfd.do_home()
        vfd.set_font_magnification(h=2, v=2)
        lt = get_local_time(UTC_OFFSET_SEC)
        print(f"[DEBUG] local time: {lt}")
        formatted_time_str = f"{lt[3]:02}:{lt[4]:02}"
        print(f"[INFO] sending time: {formatted_time_str}")
        vfd.write_text(formatted_time_str)

    # Update the time every interval, but I would recommend updating the weather every 5, or more, minutes to save on
    # the number of API calls made and to keep it under the 1,000 API call limit for a free plan. If you reduce this
    # number, then update the logic above for the number of updates before the weather gets updated; for example, if
    # this gets changed to 30 seconds, then update the weather check to 10 instead of 5 to keep it at 5 minutes.
    time.sleep(60)
