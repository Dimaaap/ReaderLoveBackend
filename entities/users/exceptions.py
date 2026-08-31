class AuthException(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.detail)


class GitHubException(AuthException): ...


class UserAlreadyExistsError(AuthException):
    def __init__(self, detail: str = "User with this email or username already exists"):
        super().__init__(detail=detail, status_code=409)


class InvalidOTPError(AuthException):
    def __init__(self, detail: str = "Invalid or expired OTP"):
        super().__init__(detail=detail, status_code=409)
