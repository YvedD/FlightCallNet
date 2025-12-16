#!/usr/bin/env python3
"""Run full pipeline: fetch recordings (all or one species) then chunk.

Usage:
  python scripts/run_pipeline.py [-p PROJECT_ROOT] [--species "Anthus pratensis"] [--dry-run] [--skip-deps-check]

This script will:
 - detect PROJECT_ROOT (CLI > FLIGHTCALLNET_ROOT env > autodetect)
 - optionally run scripts/check_and_install_deps.py to verify ffmpeg and pip deps
 - run scripts/fetch_xc.py (for a single species if --species provided, else all)
 - run scripts/download_and_chunk_xeno_canto.py
 - write timestamped logs to PROJECT_ROOT/logs
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path
import datetime
import os

SCRIPT_DIR = Path(__file__).resolve().parent
FETCH_SCRIPT = SCRIPT_DIR / 'fetch_xc.py'
CHUNK_SCRIPT = SCRIPT_DIR / 'download_and_chunk_xeno_canto.py'
DEPS_SCRIPT = SCRIPT_DIR / 'check_and_install_deps.py'


def find_project_root(config_filename: str = 'species_config.json', max_up: int = 4) -> Path:
    cwd = Path.cwd()
    cand = cwd / config_filename
    if cand.exists():
        return cwd
    script_dir = Path(__file__).resolve().parent
    cand = script_dir / '..' / config_filename
    cand = (script_dir / '..' / config_filename).resolve()
    # search parents of repo root
    p = script_dir
    for _ in range(max_up):
        p = p.parent
        candidate = p / config_filename
        if candidate.exists():
            return p
    return script_dir.parent


def run_cmd(cmd: list[str], log_path: Path) -> int:
    """Run command and stream output to console and a log file. Returns exit code."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('wb') as lf:
        # start the process
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert proc.stdout is not None
        for chunk in iter(proc.stdout.readline, b''):
            lf.write(chunk)
            lf.flush()
            try:
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
            except Exception:
                # fallback
                print(chunk.decode('utf-8', errors='replace'), end='')
        proc.wait()
        return proc.returncode


def main():
    parser = argparse.ArgumentParser(description='Run fetch+chunk pipeline for FlightCallNet')
    parser.add_argument('--project-root', '-p', dest='project_root', help='Force project root path (overrides env and auto-detect)')
    parser.add_argument('--species', dest='species', help='Optional species name (e.g. "Anthus pratensis") — default: all species in species_config.json')
    parser.add_argument('--dry-run', action='store_true', dest='dry_run', help='Dry run: do not perform downloads or writes')
    parser.add_argument('--skip-deps-check', action='store_true', dest='skip_deps', help='Skip dependency check')
    args = parser.parse_args()

    # Determine project root
    if args.project_root:
        project_root = Path(args.project_root).resolve()
    else:
        env = os.environ.get('FLIGHTCALLNET_ROOT')
        if env:
            project_root = Path(env).resolve()
        else:
            project_root = find_project_root()
    print(f'Using PROJECT_ROOT: {project_root}')

    # logs
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    # Optional dependency check
    if not args.skip_deps:
        if DEPS_SCRIPT.exists():
            print('Running dependency check...')
            logp = logs_dir / f'deps_check_{ts}.log'
            rc = run_cmd([sys.executable, str(DEPS_SCRIPT)], logp)
            if rc != 0:
                print(f'Dependency check exited with {rc}; inspect {logp}')
                # continue or abort? abort to be safe
                print('Aborting pipeline due to failed dependency check.')
                sys.exit(rc)
        else:
            print('No dependency helper found; skipping automated check')

    # Run fetch_xc.py
    fetch_log = logs_dir / f'fetch_{ts}.log'
    fetch_cmd = [sys.executable, str(FETCH_SCRIPT)]
    if args.species:
        fetch_cmd.append(args.species)
    if args.dry_run:
        fetch_cmd.append('--dry-run')
    fetch_cmd.extend(['-p', str(project_root)])

    print('Running fetch step:',' '.join(fetch_cmd))
    rc = run_cmd(fetch_cmd, fetch_log)
    if rc != 0:
        print(f'fetch_xc.py returned {rc}; see {fetch_log} for details')
        sys.exit(rc)

    # Run download_and_chunk_xeno_canto.py
    chunk_log = logs_dir / f'chunk_{ts}.log'
    chunk_cmd = [sys.executable, str(CHUNK_SCRIPT)]
    if args.dry_run:
        chunk_cmd.append('--dry-run')
    chunk_cmd.extend(['-p', str(project_root)])

    print('Running chunk step:',' '.join(chunk_cmd))
    rc = run_cmd(chunk_cmd, chunk_log)
    if rc != 0:
        print(f'download_and_chunk_xeno_canto.py returned {rc}; see {chunk_log} for details')
        sys.exit(rc)

    print('Pipeline finished successfully.')

if __name__ == '__main__':
    main()

