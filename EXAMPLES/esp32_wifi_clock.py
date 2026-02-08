from futaba import NAGP1250
import time
from machine import SPI
import ntptime
import os
import urequests
from wifi_manager import WifiManager

# Tested on:
# - MicroPython v1.26.1; LOLIN_S2_MINI
# - MicroPython v1.27.0; LOLIN_S2_MINI

#
# Basic Setup
#

if os.stat("_time_key"):
    with open("_time_key", "r") as f:
        TIME_API_KEY = f.read().strip()
else:
    TIME_API_KEY = "<API KEY>"

PIN_SIN = 33
PIN_SCK = 37
PIN_RESET = 39
PIN_SBUSY = 35

UTC_OFFSET_SEC = 0
# Set up the initial state as None until we get a valid value from the API
UPDATED_OFFSET = False
TIMEZONE = "America/Chicago"

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def do_http_get(url: str, retries: int = 50000, header: dict = None) -> dict | None:
    """
    Performs an HTTP GET request to the specified URL with a retry mechanism.

    Repeatedly attempts to fetch data from the provided URL up to the given number of retries. If the response status
    code is 200, the JSON response body is returned. Otherwise, it retries after a delay. If the maximum retry count
    is exceeded, the function returns None.

    :param url: The URL to send the HTTP GET request to.
    :type url: str
    :param retries: The maximum number of retries before stopping. Defaults to 50,000.
    :type retries: int
    :param header: (optional) Additional headers to include in the request. (default: None)
    :type header: dict | None
    :return: A dictionary representation of the JSON response if successful, or None if all retries are exhausted.
    :rtype: dict | None
    """
    retry_count = 0
    while True:
        if retry_count >= retries:
            return None

        try:
            if header:
                response = urequests.get(url=url, headers=header)
            else:
                response = urequests.get(url=url)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"[DO_HTTP_GET][ERROR] Failed to get weather data: HTTP {response.status_code}, retrying in 10 seconds...")
                print(f"[DO_HTTP_GET][DEBUG] URL: {url}")
        except Exception as e:
            print(f"[DO_HTTP_GET][ERROR] Failed to get weather data: {e}")
            print(f"[DO_HTTP_GET][DEBUG] URL: {url}")
        finally:
            retry_count += 1
            time.sleep(10)


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

    url = f"https://world-time-api3.p.rapidapi.com/timezone/{timezone}"
    response_data = do_http_get(url=url, header={'x-rapidapi-key': TIME_API_KEY})

    if response_data is not None:
        # Get offset in seconds
        utc_offset_seconds = response_data['raw_offset'] + response_data.get('dst_offset', 0)
        utc_offset_hours = utc_offset_seconds / 3600

        print(f"[INFO] Timezone offset: {utc_offset_hours} hours ({utc_offset_seconds} seconds)")
        print(f"[INFO] DST active: {response_data.get('dst', False)}")

        return utc_offset_seconds
    else:
        print(f"[ERROR] Failed to get timezone data: {response_data}")
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
            print(f"Fetching time from NTP server: {ntp_host}...")
            ntptime.settime()

            # Get current UTC time
            utc_time = time.gmtime()
            print(f"UTC time: {utc_time}")
            break
        except Exception as e:
            print(f"Failed to get NTP time: {e}")
            print("Retrying NTP time setting in 5 seconds...")
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
        print(f"Connected to {kwargs.get('ssid')} with IP {kwargs.get('ip')}")
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
        print(f"Using stored offset: {local}")

    elif event == 'disconnected':
        print("Lost WiFi connection")

    elif event == 'ap_started':
        print(f"Started access point: {kwargs.get('essid')}")

    elif event == 'connection_failed':
        print(f"Failed to connect to: {kwargs.get('attempted_networks')}")


# Add the connection handler to WifiManager
WifiManager.on_connection_change(my_connection_handler)


#
# Display Logic
#

# Leverage hardware-specific optimizations at a consistent baud rate. This display supports a
# maximum baud rate of 115,200.
spi = SPI(2, mosi=PIN_SIN, sck=PIN_SCK, baudrate=115200)

vfd = NAGP1250(spi=spi, reset=PIN_RESET, sbusy=PIN_SBUSY)

# Set up multiple windows so we only update the portion of the display that needs updating.
# Time
vfd.define_user_window(window_num=1, x=0, y=0, w=140, h=2)
# Day of week
vfd.define_user_window(window_num=2, x=0, y=2, w=60, h=2)
# Month
vfd.define_user_window(window_num=3, x=61, y=2, w=90, h=1)
# Month day and year
vfd.define_user_window(window_num=4, x=61, y=3, w=90, h=1)

# Set up an initial "waiting for Wi-Fi" message, then clear once the offset has been updated.
vfd.clear_window()
vfd.do_home()
vfd.set_font_magnification(h=2, v=2)
vfd.write_text("WAITING")
vfd.do_line_feed()
vfd.do_carriage_return()
vfd.write_text("FOR WIFI")

# Try to connect to Wi-Fi after setting the initial display message.
WifiManager.setup_network()

# Initialize core logic variables
# If we cleared the base display after Wi-Fi is connected, the initial state is false.
did_clear = False
# Set up comparison strings so we only update the display when something changes
last_written_t = ''
last_written_wday = ''

# TODO: Re-check NTP after period of time...
# 720 5-second increments is 1 hour
while True:
    if UPDATED_OFFSET:
        # Clear the base window only once
        if not did_clear:
            vfd.clear_window(window_num=0)
            did_clear = True

        # Get the current local time based on UTC offset
        year, month, day, hour, minute, sec, wday, _ = get_local_time(utc_offset_seconds=UTC_OFFSET_SEC)

        # Set up the format string
        current_t = f"{hour:02d}:{minute:02d}"

        # If the current string doesn't match the last written string, then update the display.
        if current_t != last_written_t:
            vfd.do_select_window(window_num=1)
            vfd.do_home()
            vfd.set_font_magnification(h=3, v=2)
            vfd.write_text(current_t)

            # Update the last written time string variable so the next iteration has something to compare to.
            last_written_t = current_t

        # Same as above but for the date.
        current_wday = f"{WEEKDAYS[wday]}"

        if current_wday != last_written_wday:
            vfd.do_select_window(window_num=2)
            vfd.do_home()
            vfd.set_font_magnification(h=1, v=2)
            vfd.write_text(current_wday)

            # update the last written date string
            last_written_wday = current_wday

            vfd.do_select_window(window_num=3)
            vfd.do_home()
            vfd.set_font_magnification(h=1, v=1)
            vfd.write_text(f"{MONTHS[month-1]}")

            vfd.do_select_window(window_num=4)
            vfd.do_home()
            vfd.set_font_magnification(h=1, v=1)
            vfd.write_text(f"{day}, {year}")

    time.sleep(5)
