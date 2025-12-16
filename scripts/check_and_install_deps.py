#!/usr/bin/env python3
"""Check presence of ffmpeg and install missing python packages via pip (venv context).
This helper is intended to run after activating a venv.

Behavior:
- Checks whether ffmpeg is in PATH. If missing and running on a Debian/Ubuntu-based Linux as root, it will attempt `apt update && apt install -y ffmpeg`.
- Installs Python requirements from requirements.txt using the current Python interpreter's pip.
- Prints helpful instructions if it cannot perform system installs.
"""
import shutil
import subprocess
import sys
import os
import platform
from pathlib import Path

req_file = Path(__file__).resolve().parents[1] / 'requirements.txt'


def in_venv() -> bool:
    """Return True when running inside a virtual environment."""
    # On venv, sys.prefix != sys.base_prefix
    return getattr(sys, 'base_prefix', sys.prefix) != sys.prefix


def check_ffmpeg() -> bool:
    """Return True if ffmpeg is available in PATH."""
    ff = shutil.which('ffmpeg')
    if ff is None:
        print('ffmpeg niet gevonden in PATH.')
        return False
    print('ffmpeg gevonden:', ff)
    return True


def try_install_ffmpeg_debian():
    """Attempt to install ffmpeg via apt (Debian/Ubuntu). Only runs when effective uid is 0.
    Returns True on success, False otherwise.
    """
    if shutil.which('apt') is None:
        print('apt niet beschikbaar; automatische installatie niet mogelijk op dit systeem.')
        return False
    try:
        print('Proberen ffmpeg te installeren via apt... (apt update && apt install -y ffmpeg)')
        subprocess.check_call(['apt', 'update'])
        subprocess.check_call(['apt', 'install', '-y', 'ffmpeg'])
        return True
    except subprocess.CalledProcessError as e:
        print('Automatische installatie van ffmpeg via apt mislukt:', e)
        return False


def install_python_reqs():
    if not req_file.exists():
        print('requirements.txt niet gevonden; geen pip packages te installeren')
        return
    print('Installing Python requirements from', req_file)
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', str(req_file)])


def main():
    print('Running dependency checks for FlightCallNet')

    # 1) Check if running in venv and warn if not
    if not in_venv():
        print('Opmerking: het script draait NIET binnen een Python virtualenv. Het wordt aanbevolen een venv te gebruiken.')
    else:
        print('Virtualenv gedetecteerd.')

    # 2) Check ffmpeg
    ff_ok = check_ffmpeg()
    if not ff_ok:
        # If on Linux and running as root, attempt apt install
        system = platform.system().lower()
        euid = os.geteuid() if hasattr(os, 'geteuid') else None
        if system == 'linux' and euid == 0:
            print('Linux + root gedetecteerd — probeer automatisch ffmpeg te installeren via apt.')
            installed = try_install_ffmpeg_debian()
            if installed:
                ff_ok = check_ffmpeg()
        else:
            print('Automatische installatie van ffmpeg niet uitgevoerd (linux+root vereist).')
            print('Installeer ffmpeg handmatig, bijv.: sudo apt install ffmpeg')

    # 3) Install python requirements via pip (current interpreter)
    try:
        install_python_reqs()
    except subprocess.CalledProcessError as e:
        print('pip install failed:', e)
        sys.exit(1)

    # 4) Final status
    if not ff_ok:
        print('Let op: ffmpeg ontbreekt; audio conversie werkt mogelijk niet totdat ffmpeg is geïnstalleerd.')
        sys.exit(2)
    else:
        print('All checks passed (ffmpeg and python requirements).')


if __name__ == '__main__':
    main()
