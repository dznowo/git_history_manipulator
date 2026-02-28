import subprocess
from datetime import datetime
from .models import Commit


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return r.stdout.strip()


def list_branches():
    output = run(["git", "branch", "--format=%(refname:short)"])
    return output.splitlines()


def get_commits(branch):
    output = run([
        "git", "log", branch,
        "--reverse",
        "--pretty=format:%H|%ct"
    ])

    commits = []
    for line in output.splitlines():
        sha, ts = line.split("|")
        commits.append(
            Commit(
                sha,
                datetime.fromtimestamp(int(ts))
            )
        )
    return commits