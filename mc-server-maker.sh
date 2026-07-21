#!/usr/bin/env bash

# MCSMaker - erstellt Minecraft-Java-Server unter Linux.
# Unterstützt Paper, Forge, Fabric und Vanilla über deren offizielle Downloads.

set -Eeuo pipefail

SCRIPT_VERSION="2.0.0"
PAPER_API="https://fill.papermc.io/v3"
PAPER_USER_AGENT="${MCSMAKER_USER_AGENT:-MCSMaker/${SCRIPT_VERSION} (https://chatgpt.com/)}"
FABRIC_META="https://meta.fabricmc.net/v2"
FORGE_FILES="https://files.minecraftforge.net/net/minecraftforge/forge"
FORGE_MAVEN="https://maven.minecraftforge.net/net/minecraftforge/forge"
MOJANG_MANIFEST="https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

PLATFORM=""
REQUESTED_VERSION="latest"
MC_VERSION=""
SERVER_DIR=""
MIN_RAM="1G"
MAX_RAM="4G"
ACCEPT_EULA=0
ALLOW_NONEMPTY=0
SKIP_JAVA_CHECK=0
INTERACTIVE=0
TMP_DIR=""
INSTALL_DETAIL=""
JAVA_COMMAND="${JAVA_BIN:-java}"
VANILLA_MANIFEST_JSON=""
FORGE_PROMOTIONS_JSON=""

if [[ -t 1 ]]; then
  C_RESET=$'\033[0m'
  C_BLUE=$'\033[1;34m'
  C_GREEN=$'\033[1;32m'
  C_YELLOW=$'\033[1;33m'
  C_RED=$'\033[1;31m'
  C_DIM=$'\033[2m'
else
  C_RESET=""
  C_BLUE=""
  C_GREEN=""
  C_YELLOW=""
  C_RED=""
  C_DIM=""
fi

info()    { printf '%s[i]%s %s\n' "$C_BLUE" "$C_RESET" "$*" >&2; }
success() { printf '%s[+]%s %s\n' "$C_GREEN" "$C_RESET" "$*" >&2; }
warn()    { printf '%s[!]%s %s\n' "$C_YELLOW" "$C_RESET" "$*" >&2; }
die()     { printf '%s[FEHLER]%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; exit 1; }

cleanup() {
  if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
    rm -rf -- "$TMP_DIR"
  fi
}

trap cleanup EXIT
trap 'exit 130' INT TERM

show_banner() {
  printf '%s' "$C_BLUE"
  printf '%s\n' '  __  __  ____ ____  __  __       _             '
  printf '%s\n' ' |  \/  |/ ___/ ___||  \/  | __ _| | _____ _ __ '
  printf '%s\n' ' | |\/| | |   \___ \| |\/| |/ _` | |/ / _ \ `__|'
  printf '%s\n' ' | |  | | |___ ___) | |  | | (_| |   <  __/ |   '
  printf '%s\n' ' |_|  |_|\____|____/|_|  |_|\__,_|_|\_\___|_|   '
  printf '%s\n' "$C_RESET"
  printf '%sLinux Minecraft Server Maker v%s%s\n\n' "$C_DIM" "$SCRIPT_VERSION" "$C_RESET"
}

usage() {
  cat <<EOF
MCSMaker ${SCRIPT_VERSION}

Benutzung:
  ./mc-server-maker.sh
  ./mc-server-maker.sh --type paper --version 26.1.2 --dir ./mein-server --accept-eula

Optionen:
  -t, --type TYPE          paper, forge, fabric oder vanilla
  -v, --version VERSION    Minecraft-Version oder "latest" (Standard)
  -d, --dir PFAD           Zielordner
      --min-ram WERT       Start-RAM, z. B. 1G oder 512M
      --max-ram WERT       Maximaler RAM, z. B. 4G
      --ram WERT           Kurzform für --max-ram
      --accept-eula        Minecraft-EULA ausdrücklich akzeptieren
  -f, --force              Installation in einen nicht leeren Ordner erlauben
      --skip-java-check    Prüfung der installierten Java-Version überspringen
  -h, --help               Diese Hilfe anzeigen

Ohne Optionen startet ein interaktives Menü.
EOF
}

parse_args() {
  while (($#)); do
    case "$1" in
      -t|--type)
        (($# >= 2)) || die "Nach $1 fehlt ein Wert."
        PLATFORM="$2"
        shift 2
        ;;
      --type=*) PLATFORM="${1#*=}"; shift ;;
      -v|--version)
        (($# >= 2)) || die "Nach $1 fehlt ein Wert."
        REQUESTED_VERSION="$2"
        shift 2
        ;;
      --version=*) REQUESTED_VERSION="${1#*=}"; shift ;;
      -d|--dir)
        (($# >= 2)) || die "Nach $1 fehlt ein Wert."
        SERVER_DIR="$2"
        shift 2
        ;;
      --dir=*) SERVER_DIR="${1#*=}"; shift ;;
      --min-ram)
        (($# >= 2)) || die "Nach $1 fehlt ein Wert."
        MIN_RAM="$2"
        shift 2
        ;;
      --min-ram=*) MIN_RAM="${1#*=}"; shift ;;
      --max-ram|--ram)
        (($# >= 2)) || die "Nach $1 fehlt ein Wert."
        MAX_RAM="$2"
        shift 2
        ;;
      --max-ram=*|--ram=*) MAX_RAM="${1#*=}"; shift ;;
      --accept-eula) ACCEPT_EULA=1; shift ;;
      -f|--force) ALLOW_NONEMPTY=1; shift ;;
      --skip-java-check) SKIP_JAVA_CHECK=1; shift ;;
      -h|--help) usage; exit 0 ;;
      --) shift; (($# == 0)) || die "Unerwartete Argumente: $*" ;;
      -*) die "Unbekannte Option: $1" ;;
      *) die "Unerwartetes Argument: $1" ;;
    esac
  done
}

choose_interactively() {
  local choice input

  show_banner
  printf '%s\n' 'Welche Server-Art willst du?'
  printf '%s\n' '  1) Paper    - Plugins und gute Performance'
  printf '%s\n' '  2) Forge    - Forge-Mods'
  printf '%s\n' '  3) Fabric   - Fabric-Mods und leichtgewichtig'
  printf '%s\n' '  4) Vanilla  - Originaler Mojang-Server'
  printf '\nAuswahl [1-4]: '
  read -r choice

  case "$choice" in
    1|paper|Paper) PLATFORM="paper" ;;
    2|forge|Forge) PLATFORM="forge" ;;
    3|fabric|Fabric) PLATFORM="fabric" ;;
    4|vanilla|Vanilla) PLATFORM="vanilla" ;;
    *) die "Ungültige Auswahl." ;;
  esac

  printf 'Minecraft-Version [latest]: '
  read -r input
  REQUESTED_VERSION="${input:-latest}"

  printf 'Minimaler RAM [1G]: '
  read -r input
  MIN_RAM="${input:-1G}"

  printf 'Maximaler RAM [4G]: '
  read -r input
  MAX_RAM="${input:-4G}"

  printf '\nMinecraft-EULA: https://aka.ms/MinecraftEULA\n'
  printf 'Hast du sie gelesen und akzeptierst du sie? [j/N]: '
  read -r input
  case "$input" in
    j|J|ja|JA|Ja|y|Y|yes|YES|Yes) ACCEPT_EULA=1 ;;
    *) ACCEPT_EULA=0 ;;
  esac
}

normalize_platform() {
  PLATFORM="${PLATFORM,,}"
  case "$PLATFORM" in
    paper|forge|fabric|vanilla) ;;
    *) die "Server-Art muss paper, forge, fabric oder vanilla sein." ;;
  esac
}

normalize_ram() {
  MIN_RAM="${MIN_RAM^^}"
  MAX_RAM="${MAX_RAM^^}"
  [[ "$MIN_RAM" =~ ^[1-9][0-9]*[MG]$ ]] || die "Ungültiger RAM-Wert: $MIN_RAM"
  [[ "$MAX_RAM" =~ ^[1-9][0-9]*[MG]$ ]] || die "Ungültiger RAM-Wert: $MAX_RAM"

  local min_mb max_mb
  min_mb=$(ram_to_mb "$MIN_RAM")
  max_mb=$(ram_to_mb "$MAX_RAM")
  ((min_mb <= max_mb)) || die "Minimaler RAM darf nicht größer als maximaler RAM sein."
}

ram_to_mb() {
  local value="$1" number unit
  number="${value%[MG]}"
  unit="${value: -1}"
  if [[ "$unit" == "G" ]]; then
    printf '%s\n' "$((number * 1024))"
  else
    printf '%s\n' "$number"
  fi
}

dependency_hint() {
  cat >&2 <<'EOF'
Installiere die fehlenden Tools mit deinem Paketmanager, zum Beispiel:
  Debian/Ubuntu: sudo apt update && sudo apt install curl jq
  Fedora:        sudo dnf install curl jq
  Arch:          sudo pacman -S curl jq
EOF
}

check_dependencies() {
  local missing=()
  command -v curl >/dev/null 2>&1 || missing+=(curl)
  command -v jq >/dev/null 2>&1 || missing+=(jq)

  if ((${#missing[@]})); then
    warn "Fehlende Programme: ${missing[*]}"
    dependency_hint
    exit 1
  fi
}

http_get() {
  local url="$1"
  curl --fail --location --silent --show-error \
    --retry 3 --retry-delay 2 --connect-timeout 20 \
    --proto '=https' "$url"
}

paper_get() {
  local url="$1"
  curl --fail --location --silent --show-error \
    --retry 3 --retry-delay 2 --connect-timeout 20 \
    --proto '=https' -H "User-Agent: $PAPER_USER_AGENT" "$url"
}

download_file() {
  local url="$1" output="$2" user_agent="${3:-}"
  local args=(
    --fail --location --silent --show-error
    --retry 3 --retry-delay 2 --connect-timeout 20
    --proto '=https' --output "$output"
  )
  if [[ -n "$user_agent" ]]; then
    args+=(-H "User-Agent: $user_agent")
  fi
  curl "${args[@]}" "$url"
  [[ -s "$output" ]] || die "Der Download ist leer: $url"
}

urlencode() {
  jq -nr --arg value "$1" '$value|@uri'
}

validate_jar() {
  local jar="$1" magic
  [[ -s "$jar" ]] || die "Die heruntergeladene JAR ist leer."
  magic=$(od -An -tx1 -N2 "$jar" 2>/dev/null | tr -d '[:space:]')
  [[ "$magic" == "504b" ]] || die "Die Download-Datei ist keine gültige JAR/ZIP-Datei."
}

verify_checksum() {
  local algorithm="$1" expected="$2" file="$3" command actual
  [[ -n "$expected" && "$expected" != "null" ]] || return 0

  case "$algorithm" in
    sha1) command="sha1sum" ;;
    sha256) command="sha256sum" ;;
    *) die "Unbekannter Prüfsummen-Typ: $algorithm" ;;
  esac

  if ! command -v "$command" >/dev/null 2>&1; then
    warn "$command fehlt. Prüfsummenprüfung wird übersprungen."
    return 0
  fi

  actual=$("$command" "$file" | awk '{print $1}')
  [[ "${actual,,}" == "${expected,,}" ]] || die "Prüfsumme stimmt nicht. Download wurde abgebrochen."
  success "Prüfsumme stimmt."
}

get_vanilla_manifest() {
  if [[ -z "$VANILLA_MANIFEST_JSON" ]]; then
    VANILLA_MANIFEST_JSON=$(http_get "$MOJANG_MANIFEST")
  fi
  printf '%s\n' "$VANILLA_MANIFEST_JSON"
}

get_forge_promotions() {
  if [[ -z "$FORGE_PROMOTIONS_JSON" ]]; then
    FORGE_PROMOTIONS_JSON=$(http_get "$FORGE_FILES/promotions_slim.json")
  fi
  printf '%s\n' "$FORGE_PROMOTIONS_JSON"
}

resolve_latest_version() {
  local json version

  case "$PLATFORM" in
    vanilla)
      json=$(get_vanilla_manifest)
      version=$(jq -r '.latest.release // empty' <<<"$json")
      ;;
    paper)
      json=$(paper_get "$PAPER_API/projects/paper")
      version=$(jq -r '.versions | to_entries[0].value[0] // empty' <<<"$json")
      ;;
    fabric)
      json=$(http_get "$FABRIC_META/versions/game")
      version=$(jq -r 'first(.[] | select(.stable == true) | .version) // empty' <<<"$json")
      ;;
    forge)
      json=$(get_forge_promotions)
      version=$(jq -r '.promos | keys[] | select(endswith("-latest")) | sub("-latest$"; "")' \
        <<<"$json" | LC_ALL=C sort -V | tail -n1)
      ;;
  esac

  [[ -n "$version" && "$version" != "null" ]] || die "Konnte die neueste Version für $PLATFORM nicht finden."
  MC_VERSION="$version"
}

resolve_version() {
  if [[ -z "$REQUESTED_VERSION" || "${REQUESTED_VERSION,,}" == "latest" ]]; then
    info "Suche die neueste verfügbare Version für $PLATFORM ..."
    resolve_latest_version
  else
    MC_VERSION="$REQUESTED_VERSION"
  fi

  [[ "$MC_VERSION" =~ ^[0-9A-Za-z._+[:space:]-]+$ ]] || die "Ungültige Minecraft-Version: $MC_VERSION"
  success "Minecraft-Version: $MC_VERSION"
}

version_ge() {
  local current="$1" minimum="$2" first
  first=$(printf '%s\n%s\n' "$minimum" "$current" | LC_ALL=C sort -V | head -n1)
  [[ "$first" == "$minimum" ]]
}

required_java_for() {
  local version="$1"

  if [[ "$version" =~ ^([0-9]+)\. ]]; then
    if ((BASH_REMATCH[1] >= 26)); then
      printf '25\n'
      return
    fi
  fi

  if version_ge "$version" "1.20.5"; then
    printf '21\n'
  elif version_ge "$version" "1.18"; then
    printf '17\n'
  elif version_ge "$version" "1.17"; then
    printf '16\n'
  else
    printf '8\n'
  fi
}

installed_java_major() {
  local output version
  output=$("$JAVA_COMMAND" -version 2>&1 || true)
  version=$(sed -n 's/.*version "\([0-9][0-9.]*\).*/\1/p' <<<"$output" | head -n1)
  [[ -n "$version" ]] || return 1

  if [[ "$version" == 1.* ]]; then
    printf '%s\n' "$(cut -d. -f2 <<<"$version")"
  else
    printf '%s\n' "${version%%.*}"
  fi
}

check_java() {
  local required installed
  required=$(required_java_for "$MC_VERSION")

  if ! command -v "$JAVA_COMMAND" >/dev/null 2>&1; then
    if [[ "$PLATFORM" == "forge" ]]; then
      die "Forge muss installiert werden, aber Java fehlt. Benötigt wird ungefähr Java $required."
    fi
    warn "Java wurde nicht gefunden. Der Download klappt, aber zum Starten brauchst du Java $required."
    return
  fi

  if ((SKIP_JAVA_CHECK)); then
    warn "Java-Versionsprüfung wurde übersprungen."
    return
  fi

  installed=$(installed_java_major || true)
  if [[ -z "$installed" ]]; then
    warn "Installierte Java-Version konnte nicht erkannt werden."
    return
  fi

  if ((installed < required)); then
    if [[ "$PLATFORM" == "forge" ]]; then
      die "Java $installed ist zu alt. Minecraft $MC_VERSION braucht ungefähr Java $required."
    fi
    warn "Java $installed ist zu alt. Minecraft $MC_VERSION braucht ungefähr Java $required."
  else
    success "Java $installed erkannt."
  fi

  if ((required <= 8 && installed > 8)); then
    warn "Alte Minecraft-/Forge-Versionen laufen oft am besten mit Java 8."
  fi
}

directory_has_files() {
  [[ -d "$1" ]] && [[ -n "$(find "$1" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]
}

prepare_server_directory() {
  local default_dir answer was_nonempty=0 safe_version

  safe_version="${MC_VERSION// /_}"
  safe_version="${safe_version//\//_}"
  default_dir="./mc-server-${PLATFORM}-${safe_version}"

  if ((INTERACTIVE)); then
    printf 'Server-Ordner [%s]: ' "$default_dir"
    read -r answer
    SERVER_DIR="${answer:-$default_dir}"
  elif [[ -z "$SERVER_DIR" ]]; then
    SERVER_DIR="$default_dir"
  fi

  [[ -n "$SERVER_DIR" ]] || die "Server-Ordner darf nicht leer sein."
  if directory_has_files "$SERVER_DIR"; then
    was_nonempty=1
  fi

  if ((was_nonempty && ! ALLOW_NONEMPTY)); then
    if ((INTERACTIVE)); then
      warn "Der Ordner ist nicht leer. Vorhandene Dateien könnten verändert werden."
      printf 'Trotzdem fortfahren? [j/N]: '
      read -r answer
      case "$answer" in
        j|J|ja|JA|Ja|y|Y|yes|YES|Yes) ALLOW_NONEMPTY=1 ;;
        *) die "Abgebrochen." ;;
      esac
    else
      die "Der Zielordner ist nicht leer. Nutze --force nur wenn das wirklich gewollt ist."
    fi
  fi

  mkdir -p -- "$SERVER_DIR"
  SERVER_DIR=$(cd -- "$SERVER_DIR" && pwd -P)
  [[ "$SERVER_DIR" != "/" ]] || die "Das Root-Verzeichnis darf kein Server-Ordner sein."
  [[ -w "$SERVER_DIR" ]] || die "Keine Schreibrechte für: $SERVER_DIR"

  TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/mcsmaker.XXXXXXXX")
  success "Server-Ordner: $SERVER_DIR"
}

backup_file() {
  local source="$1" backup counter=0
  [[ -e "$source" || -L "$source" ]] || return 0

  backup="${source}.backup-$(date +%Y%m%d-%H%M%S)"
  while [[ -e "$backup" || -L "$backup" ]]; do
    ((counter += 1))
    backup="${source}.backup-$(date +%Y%m%d-%H%M%S)-${counter}"
  done
  mv -- "$source" "$backup"
  warn "Vorhandene Datei gesichert: $(basename -- "$backup")"
}

install_server_jar() {
  local downloaded="$1" target="$SERVER_DIR/server.jar"
  validate_jar "$downloaded"
  backup_file "$target"
  mv -- "$downloaded" "$target"
  chmod 0644 "$target"
}

install_vanilla() {
  local manifest metadata_url metadata server_url sha1 downloaded

  info "Hole Vanilla-Download von Mojang ..."
  manifest=$(get_vanilla_manifest)
  metadata_url=$(jq -r --arg version "$MC_VERSION" \
    'first(.versions[] | select(.id == $version) | .url) // empty' <<<"$manifest")
  [[ -n "$metadata_url" ]] || die "Vanilla-Version $MC_VERSION wurde nicht gefunden."

  metadata=$(http_get "$metadata_url")
  server_url=$(jq -r '.downloads.server.url // empty' <<<"$metadata")
  sha1=$(jq -r '.downloads.server.sha1 // empty' <<<"$metadata")
  [[ -n "$server_url" ]] || die "Für $MC_VERSION gibt es keine Vanilla-Server-JAR."

  downloaded="$TMP_DIR/vanilla-server.jar"
  download_file "$server_url" "$downloaded"
  verify_checksum sha1 "$sha1" "$downloaded"
  install_server_jar "$downloaded"
  INSTALL_DETAIL="Vanilla $MC_VERSION"
}

install_paper() {
  local encoded builds build channel server_url sha256 downloaded build_id

  info "Hole neuesten Paper-Build ..."
  encoded=$(urlencode "$MC_VERSION")
  builds=$(paper_get "$PAPER_API/projects/paper/versions/${encoded}/builds") || \
    die "Paper bietet Minecraft $MC_VERSION nicht an."

  if jq -e '.ok == false' >/dev/null 2>&1 <<<"$builds"; then
    die "Paper-API: $(jq -r '.message // "Unbekannter Fehler"' <<<"$builds")"
  fi

  build=$(jq -c 'first(.[] | select(.channel == "STABLE")) // .[0] // empty' <<<"$builds")
  [[ -n "$build" ]] || die "Keine Paper-Builds für Minecraft $MC_VERSION gefunden."

  channel=$(jq -r '.channel // "UNKNOWN"' <<<"$build")
  build_id=$(jq -r '.id // .number // "unbekannt"' <<<"$build")
  server_url=$(jq -r '.downloads."server:default".url // empty' <<<"$build")
  sha256=$(jq -r '.downloads."server:default".checksums.sha256 // empty' <<<"$build")
  [[ -n "$server_url" ]] || die "Paper-Build enthält keine Server-JAR."

  if [[ "$channel" != "STABLE" ]]; then
    warn "Für $MC_VERSION gibt es keinen stabilen Paper-Build. Nutze $channel-Build $build_id."
  fi

  downloaded="$TMP_DIR/paper-server.jar"
  download_file "$server_url" "$downloaded" "$PAPER_USER_AGENT"
  verify_checksum sha256 "$sha256" "$downloaded"
  install_server_jar "$downloaded"
  mkdir -p -- "$SERVER_DIR/plugins"
  INSTALL_DETAIL="Paper $MC_VERSION, Build $build_id ($channel)"
}

install_fabric() {
  local encoded loader_json installer_json loader installer server_url downloaded

  info "Suche passende Fabric-Versionen ..."
  encoded=$(urlencode "$MC_VERSION")
  loader_json=$(http_get "$FABRIC_META/versions/loader/${encoded}") || \
    die "Fabric unterstützt Minecraft $MC_VERSION nicht."
  loader=$(jq -r 'first(.[] | select(.loader.stable == true) | .loader.version) // .[0].loader.version // empty' \
    <<<"$loader_json")
  [[ -n "$loader" ]] || die "Kein Fabric Loader für Minecraft $MC_VERSION gefunden."

  installer_json=$(http_get "$FABRIC_META/versions/installer")
  installer=$(jq -r 'first(.[] | select(.stable == true) | .version) // .[0].version // empty' \
    <<<"$installer_json")
  [[ -n "$installer" ]] || die "Keine Fabric-Installer-Version gefunden."

  server_url="$FABRIC_META/versions/loader/$(urlencode "$MC_VERSION")/$(urlencode "$loader")/$(urlencode "$installer")/server/jar"
  downloaded="$TMP_DIR/fabric-server.jar"
  download_file "$server_url" "$downloaded"
  install_server_jar "$downloaded"
  mkdir -p -- "$SERVER_DIR/mods"
  INSTALL_DETAIL="Fabric $MC_VERSION, Loader $loader, Launcher $installer"
}

forge_coordinate() {
  local mc_version="$1" forge_version="$2" metadata prefix coordinate candidate
  prefix="${mc_version}-${forge_version}"
  coordinate=""

  if metadata=$(http_get "$FORGE_MAVEN/maven-metadata.xml" 2>/dev/null); then
    while IFS= read -r candidate; do
      if [[ "$candidate" == "$prefix" || "$candidate" == "$prefix"-* ]]; then
        coordinate="$candidate"
      fi
    done < <(
      tr '<' '\n' <<<"$metadata" |
        sed -n 's#^version>\([^<]*\).*#\1#p' |
        LC_ALL=C sort -V
    )
  fi

  printf '%s\n' "${coordinate:-$prefix}"
}

configure_forge_jvm_args() {
  local target="$SERVER_DIR/user_jvm_args.txt" filtered="$TMP_DIR/user_jvm_args.txt"

  if [[ -f "$target" ]]; then
    awk '!/^[[:space:]]*-Xm[sx][0-9]+[mMgG][[:space:]]*$/' "$target" >"$filtered"
  else
    : >"$filtered"
  fi

  {
    printf '\n# Von MCSMaker gesetzter Arbeitsspeicher\n'
    printf -- '-Xms%s\n' "$MIN_RAM"
    printf -- '-Xmx%s\n' "$MAX_RAM"
  } >>"$filtered"
  mv -- "$filtered" "$target"
}

find_legacy_forge_jar() {
  find "$SERVER_DIR" -maxdepth 1 -type f -name 'forge-*.jar' \
    ! -name '*installer*.jar' ! -name '*sources*.jar' -print 2>/dev/null |
    sed 's#^.*/##' |
    LC_ALL=C sort -V | tail -n1
}

install_forge() {
  local promos forge_version forge_channel coordinate installer_url installer sha1 legacy_jar

  info "Suche passenden Forge-Build ..."
  promos=$(get_forge_promotions)
  forge_version=$(jq -r --arg key "${MC_VERSION}-recommended" '.promos[$key] // empty' <<<"$promos")
  forge_channel="recommended"
  if [[ -z "$forge_version" ]]; then
    forge_version=$(jq -r --arg key "${MC_VERSION}-latest" '.promos[$key] // empty' <<<"$promos")
    forge_channel="latest"
  fi
  [[ -n "$forge_version" ]] || die "Forge bietet Minecraft $MC_VERSION nicht an."

  coordinate=$(forge_coordinate "$MC_VERSION" "$forge_version")
  installer_url="$FORGE_MAVEN/${coordinate}/forge-${coordinate}-installer.jar"
  installer="$TMP_DIR/forge-installer.jar"

  info "Lade Forge $forge_version ($forge_channel) ..."
  download_file "$installer_url" "$installer" || \
    die "Forge-Installer wurde nicht gefunden: $installer_url"
  validate_jar "$installer"

  sha1=""
  if sha1=$(http_get "${installer_url}.sha1" 2>/dev/null); then
    sha1=$(awk '{print $1; exit}' <<<"$sha1")
    verify_checksum sha1 "$sha1" "$installer"
  else
    warn "Forge-Prüfsumme nicht verfügbar."
  fi

  if ((ALLOW_NONEMPTY)); then
    backup_file "$SERVER_DIR/run.sh"
    backup_file "$SERVER_DIR/user_jvm_args.txt"
  fi

  info "Forge installiert jetzt seine Server-Dateien und Bibliotheken ..."
  if ! (cd -- "$SERVER_DIR" && "$JAVA_COMMAND" -jar "$installer" --installServer); then
    die "Forge-Installation fehlgeschlagen. Prüfe besonders deine Java-Version."
  fi

  mkdir -p -- "$SERVER_DIR/mods"
  if [[ -f "$SERVER_DIR/run.sh" ]]; then
    chmod +x "$SERVER_DIR/run.sh"
    configure_forge_jvm_args
  else
    legacy_jar=$(find_legacy_forge_jar)
    [[ -n "$legacy_jar" ]] || die "Forge wurde ausgeführt, aber keine startbare Server-Datei gefunden."
  fi

  INSTALL_DETAIL="Forge $MC_VERSION-$forge_version ($forge_channel)"
}

write_direct_start_script() {
  local target="$SERVER_DIR/start.sh"
  backup_file "$target"
  cat >"$target" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd -- "\$(dirname -- "\${BASH_SOURCE[0]}")"
exec "\${JAVA_BIN:-java}" -Xms${MIN_RAM} -Xmx${MAX_RAM} -jar server.jar nogui "\$@"
EOF
  chmod +x "$target"
}

write_forge_start_script() {
  local target="$SERVER_DIR/start.sh" legacy_jar
  backup_file "$target"

  if [[ -f "$SERVER_DIR/run.sh" ]]; then
    cat >"$target" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
exec ./run.sh nogui "$@"
EOF
  else
    legacy_jar=$(find_legacy_forge_jar)
    [[ -n "$legacy_jar" ]] || die "Keine Forge-Server-JAR für das Startskript gefunden."
    cat >"$target" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd -- "\$(dirname -- "\${BASH_SOURCE[0]}")"
exec "\${JAVA_BIN:-java}" -Xms${MIN_RAM} -Xmx${MAX_RAM} -jar "${legacy_jar}" nogui "\$@"
EOF
  fi
  chmod +x "$target"
}

write_eula() {
  local target="$SERVER_DIR/eula.txt"

  if [[ -f "$target" ]]; then
    if ((ACCEPT_EULA)) && ! grep -Eq '^[[:space:]]*eula=true[[:space:]]*$' "$target"; then
      backup_file "$target"
      printf '# Akzeptiert über MCSMaker nach Hinweis auf https://aka.ms/MinecraftEULA\neula=true\n' >"$target"
    fi
    return
  fi

  if ((ACCEPT_EULA)); then
    printf '# Akzeptiert über MCSMaker nach Hinweis auf https://aka.ms/MinecraftEULA\neula=true\n' >"$target"
  else
    printf '# Lies zuerst https://aka.ms/MinecraftEULA und setze danach eula=true\neula=false\n' >"$target"
  fi
}

write_info_file() {
  local target="$SERVER_DIR/mcsmaker-info.txt"
  if [[ -e "$target" ]]; then
    backup_file "$target"
  fi
  {
    printf 'MCSMaker: %s\n' "$SCRIPT_VERSION"
    printf 'Server: %s\n' "$INSTALL_DETAIL"
    printf 'Minecraft: %s\n' "$MC_VERSION"
    printf 'RAM: %s bis %s\n' "$MIN_RAM" "$MAX_RAM"
    printf 'Erstellt: %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)"
  } >"$target"
}

install_selected_server() {
  case "$PLATFORM" in
    vanilla) install_vanilla ;;
    paper) install_paper ;;
    fabric) install_fabric ;;
    forge) install_forge ;;
  esac

  if [[ "$PLATFORM" == "forge" ]]; then
    write_forge_start_script
  else
    write_direct_start_script
  fi
  write_eula
  write_info_file
}

print_result() {
  local quoted_dir
  printf -v quoted_dir '%q' "$SERVER_DIR"

  printf '\n%sFertig.%s %s\n' "$C_GREEN" "$C_RESET" "$INSTALL_DETAIL"
  printf 'Ordner: %s\n\n' "$SERVER_DIR"
  printf 'Starten:\n  cd %s\n  ./start.sh\n' "$quoted_dir"

  if grep -Eq '^[[:space:]]*eula=true[[:space:]]*$' "$SERVER_DIR/eula.txt"; then
    printf '\nEULA: akzeptiert.\n'
  else
    printf '\n%sEULA ist noch nicht akzeptiert.%s\n' "$C_YELLOW" "$C_RESET"
    printf 'Lies https://aka.ms/MinecraftEULA und ändere danach eula.txt auf eula=true.\n'
  fi

  if [[ "$PLATFORM" == "paper" ]]; then
    printf 'Plugins kommen in: %s/plugins\n' "$SERVER_DIR"
  elif [[ "$PLATFORM" == "forge" || "$PLATFORM" == "fabric" ]]; then
    printf 'Mods kommen in: %s/mods\n' "$SERVER_DIR"
  fi
}

main() {
  if (($# == 0)); then
    [[ -t 0 ]] || die "Ohne Terminal bitte --type angeben. Nutze --help für Beispiele."
    INTERACTIVE=1
    choose_interactively
  else
    parse_args "$@"
    [[ -n "$PLATFORM" ]] || die "--type fehlt. Nutze --help für ein Beispiel."
  fi

  normalize_platform
  normalize_ram
  if ((EUID == 0)); then
    warn "Du führst das Skript als root aus. Für einen MC-Server ist ein normaler eigener Benutzer sicherer."
  fi
  check_dependencies
  resolve_version
  check_java
  prepare_server_directory

  info "Installiere $PLATFORM für Minecraft $MC_VERSION ..."
  install_selected_server
  success "Installation abgeschlossen."
  print_result
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
