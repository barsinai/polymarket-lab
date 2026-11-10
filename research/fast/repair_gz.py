"""Repair recording archives (<hour>.jsonl.gz) that hold a damaged gzip member: keep only the members that
decompress completely. Default: files modified in the last RECENT_H hours (3) under the given directories;
ALL=1 checks every file. Writes the repaired file atomically; prints what it did. Usage:
  python research/fast/repair_gz.py data/fast/rtds data/fast/bookws"""
import os, re, sys, time, zlib
RECENT_H = float(os.environ.get("RECENT_H", "3")); ALL = os.environ.get("ALL") == "1"


def members(data):
    """(start, end, ok) for every gzip member found; broken members are skipped by re-syncing on the next header"""
    out = []; pos = 0
    while pos < len(data):
        z = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            z.decompress(data[pos:])
            if not z.eof:
                raise zlib.error("truncated")
            end = len(data) - len(z.unused_data); out.append((pos, end, True)); pos = end
        except zlib.error:
            m = re.compile(b"\x1f\x8b\x08").search(data, pos + 1)
            end = m.start() if m else len(data); out.append((pos, end, False)); pos = end
    return out


n_bad = 0
for d in sys.argv[1:]:
    for name in sorted(os.listdir(d)):
        f = os.path.join(d, name)
        if not name.endswith(".jsonl.gz") or (not ALL and time.time() - os.path.getmtime(f) > RECENT_H * 3600):
            continue
        data = open(f, "rb").read()
        ms = members(data)
        if all(ok for _, _, ok in ms):
            continue
        good = b"".join(data[a:b] for a, b, ok in ms if ok)
        n_bad += 1
        print(f"{f}: {len(ms)} members, {sum(1 for m in ms if not m[2])} broken, keeping {len(good)} of {len(data)} bytes", flush=True)
        if good:
            with open(f + ".repair", "wb") as fh:
                fh.write(good)
            os.replace(f + ".repair", f)
        else:
            print(f"  nothing recoverable in {f}; left as is")
print("repair_gz: files repaired", n_bad)
