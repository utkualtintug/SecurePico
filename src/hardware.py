from machine import Pin, I2C, PWM
from ssd1306 import SSD1306_I2C
import time
import config
import shared

# Hardware Initialization
red_led = Pin(config.PIN_RED_LED, Pin.OUT)
green_led = Pin(config.PIN_GREEN_LED, Pin.OUT)
buzzer = PWM(Pin(config.PIN_BUZZER))
pir_sensor = Pin(config.PIN_PIR, Pin.IN)

i2c = I2C(0, scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

# Keypad Setup
keys = [
    ["1","2","3","A"],
    ["4","5","6","B"],
    ["7","8","9","C"],
    ["*","0","#","D"]
]
rows = [Pin(i, Pin.OUT) for i in config.PIN_KEYPAD_ROWS] # Row pins [2, 3, 4, 5]
cols = [Pin(i, Pin.IN, Pin.PULL_UP) for i in config.PIN_KEYPAD_COLS] # Column pins [6, 7, 8, 9]

def play_and_light(frequency, duration, led_pin):
    if shared.alarm_active and shared.current_mode == config.MODE_LOGIN:
        return
    led_pin.value(1)
    buzzer.freq(frequency)
    buzzer.duty_u16(32768)
    time.sleep(duration)
    buzzer.duty_u16(0)
    led_pin.value(0)

def stop_buzzer():
    buzzer.duty_u16(0)

def start_buzzer_alarm():
    buzzer.freq(2000)
    buzzer.duty_u16(32768)

# Matrix keypad scanning function
def scan_keypad():
    for row in rows: row.high()
    for r_idx, r in enumerate(rows):
        r.low()
        time.sleep(0.001)
        for c_idx, c in enumerate(cols):
            if c.value() == 0:  # Key pressed
                time.sleep(0.05)  # Debounce delay
                if c.value() == 0:
                    key = keys[r_idx][c_idx]
                    while c.value() == 0: # Wait for key release
                        time.sleep(0.01)
                    for row in rows: row.high()
                    return key
        r.high()
    return None