"""Download the FastSocial Instagram follower dataset and write it to data/.

Writes data/daily.csv (every reading), data/latest.csv (newest reading per account),
data/monthly/YYYY-MM.csv and data/manifest.json. Exits 0 with no changes if the
source has not moved.
"""
import csv
import gzip
import io
import json
import os
import sys
import urllib.request

BASE = "https://fastsocial.co"
OUT = os.path.join(os.path.dirname(__file__), "..", "data")


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "instagram-top-accounts-sync"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    manifest = json.loads(fetch("/instagram-stats/data/manifest.json"))
    text = gzip.decompress(fetch(manifest["full"]["url"])).decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    rows = [r for r in reader if r]
    if len(rows) < 100:
        sys.exit("refusing to write: only %d rows" % len(rows))
    rows.sort(key=lambda r: (r[0], r[1]))

    write_csv(os.path.join(OUT, "daily.csv"), header, rows)

    latest = {}
    for r in rows:
        latest[r[1]] = r
    ri = header.index("rank")
    by_rank = sorted(latest.values(), key=lambda r: (int(r[ri]) if r[ri].isdigit() else 10**9, r[1]))
    write_csv(os.path.join(OUT, "latest.csv"), header, by_rank)

    months = {}
    for r in rows:
        months.setdefault(r[0][:7], []).append(r)
    for m, mrows in months.items():
        write_csv(os.path.join(OUT, "monthly", m + ".csv"), header, mrows)

    keep = {k: manifest[k] for k in ("columns", "license", "source") if k in manifest}
    keep["rows"] = len(rows)
    keep["accounts"] = len(latest)
    keep["start"] = rows[0][0]
    keep["end"] = rows[-1][0]
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(keep, f, indent=1)
        f.write("\n")
    print("rows=%d accounts=%d %s..%s" % (len(rows), len(latest), keep["start"], keep["end"]))


if __name__ == "__main__":
    main()
