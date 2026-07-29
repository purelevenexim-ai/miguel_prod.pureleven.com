import secrets
import string


def generate_secure_password(length: int = 14) -> str:
    characters = string.ascii_letters + string.digits + "!@#$%^&*"

    while True:
        password = "".join(secrets.choice(characters) for _ in range(length))

        # Ensure complexity rules
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!@#$%^&*" for c in password)
        ):
            return password
