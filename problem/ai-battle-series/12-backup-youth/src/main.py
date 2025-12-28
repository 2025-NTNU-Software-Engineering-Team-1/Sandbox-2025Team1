import csv
import hashlib
import json
import sys


def load_manifest(path):
    entries = {}
    try:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("filename")
                size = int(row.get("size", 0))
                md5 = row.get("md5", "")
                if name:
                    entries[name] = {"size": size, "md5": md5}
    except FileNotFoundError:
        return {}
    return entries


def main():
    old_entries = load_manifest("old_manifest.csv")
    new_entries = load_manifest("new_manifest.csv")

    added = []
    deleted = []
    modified = []
    unchanged = []

    for name, info in new_entries.items():
        if name not in old_entries:
            added.append({"filename": name, **info})
        elif old_entries[name]["md5"] != info["md5"]:
            modified.append({
                "filename": name,
                "old_size": old_entries[name]["size"],
                "new_size": info["size"],
                "old_md5": old_entries[name]["md5"],
                "new_md5": info["md5"],
            })
        else:
            unchanged.append({"filename": name, **info})

    for name, info in old_entries.items():
        if name not in new_entries:
            deleted.append({"filename": name, **info})

    diff_summary = ("Differential Backup Report\n"
                    f"Added: {len(added)}\n"
                    f"Deleted: {len(deleted)}\n"
                    f"Modified: {len(modified)}\n"
                    f"Unchanged: {len(unchanged)}\n")

    with open("diff_summary.txt", "w", encoding="utf-8") as f:
        f.write(diff_summary)

    md5_value = hashlib.md5(diff_summary.encode("utf-8")).hexdigest()

    old_total = sum(v["size"] for v in old_entries.values())
    new_total = sum(v["size"] for v in new_entries.values())

    report = {
        "changes": {
            "added": added,
            "deleted": deleted,
            "modified": modified,
            "unchanged": unchanged,
        },
        "statistics": {
            "old_total_size": old_total,
            "new_total_size": new_total,
            "size_diff": new_total - old_total,
        },
    }

    with open("diff_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    sys.stdout.write("Differential backup completed!\n")
    sys.stdout.write(
        f"Added: {len(added)}, Deleted: {len(deleted)}, Modified: {len(modified)}, Unchanged: {len(unchanged)}\n"
    )
    sys.stdout.write(f"Report MD5: {md5_value}\n")


if __name__ == "__main__":
    main()
