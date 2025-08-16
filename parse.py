#!/usr/bin/env python3
import json, re
from pathlib import Path

MD_CANDIDATES = ["servers.md", "minecraft-server-jar-downloads.md"]
OUT_FILE = "servers.json"

# version-like tokens: releases (1.21.1, 1.20, 1.20.6-pre1) & snapshots (24w31a)
RE_VER = re.compile(r"""
    (?:
        \d+\.\d+(?:\.\d+)?(?:-[A-Za-z0-9]+)?   # 1.21 | 1.21.1 | 1.20.6-pre1
        |
        \d{2}w\d{2}[a-z]                       # 24w31a
    )
""", re.X)

RE_URL = re.compile(r"https?://[^\s\)]+/server\.jar", re.I)

def pick_md_file() -> Path:
    for name in MD_CANDIDATES:
        p = Path(name)
        if p.exists():
            return p
    raise SystemExit("No servers.md found. Put it next to this script.")

def extract_entries(text: str):
    entries = []
    for line in text.splitlines():
        u = RE_URL.search(line)
        if not u:
            continue
        url = u.group(0).strip()
        # everything before the URL -> try to find a version token
        before = line[:u.start()]
        m = RE_VER.search(before)
        if m:
            ver = m.group(0)
        else:
            # fallback: first non-empty token in the line
            tokens = [t for t in re.split(r"[|\s]+", before.strip()) if t]
            ver = tokens[0] if tokens else "unknown"
        entries.append({"name": ver, "url": url})
    return entries

def dedupe_keep_latest(items):
    # de-dupe by URL (Mojang URLs sind eindeutig)
    seen = set()
    out = []
    for it in items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        out.append(it)
    # optional sort: releases/snapshots gemischt, aber Name desc
    return sorted(out, key=lambda x: x["name"], reverse=True)

def main():
    md_path = pick_md_file()
    text = md_path.read_text(encoding="utf-8")
    found = extract_entries(text)
    if not found:
        print("[!] Parsed 0 entries. Quick tips:")
        print("    - Jede Zeile muss irgendwo eine URL mit /server.jar enthalten")
        print("    - Nimm die RAW-Ansicht oder kopiere Links ohne Umbruch")
        # kleine Debughilfe:
        print("\nFirst 5 lines preview:")
        for l in text.splitlines()[:5]:
            print("  ", l)
        return
    cleaned = dedupe_keep_latest(found)
    Path(OUT_FILE).write_text(json.dumps({"servers": cleaned}, indent=2), encoding="utf-8")
    print(f"[OK] Parsed {len(cleaned)} entries → {OUT_FILE}")

if __name__ == "__main__":
    main()
