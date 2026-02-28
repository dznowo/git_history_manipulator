from app.scheduler import Scheduler, Commit
from datetime import datetime


def test_monotonic():
    commits = [
        Commit("a", datetime(2025,1,1,10)),
        Commit("b", datetime(2025,1,2,10)),
    ]

    s = Scheduler(
        [1]*7,
        [1]*24,
        set(),
        0
    )

    result = s.schedule(commits)

    assert result[1].new_date > result[0].new_date