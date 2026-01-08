import sys
sys.path.append('src')

import time
import _thread
import config
import hardware
import storage
import ui
import server
import shared

# Local State Variables
entered_password = ""
masked_password = ""
wrong_attempts = 0
is_locked = False
lockdown_end_time = 0
last_pir_trigger = 0
alarm_arm_time = 0

def reset_input():
    global entered_password, masked_password
    entered_password = ""
    masked_password = ""

def stop_alarm():
    shared.alarm_active = False
    shared.alarm_armed = False
    hardware.stop_buzzer()
    hardware.red_led.value(0)

def start_alarm():
    shared.alarm_active = True
    hardware.start_buzzer_alarm()
    hardware.red_led.value(1)

def arm_alarm():
    global alarm_arm_time
    shared.alarm_armed = True
    alarm_arm_time = time.time() # Record start time for delay
    ui.show_message("Alarm Armed!", f"Wait {config.PIR_STARTUP_DELAY}s...")
    time.sleep(1.5)
    ui.show_menu()

# Record start time for delay
def handle_wrong_password():
    global wrong_attempts, is_locked, lockdown_end_time
    wrong_attempts += 1
    if wrong_attempts >= 3:
        is_locked = True
        lockdown_end_time = time.time() + 6 # Lock for 6 seconds
        wrong_attempts = 0
    
    ui.show_message("Wrong Password!")
    hardware.play_and_light(2000, 0.3, hardware.red_led)
    reset_input()
    time.sleep(1)
    ui.show_menu()

def handle_password_input(pressed_key):
    global entered_password, masked_password, wrong_attempts
    
    if pressed_key == "#": # Enter/Confirm key
        if shared.current_mode == config.MODE_CHANGE_PASSWORD:
            if shared.saved_password == "": # Setting first password
                storage.save_password_to_flash(entered_password)
                shared.saved_password = storage.load_password_from_flash()
                ui.show_message("Password saved")
                hardware.play_and_light(2000, 0.5, hardware.green_led)
                reset_input()
                shared.current_mode = config.MODE_MENU
                time.sleep(1.5)
                ui.show_menu()
            elif storage.hash_password(entered_password) == shared.saved_password: # Verify current
                if storage.delete_saved_password_file():
                    shared.saved_password = ""
                reset_input()
                ui.show_message("Enter new", "password:")
            else:
                handle_wrong_password()
        
        elif shared.current_mode == config.MODE_LOGIN:
            if storage.hash_password(entered_password) == shared.saved_password:
                if shared.alarm_active:
                    stop_alarm()
                    ui.show_message("Alarm Off!")
                    hardware.play_and_light(3000, 0.5, hardware.green_led)
                    time.sleep(0.5)
                else:
                    ui.show_message("Welcome!")
                    hardware.play_and_light(3000, 0.5, hardware.green_led)
                    time.sleep(0.3)
                    arm_alarm()
                reset_input()
                wrong_attempts = 0
                shared.current_mode = config.MODE_MENU
                ui.show_menu()
            else:
                handle_wrong_password()

    elif pressed_key.isdigit():
        if len(entered_password) < config.MAX_PASSWORD_LENGTH:
            entered_password += pressed_key
            masked_password += "*"
            ui.update_password_display(masked_password)
            hardware.play_and_light(2000, 0.05, hardware.red_led)
    
    elif pressed_key == "C": # Backspace
        entered_password = entered_password[:-1]
        masked_password = masked_password[:-1]
        ui.update_password_display(masked_password)
    
    elif pressed_key == "D": # Cancel
        reset_input()
        shared.current_mode = config.MODE_MENU
        ui.show_message("Cancelled")
        time.sleep(1)
        ui.show_menu()

# Logic to delete password file
def delete_saved_password_logic():
    if shared.saved_password == "":
        ui.show_message("No password", "to delete")
        time.sleep(1.5)
        ui.show_menu()
        return

    ui.show_message("Password will be", "deleted now")
    time.sleep(1)

    if storage.delete_saved_password_file():
        shared.saved_password = ""
        ui.show_message("Password", "deleted!")
        hardware.play_and_light(1500, 0.5, hardware.red_led)
    else:
        ui.show_message("Error", "deleting file")
    
    time.sleep(1.5)
    ui.show_menu()

# Setup
shared.saved_password = storage.load_password_from_flash()
ui.show_menu()

# Start Web Server in a new thread
_thread.start_new_thread(server.start, ())

# Main Loop
while True:
    now = time.time()

    # Check if system is locked due to wrong passwords
    if is_locked:
        remaining = int(lockdown_end_time - now)
        if remaining > 0:
            ui.show_message("Locked", f"{remaining}s")
            time.sleep(0.2)
            continue
        else:
            is_locked = False
            ui.show_menu()
            continue

    # Check Motion Sensor (Only if armed + delay passed)
    if shared.alarm_armed and (now - alarm_arm_time > config.PIR_STARTUP_DELAY): 
            if hardware.pir_sensor.value():
                if not shared.alarm_active and now - last_pir_trigger > config.PIR_DEBOUNCE_TIME:
                    last_pir_trigger = now
                    start_alarm()

    # Check Keypad
    key = hardware.scan_keypad()
    if not key:
        time.sleep(0.1)
        continue

    # Force Login if Alarm Active
    if shared.alarm_active:
        shared.current_mode = config.MODE_LOGIN
        ui.update_password_display(masked_password)
        handle_password_input(key)
        continue

    # Handle Menu Navigation
    if shared.current_mode == config.MODE_MENU:
        if key == "A":
            if shared.saved_password != "":
                shared.current_mode = config.MODE_LOGIN
                reset_input()
                ui.update_password_display(masked_password)
                hardware.play_and_light(2000, 0.1, hardware.green_led)
            else:
                ui.show_message("Set password")
                time.sleep(1.5)
                ui.show_menu()
        elif key == "D":
            shared.current_mode = config.MODE_CHANGE_PASSWORD
            reset_input()
            ui.update_password_display(masked_password)
            hardware.play_and_light(1500, 0.1, hardware.green_led)
        elif key == "*":
            hardware.play_and_light(1000, 0.1, hardware.red_led)
            delete_saved_password_logic()
    else:
        handle_password_input(key)

    time.sleep(0.1)