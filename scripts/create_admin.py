"""Create the first administrator on a development computer.

The code is app/commands/create_admin.py, which the API image also contains, so a deployed host
runs it inside the container (DEPLOYMENT.md). The password is read privately and never printed.
"""

import sys

from app.commands.create_admin import main

if __name__ == "__main__":
    sys.exit(main())
