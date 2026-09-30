"""Security findings the baseline blocks."""

import hashlib
import sqlite3
import subprocess
import telnetlib  # expect: suspicious-telnetlib-import


def run_command(command: str) -> None:
    """Run a command through the shell."""
    subprocess.run(command, shell=True, check=True)  # expect: subprocess-popen-with-shell-equals-true


def find_users(conn: sqlite3.Connection, name: str) -> list:
    """Query users by name.

    Returns:
        The matching rows.
    """
    return conn.execute(f"SELECT * FROM users WHERE name = '{name}'").fetchall()  # expect: hardcoded-sql-expression


def fingerprint(data: bytes) -> str:
    """Hash data for an integrity check.

    Returns:
        The hex digest.
    """
    return hashlib.md5(data).hexdigest()  # expect: hashlib-insecure-hash-function


def open_session(host: str) -> telnetlib.Telnet:
    """Open a cleartext session.

    Returns:
        The session.
    """
    return telnetlib.Telnet(host)  # expect: suspicious-telnet-usage
