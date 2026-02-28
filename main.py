import os
import sys
import subprocess
import shutil
import argparse
import random
from datetime import datetime, timedelta
from collections import defaultdict

DATE_FMT = "%d.%m.%Y"
DT_FMT = "%d.%m.%Y - %H:%M"


# -------------------------------------------------
# Git
# -------------------------------------------------

def get_commits():
    cmd = ["git", "log", "--reverse", "--pretty=format:%H|%ct"]
    out = subprocess.check_output(cmd).decode().strip().split("\n")

    commits = []
    for line in out:
        sha, ts = line.split("|")
        commits.append((sha, int(ts)))

    if not commits:
        print("Репозиторий пуст.")
        sys.exit(1)

    return commits


# -------------------------------------------------
# Holidays
# -------------------------------------------------

def load_holidays(path="holidays.txt"):
    holidays = set()
    if not os.path.exists(path):
        return holidays

    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                holidays.add(datetime.strptime(line, DATE_FMT).date())

    return holidays


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def normalize(weights):
    if weights is None:
        raise ValueError("Distribution not provided")

    if any(w < 0 for w in weights):
        raise ValueError("Distribution cannot contain negative values")

    s = sum(weights)
    if s == 0:
        raise ValueError("Distribution sum cannot be zero")

    return [w / s for w in weights]


# -------------------------------------------------
# Schedule generation
# -------------------------------------------------

def generate_schedule(commits, weekday_curve, hour_curve, holidays, min_per_day):

    weekday_curve = normalize(weekday_curve)
    hour_curve = normalize(hour_curve)

    first_dt = datetime.fromtimestamp(commits[0][1])
    last_dt = datetime.fromtimestamp(commits[-1][1])

    current = first_dt.date()
    end = last_dt.date()

    valid_days = []

    while current <= end:
        if current not in holidays:
            valid_days.append(current)
        current += timedelta(days=1)

    if not valid_days:
        raise ValueError("Нет допустимых дней (все даты исключены).")

    # Проверка минимального числа коммитов
    min_required = len(valid_days) * min_per_day
    if len(commits) < min_required:
        raise ValueError(
            f"Недостаточно коммитов. Нужно минимум {min_required}, есть {len(commits)}"
        )

    # Вес каждого дня
    day_weights = [weekday_curve[d.weekday()] for d in valid_days]
    total_day_weight = sum(day_weights)

    if total_day_weight == 0:
        raise ValueError("Все допустимые дни имеют нулевой вес.")

    day_weights = [w / total_day_weight for w in day_weights]

    commits_per_day = defaultdict(int)

    # сначала распределяем минимум
    remaining = len(commits)
    for d in valid_days:
        commits_per_day[d] = min_per_day
        remaining -= min_per_day

    # затем распределяем остальное по весам
    for d, w in zip(valid_days, day_weights):
        if remaining <= 0:
            break
        add = int(w * remaining)
        commits_per_day[d] += add

    # корректируем остаток
    total_assigned = sum(commits_per_day.values())
    remainder = len(commits) - total_assigned

    day_cycle = iter(valid_days)
    while remainder > 0:
        try:
            d = next(day_cycle)
        except StopIteration:
            day_cycle = iter(valid_days)
            d = next(day_cycle)
        commits_per_day[d] += 1
        remainder -= 1

    # генерация timestamp
    new_timestamps = []
    last_ts = 0

    for d in valid_days:
        count = commits_per_day[d]
        for _ in range(count):
            hour = random.choices(range(24), weights=hour_curve)[0]
            minute = random.randint(0, 59)
            second = random.randint(0, 59)

            dt = datetime(d.year, d.month, d.day, hour, minute, second)
            ts = int(dt.timestamp())

            if ts <= last_ts:
                ts = last_ts + 1

            last_ts = ts
            new_timestamps.append(ts)

    # строгая гарантия порядка
    if len(new_timestamps) != len(commits):
        new_timestamps = new_timestamps[:len(commits)]

    return new_timestamps


# -------------------------------------------------
# Preview
# -------------------------------------------------

def preview(commits, new_ts):

    changed = False

    for (sha, old_ts), new in zip(commits, new_ts):
        if old_ts != new:
            changed = True

            old_dt = datetime.fromtimestamp(old_ts)
            new_dt = datetime.fromtimestamp(new)

            sha_short = sha[:7]

            if old_dt.date() == new_dt.date():
                print(f"{sha_short} | {old_dt.strftime(DT_FMT)} -> {new_dt.strftime('%H:%M')}")
            else:
                print(f"{sha_short} | {old_dt.strftime(DT_FMT)} -> {new_dt.strftime(DT_FMT)}")

    if not changed:
        print("Изменения не требуются")
        return False

    # Среднее по календарным дням
    start_date = datetime.fromtimestamp(new_ts[0]).date()
    end_date = datetime.fromtimestamp(new_ts[-1]).date()

    calendar_days = (end_date - start_date).days + 1
    avg = len(new_ts) / calendar_days

    print(f"\nСреднее число коммитов в день: {avg:.2f}")

    return True


# -------------------------------------------------
# Backup & restore
# -------------------------------------------------

def make_backup():
    name = ".git_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    subprocess.check_call(["git", "clone", "--mirror", ".", name])
    return name


def restore(path):
    if not os.path.exists(path):
        print("Backup не найден.")
        sys.exit(1)

    shutil.rmtree(".git")
    shutil.copytree(path, ".git")
    print("Репозиторий восстановлен.")


# -------------------------------------------------
# Apply rewrite
# -------------------------------------------------

def apply_rewrite(commits, new_ts):

    mapping = {sha: ts for (sha, _), ts in zip(commits, new_ts)}

    script = """
from datetime import datetime
def commit_callback(commit):
    sha = commit.original_id.decode()
    if sha in mapping:
        new_ts = mapping[sha]
        commit.author_date = new_ts
        commit.committer_date = new_ts
"""

    with open("rewrite_script.py", "w") as f:
        f.write("mapping = " + repr(mapping) + "\n")
        f.write(script)

    subprocess.check_call(["git", "filter-repo", "--force", "--commit-callback", "rewrite_script.py"])

    os.remove("rewrite_script.py")


# -------------------------------------------------
# Main
# -------------------------------------------------

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--weekday", nargs=7, type=float, required=True)
    parser.add_argument("--hours", nargs=24, type=float, required=True)
    parser.add_argument("--min-per-day", type=int, default=0)

    parser.add_argument("command", nargs="?", default="run")
    parser.add_argument("restore_path", nargs="?")

    args = parser.parse_args()

    if args.command == "restore":
        restore(args.restore_path)
        return

    commits = get_commits()
    holidays = load_holidays()

    new_ts = generate_schedule(
        commits,
        args.weekday,
        args.hours,
        holidays,
        args.min_per_day
    )

    changed = preview(commits, new_ts)

    if not changed:
        return

    confirm = input("\nПрименить изменения? (y/n): ")
    if confirm.lower() != "y":
        print("Отменено.")
        return

    backup = make_backup()
    print(f"Backup создан: {backup}")

    apply_rewrite(commits, new_ts)

    print("История успешно переписана.")


if __name__ == "__main__":
    main()