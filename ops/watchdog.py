import os, sys, json, time, subprocess, signal
from pathlib import Path
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[1]
USER_ID = os.getenv("DEVI_USER_ID", "internal")
HEARTBEAT = PROJECT_ROOT / "var" / USER_ID / "state" / "bot_heartbeat.json"

BOT_CMD = [
    sys.executable,
    os.fspath(PROJECT_ROOT / "Bot Core" / "bot_runner.py"),
    "--user-id", USER_ID,
    "--align", os.getenv("DEVI_ALIGN", "quarter"),
    "--timeframe", os.getenv("DEVI_TIMEFRAME", "M15"),
    *os.getenv("DEVI_SYMBOLS", "EURUSD USDJPY").split()
]

STALE_SECS = int(os.getenv("DEVI_STALE_SECS", "90"))


def is_stale() -> bool:
    try:
        data = json.loads(HEARTBEAT.read_text(encoding="utf-8"))
        ts = data.get("last_heartbeat") or data.get("last_beat_utc")
        if not ts:
            return True
        last = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - last) > timedelta(seconds=STALE_SECS)
    except Exception:
        return True


def main():
    proc = None
    while True:
        restart = (proc is None) or (proc.poll() is not None) or is_stale()
        if restart:
            if proc and proc.poll() is None:
                try:
                    proc.send_signal(signal.SIGTERM)
                except Exception:
                    pass
            log_dir = PROJECT_ROOT / "var" / USER_ID / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            stdout = open(log_dir / "bot_stdout.log", "a", buffering=1, encoding="utf-8")
            stderr = open(log_dir / "bot_stderr.log", "a", buffering=1, encoding="utf-8")
            env = os.environ.copy(); env["DEVI_USER_ID"] = USER_ID
            proc = subprocess.Popen(BOT_CMD, cwd=os.fspath(PROJECT_ROOT), env=env,
                                    stdout=stdout, stderr=stderr)
        time.sleep(30)


if __name__ == "__main__":
    main()


