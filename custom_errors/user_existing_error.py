class UserExistingError(Exception):
    def __init__(self, message: str = "User already exists"):
        self.message = message
