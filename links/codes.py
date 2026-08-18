import secrets
import string

ALPHABET = string.ascii_letters + string.digits  # base62


def generate_code(length: int = 7) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def unique_code(length: int = 7) -> str:
    from .models import Link

    while True:
        code = generate_code(length)
        if not Link.objects.filter(code=code).exists():
            return code
