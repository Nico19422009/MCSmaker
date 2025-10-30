#!/usr/bin/env python3
import json, os, re, shutil, sys, time, urllib.request, urllib.error, subprocess
from pathlib import Path
import zipfile
import shlex
import hashlib          # <-- for Forge SHA-1 (optional)
import textwrap        # <-- pretty-print start.sh / README

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
CURRENT_VERSION = "1.5.5"  # Keep in sync with version.txt in the repo

# RAW GitHub URLs
REMOTE_MANAGER_URL = "https://raw.githubusercontent.com/Nico19422009/MCSmaker/main/manager.py"
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/Nico19422009/MCSmaker/main/version.txt"

# ------ Update helpers ---------
SEMVER_RE = re.compile(r"^v?\d+(?:\.\d+){0,2}$")

# ------------------------------------------------------------------
#  MOD-LOADER META URLs
# ------------------------------------------------------------------
FABRIC_META_URL = "https://meta.fabricmc.net/v2/versions/loader/{mc_version}/{loader_version}/server/json"
FORGE_META_URL  = "https://files.minecraftforge.net/maven/net/minecraftforge/forge/index_{mc_version}.html"
FORGE_PROMO_URL = "https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_version}-{forge_version}/forge-{mc_version}-{forge_version}-installer.jar"

FABRIC_LOADER_LATEST = "0.16.5"
FORGE_PROMO_LATEST   = "recommended"

# ------------------------------------------------------------------
#  HTTP HELPERS
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
#  SELF-UPDATE
# ------------------------------------------------------------------
def _parse_version(s: str):
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

        # ---- Verify version before replacing ----
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("updated_manager", str(tmp))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            new_ver = getattr(mod, "CURRENT_VERSION", None)
            if not new_ver or _parse_version(new_ver) <= _parse_version(CURRENT_VERSION):
                print(f"[ERR] Downloaded file has old or same version ({new_ver}). Skipping update.")
                tmp.unlink(missing_ok=True)
                return False
            print(f"[OK] Verified new version: {new_ver}")
        except Exception as e:
            print(f"[WARN] Could not verify new version: {e}. Proceeding anyway...")

        # ---- Replace the file ----
        tmp.replace(dest)
        print("[OK] manager.py updated! Restarting…")

        # ---- Restart with original args ----
        os.execv(sys.executable, [sys.executable] + sys.argv)
        return True  # never reached

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
    """
    Returns the direct server JAR URL for the latest stable Fabric loader.
    No longer relies on 'launcherMeta' which is deprecated.
    """
    # Step 1: Get list of loader versions
    loader_list_url = f"https://meta.fabricmc.net/v2/versions/loader/{mc_version}"
    try:
        loaders = fetch_json(loader_list_url)
    except Exception as e:
        print(f"[ERR] Could not fetch Fabric loader list: {e}")
        return None

    if not loaders:
        print(f"[ERR] No Fabric loaders found for Minecraft {mc_version}")
        return None

    # Step 2: Pick the latest stable loader
    stable_loader = None
    for item in loaders:
        if item.get("stable", False):
            stable_loader = item
            break
    if not stable_loader:
        stable_loader = loaders[0]  # fallback to newest

    loader_version = stable_loader["version"]

    # Step 3: Get server JAR URL
    server_url = f"https://meta.fabricmc.net/v2/versions/loader/{mc_version}/{loader_version}/server/jar"
    return server_url

def fetch_forge_installer_url(mc_version: str) -> str | None:
    html = _http_get(FORGE_META_URL.format(mc_version=mc_version)).decode(errors="ignore")
    m = re.search(r'href="(https://files\.minecraftforge\.net/maven/net/minecraftforge/forge/'
                  r'(?P<ver>[^"/]+)/(?P<file>forge-[^"/]+-installer\.jar))"', html)
    if not m:
        return None
    return m.group(1)

def install_forge(installer_jar: Path, server_dir: Path) -> bool:
    cmd = [cfg["java_path"], "-jar", str(installer_jar), "--installServer"]
    print(f"[*] Running Forge installer …")
    try:
        subprocess.check_call(cmd, cwd=str(server_dir))
        print("[OK] Forge installed.")
        return True
    except Exception as e:
        print(f"[ERR] Forge installer failed: {e}")
        return False

def get_mod_loader_jar(mc_version: str, loader: str, cache_dir: Path, server_dir: Path) -> Path | None:
    if loader == "vanilla":
        return None

    if loader == "fabric":
        meta = fetch_fabric_loader_json(mc_version)
        if not meta:
            print("[ERR] Could not fetch Fabric meta.")
            return None
        url = meta["launcherMeta"]["launch"]["server"]["url"]
        dest = cache_dir / f"fabric-server-{mc_version}-{FABRIC_LOADER_LATEST}.jar"
        if not dest.exists():
            if not download_with_resume(url, dest):
                return None
        final = server_dir / dest.name
        shutil.copy2(dest, final)
        return final

    if loader == "forge":
        installer_url = fetch_forge_installer_url(mc_version)
        if not installer_url:
            print("[ERR] Could not locate Forge installer.")
            return None
        installer_dest = cache_dir / f"forge-{mc_version}-installer.jar"
        if not installer_dest.exists():
            if not download_with_resume(installer_url, installer_dest):
                return None
        if not install_forge(installer_dest, server_dir):
            return None
        candidates = list(server_dir.glob("forge-*.jar")) + list(server_dir.glob("*.jar"))
        for c in candidates:
            if c.name.startswith("forge-") or c.name.endswith("-server.jar"):
                return c
        print("[ERR] Forge installer finished but no server JAR found.")
        return None

    return None

# ================== LAUNCH SCRIPTS ==================
def write_start_sh(folder: Path, jar_name: str, java_path: str = "java",
                   memory: str = "4G", loader: str = "vanilla"):
    mem = normalize_ram(memory, "4G")
    extra_args = ""
    if loader == "fabric":
        extra_args = "-Dfabric.server=true"

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
        # {loader.upper()} SERVER
        JAR: {jar_name}
        RAM: {mem}
        Put your mods into the folder `mods/` (create it if missing).
        """)
    write_text(folder / "README.txt", readme)

# ================== SERVER CREATE (with loader) ==================
def create_server_folder(base_dir: Path, server_name: str, version_id: str,
                         jar_url: str | None, java_path: str, memory: str,
                         loader: str = "vanilla") -> bool:
    folder = base_dir / safe_name(server_name)
    folder.mkdir(parents=True, exist_ok=True)

    jars_dir = Path(cfg["jars_dir"]).expanduser().resolve()
    mods_dir = folder / "mods"
    mods_dir.mkdir(exist_ok=True)

    # ---- 1. Get the executable JAR ----
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
    else:
        final_jar = get_mod_loader_jar(version_id, loader, jars_dir, folder)
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

    print(f"[DONE] Server ready at: {folder}")
    print("   Mods to ./mods/   |   Start to ./start.sh   (or start.bat)")
    return True

# ================== SERVER META READER ==================
def read_server_meta(folder: Path) -> dict:
    meta_path = folder / "mcsmeta.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    # fallback – guess from start.sh
    start = folder / "start.sh"
    if start.exists():
        txt = start.read_text(encoding="utf-8")
        jar = re.search(r'-jar\s+"?([^"\n]+)"?', txt)
        mem = re.search(r"-Xmx(\S+)", txt)
        return {
            "mc_version": "?",
            "loader": "vanilla",
            "jar": jar.group(1) if jar else "?",
            "memory": mem.group(1) if mem else "?"
        }
    return {}

# ================== SERVER DISCOVER ==================
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
    print(f"[OK] Started '{folder.name}' in screen session '{_session_name(folder)}' (log to {logfile})")
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
        print(f"[WARN] Forced quit for {folder.name} (screen closed).")
    else:
        print(f"[ERR] Could not close session '{name}'.")

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
        print(f"[INFO] No screen logfile at {log} yet. Use 'Attach console' to see live output.")
        return
    try:
        data = log.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in data[-lines:]:
            print(line)
    except Exception as e:
        print(f"[ERR] Cannot read log: {e}")

def attach_console(folder: Path):
    _ensure_screen()
    name = _session_name(folder)
    if not is_running(folder):
        print(f"[ERR] {folder.name} is not running.")
        return
    os.system(f"screen -r {name}")

# ================== BACKUP ==================
def backup_server(folder: Path, dest_dir: Path | None = None, include_logs: bool = False) -> Path | None:
    try:
        folder = Path(folder).resolve()
        if not folder.exists() or not folder.is_dir():
            print(f"[ERR] Folder not found: {folder}")
            return None

        running = is_running(folder)
        if running:
            print("[*] Server is running — issuing save-all before backup …")
            try:
                send_command(folder, "save-off")
                send_command(folder, "save-all flush")
                time.sleep(3)
            except Exception as e:
                print(f"[WARN] Couldn't send save commands: {e}")

        ts = time.strftime("%Y%m%d-%H%M%S")
        dest_dir = Path(dest_dir).resolve() if dest_dir else (folder.parent / "backups")
        dest_dir.mkdir(parents=True, exist_ok=True)
        out_zip = dest_dir / f"{folder.name}_{ts}.zip"

        print(f"[*] Creating backup to {out_zip}")
        with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            base = folder
            for root, dirs, files in os.walk(base):
                root_p = Path(root)
                for fname in files:
                    if not include_logs and fname == _DEF_LOG:
                        continue
                    src = root_p / fname
                    if src == out_zip:
                        continue
                    arcname = src.relative_to(base)
                    try:
                        zf.write(src, arcname=str(arcname))
                    except Exception as e:
                        print(f"[WARN] Could not add {src}: {e}")

        if running:
            try:
                send_command(folder, "save-on")
            except Exception:
                pass

        print(f"[OK] Backup completed to {out_zip}")
        return out_zip
    except Exception as e:
        print(f"[ERR] Backup failed: {e}")
        return None

# ================== HELPER: pick server ==================
def servers_menu_pick_server(base: Path, prompt: str = "Select server") -> Path | None:
    servers = sorted([p for p in base.iterdir() if p.is_dir() and (p / "start.sh").exists()])
    if not servers:
        print("[INFO] No servers found.")
        input("Press ENTER…")
        return None
    print("\n-- Available Servers --")
    for i, sv in enumerate(servers, 1):
        running = " (RUNNING)" if is_running(sv) else ""
        print(f"{i}) {sv.name}{running}")
    s = input(f"{prompt} [1-{len(servers)}] (ENTER = cancel): ").strip()
    if not s: return None
    if not s.isdigit() or not (1 <= int(s) <= len(servers)):
        print("[WARN] Invalid choice.")
        time.sleep(0.8)
        return None
    return servers[int(s)-1]

# ================== MODS MENU ==================
def mods_menu(cfg: dict):
    base = Path(cfg["servers_base"]).expanduser().resolve()

    def pick_server() -> Path | None:
        return servers_menu_pick_server(base, prompt="This Function is currently under develeopment." )

    while True:
        clear()
        print("Currently this function is under development. Sorry :(\n")
        print("0) Back")
        c = input("\nChoose: ").strip()

        if c == "1":
            sv = pick_server()
            if not sv: continue
            mods = sorted((sv / "mods").glob("*.jar"))
            if not mods:
                print("[INFO] No mods installed.")
            else:
                print("\nMods:")
                for m in mods:
                    print(f"  - {m.name}")
            input("\nPress ENTER…")

        elif c == "2":
            sv = pick_server()
            if not sv: continue
            url = input("Mod JAR URL: ").strip()
            if not url: continue
            dest = (sv / "mods") / Path(url).name
            download_with_resume(url, dest)
            input("Press ENTER…")

        elif c == "3":
            sv = pick_server()
            if not sv: continue
            mods = list((sv / "mods").glob("*.jar"))
            if not mods:
                print("[INFO] No mods to delete.")
                input("Press ENTER…"); continue
            print("\nSelect mod to delete:")
            for i, m in enumerate(mods, 1):
                print(f"{i}) {m.name}")
            idx = input("Number (or ENTER to cancel): ").strip()
            if not idx.isdigit(): continue
            idx = int(idx) - 1
            if 0 <= idx < len(mods):
                mods[idx].unlink()
                print(f"[OK] Deleted {mods[idx].name}")
            input("Press ENTER…")

        elif c == "4":
            mc = input("Minecraft version for Fabric (e.g. 1.21.1): ").strip()
            if not mc: continue
            meta = fetch_fabric_loader_json(mc)
            if not meta:
                print("[ERR] Could not fetch Fabric meta.")
                input("Press ENTER…"); continue
            url = meta["launcherMeta"]["launch"]["server"]["url"]
            dest = Path(cfg["jars_dir"]).expanduser().resolve() / f"fabric-server-{mc}-{FABRIC_LOADER_LATEST}.jar"
            download_with_resume(url, dest)
            input("Press ENTER…")

        elif c == "5":
            mc = input("Minecraft version for Forge (e.g. 1.21.1): ").strip()
            if not mc: continue
            url = fetch_forge_installer_url(mc)
            if not url:
                print("[ERR] Could not locate Forge installer.")
                input("Press ENTER…"); continue
            dest = Path(cfg["jars_dir"]).expanduser().resolve() / f"forge-{mc}-installer.jar"
            download_with_resume(url, dest)
            input("Press ENTER…")

        elif c == "0":
            break

# ================== SERVERS MENU ==================
def servers_menu(cfg: dict):
    base = Path(cfg["servers_base"]).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)

    def pick_server(prompt="Select server") -> Path | None:
        return servers_menu_pick_server(base, prompt)

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

    def act_build():
        try:
            manifest = fetch_json(MANIFEST_URL)
            versions = manifest.get("versions", [])
        except Exception as e:
            print(f"[ERR] Could not fetch Mojang manifest: {e}"); input("Press ENTER…"); return True
        sel = pick_version_interactive(versions)
        if not sel: return True

        print("\nSelect mod loader:")
        print("1) Vanilla")
        print("2) Fabric")
        print("3) Forge")
        ld = input("Choice [1-3] (default = 1): ").strip() or "1"
        loader = {"1":"vanilla","2":"fabric","3":"forge"}.get(ld, "vanilla")

        jar_url = None
        if loader == "vanilla":
            try:
                jar_url = get_server_jar_url(sel)
            except Exception as e:
                print(f"[ERR] {e}")
                input("Press ENTER…")
                return True

        default_name = sel["id"]
        name = input(f"Server name [{default_name}]: ").strip() or default_name
        alt = input(f"Save under (blank = {base}): ").strip()
        target_base = Path(alt).expanduser().resolve() if alt else base
        target_base.mkdir(parents=True, exist_ok=True)

        ok = create_server_folder(
            target_base, name, sel["id"], jar_url,
            cfg["java_path"], cfg["memory"], loader=loader
        )
        if ok:
            print("[OK] Server created – you can now drop mods into the `mods/` folder.")
        input("Press ENTER…"); return True

    def act_list():
        items = detect_servers(base)
        if not items: print("[INFO] No servers yet.")
        else:
            print("\n#  Name                        Loader   Version        RAM   Running  Path")
            print("-- --------------------------- -------- -------------- ----- -------- ------------------------------")
            for i, s in enumerate(items, 1):
                running = "yes" if is_running(s["path"]) else "no"
                loader = s.get("loader", "vanilla")
                print(f"{i:>2} {s['name'][:27]:<27} {loader[:8]:<8} {s['version'][:12]:<12} {s['memory'][:5]:<5} {running:<8} {s['path']}")
        input("Press ENTER…"); return True

    def act_status():
        sv = pick_server("Check status for")
        if not sv: return True
        print(f"[OK] {sv.name} is {'RUNNING' if is_running(sv) else 'STOPPED'} (session: {_session_name(sv)})")
        input("Press ENTER…"); return True

    def act_start():
        sv = pick_server("Start which server")
        if not sv: return True
        meta = read_server_meta(sv)
        jar = meta.get("jar")
        if not jar or not (sv / jar).exists():
            print("[ERR] JAR not found – pick manually.")
            jar = choose_jar(sv)
        if not jar: input("Press ENTER…"); return True
        ok = start_server_screen(sv, cfg.get("java_path","java"), jar, meta.get("memory", cfg.get("memory","4G")))
        if ok:
            print(f"[OK] Launched {sv.name} in screen. Attach with: screen -r {_session_name(sv)}")
        input("Press ENTER…"); return True

    def act_stop():
        sv = pick_server("Stop which server")
        if not sv: return True
        stop_server_screen(sv)
        input("Press ENTER…"); return True

    def act_restart():
        sv = pick_server("Restart which server")
        if not sv: return True
        meta = read_server_meta(sv)
        jar = meta.get("jar")
        if not jar or not (sv / jar).exists():
            jar = choose_jar(sv)
        if not jar: input("Press ENTER…"); return True
        stop_server_screen(sv); time.sleep(1.0)
        start_server_screen(sv, cfg.get("java_path","java"), jar, meta.get("memory", cfg.get("memory","4G")))
        print(f"[OK] Restarted {sv.name}")
        input("Press ENTER…"); return True

    def act_logs():
        sv = pick_server("Show recent console (tail)")
        if not sv: return True
        try:
            n = int(input("How many lines? (default 100): ") or 100)
        except: n = 100
        tail_console(sv, n)
        input("Press ENTER…"); return True

    def act_attach():
        sv = pick_server("Attach to console of")
        if not sv: return True
        print("[INFO] Attaching… Detach with Ctrl+A, D")
        attach_console(sv)
        return True

    def act_cmd():
        sv = pick_server("Send command to")
        if not sv: return True
        cmd = input("Command (without leading /): ").strip()
        if not cmd: return True
        if not cmd.startswith("/"): cmd = "/" + cmd
        send_command(sv, cmd)
        input("Press ENTER…"); return True

    def act_backup():
        sv = pick_server("Backup which server")
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
            meta = read_server_meta(sv)
            jar = meta.get("jar")
            if not jar or not (sv / jar).exists():
                jar = choose_jar(sv)
            if not jar: print(f"[SKIP] {sv.name}: no jar"); continue
            start_server_screen(sv, cfg.get("java_path","java"), jar, meta.get("memory", cfg.get("memory","4G")))
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
        act = actions.get(choice)
        if act is None:
            print("[WARN] Unknown option.")
            time.sleep(0.6)
            continue
        if not act():
            break

# ================== SETTINGS MENU ==================
def settings_menu(cfg: dict):
    while True:
        clear()
        print("=== MCSmaker · Settings ===")
        print(f"1) JARs dir         : {cfg['jars_dir']}")
        print(f"2) Servers base dir : {cfg['servers_base']}")
        print(f"3) Java path        : {cfg['java_path']}")
        print(f"4) Default RAM      : {cfg['memory']}")
        print(f"5) Default mod loader : {cfg.get('default_mod_loader','vanilla')}")
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
                cfg["memory"] = normalize_ram(p, cfg["memory"])
                save_cfg(cfg)
        elif c == "5":
            print("1) Vanilla   2) Fabric   3) Forge")
            ch = input("Choice [1-3] (default = 1): ").strip() or "1"
            cfg["default_mod_loader"] = {"1":"vanilla","2":"fabric","3":"forge"}.get(ch, "vanilla")
            save_cfg(cfg)
        elif c == "0":
            break

# ================== MAIN MENU ==================
def main_menu():
    check_and_install_dependencies()
    check_for_updates(auto_prompt=True)

    global cfg
    cfg = load_cfg()
    Path(cfg["jars_dir"]).expanduser().mkdir(parents=True, exist_ok=True)
    Path(cfg["servers_base"]).expanduser().mkdir(parents=True, exist_ok=True)

    def do_jars(): jars_menu(cfg); return True
    def do_servers(): servers_menu(cfg); return True
    def do_mods(): mods_menu(cfg); return True
    def do_settings(): settings_menu(cfg); return True
    def do_update(): self_update(); input("Press ENTER…"); return True
    def do_exit(): print("[BYE]"); return False
    def unknown(): print("[WARN] Unknown option."); time.sleep(0.6); return True

    actions = {
        "1": do_jars,
        "2": do_servers,
        "3": do_mods,
        "4": do_settings,
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
██║ ╚═╝ ██║╚██████╗███████║    ██║ ╚═╝ ██║██║  ██║██║  ██╗███████╗██║  ██║
╚═╝     ╚═╝ ╚═════╝╚══════╝    ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
                                                                          
                 MCSMAKER — Minecraft Automation Tool by Nico19422009 · v{CURRENT_VERSION}
""")
        print("1) JARs")
        print("2) Servers")
        print("3) Mods")
        print("4) Settings")
        print("U) Update program")
        print("0) Exit")
        choice = input("\nChoose: ").strip().lower()
        act = actions.get(choice, unknown)
        if act is None or not act():
            break

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n[BYE]")
