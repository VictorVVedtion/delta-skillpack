import re
from typing import Tuple


class EmailValidator:
    """
    Email validation with format and domain whitelist checks.

    This class provides methods to validate email addresses by:
    - Checking format against RFC 5322 simplified regex
    - Verifying domain against a whitelist of common providers
    """

    _EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
    _DOMAIN_WHITELIST = {
        "gmail.com",
        "outlook.com",
        "yahoo.com",
        "hotmail.com",
        "icloud.com",
        "qq.com",
        "163.com",
        "126.com",
        "sina.com",
        "foxmail.com",
    }

    def validate_format(self, email: str) -> bool:
        if not isinstance(email, str):
            return False
        email = email.strip()
        return bool(self._EMAIL_REGEX.match(email))

    def validate_domain(self, email: str) -> bool:
        if not isinstance(email, str):
            return False
        email = email.strip()
        parts = email.rsplit("@", 1)
        if len(parts) != 2:
            return False
        domain = parts[1].lower()
        return domain in self._DOMAIN_WHITELIST

    def validate_length(self, email: str) -> bool:
        if not isinstance(email, str):
            return False
        email = email.strip()
        return len(email) <= 254

    def validate(self, email: str) -> Tuple[bool, str]:
        if not self.validate_format(email):
            return False, "Invalid email format."
        if not self.validate_length(email):
            return False, "Email length exceeds 254 characters."
        if not self.validate_domain(email):
            return False, "Email domain is not supported."
        return True, ""
