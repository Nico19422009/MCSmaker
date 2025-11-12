#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, os, re, shutil, sys, time, urllib.request, urllib.error, subprocess
from pathlib import Path
import zipfile, shlex, hashlib, textwrap, importlib.util

# ================== CONFIG (persisted) ==================
CONFIG_FILE = "mcauto.json"
DEFAULTS = {
    "jars_dir": "minecraft_jars",
    "servers_base": "minecraft_servers",
    "java_path": "java",
    "memory": "4G",
    "default_mod_loader": "vanilla"   # vanilla | fabric | forge
}
MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

# ------- Self-update config ----------
APP_NAME = "MCSmaker"
CURRENT_VERSION = "1.6.0"

REMOTE_MANAGER_URL = "https://raw.githubusercontent.com/Nico19422009/MCSmaker/main/manager.py"
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/Nico19422009/MCSmaker/main/version.txt"

# ------------------------------------------------------------------
#  MOD-LOADER META URLs
# ------------------------------------------------------------------
FABRIC_META_URL = "https://meta.fabricmc.net/v2/versions/loader/{mc_version}"
FORGE_META_URL  = "https://files.minecraftforge.net/net/minecraftforge/forge/index_{mc_version}.html"

# ================== HTTP HELPERS ==================
def _http_get(url: str, timeout: int = 10, cache_bust: bool = True) -> bytes:
    if cache_bust:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}_ts={int(time.time())}"
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

# ================== SELF-UPDATE ==================
SEMVER_RE = re.compile(r"^v?\d+(?:\.\d+){0,2}$")

def _parse_version(s: str):
    if not s: return None
    s = s.lstrip("\ufeff").strip().replace("\r", "")
    if not SEMVER_RE.match(s):
        return None
    if s.startswith("v"):
        s = s[1:]
    parts = [int(p) for p in s.split('.')]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])

def self_update() -> bool:
    dest = Path(__file__).resolve()
    try:
        print("[*] Downloading latest manager.py …")
        data = _http_get(REMOTE_MANAGER_URL, timeout=20)
        if data[:1] == b"<":
            print("[ERR] Download looked like HTML (wrong URL?). Aborting.")
            return False

        tmp = dest.with_suffix(dest.suffix + ".new")
        with tmp.open("wb") as f:
            f.write(data)

        # ---- Verify version ----
        new_ver = None
        try:
            spec = importlib.util.spec_from_file_location("updated_manager", str(tmp))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            new_ver = getattr(mod, "CURRENT_VERSION", None)
            if not new_ver:
                raise ValueError("No CURRENT_VERSION")
            cv = _parse_version(CURRENT_VERSION)
            nv = _parse_version(new_ver)
            if nv is None or cv is None or nv <= cv:
                print(f"[INFO] New version {new_ver} not newer than {CURRENT_VERSION}. Skipping.")
                tmp.unlink(missing_ok=True)
                return False
            print(f"[OK] Verified new version: {new_ver} > {CURRENT_VERSION}")
        except Exception as e:
            print(f"[WARN] Could not verify version ({e}). Proceeding anyway...")

        tmp.replace(dest)
        print("[OK] manager.py updated! Restarting…")
        os.execv(sys.executable, [sys.executable] + sys.argv)
        return True
    except Exception as e:
        print(f"[ERR] Update failed: {e}")
    return False

def check_for_updates(auto_prompt: bool = True, debug: bool = False) -> None:
    try:
        raw = _http_get(REMOTE_VERSION_URL, timeout=6).decode("utf-8", errors="replace")
    except Exception:
        print("[i] Update check skipped.")
        return

    rv = _parse_version(raw)
    cv = _parse_version(CURRENT_VERSION)

    if rv is None or cv is None:
        print("[i] Update check skipped (invalid version).")
        return

    if rv > cv:
        print(f"[UPDATE] New version {raw.strip()} (current {CURRENT_VERSION})")
        if auto_prompt:
            ans = input("Update now? [Y/n] ").strip().lower()
            if ans in ("", "y", "yes"):
                if not self_update():
                    print("[ERR] Update failed.")
    else:
        print(f"[OK] Up to date (v{CURRENT_VERSION}).")

# ================== UTILITIES ==================
def clear(): os.system("cls" if os.name == "nt" else "clear")

cfg: dict = {}

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
    req = urllib.request.Request(url, headers={"User-Agent": "MCSmaker/1.6.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)

def download_with_resume(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    if dest.exists():
        print(f"[SKIP] {dest.name} already exists."); return True
    headers = {"User-Agent": "MCSmaker/1.6.0"}
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
        if e.code == 416:
            print("[INFO] Range not satisfiable — starting from scratch.")
            part.unlink(missing_ok=True)
            return download_with_resume(url, dest)
        print(f"[ERR] HTTP {e.code}: {e.reason}"); return False
    except urllib.error.URLError as e:
        print(f"[ERR] URL error: {e.reason}"); return False
    part.replace(dest)
    print(f"[OK] Saved to {dest}")
    return True

# ================== JAR CACHING ==================
def copy_jar_from_cache(jars_dir: Path, version_id: str, dest_folder: Path) -> Path | None:
    safe_ver = safe_name(version_id)
    candidates = [
        jars_dir / f"{safe_ver}.jar",
        jars_dir / f"server-{safe_ver}.jar",
    ]
    for src in candidates:
        if src.is_file():
            jar_name = f"server-{safe_ver}.jar"
            dest = dest_folder / jar_name
            print(f"[CACHE] Re-using {src.name} to {dest}")
            shutil.copy2(src, dest)
            return dest
    return None

# ================== RAM NORMALIZATION ==================
def normalize_ram(value: str, fallback: str = "4G") -> str:
    if not value: return fallback
    v = value.strip().upper().replace(" ", "")
    v = re.sub(r"B$", "", v)
    m = re.match(r"^(\d+)([KMG]?)$", v)
    if not m: return fallback
    num, unit = m.groups()
    if unit in ("K", "M", "G") and int(num) > 0:
        return f"{num}{unit}"
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

# ================== DEPENDENCY CHECK ==================
REQUIRED_PKGS = ["python3", "default-jdk", "screen"]

def _dpkg_installed(pkg: str) -> bool:
    res = subprocess.run(["dpkg", "-s", pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0

def check_and_install_dependencies():
    print("[*] Checking dependencies…")
    java_path = shutil.which("java")
    if not java_path:
        print("[WARN] No Java found. Installing default-jdk via apt…")
        try:
            subprocess.run(["sudo", "apt-get", "update", "-y"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "default-jdk"], check=True)
            print("[OK] Java installed.")
        except Exception as e:
            print(f"[ERR] Could not install Java: {e}")
            print("Please install manually: sudo apt-get install default-jdk")
    else:
        try: ver = subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT).decode().splitlines()[0]
        except Exception: ver = "(version unknown)"
        print(f"[OK] Found Java at {java_path} {ver}")

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
    show = versions[:30]
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

# ================== MOD-LOADER HELPERS ==================
def fetch_fabric_loader_json(mc_version: str) -> str | None:
    """Return direct server JAR URL for the latest *stable* Fabric loader."""
    url = f"https://meta.fabricmc.net/v2/versions/loader/{mc_version}"
    try:
        loaders = fetch_json(url)
    except Exception as e:
        print(f"[ERR] Fabric loader list: {e}")
        return None
    if not loaders:
        print(f"[ERR] No Fabric loaders for {mc_version}")
        return None
    stable = next((l for l in loaders if l.get("stable")), loaders[0])
    return f"https://meta.fabricmc.net/v2/versions/loader/{mc_version}/{stable['version']}/server/jar"

def fetch_forge_installer_url(mc_version: str) -> str | None:
    html = _http_get(FORGE_META_URL.format(mc_version=mc_version)).decode(errors="ignore")
    m = re.search(r'href="(https://files\.minecraftforge\.net/maven/net/minecraftforge/forge/'
                  r'(?P<ver>[^"/]+)/(?P<file>forge-[^"/]+-installer\.jar))"', html)
    return m.group(1) if m else None

def install_forge(installer_jar: Path, server_dir: Path, java_path: str) -> bool:
    cmd = [java_path, "-jar", str(installer_jar), "--installServer"]
    print(f"[*] Running Forge installer …")
    try:
        result = subprocess.run(cmd, cwd=str(server_dir), capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"[ERR] Forge installer failed:\n{result.stderr}")
            return False
        print("[OK] Forge installed.")
        return True
    except subprocess.TimeoutExpired:
        print("[ERR] Forge installer timed out.")
        return False
    except Exception as e:
        print(f"[ERR] Forge installer failed: {e}")
        return False

def get_mod_loader_jar(mc_version: str, loader: str, cache_dir: Path, server_dir: Path, java_path: str) -> Path | None:
    if loader == "vanilla":
        return None

    # ---------- FABRIC ----------
    if loader == "fabric":
        url = fetch_fabric_loader_json(mc_version)
        if not url:
            return None
        dest = cache_dir / f"fabric-server-{mc_version}.jar"
        if not dest.exists():
            print(f"[*] Downloading Fabric {mc_version} …")
            if not download_with_resume(url, dest):
                return None
        final = server_dir / dest.name
        shutil.copy2(dest, final)
        return final

    # ---------- FORGE ----------
    if loader == "forge":
        installer_url = fetch_forge_installer_url(mc_version)
        if not installer_url:
            return None
        installer_dest = cache_dir / f"forge-{mc_version}-installer.jar"
        if not installer_dest.exists():
            print(f"[*] Downloading Forge installer for {mc_version} …")
            if not download_with_resume(installer_url, installer_dest):
                return None
        if not install_forge(installer_dest, server_dir, java_path):
            return None
        candidates = list(server_dir.glob("forge-*.jar"))
        for c in candidates:
            if c.name.endswith(".jar"):
                print(f"[OK] Using Forge JAR: {c.name}")
                return c
        print("[ERR] Forge installed but no JAR found.")
        return None

    return None

# ================== LAUNCH SCRIPTS ==================
def write_start_sh(folder: Path, jar_name: str, java_path: str = "java",
                   memory: str = "4G", loader: str = "vanilla"):
    mem = normalize_ram(memory, "4G")
    extra_args = "-Dfabric.server=true" if loader == "fabric" else ""
    sh = textwrap.dedent(f"""\
        #!/usr/bin/env bash
        cd "$(dirname "$0")"
        exec {java_path} -Xms{mem} -Xmx{mem} {extra_args} -jar "{jar_name}" nogui
        """)
    write_text(folder / "start.sh", sh, 0o755)

    bat = textwrap.dedent(f"""\
        @echo off
        cd /d %~dp0
        {java_path} -Xms{mem} -Xmx{mem} {extra_args} -jar "{jar_name}" nogui
        pause
        """)
    write_text(folder / "start.bat", bat)

    readme = textwrap.dedent(f"""\
        # {loader.upper()} SERVER SETUP
        JAR: {jar_name}
        RAM: {mem}
        Mods: Drop .jar files into `./mods/` (auto-created).
        Start: `./start.sh` (Linux) or `start.bat` (Windows)
        """)
    write_text(folder / "README.txt", readme)

# ================== SERVER CREATE (generic) ==================
def create_server_folder(base_dir: Path, server_name: str, version_id: str,
                         jar_url: str | None, java_path: str, memory: str,
                         loader: str = "vanilla") -> bool:
    folder = base_dir / safe_name(server_name)
    folder.mkdir(parents=True, exist_ok=True)

    jars_dir = Path(cfg["jars_dir"]).expanduser().resolve()
    mods_dir = folder / "mods"
    mods_dir.mkdir(exist_ok=True)

    # ---- 1. Get the executable JAR ----
    jar_path = None
    if loader == "vanilla":
        jar_name = f"server-{safe_name(version_id)}.jar"
        jar_path = folder / jar_name
        cached = copy_jar_from_cache(jars_dir, version_id, folder)
        if not cached:
            print(f"[*] Downloading vanilla {version_id} …")
            tmp = jars_dir / f"{jar_name}.part"
            if not download_with_resume(jar_url, tmp):
                return False
            final_cache = jars_dir / jar_name
            tmp.replace(final_cache)
            shutil.copy2(final_cache, jar_path)
        else:
            jar_path = cached
        jar_name = jar_path.name
    else:
        final_jar = get_mod_loader_jar(version_id, loader, jars_dir, folder, java_path)
        if not final_jar:
            return False
        jar_name = final_jar.name
        jar_path = final_jar

    # ---- 2. Common files ----
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
    write_start_sh(folder, jar_name, java_path, mem_norm, loader=loader)

    # ---- 3. Persist meta ----
    meta = folder / "mcsmeta.json"
    meta_data = {
        "mc_version": version_id,
        "loader": loader,
        "jar": jar_name,
        "memory": mem_norm,
    }
    write_text(meta, json.dumps(meta_data, indent=2))

    print(f"[DONE] {loader.upper()} server '{server_name}' ready at: {folder}")
    print("   Mods → ./mods/   |   Start → ./start.sh   (or start.bat)")
    return True

# ================== SERVER META READER ==================
def read_server_meta(folder: Path) -> dict:
    meta_path = folder / "mcsmeta.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Fallback from start.sh
    start = folder / "start.sh"
    if start.exists():
        txt = start.read_text(encoding="utf-8", errors="ignore")
        jar_match = re.search(r'-jar\s+"?([^"\n]+)"?', txt)
        mem_match = re.search(r"-Xmx(\S+)", txt)
        return {
            "mc_version": "?",
            "loader": "vanilla",
            "jar": jar_match.group(1) if jar_match else "?",
            "memory": mem_match.group(1) if mem_match else "?"
        }
    return {}

# ================== SERVER DISCOVER ==================
def detect_servers(base_dir: Path) -> list[dict]:
    base_dir.mkdir(parents=True, exist_ok=True)
    servers = []
    for p in sorted(base_dir.iterdir()):
        if not p.is_dir() or not (p / "start.sh").exists(): continue
        start_txt = p.joinpath("start.sh").read_text(encoding="utf-8", errors="ignore")
        mem = re.search(r"-Xmx(\S+)", start_txt)
        jar = re.search(r'-jar\s+"?([^"\n]+)"?', start_txt)
        ver = "?"
        if jar:
            jname = Path(jar.group(1)).name
            mver = re.search(r"server-([A-Za-z0-9._-]+)\.jar", jname)
            if mver: ver = mver.group(1)
        meta = read_server_meta(p)
        servers.append({
            "name": p.name,
            "path": p,
            "memory": mem.group(1) if mem else "?",
            "version": ver,
            "loader": meta.get("loader", "vanilla"),
            "jar": meta.get("jar", "?")
        })
    return servers

# ================== SCREEN MANAGEMENT ==================
_DEF_LOG = "screen.log"

def _ensure_screen():
    if not shutil.which("screen"):
        raise RuntimeError("GNU screen is not installed. Install with: sudo apt-get install screen")

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
    try:
        subprocess.check_call([
            "screen", "-L", "-Logfile", str(logfile), "-dmS", _session_name(folder),
            "bash", "-lc", cmd
        ])
    except Exception as e:
        print(f"[ERR] Failed to start screen session: {e}")
        return False
    print(f"[OK] Started '{folder.name}' in screen '{_session_name(folder)}' (log → {logfile})")
    print(f"Attach: screen -r {_session_name(folder)}  |  Detach: Ctrl+A, D")
    return True

def stop_server_screen(folder: Path):
    _ensure_screen()
    name = _session_name(folder)
    if not is_running(folder):
        print(f"[INFO] {folder.name} is not running.")
        return
    send_command(folder, "stop")
    for _ in range(20):
        if not is_running(folder):
            print(f"[OK] {folder.name} stopped.")
            return
        time.sleep(1)
    subprocess.call(["screen", "-S", name, "-X", "quit"])
    if not is_running(folder):
        print(f"[WARN] Forced quit for {folder.name}.")
    else:
        print(f"[ERR] Could not close '{name}'.")

def send_command(folder: Path, command: str):
    _ensure_screen()
    name = _session_name(folder)
    if not is_running(folder):
        print(f"[ERR] {folder.name} is not running.")
        return
    subprocess.call(["screen", "-S", name, "-X", "stuff", command + "\r"])
    print(f"[OK] Sent: {command}")

def tail_console(folder: Path, lines: int = 100):
    log = folder / _DEF_LOG
    if not log.exists():
        print(f"[INFO] No log at {log}. Use 'Attach' for live.")
        return
    try:
        data = log.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in data[-lines:]:
            print(line)
    except Exception as e:
        print(f"[ERR] Log read failed: {e}")

def attach_console(folder: Path):
    _ensure_screen()
    name = _session_name(folder)
    if not is_running(folder):
        print(f"[ERR] {folder.name} not running.")
        return
    os.system(f"screen -r {name}")

# ================== BACKUP ==================
def backup_server(folder: Path, dest_dir: Path | None = None, include_logs: bool = False) -> Path | None:
    try:
        folder = Path(folder).resolve()
        if not folder.is_dir():
            print(f"[ERR] Folder not found: {folder}")
            return None

        running = is_running(folder)
        if running:
            print("[*] Running server — save-all before backup…")
            send_command(folder, "save-off")
            send_command(folder, "save-all flush")
            time.sleep(3)

        ts = time.strftime("%Y%m%d-%H%M%S")
        dest_dir = Path(dest_dir).resolve() if dest_dir else (folder.parent / "backups")
        dest_dir.mkdir(parents=True, exist_ok=True)
        out_zip = dest_dir / f"{folder.name}_{ts}.zip"

        print(f"[*] Backing up to {out_zip}")
        with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(folder):
                root_p = Path(root)
                for fname in files:
                    if not include_logs and fname == _DEF_LOG: continue
                    src = root_p / fname
                    arcname = src.relative_to(folder)
                    zf.write(src, arcname=str(arcname))

        if running:
            send_command(folder, "save-on")

        print(f"[OK] Backup done: {out_zip}")
        return out_zip
    except Exception as e:
        print(f"[ERR] Backup failed: {e}")
        return None

# ================== PICK SERVER HELPER ==================
def servers_menu_pick_server(base: Path, prompt: str = "Select server") -> Path | None:
    servers = sorted([p for p in base.iterdir() if p.is_dir() and (p / "start.sh").exists()])
    if not servers:
        print(f"[INFO] No servers in {base}. Create one!")
        input("Press ENTER…")
        return None
    print("\n-- Servers --")
    for i, sv in enumerate(servers, 1):
        running = " (RUNNING)" if is_running(sv) else ""
        print(f"{i:>2}. {sv.name}{running}")
    s = input(f"{prompt} [1-{len(servers)}] (ENTER=cancel): ").strip()
    if not s: return None
    try:
        idx = int(s) - 1
        if 0 <= idx < len(servers): return servers[idx]
    except ValueError:
        pass
    print("[WARN] Bad choice.")
    time.sleep(0.8)
    return None

# ================== MODDED SERVER BUILDER MENU ==================
def build_modded_server_menu(cfg: dict):
    """
    Unified menu for **Vanilla / Fabric / Forge** server creation.
    Re-uses all the heavy-lifting functions defined above.
    """
    base = Path(cfg["servers_base"]).expanduser().resolve()
    jars_dir = Path(cfg["jars_dir"]).expanduser().resolve()
    java_path = cfg.get("java_path", "java")
    memory = cfg.get("memory", "4G")

    while True:
        clear()
        print("=== MCSmaker · Build Modded Server ===")
        print("1) Vanilla")
        print("2) Fabric")
        print("3) Forge")
        print("0) Back")
        choice = input("\nLoader [1-3]: ").strip()

        if choice not in ("1", "2", "3"):
            if choice == "0":
                break
            print("[WARN] Invalid choice.")
            time.sleep(0.7)
            continue

        loader_map = {"1": "vanilla", "2": "fabric", "3": "forge"}
        loader = loader_map[choice]

        # ----- Minecraft version -----
        mc_version = input("\nMinecraft version (e.g. 1.21.1): ").strip()
        if not mc_version:
            print("[ERR] Version required.")
            input("ENTER…")
            continue

        # ----- Vanilla needs the official manifest -----
        jar_url = None
        if loader == "vanilla":
            try:
                manifest = fetch_json(MANIFEST_URL)
                versions = manifest.get("versions", [])
                ver_obj = next((v for v in versions if v["id"] == mc_version), None)
                if not ver_obj:
                    print(f"[ERR] Version {mc_version} not found in manifest.")
                    input("ENTER…")
                    continue
                jar_url = get_server_jar_url(ver_obj)
            except Exception as e:
                print(f"[ERR] Could not fetch vanilla URL: {e}")
                input("ENTER…")
                continue

        # ----- Server name -----
        default_name = f"{loader}-{mc_version}"
        server_name = input(f"Server name [{default_name}]: ").strip() or default_name

        # ----- Create the server -----
        success = create_server_folder(
            base_dir=base,
            server_name=server_name,
            version_id=mc_version,
            jar_url=jar_url,
            java_path=java_path,
            memory=memory,
            loader=loader
        )
        if success:
            print("\nServer is ready! Add mods to ./mods/ and run ./start.sh")
        input("\nPress ENTER to continue…")

# ================== MODS MENU (unchanged) ==================
def mods_menu(cfg: dict):
    base = Path(cfg["servers_base"]).expanduser().resolve()
    while True:
        clear()
        print("=== MCSmaker · Mods & Modded Servers ===")
        print("1) List mods in server")
        print("2) Add mod (URL download)")
        print("3) Delete mod")
        print("4) Build modded server (Fabric/Forge/Vanilla)   <-- NEW")
        print("0) Back")
        c = input("\nChoose: ").strip()

        if c == "1":
            sv = servers_menu_pick_server(base, "Pick server")
            if not sv: continue
            mods = list((sv / "mods").glob("*.jar"))
            if not mods:
                print("[INFO] No mods in ./mods/")
            else:
                print("\nMods:")
                for m in sorted(mods, key=lambda x: x.name):
                    print(f"  - {m.name} ({m.stat().st_size / 1024:.1f} KB)")
            input("\nENTER…")

        elif c == "2":
            sv = servers_menu_pick_server(base, "Pick server")
            if not sv: continue
            url = input("Mod JAR URL (e.g. from CurseForge): ").strip()
            if not url: continue
            dest = (sv / "mods") / Path(url).with_suffix('.jar').name
            if download_with_resume(url, dest):
                print(f"[OK] Added {dest.name} to {sv.name}/mods/")
            input("ENTER…")

        elif c == "3":
            sv = servers_menu_pick_server(base, "Pick server")
            if not sv: continue
            mods = list((sv / "mods").glob("*.jar"))
            if not mods:
                print("[INFO] No mods to delete."); input("ENTER…"); continue
            print("\nDelete which?")
            for i, m in enumerate(mods, 1):
                print(f"{i:>2}. {m.name}")
            idx_str = input("Number (ENTER=cancel): ").strip()
            if not idx_str.isdigit(): continue
            idx = int(idx_str) - 1
            if 0 <= idx < len(mods):
                mods[idx].unlink()
                print(f"[OK] Deleted {mods[idx].name}")
            input("ENTER…")

        elif c == "4":
            build_modded_server_menu(cfg)   # <-- NEW unified builder

        elif c == "0":
            break
        else:
            print("[WARN] Unknown option.")
            time.sleep(0.6)

# ================== SERVERS MENU (unchanged) ==================
def servers_menu(cfg: dict):
    base = Path(cfg["servers_base"]).expanduser().resolve()
    while True:
        clear()
        print("=== MCSmaker · Servers ===")
        print("1) List servers")
        print("2) Start server")
        print("3) Stop server")
        print("4) Attach to server console")
        print("5) Tail server log")
        print("6) Backup server")
        print("0) Back")
        c = input("\nChoose: ").strip()
        if c == "1":
            servers = detect_servers(base)
            if not servers:
                print("[INFO] No servers found.")
            else:
                print("\nServers:")
                for i, sv in enumerate(servers, 1):
                    running = " (RUNNING)" if is_running(sv["path"]) else ""
                    print(f"{i:>2}. {sv['name']} [{sv['version']}] {sv['loader']} {sv['memory']}{running}")
            input("\nENTER…")
        elif c == "2":
            sv = servers_menu_pick_server(base, "Start which server")
            if not sv: continue
            meta = read_server_meta(sv)
            start_server_screen(sv, cfg.get("java_path", "java"), meta.get("jar", "?"), meta.get("memory", "4G"))
            input("ENTER…")
        elif c == "3":
            sv = servers_menu_pick_server(base, "Stop which server")
            if not sv: continue
            stop_server_screen(sv)
            input("ENTER…")
        elif c == "4":
            sv = servers_menu_pick_server(base, "Attach to which server")
            if not sv: continue
            attach_console(sv)
        elif c == "5":
            sv = servers_menu_pick_server(base, "Tail log for which server")
            if not sv: continue
            tail_console(sv)
            input("ENTER…")
        elif c == "6":
            sv = servers_menu_pick_server(base, "Backup which server")
            if not sv: continue
            backup_server(sv)
            input("ENTER…")
        elif c == "0":
            break
        else:
            print("[WARN] Unknown option.")
            time.sleep(0.6)

# ================== SETTINGS ==================
def settings_menu(cfg: dict):
    while True:
        clear()
        print("=== MCSmaker · Settings ===")
        print(f"1) JARs dir: {cfg['jars_dir']}")
        print(f"2) Servers dir: {cfg['servers_base']}")
        print(f"3) Java: {cfg['java_path']}")
        print(f"4) RAM: {cfg['memory']}")
        print(f"5) Default loader: {cfg['default_mod_loader']}")
        print("0) Back")
        c = input("\nChange #: ").strip()
        if c == "1":
            p = input("JARs dir: ").strip()
            if p:
                cfg["jars_dir"] = p
                save_cfg(cfg)
        elif c == "2":
            p = input("Servers dir: ").strip()
            if p:
                cfg["servers_base"] = p
                save_cfg(cfg)
        elif c == "3":
            p = input("Java path: ").strip()
            if p:
                cfg["java_path"] = p
                save_cfg(cfg)
        elif c == "4":
            p = input("RAM (4G): ").strip()
            if p: cfg["memory"] = normalize_ram(p, cfg["memory"]); save_cfg(cfg)
        elif c == "5":
            print("1) Vanilla 2) Fabric 3) Forge")
            ch = input("Default [1]: ").strip() or "1"
            loader_map = {"1": "vanilla", "2": "fabric", "3": "forge"}
            cfg["default_mod_loader"] = loader_map.get(ch, "vanilla")
            save_cfg(cfg)
        elif c == "0":
            break
        else:
            print("[WARN] ?"); time.sleep(0.6)

# ================== MAIN ==================
def main_menu():
    check_and_install_dependencies()
    check_for_updates(auto_prompt=True)

    global cfg
    cfg = load_cfg()
    Path(cfg["jars_dir"]).expanduser().mkdir(parents=True, exist_ok=True)
    Path(cfg["servers_base"]).expanduser().mkdir(parents=True, exist_ok=True)

    def do_jars():
        print("[INFO] jars_menu is not yet implemented.")
        input("Press ENTER…")
        return True

    def do_servers(): servers_menu(cfg); return True
    def do_mods(): mods_menu(cfg); return True
    def do_settings(): settings_menu(cfg); return True
    def do_update():
        if self_update(): sys.exit(0)
        input("ENTER…"); return True
    def do_exit(): print("[BYE]"); return False
    def unknown(): print("[WARN] ?"); time.sleep(0.6); return True

    actions = {
        "1": do_jars, "jars": do_jars,
        "2": do_servers, "servers": do_servers,
        "3": do_mods, "mods": do_mods,
        "4": do_settings, "set": do_settings,
        "u": do_update, "update": do_update,
        "0": do_exit, "q": do_exit, "exit": do_exit
    }

    while True:
        clear()
        print(rf"""
███╗   ███╗ ██████╗███████╗    ███╗   ███╗ █████╗ ██╗  ██╗███████╗██████╗ 
████╗ ████║██╔════╝██╔════╝    ████╗ ████║██╔══██╗██║ ██╔╝██╔════╝██╔══██╗
██╔████╔██║██║     ███████╗    ██╔████╔██║███████║█████╔╝ █████╗  ██████╔╝
██║╚██╔╝██║██║     ╚════██║    ██║╚██╔╝██║██╔══██║██╔═██╗ ██╔══╝  ██╔══██╗
██║ ╚═╝ ██║██████╗███████║    ██║ ╚═╝ ██║██║  ██║██║  ██╗███████╗██║  ██║
╚═╝     ╚═╝ ╚═════╝╚══════╝    ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝

        MCSmaker v{CURRENT_VERSION} — Modded Minecraft Server Manager
        """)
        print("1/jars) Manage JARs")
        print("2/servers) Servers (build/start/stop)")
        print("3/mods) Mods (add/list/delete) + **Build Fabric/Forge**")
        print("4/set) Settings")
        print("u/update) Update")
        print("0/q) Exit")
        choice = input("\n> ").strip().lower()
        act = actions.get(choice, unknown)
        if not act():
            break

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n[BYE]")
    except Exception as e:
        print(f"[FATAL] {e}")
        input("ENTER to exit...")