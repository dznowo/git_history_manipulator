
# Git Time Rewriter – Usage Guide (GitHub)

This tool rewrites commit dates and times in a Git repository using configurable distribution curves.

It:

* Redistributes commits by day of week (7-point curve)
* Redistributes commits by hour of day (24-point curve)
* Skips dates listed in `holidays.txt`
* Preserves strict chronological order
* Works per branch
* Creates a full backup before rewriting
* Supports restore from backup
* Supports dry-run preview

⚠️ **Warning:** This tool rewrites Git history. Commit SHAs will change.
Only use it on branches where force-push is acceptable.

---

# 1. Requirements

* Python 3.10+
* Git
* git-filter-repo

## Install git-filter-repo (recommended)

On Ubuntu/Debian:

```bash
sudo apt install git-filter-repo
```

Or using pipx:

```bash
sudo apt install pipx
pipx install git-filter-repo
```

Verify installation:

```bash
git filter-repo --help
```

---

# 2. Setup

## Step 1 — Go to your repository

You must run the tool inside the Git repository (where `.git` exists):

```bash
cd /path/to/your/repository
```

## Step 2 — Optional: Create holidays.txt

If you want to exclude certain dates from receiving commits, create:

```
holidays.txt
```

Example:

```
02.01.2026
23.03.2026
```

Format must be:

```
DD.MM.YYYY
```

If you do not need excluded dates, you can skip this file.

---

# 3. Running the Tool (CLI)

Basic example:

```bash
python main.py \
  --day-curve 0.2 0.3 0.4 0.4 0.5 0.1 0.05 \
  --hour-curve 0 0 0 0 0 0.1 0.3 0.6 1 1 1 0.8 0.6 0.4 0.3 0.2 0.1 0 0 0 0 0 0 0 \
  --min-per-day 2
```

---

# 4. Parameters Explained

## --day-curve (7 numbers)

Order:

```
Mon Tue Wed Thu Fri Sat Sun
```

Higher numbers = more commits on that day.

Example (more activity on weekdays):

```
0.5 0.5 0.7 0.7 1 0.1 0.05
```

---

## --hour-curve (24 numbers)

Each number corresponds to an hour:

```
0 = 00:00
23 = 23:00
```

Example (typical workday):

```
0 0 0 0 0 0.1 0.3 0.6 1 1 1 0.8 0.6 0.4 0.3 0.2 0.1 0 0 0 0 0 0 0
```

The tool automatically normalizes values.

---

## --min-per-day

Minimum number of commits per valid day
(holidays excluded)

---

## --branch

Process specific branches only:

```bash
python main.py --branch main --branch dev ...
```

If not specified, all branches are processed separately.

---

# 5. Dry Run (Preview Mode)

When you run the tool, it first performs a preview.

Example output:

```
a91cd2e | 21.02.2026 - 18:02 -> 13:58
f10aa22 | 22.02.2026 - 10:15 -> 19.03.2026 - 14:22
```

If only time changed:

```
ab32cd1 | 21.02.2026 - 18:02 -> 13:58
```

At the end, it prints:

```
Average commits per day: 3.47
```

If commits already match the distribution:

```
No changes required
```

---

# 6. Applying Changes

After preview, the tool asks:

```
Apply changes? (y/n):
```

If you type:

```
y
```

It will:

1. Create a backup folder:

```
.git_backup_YYYYMMDD_HHMMSS
```

2. Rewrite commit history using git-filter-repo

---

# 7. Restoring from Backup

If something goes wrong:

```bash
python main.py restore .git_backup_YYYYMMDD_HHMMSS
```

Your repository will be fully restored.

---

# 8. After Rewriting (GitHub)

Since commit SHAs change, you must force push:

```bash
git push --force --all
git push --force --tags
```

⚠ Only do this if you understand the consequences.

---

# 9. Using the GUI

Run:

```bash
python main.py --gui
```

The GUI allows you to:

* Select branches
* Enter distribution curves
* Load holidays file
* Run preview
* Apply changes

---

# 10. Common Errors

### "Not enough slots"

Your distribution curve allows too few valid hours.

### "No valid time slots"

All day/hour weights are zero.

### "Minimum commits per day not satisfied"

Your `--min-per-day` value is too high.

---

# Typical Workflow

1. Go to repository
2. Create holidays.txt (optional)
3. Run the tool
4. Review preview
5. Confirm
6. Force push to GitHub

---

# Important Notes

* Commit order is strictly preserved
* Distribution is mathematically deterministic
* No randomness is used
* Each branch is processed independently
* Backup is always created before rewrite

