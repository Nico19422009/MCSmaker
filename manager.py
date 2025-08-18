#!/usr/bin/env python3
import json, os, re, shutil, sys, time, urllib.request, urllib.error
from pathlib import Path

# ================== CONFIG (persisted) ==================
CONFIG_FILE = "mcauto.json"
DEFAULTS = {
    "jars_dir": "minecraft_jars",
    "servers_base": "minecraft_servers",
    "java_path": "java",
    "memory": "4G"  # start.sh RAM
}
MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

# ================== UTILITIES ==================
def clear(): os.system("cls" if os.name == "nt" else "clear")

def load_cfg() -> dict:
    if Path(CONFIG_FILE).exists():
        try:
            return {**DEFAULTS, **json.loads(Path(CONFIG_FILE).read_text(encoding="utf-8"))}
        except Exception:
            pass
    return DEFAULTS.copy()

def save_cfg(cfg: dict):
    Path(CONFIG_FILE).write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", (s or "")).strip("_") or "server"

def write_text(path: Path, content: str, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    try: os.chmod(path, mode)
    except: pass

def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "McAuto/1.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)

def download_with_resume(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    if dest.exists():
        print(f"[SKIP] {dest.name} already exists."); return True
    headers = {"User-Agent": "McAuto/1.1"}
    downloaded = 0
    if part.exists():
        downloaded = part.stat().st_size
        headers["Range"] = f"bytes={downloaded}-"
        print(f"[*] Resuming at {downloaded} bytes")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, part.open("ab") as out:
            total = None
            cr = resp.headers.get("Content-Range")
            if cr and "/" in cr:
                try: total = int(cr.split("/")[-1])
                except: total = None
            elif resp.headers.get("Content-Length"):
                try: total = downloaded + int(resp.headers["Content-Length"])
                except: total = None
            block = 1024 * 1024
            done = downloaded
            while True:
                chunk = resp.read(block)
                if not chunk: break
                out.write(chunk); done += len(chunk)
                if total:
                    pct = int(done * 100 / total)
                    print(f"\r[DL] {dest.name} {pct}% ({done}/{total} bytes)", end="")
                else:
                    print(f"\r[DL] {dest.name} {done} bytes", end="")
            print()
    except urllib.error.HTTPError as e:
        print(f"[ERR] HTTP {e.code}: {e.reason}"); return False
    except urllib.error.URLError as e:
        print(f"[ERR] URL error: {e.reason}"); return False
    part.replace(dest)
    print(f"[OK] Saved → {dest}")
    return True

# ================== RAM NORMALIZATION & HEAP SAFETY ==================
import re as _re

def normalize_ram(value: str, fallback: str = "4G") -> str:
    """Accepts '4G', '4GB', '4096', '4096M', '2048MB', '2 g', etc. → returns JVM-safe '4G'/'4096M'."""
    if not value:
        return fallback
    v = value.strip().upper().replace(" ", "")
    v = _re.sub(r"B$", "", v)  # strip optional trailing B
    m = _re.match(r"^(\d+)([KMG]?)$", v)
    if not m:
        return fallback
    num, unit = m.groups()
    if unit in ("K", "M", "G") and int(num) > 0:
        return f"{num}{unit}"
    # No unit → assume MB if big, else GB
    n = int(num)
    if n >= 256:
        return f"{n}M"
    return f"{n}G"

def _total_mem_mb_linux() -> int | None:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return kb // 1024
    except Exception:
        return None
    return None

def warn_if_heap_too_big(mem_str: str):
    m = _re.match(r"^(\d+)([MG])$", mem_str.upper())
    if not m:
        return
    n, u = int(m.group(1)), m.group(2)
    want_mb = n * (1024 if u == 'G' else 1)
    total = _total_mem_mb_linux()
    if total and want_mb > int(total * 0.85):
        print(f"[WARN] Requested heap {want_mb}MB is close to/above system RAM {total}MB. Consider lowering it.")

# ================== MOJANG PICKER ==================
def pick_version_interactive(versions: list[dict]) -> dict | None:
    show = versions[:30]  # latest 30
    while True:
        print("\nLatest versions (newest first):")
        for i, v in enumerate(show, 1):
            print(f"{i:>2}. {v['id']}  [{v.get('type','')}]")
        print("\n[f] Filter   [a] Show 100   [q] Cancel")
        choice = input("Pick number or action: ").strip().lower()
        if choice == "q": return None
        if choice == "f":
            term = input("Filter (e.g. 1.21 or 24w): ").strip().lower()
            show = [v for v in versions if term in v["id"].lower()][:100]; continue
        if choice == "a":
            show = versions[:100]; continue
        if choice.isdigit():
            idx = int(choice)-1
            if 0 <= idx < len(show): return show[idx]
        print("[!] Invalid choice.")

def get_server_jar_url(ver_obj: dict) -> str:
    detail = fetch_json(ver_obj["url"])
    dl = detail.get("downloads", {})
    if "server" not in dl:
        raise KeyError("server.jar not available for this version")
    return dl["server"]["url"]

# ================== JARs MENU ==================
def jars_menu(cfg: dict):
    jars_dir = Path(cfg["jars_dir"]).expanduser().resolve()
    jars_dir.mkdir(parents=True, exist_ok=True)

    # optional legacy URL list
    url_cfg_path = Path("servers.json")
    url_cfg = {"servers": []}
    if url_cfg_path.exists():
        try: url_cfg = json.loads(url_cfg_path.read_text(encoding="utf-8"))
        except: pass

    while True:
        clear()
        print("=== McAuto · JARs ===")
        print(f"JARs dir: {jars_dir}")
        print("[1] Download JAR from Mojang (pick version)")
        print("[2] Download JAR from Mojang & save to servers.json")
        print("[3] Show local JAR files")
        print("[4] Change JARs directory")
        print("[5] (Optional) Download ONE from servers.json URL list")
        print("[6] (Optional) Download ALL from servers.json URL list")
        print("[0] Back")
        c = input("\nChoose: ").strip()

        if c == "1" or c == "2":
            try:
                manifest = fetch_json(MANIFEST_URL)
                versions = manifest.get("versions", [])
            except Exception as e:
                print(f"[ERR] Could not fetch Mojang manifest: {e}"); input("Press ENTER…"); continue
            sel = pick_version_interactive(versions)
            if not sel: continue
            try: url = get_server_jar_url(sel)
            except Exception as e:
                print(f"[ERR] {e}"); input("Press ENTER…"); continue
            name = safe_name(sel["id"])
            dest = jars_dir / f"{name}.jar"
            if download_with_resume(url, dest) and c == "2":
                url_cfg.setdefault("servers", []).append({"name": sel["id"], "url": url})
                url_cfg_path.write_text(json.dumps(url_cfg, indent=2), encoding="utf-8")
                print(f"[OK] Added to servers.json: {sel['id']}")
            input("Press ENTER…")

        elif c == "3":
            files = sorted([p.name for p in jars_dir.glob("*.jar")])
            if not files: print("[INFO] No JARs yet.")
            else:
                print("\nJAR files:")
                for n in files: print(" -", n)
            input("Press ENTER…")

        elif c == "4":
            newp = input("New JARs directory: ").strip()
            if newp:
                jars_dir = Path(newp).expanduser().resolve(); jars_dir.mkdir(parents=True, exist_ok=True)
                cfg["jars_dir"] = str(jars_dir); save_cfg(cfg)
                print(f"[OK] Using {jars_dir}")
            input("Press ENTER…")

        elif c == "5":
            servers = url_cfg.get("servers", [])
            if not servers: print("[INFO] servers.json empty."); input("Press ENTER…"); continue
            for i, s in enumerate(servers, 1):
                print(f"{i:>2}. {s.get('name','?')} -> {s.get('url','')}")
            try: idx = int(input("Which #? ")) - 1
            except: idx = -1
            if not (0 <= idx < len(servers)): print("[WARN] Invalid."); input("Press ENTER…"); continue
            name = safe_name(servers[idx].get("name") or f"server_{idx+1}")
            url  = servers[idx].get("url","").strip()
            if not url: print("[ERR] Missing URL."); input("Press ENTER…"); continue
            dest = jars_dir / f"{name}.jar"
            download_with_resume(url, dest)
            input("Press ENTER…")

        elif c == "6":
            servers = url_cfg.get("servers", [])
            if not servers: print("[INFO] servers.json empty."); input("Press ENTER…"); continue
            for i, s in enumerate(servers, 1):
                name = safe_name(s.get("name") or f"server_{i}")
                url  = s.get("url","").strip()
                if not url: print(f"[SKIP] {name}: missing URL."); continue
                dest = jars_dir / f"{name}.jar"
                download_with_resume(url, dest)
            input("Press ENTER…")

        elif c == "0":
            break
        else:
            print("[WARN] Unknown option."); time.sleep(0.6)

# ================== SERVERS MENU ==================
def write_start_sh(folder: Path, jar_name: str, java_path="java", memory="4G"):
    mem = normalize_ram(memory, "4G")
    sh = f"""#!/usr/bin/env bash
cd "$(dirname "$0")"
{java_path} -Xms{mem} -Xmx{mem} -jar "{jar_name}" nogui
"""
    write_text(folder / "start.sh", sh, 0o755)
    bat = f"""@echo off
cd /d %~dp0
{java_path} -Xms{mem} -Xmx{mem} -jar "{jar_name}" nogui
pause
"""
    write_text(folder / "start.bat", bat)

def create_server_folder(base_dir: Path, server_name: str, version_id: str, jar_url: str, java_path: str, memory: str):
    folder = base_dir / safe_name(server_name)
    folder.mkdir(parents=True, exist_ok=True)
    jar_name = f"server-{safe_name(version_id)}.jar"
    jar_path = folder / jar_name

    print(f"[*] Downloading server.jar for {version_id} → {jar_path}")
    if not download_with_resume(jar_url, jar_path):
        print("[ERR] Download failed."); return False

    write_text(folder / "eula.txt", "eula=true\n")
    props = [
        f"# Generated {int(time.time())}",
        "motd=A Minecraft Server",
        "online-mode=true",
        "enable-command-block=false",
        "white-list=false",
        "view-distance=10",
        "simulation-distance=10",
        "max-players=20",
        "enable-status=true"
    ]
    write_text(folder / "server.properties", "\n".join(props) + "\n")
    # Normalize & warn before writing launcher scripts
    mem_norm = normalize_ram(memory, "4G")
    warn_if_heap_too_big(mem_norm)
    write_start_sh(folder, jar_name, java_path, mem_norm)
    print(f"[DONE] Server ready at: {folder}")
    print("Start it with: ./start.sh  (Linux)  or  start.bat (Windows)")
    return True

def detect_servers(base_dir: Path) -> list[dict]:
    base_dir.mkdir(parents=True, exist_ok=True)
    servers = []
    for p in sorted(base_dir.iterdir()):
        if not p.is_dir(): continue
        if not (p / "start.sh").exists(): continue
        start_txt = ""
        try: start_txt = (p / "start.sh").read_text(encoding="utf-8")
        except: pass
        mem = re.search(r"-Xmx(\S+)", start_txt)
        jar = re.search(r'-jar\s+"?([^"\n]+)"?', start_txt)
        ver = "?"
        if jar:
            jname = Path(jar.group(1)).name
            mver = re.search(r"server-([A-Za-z0-9._-]+)\.jar", jname)
            if mver: ver = mver.group(1)
        servers.append({
            "name": p.name,
            "path": p,
            "memory": mem.group(1) if mem else "?",
            "version": ver
        })
    return servers

def servers_menu(cfg: dict):
    base_dir = Path(cfg["servers_base"]).expanduser().resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    while True:
        clear()
        print("=== McAuto · Servers ===")
        print(f"Base dir: {base_dir}   |   Default RAM: {cfg['memory']}   |   Java: {cfg['java_path']}")
        print("[1] Build full server (choose Mojang version)")
        print("[2] Show servers")
        print("[3] Delete server")
        print("[4] Change servers base directory")
        print("[0] Back")
        c = input("\nChoose: ").strip()

        if c == "1":
            try:
                manifest = fetch_json(MANIFEST_URL)
                versions = manifest.get("versions", [])
            except Exception as e:
                print(f"[ERR] Could not fetch Mojang manifest: {e}"); input("Press ENTER…"); continue
            sel = pick_version_interactive(versions)
            if not sel: continue
            try: url = get_server_jar_url(sel)
            except Exception as e:
                print(f"[ERR] {e}"); input("Press ENTER…"); continue

            default_name = sel["id"]
            name = input(f"Server name [{default_name}]: ").strip() or default_name
            alt = input(f"Save under (blank = {base_dir}): ").strip()
            target_base = Path(alt).expanduser().resolve() if alt else base_dir
            target_base.mkdir(parents=True, exist_ok=True)
            create_server_folder(target_base, name, sel["id"], url, cfg["java_path"], cfg["memory"])
            input("Press ENTER…")

        elif c == "2":
            items = detect_servers(base_dir)
            if not items: print("[INFO] No servers yet.")
            else:
                print("\n#  Name                        Version        RAM   Path")
                print("-- --------------------------- -------------- ----- ------------------------------")
                for i, s in enumerate(items, 1):
                    print(f"{i:>2} {s['name'][:27]:<27} {s['version'][:12]:<12} {s['memory'][:5]:<5} {s['path']}")
            input("Press ENTER…")

        elif c == "3":
            items = detect_servers(base_dir)
            if not items: print("[INFO] No servers to delete."); input("Press ENTER…"); continue
            print("\nSelect server to delete:")
            for i, s in enumerate(items, 1):
                print(f"{i:>2}. {s['name']}  ({s['version']}, {s['memory']})")
            try: idx = int(input("Which #? ")) - 1
            except: idx = -1
            if not (0 <= idx < len(items)): print("[WARN] Invalid."); input("Press ENTER…"); continue
            target = items[idx]
            yn = input(f"Type 'YES' to delete '{target['name']}' at {target['path']}: ").strip()
            if yn != "YES":
                print("[CANCELLED]"); input("Press ENTER…"); continue
            shutil.rmtree(target["path"], ignore_errors=True)
            print(f"[OK] Deleted {target['name']}")
            input("Press ENTER…")

        elif c == "4":
            newp = input("New servers base directory: ").strip()
            if newp:
                base_dir = Path(newp).expanduser().resolve(); base_dir.mkdir(parents=True, exist_ok=True)
                cfg["servers_base"] = str(base_dir); save_cfg(cfg)
                print(f"[OK] Using {base_dir}")
            input("Press ENTER…")

        elif c == "0":
            break
        else:
            print("[WARN] Unknown option."); time.sleep(0.6)

# ================== SETTINGS MENU ==================
def settings_menu(cfg: dict):
    while True:
        clear()
        print("=== McAuto · Settings ===")
        print(f"1) JARs dir         : {cfg['jars_dir']}")
        print(f"2) Servers base dir : {cfg['servers_base']}")
        print(f"3) Java path        : {cfg['java_path']}")
        print(f"4) Default RAM      : {cfg['memory']}")
        print("0) Back")
        c = input("\nChange which? ").strip()
        if c == "1":
            p = input("New JARs dir: ").strip()
            if p: cfg["jars_dir"] = p; save_cfg(cfg)
        elif c == "2":
            p = input("New Servers base dir: ").strip()
            if p: cfg["servers_base"] = p; save_cfg(cfg)
        elif c == "3":
            p = input("Java path (e.g., java or /usr/bin/java): ").strip()
            if p: cfg["java_path"] = p; save_cfg(cfg)
        elif c == "4":
            p = input("Default RAM (e.g., 4G or 4096M): ").strip()
            if p:
                cfg["memory"] = normalize_ram(p, cfg["memory"])  # sanitize
                save_cfg(cfg)
        elif c == "0":
            break

# ================== MAIN MENU ==================
def main_menu():
    cfg = load_cfg()
    Path(cfg["jars_dir"]).expanduser().mkdir(parents=True, exist_ok=True)
    Path(cfg["servers_base"]).expanduser().mkdir(parents=True, exist_ok=True)

    while True:
        clear()
        print(r"""


               __       __   ______    ______                           __                           
/  \     /  | /      \  /      \                         /  |                          
$$  \   /$$ |/$$$$$$  |/$$$$$$  | _____  ____    ______  $$ |   __   ______    ______  
$$$  \ /$$$ |$$ |  $$/ $$ \__$$/ /     \/    \  /      \ $$ |  /  | /      \  /      \ 
$$$$  /$$$$ |$$ |      $$      \ $$$$$$ $$$$  | $$$$$$  |$$ |_/$$/ /$$$$$$  |/$$$$$$  |
$$ $$ $$/$$ |$$ |   __  $$$$$$  |$$ | $$ | $$ | /    $$ |$$   $$<  $$    $$ |$$ |  $$/ 
$$ |$$$/ $$ |$$ \__/  |/  \__$$ |$$ | $$ | $$ |/$$$$$$$ |$$$$$$  \ $$$$$$$$/ $$ |      
$$ | $/  $$ |$$    $$/ $$    $$/ $$ | $$ | $$ |$$    $$ |$$ | $$  |$$       |$$ |      
$$/      $$/  $$$$$$/   $$$$$$/  $$/  $$/  $$/  $$$$$$$/ $$/   $$/  $$$$$$$/ $$/       
                                                                                       
                                                                                       
                                                                                       



                 MCSMAKER — Minecraft Automation Tool Created by Nico19422009 Ver 0.2.1
""")
        print("1) JARs")
        print("2) Servers")
        print("3) Settings")
        print("0) Exit")
        c = input("\nChoose: ").strip()
        if c == "1": jars_menu(cfg)
        elif c == "2": servers_menu(cfg)
        elif c == "3": settings_menu(cfg)
        elif c == "0": print("[BYE]"); break
        else: print("[WARN] Unknown option."); time.sleep(0.6)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n[BYE]")
