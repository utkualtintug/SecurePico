from machine import Pin, I2C, PWM
from ssd1306 import SSD1306_I2C
import hashlib
import ubinascii
import time
import network
import ure
import _thread
import os

# Hardware Pin Definitions
red_led = Pin(16, Pin.OUT)
green_led = Pin(18, Pin.OUT)
buzzer = PWM(Pin(17))
pir_sensor = Pin(19, Pin.IN)  # Motion sensor
i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

# System Operation Modes
MODE_MENU = 0
MODE_LOGIN = 1
MODE_CHANGE_PASSWORD = 2

# Global State Variables
current_mode = MODE_MENU
entered_password = ""
masked_password = ""  # Password display with asterisks
saved_password = ""
wrong_attempts = 0
is_locked = False  # Lockout after failed attempts
lockdown_end_time = 0
alarm_armed = False
alarm_active = False
last_pir_trigger = 0
PIR_DEBOUNCE_TIME = 2  # Prevent false PIR triggers
MAX_PASSWORD_LENGTH = 8


# Wi-Fi Settings
ssid = "WIFI NAME"
password = "PASSWORD"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print("Connecting to Wi-Fi...")
while not wlan.isconnected():
    time.sleep(1)
print("Connected! IP address:", wlan.ifconfig()[0])


# 4x4 Keypad Configuration
keys = [
    ["1","2","3","A"],
    ["4","5","6","B"],
    ["7","8","9","C"],
    ["*","0","#","D"]
]
rows = [Pin(i, Pin.OUT) for i in [2, 3, 4, 5]]  # Row pins
cols = [Pin(i, Pin.IN, Pin.PULL_UP) for i in [6, 7, 8, 9]]  # Column pins


# Hash password using SHA256 for security
def hash_password(password):
    return ubinascii.hexlify(hashlib.sha256(password.encode()).digest()).decode()

# Save encrypted password to flash memory
def save_password_to_flash(password):
    with open("password.txt", "w") as f:
        f.write(hash_password(password))

# Load saved password from flash memory
def load_password_from_flash():
    try:
        with open("password.txt", "r") as f:
            return f.read().strip()
    except OSError:
        return ""

# Check if password exists in memory
def is_password_set():
    return saved_password != ""

# Audio and visual feedback function
def play_and_light(frequency, duration, led_pin):
    if alarm_active and current_mode == MODE_LOGIN:
        return
    led_pin.value(1)
    buzzer.freq(frequency)
    buzzer.duty_u16(32768)
    time.sleep(duration)
    buzzer.duty_u16(0)
    led_pin.value(0)

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
                    while c.value() == 0:  # Wait for key release
                        time.sleep(0.01)
                    for row in rows: row.high()
                    return key
        r.high()
    return None

# Update OLED display for password entry
def update_password_display():
    oled.fill(0)
    if current_mode == MODE_LOGIN:
        oled.text("Password:", 0, 0)
    elif current_mode == MODE_CHANGE_PASSWORD:
        oled.text("New password:" if not is_password_set() else "Current password:", 0, 0)
    oled.text(masked_password, 0, 10)  # Show asterisks
    oled.text("# to confirm", 0, 30)
    oled.text("D to cancel", 0, 40)
    oled.show()


def generate_html_response():
    global alarm_active 
    
    html = """<!DOCTYPE html>
    <html>
    <head>
        <title>SecurePico</title>
        <meta charset="utf-8">
        <style>
            body {{ text-align:center; font-family:sans-serif; background-color: {} }}; /* Dynamic background in style */
        </style>
        <script>
            function updateAlarmStatus() {{
                fetch('/') // Request the same page, the server will send updated status
                    .then(response => response.text())
                    .then(html => {{
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(html, 'text/html');
                        const newStatus = doc.querySelector('#alarm-status-text').innerText;
                        const newBgColor = doc.body.style.backgroundColor; // Get new background color
                        document.querySelector('#alarm-status-text').innerText = newStatus;
                        document.body.style.backgroundColor = newBgColor; // Apply new background color
                    }})
                    .catch(error => console.error('Error fetching alarm status:', error));
            }}
            setInterval(updateAlarmStatus, 2000); // Refresh every 2 seconds
        </script>
    </head>
    <body style="text-align:center; font-family:sans-serif; background-color:{}">
        <h1>SecurePico Security System</h1>
        <p>Alarm Status: <strong id="alarm-status-text">{}</strong></p>
        <form>
            <input type="password" name="pwd" placeholder="Enter password">
            <input type="submit" value="Deactivate Alarm">
        </form>
    </body>
    </html>
    """.format("red" if alarm_active else "white", "red" if alarm_active else "white", "ACTIVE" if alarm_active else "INACTIVE") 
    return html


# Clear password input fields
def reset_input():
    global entered_password, masked_password
    entered_password = ""
    masked_password = ""

# Handle incorrect password attempts and lockout
def handle_wrong_password():
    global wrong_attempts, is_locked, lockdown_end_time
    wrong_attempts += 1
    if wrong_attempts >= 3:  # Lock after 3 failed attempts
        is_locked = True
        lockdown_end_time = time.time() + 6  # 6 second lockout
        wrong_attempts = 0
    oled.fill(0)
    oled.text("Wrong Password!", 0, 0)
    oled.show()
    play_and_light(2000, 0.3, red_led)
    reset_input()
    time.sleep(1)
    show_menu()

# Main password input processing function
def handle_password_input(pressed_key):
    global entered_password, masked_password, saved_password
    global current_mode, last_input_time, alarm_active

    if pressed_key == "#":  # Confirm password
        if current_mode == MODE_CHANGE_PASSWORD:
            if not is_password_set():  # First time password setup
                save_password_to_flash(entered_password)
                saved_password = load_password_from_flash()
                oled.fill(0)
                oled.text("Password saved", 0, 0)
                oled.show()
                play_and_light(2000, 0.5, green_led)
                reset_input()
                current_mode = MODE_MENU
                time.sleep(1.5)
                show_menu()
                return
            elif hash_password(entered_password) == saved_password:  # Verify current password
                delete_saved_password()  
                saved_password = ""
                reset_input()
                oled.fill(0)
                oled.text("Enter new", 0, 0)
                oled.text("password:", 0, 10)
                oled.show()
                return
            else:
                handle_wrong_password()
                return

        elif current_mode == MODE_LOGIN:
            if hash_password(entered_password) == saved_password:  # Correct password
                if alarm_active:
                    stop_alarm()
                    oled.fill(0)
                    oled.text("Alarm Off!", 0, 0)
                    oled.show()
                    play_and_light(3000, 0.5, green_led)
                    time.sleep(0.5)
                else:
                    oled.fill(0)
                    oled.text("Welcome!", 0, 0)
                    oled.show()
                    play_and_light(3000, 0.5, green_led)
                    time.sleep(0.3)
                    arm_alarm()
                reset_input()
                wrong_attempts = 0
                current_mode = MODE_MENU
                show_menu()

            else:
                handle_wrong_password()
    elif pressed_key.isdigit():  # Number key pressed
        if len(entered_password) < MAX_PASSWORD_LENGTH:
            entered_password += pressed_key
            masked_password += "*"  # Add asterisk to display
            update_password_display()
            play_and_light(2000, 0.05, red_led)
    elif pressed_key == "C":  # Backspace
        entered_password = entered_password[:-1]
        masked_password = masked_password[:-1]
        update_password_display()
    elif pressed_key == "D":  # Cancel
        reset_input()
        current_mode = MODE_MENU
        oled.fill(0)
        oled.text("Cancelled", 0, 0)
        oled.show()
        time.sleep(1)
        show_menu()

# Delete saved password from flash memory
def delete_saved_password():
    global saved_password
    if not is_password_set():
        oled.fill(0)
        oled.text("No password", 0, 0)
        oled.text("to delete", 0, 10)
        oled.show()
        time.sleep(1.5)
        show_menu()
        return

    oled.fill(0)
    oled.text("Password will be", 0, 0)
    oled.text("deleted now", 0, 10)
    oled.show()
    time.sleep(1)

    try:
        os.remove("password.txt")  # Delete password file
        saved_password = ""
        oled.fill(0)
        oled.text("Password", 0, 0)
        oled.text("deleted!", 0, 10)
        oled.show()
        play_and_light(1500, 0.5, red_led)
    except:
        oled.fill(0)
        oled.text("Error", 0, 0)
        oled.text("deleting file", 0, 10)
        oled.show()

    time.sleep(1.5)
    show_menu()

# Display main menu on OLED
def show_menu():
    oled.fill(0)
    oled.text("A: Login", 0, 0)
    oled.text("D: Set/Change", 0, 10)
    if is_password_set():
        oled.text("*: Delete pwd", 0, 30)
    oled.show()

def start_web_server():
    import socket
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Web server started at:", wlan.ifconfig()[0])

    while True:
        client, addr = s.accept()
        print("Client connected:", addr)
        request = client.recv(1024).decode()

        # Check for password in GET request
        match = ure.search("GET /\\?pwd=([a-zA-Z0-9]+)", request)
        if match:
            pwd = match.group(1)
            if hash_password(pwd) == saved_password:
                stop_alarm()

        # Send HTML page
        response = generate_html_response()
        client.send("HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n")
        client.send(response)
        client.close()

# Activate alarm when motion detected
def start_alarm():
    global alarm_active
    alarm_active = True
    buzzer.freq(2000)
    buzzer.duty_u16(32768)

# Stop alarm and disarm system
def stop_alarm():
    global alarm_active, alarm_armed
    alarm_active = False
    alarm_armed = False
    buzzer.duty_u16(0)

# Arm the PIR motion detection system
def arm_alarm():
    global alarm_armed
    alarm_armed = True
    oled.fill(0)
    oled.text("Alarm Armed!", 0, 0)
    oled.show()
    time.sleep(1.5)
    show_menu()


# Load saved password and show initial menu
saved_password = load_password_from_flash()
show_menu()

_thread.start_new_thread(start_web_server, ())

# Main program loop
while True:
    now = time.time()

    # Handle system lockout after failed attempts
    if is_locked:
        remaining = int(lockdown_end_time - now)
        if remaining > 0:
            oled.fill(0)
            oled.text("Locked", 0, 0)
            oled.text(f"{remaining}s", 0, 20)
            oled.show()
            time.sleep(0.2)
            continue
        else:
            is_locked = False
            show_menu()
            continue

    # Check PIR sensor for motion when armed
    if alarm_armed and pir_sensor.value():
        if not alarm_active and now - last_pir_trigger > PIR_DEBOUNCE_TIME:
            last_pir_trigger = now
            start_alarm()

    # Scan keypad for input
    key = scan_keypad()
    if not key:
        time.sleep(0.1)
        continue

    # Force login mode when alarm is active
    if alarm_active:
        current_mode = MODE_LOGIN
        update_password_display()
        handle_password_input(key)
        continue

    # Handle menu navigation
    if current_mode == MODE_MENU:
        if key == "A":  # Login option
            if is_password_set():
                current_mode = MODE_LOGIN
                reset_input()
                update_password_display()
                play_and_light(2000, 0.1, green_led)
            else:
                oled.fill(0)
                oled.text("Set password", 0, 0)
                oled.show()
                time.sleep(1.5)
                show_menu()
        elif key == "D":  # Set/Change password option
            current_mode = MODE_CHANGE_PASSWORD
            reset_input()
            update_password_display()
            play_and_light(1500, 0.1, green_led)
        elif key == "*":  # Delete password option
            play_and_light(1000, 0.1, red_led)
            delete_saved_password()
    else:
        # Handle password input in login/change modes
        handle_password_input(key)

    time.sleep(0.1)  # Small delay to prevent excessive CPU usage
    
