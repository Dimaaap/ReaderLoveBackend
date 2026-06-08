import random
import os

LOW_BORDER = int(os.getenv("OTP_BOTTOM_BORDER"))
HIGH_BORDER = int(os.getenv("OTP_HIGH_BORDER"))


def generate_random_otp() -> str:
    return f"{random.randint(LOW_BORDER, HIGH_BORDER):06d}"
