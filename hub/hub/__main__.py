"""`python -m hub` 入口：转发到 CLI。"""

import sys

from hub.cli import main

if __name__ == "__main__":
    sys.exit(main())
