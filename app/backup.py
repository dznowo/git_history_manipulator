import shutil
import os
from datetime import datetime


def create_backup():
    name = f".git_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copytree(".git", name)
    return name


def restore_backup(path):
    shutil.rmtree(".git")
    shutil.copytree(path, ".git")