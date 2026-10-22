"""Project-local test runner: no credentials, external temp files, or live AI calls."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCAL_TEMP = ROOT / ".test-work"
LOCAL_TEMP.mkdir(exist_ok=True)
os.environ["TEMP"] = str(LOCAL_TEMP)
os.environ["TMP"] = str(LOCAL_TEMP)
os.environ["TMPDIR"] = str(LOCAL_TEMP)
# Must precede importing the app: tests never load the personal .env file.
import dotenv

dotenv.load_dotenv = lambda *args, **kwargs: False
import tempfile

tempfile.tempdir = str(LOCAL_TEMP)
import pytest

if __name__ == "__main__":
    args = sys.argv[1:] or ["-q"]
    raise SystemExit(pytest.main([*args, "--basetemp=" + str(LOCAL_TEMP / "pytest")]))
