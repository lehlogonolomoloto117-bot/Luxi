import getpass
import hashlib
import os


def authorize() -> None:
    owner = os.getenv("BOT_OWNER", "lehlogonolomoloto")
    required_hash = os.getenv("BOT_PASSWORD_HASH")
    if not required_hash:
        raise EnvironmentError(
            "Missing BOT_PASSWORD_HASH. Set the SHA256 hash of your access password in the environment."
        )

    password = os.getenv("BOT_PASSWORD")
    if not password:
        password = getpass.getpass("Enter trading bot access password: ")

    password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if password_hash != required_hash:
        raise PermissionError("Access denied: invalid password.")

    print(f"[SECURITY] Authorized owner: {owner}")
