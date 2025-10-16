from futaba import NAGP1250
import time
from machine import SPI
import ntptime
import urequests
from wifi_manager import WifiManager

# Tested on:
# - MicroPython v1.26.1; LOLIN_S2_MINI

#
# Basic Setup
#

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
    print(f"Getting timezone offset for {timezone}...")

    # This API also supports HTTP if HTTPS is not working correctly.
    response = urequests.get(f"https://worldtimeapi.org/api/timezone/{timezone}")

    if response.status_code == 200:
        data = response.json()

        # Get offset in seconds
        utc_offset_seconds = data['raw_offset'] + data.get('dst_offset', 0)
        utc_offset_hours = utc_offset_seconds / 3600

        print(f"Timezone offset: {utc_offset_hours} hours ({utc_offset_seconds} seconds)")
        print(f"DST active: {data.get('dst', False)}")

        return utc_offset_seconds
    else:
        print(f"Failed to get timezone data: HTTP {response.status_code}")
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
# Helper Functions
#
def modify_angle_ccw_x_axis(angle: float):
    """
    Modify an angle in degrees measured counter-clockwise (CCW) from the x-axis.

    Because `draw_graphic_lines()` rotates the input angle counter-clockwise (CCW) from the x-axis, this function
    adjusts an input angle to align with the counter-clockwise rotation from the x-axis.

    :param angle: Angle in degrees to be modified.
    :type angle: float
    :return: The angular position in degrees within 0 to 360 range.
    :rtype: float
    """
    return (90 - angle) % 360


def time_position_minutes(minutes: int, align_to_five_minutes: bool = False):
    """
    Calculate the angular position on a clock face based on the given time in
    minutes. Optionally align to the nearest 5-minute mark.

    :param minutes: The number of minutes for which the angular position should be calculated.
    :type minutes: int
    :param align_to_five_minutes: (optional) Whether to align the minutes to the nearest 5-minute mark. (default: False)
    :type align_to_five_minutes: bool
    :return: The angular position in degrees within 0 to 360 range.
    :rtype: float
    """
    if not align_to_five_minutes:
        # 360° / 60 minutes = 6° per minute
        return minutes * 6
    else:
        # rounded minutes to the nearest 5-minute mark
        return (round(minutes / 5) * 5) * 6


def time_position_hours(hours: int):
    """
    Calculates the angular position on a circular clock face represented in degrees
    for a given hour. The position is calculated based on the standard 12-hour
    clock format.

    :param hours: The number of hours for which the angular position should be calculated.
    :type hours: int
    :return: The angular position in degrees within 0 to 360 range.
    :rtype: int
    """
    # 360° / 12 hours = 30° per hour
    return (hours % 12) * 30


def time_position_hours_with_minutes(hours: int, minutes: int):
    """
    Calculates the angular position of the hour hand on a clock, factoring in both
    the hour and the contribution of the minutes. The function considers a
    12-hour clock format where each hour represents 30 degrees. The minutes further
    adjust the hour hand proportionally.

    :param hours: The hour value on the clock, where valid ranges are between
        0-11. Can exceed 11, but will be automatically adjusted to fit a 12-hour
        format.
    :type hours: int
    :param minutes: Minutes past the current hour, where valid ranges are
        between 0-59. The minutes contribute to a fractional movement of the hour
        hand.
    :type minutes: int
    :return: The angular position of the hour hand on the clock in degrees,
        calculated as a float. The result is a value within the range 0-360.
    :rtype: float
    """
    # Factor in the hour hand change based on minutes
    return (hours % 12) * 30 + (minutes / 60) * 30


#
# Display Logic
#

# Leverage hardware-specific optimizations at a consistent baud rate. This display supports a
# maximum baud rate of 115,200.
spi = SPI(2, mosi=PIN_SIN, sck=PIN_SCK, baudrate=115200)

vfd = NAGP1250(spi=spi, reset=PIN_RESET, sbusy=PIN_SBUSY)

# Set up multiple windows so we only update the portion of the display that needs updating.
# Time
vfd.define_user_window(window_num=1, x=0, y=1, w=100, h=2)
# Clock face
vfd.define_user_window(window_num=2, x=100, y=0, w=40, h=4)

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
            vfd.set_font_magnification(h=2, v=2)
            vfd.write_text(current_t)

            # Update the last written time string variable so the next iteration has something to compare to.
            last_written_t = current_t

            # Center point for clock
            cx = 15
            cy = 15

            # Create blank bitmap
            width = 140
            height = 32
            bitmap = [[0 for _ in range(width)] for _ in range(height)]

            # Get the angle positions for the clock hands
            angle_hours = time_position_hours_with_minutes(hours=hour, minutes=minute)
            angle_minutes = time_position_minutes(minutes=minute)

            # Draw the clock face
            bitmap = vfd.draw_graphic_circle(bitmap=bitmap, cx=cx, cy=cy, radius=15)

            # Draw the hands by using `modify_angle_ccw_x_axis()` to make the clock face rotate counter-clockwise
            # from the x-axis because that is what `draw_graphic_lines()` expects.

            # Draw the hour hand with a length of 8px
            bitmap = vfd.draw_graphic_lines(bitmap=bitmap, lines=[(cx, cy, modify_angle_ccw_x_axis(angle_hours), 8)],
                                            width=width, height=height)
            # Draw the minute hand with a length of 13px
            bitmap = vfd.draw_graphic_lines(bitmap=bitmap, lines=[(cx, cy, modify_angle_ccw_x_axis(angle_minutes), 13)],
                                            width=width, height=height)

            # Pack the bitmap and get it ready for display
            packed = vfd.pack_bitmap(bitmap=bitmap, width=width, height=height)

            # Send the packed bitmap to the display window
            vfd.do_select_window(window_num=2)
            vfd.display_graphic_image(image_data=packed, width=width, height=height)

    time.sleep(5)
