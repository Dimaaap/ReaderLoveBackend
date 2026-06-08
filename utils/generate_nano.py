import os

from nanoid import generate


def generate_nanoid() -> str:
    size_env = os.getenv("NANOID_KEY_SIZE", "21")
    size = int(size_env)
    return generate(size=size)
