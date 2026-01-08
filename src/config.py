# Wi-Fi Settings
SSID = "SSID" 
PASSWORD = "PASSWORD"

# Hardware Pin Definitions
PIN_RED_LED = 16
PIN_GREEN_LED = 18
PIN_BUZZER = 17
PIN_PIR = 27
PIN_I2C_SCL = 1
PIN_I2C_SDA = 0
PIN_KEYPAD_ROWS = [2, 3, 4, 5]
PIN_KEYPAD_COLS = [6, 7, 8, 9]

# System Constants
MODE_MENU = 0 # State: Main menu display
MODE_LOGIN = 1 # State: Password entry screen
MODE_CHANGE_PASSWORD = 2 # State: Setup new password
PIR_DEBOUNCE_TIME = 2 # Seconds to wait between motion triggers
MAX_PASSWORD_LENGTH = 12
PIR_STARTUP_DELAY = 10 # Seconds to exit room after arming