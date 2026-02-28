import subprocess
import sys
import os
import shutil
from datetime import datetime, timedelta
from collections import defaultdict
import random
import argparse


# -----------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# -----------------------------

def run_git_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(1)
    return result.stdout.strip()


def get_commits():
    output = run_git_command(
        ["git", "log", "--reverse", "--pretty=format:%H|%ct"]
    )
    commits = []
    for line in output.splitlines():
        sha, ts = line.split("|")
        commits.append((sha, datetime.fromtimestamp(int(ts))))
    return commits


def load_holidays(path):
    holidays = set()
    if not os.path.exists(path):
        return holidays
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                holidays.add(datetime.strptime(line, "%d.%m.%Y").date())
    return holidays


def normalize_curve(curve):
    total = sum(curve)
    return [x / total for x in curve]


def weighted_choice(weights):
    r = random.random()
    cumulative = 0
    for i, w in enumerate(weights):
        cumulative += w
        if r <= cumulative:
            return i
    return len(weights) - 1


# -----------------------------
# ГЕНЕРАЦИЯ НОВЫХ ДАТ
# -----------------------------

def generate_schedule(commits, day_curve, hour_curve,
                      holidays, min_commits_per_day):

    day_curve = normalize_curve(day_curve)
    hour_curve = normalize_curve(hour_curve)

    start = commits[0][1]
    end = commits[-1][1]
    total_commits = len(commits)

    days = []
    current = start.date()
    while current <= end.date():
        if current not in holidays:
            days.append(current)
        current += timedelta(days=1)

    if not days:
        raise Exception("Нет доступных дней для размещения коммитов")

    # проверка минимального числа коммитов
    max_capacity = len(days) * 24
    if total_commits > max_capacity:
        raise Exception("Недостаточно слотов для размещения коммитов")

    min_required = len(days) * min_commits_per_day
    if total_commits < min_required:
        raise Exception("Недостаточно коммитов для соблюдения минимального числа в день")

    schedule = []
    day_counts = defaultdict(int)

    last_time = start

    for sha, old_dt in commits:

        while True:
            day_index = weighted_choice(day_curve)
            target_day = days[day_index % len(days)]

            hour = weighted_choice(hour_curve)

            new_dt = datetime.combine(
                target_day,
                datetime.min.time()
            ) + timedelta(hours=hour)

            if new_dt > last_time:
                break

        last_time = new_dt
        day_counts[target_day] += 1
        schedule.append((sha, old_dt, new_dt))

    avg_per_day = total_commits / len(days)

    return schedule, avg_per_day
def print_preview(schedule):
    changes = False
    for sha, old_dt, new_dt in schedule:
        short = sha[:8]
        old_date = old_dt.strftime("%d.%m.%Y")
        new_date = new_dt.strftime("%d.%m.%Y")

        if old_dt.date() == new_dt.date():
            if old_dt.time() != new_dt.time():
                print(f"{short} | {old_date} - {old_dt.strftime('%H:%M')} -> {new_dt.strftime('%H:%M')}")
                changes = True
        else:
            print(f"{short} | {old_date} - {old_dt.strftime('%H:%M')} -> {new_date} - {new_dt.strftime('%H:%M')}")
            changes = True

    if not changes:
        print("Изменения не требуются — коммиты уже соответствуют параметрам.")

def create_backup():
    backup_path = f".git_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copytree(".git", backup_path)
    print(f"Бэкап создан: {backup_path}")
    return backup_path


def apply_rewrite(schedule):

    env_script = "env-filter.sh"
    with open(env_script, "w") as f:
        f.write("case \"$GIT_COMMIT\" in\n")
        for sha, _, new_dt in schedule:
            ts = int(new_dt.timestamp())
            f.write(f"{sha})\n")
            f.write(f"export GIT_AUTHOR_DATE=\"{ts}\"\n")
            f.write(f"export GIT_COMMITTER_DATE=\"{ts}\"\n")
            f.write(";;\n")
        f.write("esac\n")

    subprocess.run([
        "git", "filter-branch", "--env-filter",
        f"bash {env_script}", "--", "--all"
    ])

def restore_backup(path):
    if not os.path.exists(path):
        print("Бэкап не найден")
        return
    shutil.rmtree(".git")
    shutil.copytree(path, ".git")
    print("История восстановлена")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--holidays", default="holidays.txt")
    parser.add_argument("--min-per-day", type=int, default=0)
    parser.add_argument("--day-curve", nargs=7, type=float, required=False)
    parser.add_argument("--hour-curve", nargs=24, type=float, required=False)
    parser.add_argument("command", nargs="?")

    args = parser.parse_args()

    if args.command == "restore":
        restore_backup(sys.argv[-1])
        return

    commits = get_commits()
    holidays = load_holidays(args.holidays)

    schedule, avg = generate_schedule(
        commits,
        args.day_curve,
        args.hour_curve,
        holidays,
        args.min_per_day
    )

    print_preview(schedule)
    print(f"\nСреднее число коммитов в день: {avg:.2f}")

    confirm = input("Применить изменения? (y/n): ")
    if confirm.lower() == "y":
        backup = create_backup()
        apply_rewrite(schedule)
        print("Готово.")