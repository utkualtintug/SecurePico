from machine import Pin, I2C, PWM
from ssd1306 import SSD1306_I2C
import hashlib
import ubinascii
import time

# Hardware setup
red_led = Pin(16, Pin.OUT)
green_led = Pin(18, Pin.OUT)
buzzer = PWM(Pin(17)) 
pir_sensor = Pin(19, Pin.IN)  # Motion sensor
i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

# Mode constants
MODE_MENU = 0
MODE_LOGIN = 1
MODE_CHANGE_PASSWORD = 2

# Global variables
current_mode = MODE_MENU
entered_password = ""
masked_password = ""
saved_password = ""
wrong_attempts = 0
is_locked = False
alarm_armed = False
alarm_active = False
lockdown_end_time = 0
last_input_time = time.time()
MAX_PASSWORD_LENGTH = 8

# Keypad layout
keys = [
    ["1","2","3","A"],
    ["4","5","6","B"],
    ["7","8","9","C"],
    ["*","0","#","D"]
]

# Keypad pins
rows = [Pin(i, Pin.OUT) for i in [2, 3, 4, 5]]
cols = [Pin(i, Pin.IN, Pin.PULL_DOWN) for i in [6, 7, 8, 9]]


def hash_password(password):
    """Hash password using SHA256"""
    sha = hashlib.sha256(password.encode())
    return ubinascii.hexlify(sha.digest()).decode()


def save_password_to_flash(password):
    """Save hashed password to file"""
    print(password)
    hashed = hash_password(password)
    print(hashed)
    with open("password.txt", "w") as f:
        f.write(hashed)


def load_password_from_flash():
    """Load saved password from file"""
    try:
        with open("password.txt", "r") as f:
            return f.read().strip() 
    except OSError:
        return ""
    
saved_password = load_password_from_flash()


def play_and_light(frequency, duration, led_pin):
    """Play buzzer sound and flash LED"""
    led_pin.value(1)
    buzzer.freq(frequency)
    buzzer.duty_u16(32768)
    time.sleep(duration)
    buzzer.duty_u16(0)  
    led_pin.value(0)


def scan_keypad():
    """Scan 4x4 keypad for key press"""
    for row_num, row_pin in enumerate(rows):
        row_pin.high()  
        for col_num, col_pin in enumerate(cols):
            if col_pin.value() == 1:
                time.sleep(0.1)  # Debounce
                if col_pin.value() == 1:
                    row_pin.low()
                    key = keys[row_num][col_num]
                    while col_pin.value() == 1:
                        pass  # Wait for release
                    return key
        row_pin.low()
    return None


def handle_password_input(pressed_key):
    """Process password input from keypad"""
    global saved_password, entered_password, wrong_attempts, masked_password
    global last_input_time, current_mode, is_locked, lockdown_end_time
    
    last_input_time = time.time()
    
    # Submit password with #
    if pressed_key == "#":
        # First-time password setting
        if current_mode == MODE_CHANGE_PASSWORD and saved_password == "":
            hashed = hash_password(entered_password)
            saved_password = hashed
            save_password_to_flash(entered_password)
            oled.fill(0)
            oled.text("Password set!", 0, 0)
            oled.show()
            play_and_light(2000, 0.7, green_led)
            reset_input()
            current_mode = MODE_MENU
            time.sleep(1.5)
            show_menu()
            return
            
        # Password changing mode
        if current_mode == MODE_CHANGE_PASSWORD and saved_password != "":
            if hash_password(entered_password) == saved_password:
                # Validate current password first
                oled.fill(0)
                oled.text("Enter new", 0, 0)
                oled.text("password:", 0, 10)
                oled.show()
                saved_password = ""  # Clear to allow new password
                reset_input()
                return
            else:
                handle_wrong_password()
                return
                
        # Login mode
        if current_mode == MODE_LOGIN:
            if hash_password(entered_password) == saved_password:
                oled.fill(0)
                oled.text("Welcome!", 0, 0)
                oled.show()
                play_and_light(2000, 0.7, green_led)
                wrong_attempts = 0  # Reset on success
                reset_input()
                arm_alarm()
                current_mode = MODE_MENU
                time.sleep(1.5)
                show_menu()
                return
            else:
                handle_wrong_password()
                return

    # Add digit to password
    elif pressed_key.isdigit():
        if len(entered_password) < MAX_PASSWORD_LENGTH:
            entered_password += pressed_key
            masked_password += "*"
            update_password_display()
            play_and_light(2000, 0.1, red_led)
        
    # Backspace with C
    elif pressed_key == "C":
        if entered_password:
            entered_password = entered_password[:-1]
            masked_password = masked_password[:-1]
            update_password_display()
            play_and_light(1000, 0.1, red_led)
            
    # Cancel with D
    elif pressed_key == "D":
        reset_input()
        current_mode = MODE_MENU
        oled.fill(0)
        oled.text("Cancelled", 0, 0)
        oled.show()
        time.sleep(1.5)
        show_menu()


def update_password_display():
    """Update OLED with password input screen"""
    oled.fill(0)
    if current_mode == MODE_LOGIN:
        oled.text("Password:", 0, 0)
    elif current_mode == MODE_CHANGE_PASSWORD:
        if saved_password == "":
            oled.text("New password:", 0, 0)
        else:
            oled.text("Current password:", 0, 0)
    oled.text(masked_password, 0, 10)
    oled.text("# to confirm", 0, 30)
    oled.text("D to cancel", 0, 40)
    oled.show()


def handle_wrong_password():
    """Handle incorrect password attempts"""
    global wrong_attempts, is_locked, lockdown_end_time
    
    wrong_attempts += 1
    if wrong_attempts >= 3:
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


def reset_input():
    """Clear password input fields"""
    global entered_password, masked_password
    entered_password = ""
    masked_password = ""


def delete_saved_password():
    """Delete saved password with hold confirmation"""
    global saved_password
    if saved_password == "":
        oled.fill(0)
        oled.text("No password", 0, 0)
        oled.text("to delete", 0, 10)
        oled.show()
        time.sleep(1.5)
        show_menu()
        return
    
    oled.fill(0)
    oled.text("Hold * to delete", 0, 0)
    oled.text("password", 0, 10)
    oled.show()
    
    hold_time = 3  # Seconds to hold
    
    start = time.time()
    while True:
        elapsed = time.time() - start
        remaining = int(hold_time - elapsed)
        if remaining < 0:
            break
        
        oled.fill_rect(0, 30, 128, 20, 0)  
        oled.text(f"Releasing in: {remaining}s", 0, 30)
        oled.show()
        
        key = scan_keypad()
        if key != "*":  # Released too early
            oled.fill(0)
            oled.text("Cancelled", 0, 0)
            oled.show()
            time.sleep(1.5)
            show_menu()
            return
        
        time.sleep(0.1)
    
    # Delete password file
    try:
        import os
        os.remove("password.txt")
        saved_password = ""
        oled.fill(0)
        oled.text("Password", 0, 0)
        oled.text("deleted!", 0, 10)
        oled.show()
        play_and_light(1500, 0.5, red_led)
        time.sleep(1.5)
        show_menu()
    except OSError:
        oled.fill(0)
        oled.text("Error:", 0, 0)
        oled.text("File missing", 0, 10)
        oled.show()
        time.sleep(1.5)
        show_menu()


def show_menu():
    """Display main menu on OLED"""
    oled.fill(0)
    oled.text("Press A: Login", 0, 0)
    if saved_password != "":
        oled.text("Press D: Change", 0, 20)
        oled.text("password", 0, 30)
        oled.text("*: Delete pwd", 0, 50)  
    else:
        oled.text("Press D: Set", 0, 20)
        oled.text("password", 0, 30)
    oled.show()


show_menu()  # Show initial menu


def start_alarm():
    """Start alarm buzzer"""
    global alarm_active
    alarm_active = True
    buzzer.freq(2000)
    buzzer.duty_u16(32768) 

def stop_alarm():
    """Stop alarm and disarm"""
    global alarm_active, alarm_armed
    alarm_active = False
    alarm_armed = False
    buzzer.duty_u16(0) 

def arm_alarm():
    """Arm motion detection alarm"""
    global alarm_armed
    alarm_armed = True
    oled.fill(0)
    oled.text("Alarm Set!", 0, 0)
    oled.show()
    time.sleep(1.5)
    show_menu()

# Main loop
while True:
    current_time = time.time()
    
    # Check motion sensor when armed
    if alarm_armed and pir_sensor.value() == 1:
        if not alarm_active:
            start_alarm()

    # Handle security lockdown
    if is_locked:
        remaining = int(lockdown_end_time - current_time)
        if remaining > 0:
            oled.fill(0)
            oled.text("Too many attempts", 0, 0)
            oled.text(f"Locked: {remaining}s", 0, 20)
            oled.show()
            time.sleep(0.1)
            continue
        else:
            is_locked = False
            show_menu()
            continue
    
    # Check for input timeout
    if current_time - last_input_time > 10 and (entered_password != "" or current_mode != MODE_MENU):
        reset_input()
        oled.fill(0)
        oled.text("Timeout!", 0, 0)
        oled.show()
        time.sleep(1)
        current_mode = MODE_MENU
        show_menu()
    
    # Get keypad input
    pressed_key = scan_keypad()
    if not pressed_key:
        continue
    
    # Handle alarm mode (forces login)
    if alarm_active:
        if current_mode != MODE_LOGIN:
            current_mode = MODE_LOGIN
            reset_input()
            update_password_display()
            continue
        
        if pressed_key:
            handle_password_input(pressed_key)
            
            # Stop alarm on correct password
            if pressed_key == "#" and hash_password(entered_password) == saved_password:
                stop_alarm()
                oled.fill(0)
                oled.text("Alarm Off!", 0, 0)
                oled.show()
                time.sleep(1.5)
                current_mode = MODE_MENU
                reset_input()
                show_menu()
            continue
    
    # Handle menu navigation
    if current_mode == MODE_MENU:
        if pressed_key == "A":  # Login
            if saved_password == "":
                oled.fill(0)
                oled.text("No password set", 0, 0)
                oled.text("Set one first", 0, 10)
                oled.show()
                time.sleep(2)
                show_menu()
            else:
                current_mode = MODE_LOGIN
                reset_input()
                update_password_display()
                last_input_time = current_time
                
        elif pressed_key == "D":  # Change/Set password
            current_mode = MODE_CHANGE_PASSWORD
            reset_input()
            update_password_display()
            last_input_time = current_time
            
        elif pressed_key == "*":  # Delete password
            delete_saved_password()
            current_mode = MODE_MENU

    # Handle password input modes
    elif current_mode in [MODE_LOGIN, MODE_CHANGE_PASSWORD]:
        handle_password_input(pressed_key)

        # Auto-arm after successful login
        if current_mode == MODE_LOGIN and pressed_key == "#" and hash_password(entered_password) == saved_password:
            arm_alarm()
            reset_input()
            last_input_time = current_time

    time.sleep(0.1)  # Small delay