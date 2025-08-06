from random_username.generate import generate_username
from uuid import uuid1
import subprocess
import sys

def generate_random_username():
    return generate_username()[0]

def generate_random_uuid():
    return str(uuid1())

def is_package_installed(package: str) -> bool:
    try:
        subprocess.check_output([sys.executable, "-m", "pip", "show", package])
        return True
    except subprocess.CalledProcessError:
        return False

def install_package(package: str) -> bool:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False