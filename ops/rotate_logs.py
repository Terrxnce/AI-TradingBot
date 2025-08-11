import gzip
import shutil
from pathlib import Path

MAX_SIZE_MB = 50
ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "var" / "internal" / "logs"


def rotate(p: Path):
    if not p.exists():
        return
    if p.stat().st_size < MAX_SIZE_MB * 1024 * 1024:
        return
    gz = p.with_suffix(p.suffix + ".1.gz")
    with open(p, "rb") as f_in, gzip.open(gz, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    p.write_text("", encoding="utf-8")


def main():
    LOGS.mkdir(parents=True, exist_ok=True)
    targets = [
        LOGS / "bot_stdout.log",
        LOGS / "bot_stderr.log",
        LOGS / "ai_decision_log.jsonl",
        LOGS / "trade_log.csv",
    ]
    for t in targets:
        rotate(t)


if __name__ == "__main__":
    main()


