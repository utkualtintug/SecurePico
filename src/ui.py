import hardware
import config
import shared

# Display password entry screen
def update_password_display(masked_password):
    hardware.oled.fill(0) # Clear screen
    if shared.current_mode == config.MODE_LOGIN:
        hardware.oled.text("Password:", 0, 0)
    elif shared.current_mode == config.MODE_CHANGE_PASSWORD:
        hardware.oled.text("New pwd:" if shared.saved_password == "" else "Current pwd:", 0, 0)
    
    hardware.oled.text(masked_password, 0, 10)
    hardware.oled.text("# to confirm", 0, 30)
    hardware.oled.text("D to cancel", 0, 40)
    hardware.oled.show()

# Display main menu
def show_menu():
    hardware.oled.fill(0)
    hardware.oled.text("A: Login", 0, 0)
    hardware.oled.text("D: Set/Change", 0, 10)
    if shared.saved_password != "":
        hardware.oled.text("*: Delete pwd", 0, 30)
    hardware.oled.show()

def show_message(line1, line2=""):
    hardware.oled.fill(0)
    hardware.oled.text(line1, 0, 0)
    if line2:
        hardware.oled.text(line2, 0, 10)
    hardware.oled.show()