import hashlib
import ubinascii
import os

def hash_password(password):
    return ubinascii.hexlify(hashlib.sha256(password.encode()).digest()).decode()

def save_password_to_flash(password):
    with open("password.txt", "w") as f:
        f.write(hash_password(password))

def load_password_from_flash():
    try:
        with open("password.txt", "r") as f:
            return f.read().strip()
    except OSError:
        return ""

def delete_saved_password_file():
    try:
        os.remove("password.txt")
        return True
    except:
        return False