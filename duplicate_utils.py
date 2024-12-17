import hashlib
from os import listdir, remove
from os.path import isfile, join
from common import console


def calculate_file_hash(file_path):
    """Calculate the hash of a file to detect duplicates."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as file:
        buf = file.read()
        hasher.update(buf)
    return hasher.hexdigest()


def remove_duplicate_files(path_to_logs):
    """Remove duplicate files from the logs directory based on file content."""
    files = [
        join(path_to_logs, f)
        for f in listdir(path_to_logs)
        if isfile(join(path_to_logs, f))
    ]
    seen_hashes = {}
    duplicates_removed = 0
    for file_path in files:
        file_hash = calculate_file_hash(file_path)
        if file_hash in seen_hashes:
            console.print(
                f"[bold red]Duplicate detected:[/bold red] {file_path} [red](removed)[/red]"
            )
            remove(file_path)
            duplicates_removed += 1
        else:
            seen_hashes[file_hash] = file_path

    if duplicates_removed > 0:
        console.print(
            f"[bold green]Duplicate file removal completed.[/bold green] "
            f"[bright_green]{duplicates_removed} duplicates removed.[/bright_green]"
        )
    else:
        console.print("[bold green]No duplicates found.[/bold green]")


def load_logs(path_to_logs):
    """Load and reverse logs from the specified directory."""
    import pandas as pd
    from common import console
    from rich.progress import track

    files = [f for f in listdir(path_to_logs) if isfile(join(path_to_logs, f))]
    if not files:
        console.print(f"[bold red]No log files found in {path_to_logs}![/bold red]")
        return []
    logs = []
    for file in track(files, description="[cyan]Loading logs...[/cyan]"):
        df = pd.read_csv(join(path_to_logs, file))
        if "entry" not in df.columns:
            console.print(
                f"[yellow]Skipping file {file} as 'entry' column not found.[/yellow]"
            )
            continue
        logs.extend(reversed(df["entry"]))
    return logs
