from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List
import bisect


@dataclass
class Commit:
    sha: str
    date: datetime


@dataclass
class ScheduledCommit:
    sha: str
    old_date: datetime
    new_date: datetime


class Scheduler:

    def __init__(self, day_curve, hour_curve, holidays, min_per_day):
        self.day_curve = self._normalize(day_curve)
        self.hour_curve = self._normalize(hour_curve)
        self.holidays = holidays
        self.min_per_day = min_per_day

    def _normalize(self, arr):
        total = sum(arr)
        if total == 0:
            raise ValueError("Кривая не может быть нулевой")
        return [x / total for x in arr]

    def generate_slots(self, start: datetime, end: datetime):

        slots = []
        weights = []

        current = start.replace(minute=0, second=0, microsecond=0)

        while current <= end:
            if current.date() not in self.holidays:
                dow = current.weekday()
                hour = current.hour
                w = self.day_curve[dow] * self.hour_curve[hour]
                if w > 0:
                    slots.append(current)
                    weights.append(w)
            current += timedelta(hours=1)

        if not slots:
            raise ValueError("Нет допустимых временных слотов")

        return slots, weights

    def schedule(self, commits: List[Commit]) -> List[ScheduledCommit]:

        start = commits[0].date
        end = commits[-1].date

        slots, weights = self.generate_slots(start, end)

        if len(commits) > len(slots):
            raise ValueError("Недостаточно слотов")

        cumulative = []
        total = 0
        for w in weights:
            total += w
            cumulative.append(total)

        step = total / len(commits)

        result = []
        last_time = start

        for i, commit in enumerate(commits):
            target = i * step
            idx = bisect.bisect_left(cumulative, target)

            new_time = slots[idx]

            if new_time <= last_time:
                new_time = last_time + timedelta(seconds=1)

            last_time = new_time

            result.append(
                ScheduledCommit(
                    commit.sha,
                    commit.date,
                    new_time
                )
            )

        return result