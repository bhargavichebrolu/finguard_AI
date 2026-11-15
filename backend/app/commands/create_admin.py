"""Create an administrator. The password is read privately and never printed or stored.

    python -m app.commands.create_admin --email admin@example.com

The password comes from FINGUARD_ADMIN_PASSWORD if it is set, otherwise from a prompt that does
not echo. Part of the API image (Phase 6), so the first account on a deployed host is created
inside the running container:

    docker compose -f docker-compose.prod.yml --env-file .env.production \\
        exec api python -m app.commands.create_admin --email admin@example.com

scripts/create_admin.py runs the same code on a development computer.
"""

import argparse
import getpass
import os
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.api.schemas.auth import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from app.core.errors import ConflictError
from app.database.session import session_scope
from app.models.enums import UserRole
from app.services.auth_service import create_user

PASSWORD_VARIABLE = "FINGUARD_ADMIN_PASSWORD"


def read_password() -> str:
    """Take the password from the environment if set, otherwise prompt without echoing it."""
    return os.environ.get(PASSWORD_VARIABLE) or getpass.getpass("Administrator password: ")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    arguments = parser.parse_args(argv)

    try:
        email = TypeAdapter(EmailStr).validate_python(arguments.email)
    except ValidationError:
        print("That email address is not valid.")
        return 1
    password = read_password()
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        print(f"The password needs {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters.")
        return 1

    with session_scope() as session:
        try:
            user = create_user(session, email, password, UserRole.ADMIN, None)
        except ConflictError as error:
            print(error.message)
            return 1
    print(f"Created administrator {user.email}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
