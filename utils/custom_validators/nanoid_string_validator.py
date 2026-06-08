import os

from pydantic_core import core_schema


class NanoIDString(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        return core_schema.str_schema(
            min_length=int(os.getenv("NANOID_KEY_SIZE")),
            max_length=int(os.getenv("NANOID_KEY_SIZE")),
        )
