#!/usr/bin/env python3
import json, os, re, shutil, sys, time, urllib.request, urllib.error, subprocess
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

# ------- Self-update config ----------
APP_NAME = "MCSmaker"
CURRENT_VERSION = "1.5.0"  # Keep in sync with version.txt in the repo

# RAW GitHub URLs (must be raw.githubusercontent.com)
REMOTE_MANAGER_URL = "https://raw.githubusercontent.com/Nico19422009/MCSmaker/main/manager.py"
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/Nico19422009/MCSmaker/main/version.txt"

# ------ Update helpers ---------
import urllib.request, urllib.error

SEMVER_RE = re.compile(r"^v?\d+(?:\.\d+){0,2}$")  # 1 / 1.2 / 1.2.3 (optional leading 'v')

def _http_get(url: str, timeout: int = 10, cache_bust: bool = True) -> bytes:
    if cache_bust:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}_ts={int(time.time())}"  # cache buster vs CDN caching
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"{APP_NAME}/update-check",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def _parse_version(s: str):
    # robust parsing: strip BOM/CR/whitespace, allow v-prefix
    s = s.lstrip("\ufeff").strip().replace("\r", "")
    if not SEMVER_RE.match(s):
        return None
    if s.startswith("v"):
        s = s[1:]
    parts = [int(p) for p in s.split(".")]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])

def self_update() -> bool:
    dest = Path(__file__).resolve()
    try:
        print("[*] Downloading latest manager.py …")
        data = _http_get(REMOTE_MANAGER_URL, timeout=20)
        # Quick sanity check: should not be HTML
        if data[:1] == b"<":
            print("[ERR] Download looked like HTML (wrong URL?). Aborting.")
            return False
        tmp = dest.with_suffix(dest.suffix + ".new")
        with tmp.open("wb") as f:
            f.write(data)
        tmp.replace(dest)
        print("[OK] manager.py updated! Restarting…")
        # Restart into the new file
        os.execv(sys.executable, [sys.executable, str(dest)])
        return True
    except urllib.error.HTTPError as e:
        print(f"[ERR] Update failed (HTTP {e.code}): {e.reason}")
    except urllib.error.URLError as e:
        print(f"[ERR] Update failed (URL): {e.reason}")
    except Exception as e:
        print(f"[ERR] Update failed: {e}")
    return False

def check_for_updates(auto_prompt: bool = True, debug: bool = False) -> None:
    try:
        raw = _http_get(REMOTE_VERSION_URL, timeout=6).decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[i] Update check skipped ({e.__class__.__name__}).")
        return

    rv = _parse_version(raw)
    cv = _parse_version(CURRENT_VERSION)

    if debug:
        print(f"[dbg] remote raw: {repr(raw)}")
        print(f"[dbg] parsed remote: {rv}, local: {cv}")

    if rv is None:
        print(f"[i] Update check skipped (invalid remote version: {raw!r}).")
        return
    if cv is None:
        print(f"[i] Local CURRENT_VERSION invalid ({CURRENT_VERSION!r}). Use e.g. 1.0.0")
        return

    if rv > cv:
        print(f"[UPDATE] New version available: {raw.strip()} (current {CURRENT_VERSION})")
        if auto_prompt:
            ans = input("Update now? [Y/n] ").strip().lower()
            if ans in ("", "y", "yes"):
                self_update()
        else:
            print("Tip: run 'Update program' from the menu.")
    else:
        print(f"[OK] You are up to date (v{CURRENT_VERSION}).")

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
    req = urllib.request.Request(url, headers={"User-Agent": "MCSmaker/1.4.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)

def download_with_resume(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    if dest.exists():
        print(f"[SKIP] {dest.name} already exists."); return True
    headers = {"User-Agent": "MCSmaker/1.4.0"}
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

def normalize_ram(value: str, fallback: str = "4G") -> str:
    """Accepts '4G', '4GB', '4096', '4096M', '2048MB', '2 g', etc. → returns JVM-safe '4G'/'4096M'."""
    if not value: return fallback
    v = value.strip().upper().replace(" ", "")
    v = re.sub(r"B$", "", v)  # strip optional trailing B
    m = re.match(r"^(\d+)([KMG]?)$", v)
    if not m: return fallback
    num, unit = m.groups()
    if unit in ("K", "M", "G") and int(num) > 0:
        return f"{num}{unit}"
    # No unit → assume MB if big, else GB
    n = int(num)
    if n >= 256: return f"{n}M"
    return f"{n}G"

def _total_mem_mb_linux() -> int | None:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1]); return kb // 1024
    except Exception:
        return None
    return None

def warn_if_heap_too_big(mem_str: str):
    m = re.match(r"^(\d+)([MG])$", mem_str.upper())
    if not m: return
    n, u = int(m.group(1)), m.group(2)
    want_mb = n * (1024 if u == 'G' else 1)
    total = _total_mem_mb_linux()
    if total and want_mb > int(total * 0.85):
        print(f"[WARN] Requested heap {want_mb}MB is close to/above system RAM {total}MB. Consider lowering it.")

# ================== DEPENDENCY CHECK (apt) ==================
REQUIRED_PKGS = [
    "python3",
    "default-jdk",
    # screen for live console mgmt
    "screen",
]

def _dpkg_installed(pkg: str) -> bool:
    res = subprocess.run(["dpkg", "-s", pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0

def check_and_install_dependencies():
    print("[*] Checking dependencies…")

    # ---- Java ----
    java_path = shutil.which("java")
    if not java_path:
        print("[WARN] No Java found on system. Installing default-jdk via apt…")
        try:
            subprocess.run(["sudo", "apt-get", "update", "-y"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "default-jdk"], check=True)
            print("[OK] Java installed.")
        except Exception as e:
            print(f"[ERR] Could not install Java automatically: {e}")
            print("Please install manually: sudo apt-get install default-jdk")
    else:
        try: ver = subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT).decode().splitlines()[0]
        except Exception: ver = "(version unknown)"
        print(f"[OK] Found Java at {java_path} {ver}")

    # ---- Other packages ----
    missing = [pkg for pkg in REQUIRED_PKGS if not _dpkg_installed(pkg)]
    if missing:
        print(f"[WARN] Missing packages: {', '.join(missing)}")
        try:
            subprocess.run(["sudo", "apt-get", "install", "-y"] + missing, check=True)
            print("[OK] Dependencies installed.")
        except Exception as e:
            print(f"[ERR] Could not install: {e}")
            print("Please install manually: sudo apt-get install " + " ".join(missing))
    else:
        print("[OK] All other dependencies already installed.")

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
        print("=== MCSmaker · JARs ===")
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
            url  = servers[idx].get("url","\n").strip()
            if not url: print("[ERR] Missing URL."); input("Press ENTER…"); continue
            dest = jars_dir / f"{name}.jar"
            download_with_resume(url, dest)
            input("Press ENTER…")

        elif c == "6":
            servers = url_cfg.get("servers", [])
            if not servers: print("[INFO] servers.json empty."); input("Press ENTER…"); continue
            for i, s in enumerate(servers, 1):
                name = safe_name(s.get("name") or f"server_{i}")
                url  = s.get("url","\n").strip()
                if not url: print(f"[SKIP] {name}: missing URL."); continue
                dest = jars_dir / f"{name}.jar"
                download_with_resume(url, dest)
            input("Press ENTER…")

        elif c == "0":
            break
        else:
            print("[WARN] Unknown option."); time.sleep(0.6)

# ================== LAUNCH SCRIPTS ==================

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

# ================== SERVER CREATE/DISCOVER ==================

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

# ================== SCREEN-BASED SERVER MANAGEMENT ==================

# All server processes run inside GNU screen sessions.
# Session name pattern: mc_<foldername>

def _ensure_screen():
    if not shutil.which("screen"):
        raise RuntimeError("GNU screen is not installed. Install with: sudo apt-get install screen")

_DEF_LOG = "screen.log"

def _session_name(folder: Path) -> str:
    return f"mc_{safe_name(folder.name)}"

def _screen_ls() -> str:
    try:
        out = subprocess.check_output(["screen", "-ls"], stderr=subprocess.STDOUT).decode()
    except subprocess.CalledProcessError as e:
        out = e.output.decode() if e.output else ""
    return out

def is_running(folder: Path) -> bool:
    name = _session_name(folder)
    return name in _screen_ls()

def start_server_screen(folder: Path, java_path: str, jar_name: str, memory: str) -> bool:
    _ensure_screen()
    if is_running(folder):
        print(f"[WARN] {folder.name} already running in screen '{_session_name(folder)}'")
        return False
    mem = normalize_ram(memory)
    jar_path = folder / jar_name
    if not jar_path.exists():
        print(f"[ERR] JAR not found: {jar_path}")
        return False
    logfile = folder / _DEF_LOG
    cmd = (
        f"cd {shlex.quote(str(folder))} && "
        f"exec {shlex.quote(java_path)} -Xms{mem} -Xmx{mem} -jar {shlex.quote(jar_name)} nogui"
    )
    # Start detached screen with logging enabled
    try:
        subprocess.check_call([
            "screen", "-L", "-Logfile", str(logfile), "-dmS", _session_name(folder),
            "bash", "-lc", cmd
        ])
    except Exception as e:
        print(f"[ERR] Failed to start screen session: {e}")
        return False
    print(f"[OK] Started '{folder.name}' in screen session '{_session_name(folder)}' (log → {logfile})")
    print(f"Attach: screen -r {_session_name(folder)}  |  Detach: Ctrl+A, D")
    return True

def stop_server_screen(folder: Path):
    _ensure_screen()
    name = _session_name(folder)
    if not is_running(folder):
        print(f"[INFO] {folder.name} is not running.")
        return
    # Send 'stop' to the Minecraft console, then wait
    send_command(folder, "stop")
    for _ in range(20):  # wait up to ~20s
        if not is_running(folder):
            print(f"[OK] {folder.name} stopped.")
            return
        time.sleep(1)
    # Force-quit the screen session if still alive
    subprocess.call(["screen", "-S", name, "-X", "quit"])  # last resort
    if not is_running(folder):
        print(f"[WARN] Forced quit for {folder.name} (screen closed).")
    else:
        print(f"[ERR] Could not close session '{name}'.")

def send_command(folder: Path, command: str):
    """Send a command to the server console (adds ENTER)."""
    _ensure_screen()
    name = _session_name(folder)
    if not is_running(folder):
        print(f"[ERR] {folder.name} is not running.")
        return
    # screen 'stuff' needs a trailing newline (\r)
    subprocess.call(["screen", "-S", name, "-X", "stuff", command + "\r"])
    print(f"[OK] Sent: {command}")

def tail_console(folder: Path, lines: int = 100):
    """Show the last lines from the screen logfile (if present)."""
    log = folder / _DEF_LOG
    if not log.exists():
        print(f"[INFO] No screen logfile at {log} yet. Use 'Attach console' to see live output.")
        return
    try:
        data = log.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in data[-lines:]:
            print(line)
    except Exception as e:
        print(f"[ERR] Cannot read log: {e}")

def attach_console(folder: Path):
    """Attach to the live screen console (blocking until you detach with Ctrl+A, D)."""
    _ensure_screen()
    name = _session_name(folder)
    if not is_running(folder):
        print(f"[ERR] {folder.name} is not running.")
        return
    os.system(f"screen -r {name}")

# ================== SERVERS MENU (with Screen) ==================

import shlex

def servers_menu(cfg: dict):
    base = Path(cfg["servers_base"]).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)

    def list_servers() -> list[Path]:
        return sorted([p for p in base.iterdir() if p.is_dir()])

    def pick_server(prompt="Select server") -> Path | None:
        servers = list_servers()
        if not servers:
            print("[INFO] No servers found. Create/copy one under:", base)
            input("Press ENTER…"); return None
        print("\n-- Available Servers --")
        for i, sv in enumerate(servers, 1):
            running = " (RUNNING)" if is_running(sv) else ""
            print(f"{i}) {sv.name}{running}")
        s = input(f"{prompt} [1-{len(servers)}] (or ENTER to cancel): ").strip()
        if not s: return None
        if not s.isdigit() or not (1 <= int(s) <= len(servers)):
            print("[WARN] Invalid choice."); time.sleep(0.8); return None
        return servers[int(s)-1]

    def choose_jar(folder: Path) -> str | None:
        jars = sorted([p.name for p in folder.glob("*.jar")])
        if not jars:
            print("[ERR] No .jar found in", folder); return None
        if len(jars) == 1: return jars[0]
        print("\n-- JARs in", folder.name, "--")
        for i, j in enumerate(jars, 1): print(f"{i}) {j}")
        s = input(f"Choose JAR [1-{len(jars)}] (ENTER = 1): ").strip() or "1"
        if not s.isdigit() or not (1 <= int(s) <= len(jars)):
            print("[WARN] Invalid choice."); return None
        return jars[int(s)-1]

    # ===== Actions =====
    def act_build():
        try:
            manifest = fetch_json(MANIFEST_URL)
            versions = manifest.get("versions", [])
        except Exception as e:
            print(f"[ERR] Could not fetch Mojang manifest: {e}"); input("Press ENTER…"); return True
        sel = pick_version_interactive(versions)
        if not sel: return True
        try: url = get_server_jar_url(sel)
        except Exception as e:
            print(f"[ERR] {e}"); input("Press ENTER…"); return True
        default_name = sel["id"]
        name = input(f"Server name [{default_name}]: ").strip() or default_name
        alt = input(f"Save under (blank = {base}): ").strip()
        target_base = Path(alt).expanduser().resolve() if alt else base
        target_base.mkdir(parents=True, exist_ok=True)
        create_server_folder(target_base, name, sel["id"], url, cfg["java_path"], cfg["memory"])
        input("Press ENTER…"); return True

    def act_list():
        items = detect_servers(base)
        if not items: print("[INFO] No servers yet.")
        else:
            print("\n#  Name                        Version        RAM   Running  Path")
            print("-- --------------------------- -------------- ----- -------- ------------------------------")
            for i, s in enumerate(items, 1):
                running = "yes" if is_running(s["path"]) else "no"
                print(f"{i:>2} {s['name'][:27]:<27} {s['version'][:12]:<12} {s['memory'][:5]:<5} {running:<8} {s['path']}")
        input("Press ENTER…"); return True

    def act_status():
        sv = pick_server("Check status for");  
        if not sv: return True
        print(f"[OK] {sv.name} is {'RUNNING' if is_running(sv) else 'STOPPED'} (session: {_session_name(sv)})")
        input("Press ENTER…"); return True

    def act_start():
        sv = pick_server("Start which server");  
        if not sv: return True
        jar = choose_jar(sv);  
        if not jar: input("Press ENTER…"); return True
        ok = start_server_screen(sv, cfg.get("java_path","java"), jar, cfg.get("memory","4G"))
        if ok:
            print(f"[OK] Launched {sv.name} in screen. Attach with: screen -r {_session_name(sv)}")
        input("Press ENTER…"); return True

    def act_stop():
        sv = pick_server("Stop which server");  
        if not sv: return True
        stop_server_screen(sv)
        input("Press ENTER…"); return True

    def act_restart():
        sv = pick_server("Restart which server");  
        if not sv: return True
        jar = choose_jar(sv)
        if not jar: input("Press ENTER…"); return True
        stop_server_screen(sv); time.sleep(1.0)
        start_server_screen(sv, cfg.get("java_path","java"), jar, cfg.get("memory","4G"))
        print(f"[OK] Restarted {sv.name}")
        input("Press ENTER…"); return True

    def act_logs():
        sv = pick_server("Show recent console (tail)");  
        if not sv: return True
        try:
            n = int(input("How many lines? (default 100): ") or 100)
        except: n = 100
        tail_console(sv, n)
        input("Press ENTER…"); return True

    def act_attach():
        sv = pick_server("Attach to console of");  
        if not sv: return True
        print("[INFO] Attaching… Detach with Ctrl+A, D")
        attach_console(sv)
        return True

    def act_cmd():
        sv = pick_server("Send command to");  
        if not sv: return True
        cmd = input("Command (without leading /): ").strip()
        if not cmd: return True
        if not cmd.startswith("/"): cmd = "/" + cmd
        send_command(sv, cmd)
        input("Press ENTER…"); return True

    def act_backup():
        sv = pick_server("Backup which server");  
        if not sv: return True
        backup_server(sv)
        input("Press ENTER…"); return True

    def act_start_all():
        items = detect_servers(base)
        if not items: print("[INFO] No servers to start."); input("Press ENTER…"); return True
        for s in items:
            sv = s["path"]
            if is_running(sv):
                print(f"[SKIP] {sv.name} already running"); continue
            jar = choose_jar(sv)
            if not jar: print(f"[SKIP] {sv.name}: no jar"); continue
            start_server_screen(sv, cfg.get("java_path","java"), jar, cfg.get("memory","4G"))
        input("Press ENTER…"); return True

    def act_stop_all():
        items = detect_servers(base)
        any_running = False
        for s in items:
            sv = s["path"]
            if is_running(sv): any_running = True; stop_server_screen(sv)
        if not any_running: print("[INFO] No running servers.")
        input("Press ENTER…"); return True

    def act_change_base():
        newp = input("New servers base directory: ").strip()
        if newp:
            nonlocal base
            base = Path(newp).expanduser().resolve(); base.mkdir(parents=True, exist_ok=True)
            cfg["servers_base"] = str(base); save_cfg(cfg)
            print(f"[OK] Using {base}")
        input("Press ENTER…"); return True

    def act_back(): return False

    actions = {
        "1": act_build,
        "2": act_list,      "ls": act_list,
        "3": act_status,    "st": act_status,
        "4": act_start,     "start": act_start,
        "5": act_stop,      "stop": act_stop,
        "6": act_restart,   "re": act_restart,
        "7": act_logs,      "log": act_logs, "logs": act_logs,
        "8": act_attach,    "attach": act_attach,
        "9": act_cmd,       "cmd": act_cmd, "command": act_cmd,
        "10": act_backup,   "bk": act_backup, "backup": act_backup,
        "startall": act_start_all, "sa": act_start_all,
        "stopall": act_stop_all,   "so": act_stop_all,
        "base": act_change_base,
        "0": act_back, "b": act_back, "back": act_back,
    }

    while True:
        clear()
        print("=== MCSmaker · Servers (screen) ===")
        print(f"Base dir: {base}   |   Default RAM: {cfg['memory']}   |   Java: {cfg['java_path']}")
        print("1) Build full server (pick Mojang version)")
        print("2) List servers")
        print("3) Status")
        print("4) Start server (screen)")
        print("5) Stop server")
        print("6) Restart server")
        print("7) Show recent console (tail)")
        print("8) Attach console (screen -r)")
        print("9) Send command to server")
        print("10) Backup server (ZIP)")
        print("startall) Start ALL servers")
        print("stopall)  Stop ALL servers")
        print("base)     Change servers base directory")
        print("0) Back")
        choice = input("\nChoose: ").strip().lower()
        if not actions.get(choice, lambda: (print("[WARN] Unknown option."), time.sleep(0.6), True)[2])():
            break

# ================== SETTINGS & MAIN ==================

def settings_menu(cfg: dict):
    while True:
        clear()
        print("=== MCSmaker · Settings ===")
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

# ---- Main menu (dispatch) ----

def main_menu():
    check_and_install_dependencies()
    check_for_updates(auto_prompt=True)

    cfg = load_cfg()
    Path(cfg["jars_dir"]).expanduser().mkdir(parents=True, exist_ok=True)
    Path(cfg["servers_base"]).expanduser().mkdir(parents=True, exist_ok=True)

    def do_jars(): jars_menu(cfg); return True
    def do_servers(): servers_menu(cfg); return True
    def do_settings(): settings_menu(cfg); return True
    def do_update(): self_update(); input("Press ENTER…"); return True
    def do_exit(): print("[BYE]"); return False
    def unknown(): print("[WARN] Unknown option."); time.sleep(0.6); return True

    actions = {"1": do_jars, "2": do_servers, "3": do_settings, "u": do_update, "update": do_update, "0": do_exit, "q": do_exit, "exit": do_exit}

    while True:
        clear()
        print(rf"""

$$\      $$\  $$$$$$\   $$$$$$\  $$\      $$\  $$$$$$\  $$\   $$\ $$$$$$$$\ $$$$$$$\  
$$$\    $$$ |$$  __$$\ $$  __$$\ $$$\    $$$ |$$  __$$\ $$ | $$  |$$  _____|$$  __$$\ 
$$$$\  $$$$ |$$ /  \__|$$ /  \__|$$$$\  $$$$ |$$ /  $$ |$$ |$$  / $$ |      $$ |  $$ |
$$\$$\$$ $$ |\$$$$$$\  $$ |      $$\\$$\\$$ $$ |$$$$$$$$ |$$$$$  /  $$$$$\    $$$$$$$  |
$$ \$$$  $$ | \____$$\ $$ |      $$ \$$$  $$ |$$  __$$ |$$  $$<   $$  __|   $$  __$$< 
$$ |\$  /$$ |$$\   $$ |$$ |  $$\ $$ |\$  /$$ |$$ |  $$ |$$ |\$$\  $$ |      $$ |  $$ |
$$ | \_/ $$ |\$$$$$$  |\$$$$$$  |$$ | \_/ $$ |$$ |  $$ |$$ | \$$\ $$$$$$$$\ $$ |  $$ |
\__|     \__| \______/  \______/ \__|     \__|\__|  \__|\__|  \__|\________|\__|  \__|

                 MCSMAKER — Minecraft Automation Tool by Nico19422009 · v{CURRENT_VERSION}
""")
        print("1) JARs\n2) Servers\n3) Settings\nU) Update program\n0) Exit")
        choice = input("\nChoose: ").strip().lower()
        if not actions.get(choice, unknown)():
            break

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n[BYE]")
