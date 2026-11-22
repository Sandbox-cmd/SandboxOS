# SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name
# SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0
"""python3 -m sandbox_os ...: the maker's verbs and the hosts' hook and mcp, all through the command's router (cli.main)."""
import sys

from sandbox_os.command.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
