#!/usr/bin/env bash

# MCSMaker - erstellt Minecraft-Java-Server unter Linux.
# Unterstützt Paper, Forge, Fabric und Vanilla über deren offizielle Downloads.

set -Eeuo pipefail

SCRIPT_VERSION="3.1.0"
PROJECT_URL="https://github.com/Nico19422009/MCSmaker"
PAPER_API="https://fill.papermc.io/v3"
PAPER_USER_AGENT="${MCSMAKER_USER_AGENT:-Nico19422009/MCSmaker/${SCRIPT_VERSION} (${PROJECT_URL})}"
FABRIC_META="https://meta.fabricmc.net/v2"
FORGE_FILES="https://files.minecraftforge.net/net/minecraftforge/forge"
FORGE_MAVEN="https://maven.minecraftforge.net/net/minecraftforge/forge"
MOJANG_MANIFEST="https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
MODRINTH_API="https://api.modrinth.com/v2"
MODRINTH_USER_AGENT="${MODRINTH_USER_AGENT:-Nico19422009/MCSmaker/${SCRIPT_VERSION} (${PROJECT_URL})}"

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
MANAGED_SERVER_DIR=""
MANAGED_PLATFORM=""
MANAGED_VERSION=""
MANAGED_STATE_DIR=""
MANAGED_PID_FILE=""
MANAGED_INPUT_FIFO=""
MANAGED_CONSOLE_LOG=""
LANGUAGE="en"
CONFIG_DIRECTORY="${XDG_CONFIG_HOME:-${HOME:-.}/.config}/mcsmaker"
CONFIG_FILE="${MCSMAKER_CONFIG:-$CONFIG_DIRECTORY/config}"

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

declare -A TEXT_EN=()
declare -A TEXT_DE=()

load_messages() {
  local key english german
  while IFS=$'\t' read -r key english german; do
    [[ -n "$key" ]] || continue
    TEXT_EN["$key"]="$english"
    TEXT_DE["$key"]="$german"
  done <<'EOF'
error_label	ERROR	FEHLER
config_created	Configuration created: %s	Konfiguration erstellt: %s
config_save_failed	Could not write configuration: %s	Konfiguration konnte nicht geschrieben werden: %s
language_saved	Language saved: English	Sprache gespeichert: Deutsch
current_language	Current language: %s	Aktuelle Sprache: %s
english_name	English	Englisch
german_name	German	Deutsch
choose_language	Choose language / Sprache wählen:	Sprache wählen / Choose language:
english_default	English (default)	Englisch (Standard)
german	German	Deutsch
choice	Choice: 	Auswahl: 
invalid_language	Language must be en or de.	Sprache muss en oder de sein.
missing_value	Missing value after %s.	Nach %s fehlt ein Wert.
unexpected_args	Unexpected arguments: %s	Unerwartete Argumente: %s
unknown_option	Unknown option: %s	Unbekannte Option: %s
unexpected_arg	Unexpected argument: %s	Unerwartetes Argument: %s
server_type_question	Which server type do you want?	Welche Server-Art willst du?
paper_description	Plugins and strong performance	Plugins und gute Performance
forge_description	Forge mods	Forge-Mods
fabric_description	Fabric mods and lightweight	Fabric-Mods und leichtgewichtig
vanilla_description	Original Mojang server	Originaler Mojang-Server
selection_1_4	Selection [1-4]: 	Auswahl [1-4]: 
mc_version_prompt	Minecraft version [latest]: 	Minecraft-Version [latest]: 
min_ram_prompt	Minimum RAM [1G]: 	Minimaler RAM [1G]: 
max_ram_prompt	Maximum RAM [4G]: 	Maximaler RAM [4G]: 
eula_accept_prompt	Have you read and accepted it? [y/N]: 	Hast du sie gelesen und akzeptierst du sie? [j/N]: 
invalid_choice	Invalid selection.	Ungültige Auswahl.
invalid_platform	Server type must be paper, forge, fabric, or vanilla.	Server-Art muss paper, forge, fabric oder vanilla sein.
invalid_ram	Invalid RAM value: %s	Ungültiger RAM-Wert: %s
ram_order	Minimum RAM must not be greater than maximum RAM.	Minimaler RAM darf nicht größer als maximaler RAM sein.
missing_programs	Missing programs: %s	Fehlende Programme: %s
download_empty	The download is empty: %s	Der Download ist leer: %s
jar_empty	The downloaded JAR is empty.	Die heruntergeladene JAR ist leer.
not_jar	The downloaded file is not a valid JAR/ZIP file.	Die Download-Datei ist keine gültige JAR/ZIP-Datei.
unknown_checksum	Unknown checksum type: %s	Unbekannter Prüfsummen-Typ: %s
checksum_tool_missing	%s is missing. Checksum verification is skipped.	%s fehlt. Prüfsummenprüfung wird übersprungen.
checksum_mismatch	Checksum mismatch. The download was aborted.	Prüfsumme stimmt nicht. Download wurde abgebrochen.
checksum_ok	Checksum verified.	Prüfsumme stimmt.
latest_not_found	Could not find the latest version for %s.	Konnte die neueste Version für %s nicht finden.
latest_search	Looking up the latest available version for %s ...	Suche die neueste verfügbare Version für %s ...
invalid_mc_version	Invalid Minecraft version: %s	Ungültige Minecraft-Version: %s
mc_version_selected	Minecraft version: %s	Minecraft-Version: %s
forge_java_missing	Forge must be installed, but Java is missing. Approximately Java %s is required.	Forge muss installiert werden, aber Java fehlt. Benötigt wird ungefähr Java %s.
java_missing	Java was not found. The download works, but Java %s is required to start.	Java wurde nicht gefunden. Der Download klappt, aber zum Starten brauchst du Java %s.
java_check_skipped	Java version check was skipped.	Java-Versionsprüfung wurde übersprungen.
java_unknown	Could not detect the installed Java version.	Installierte Java-Version konnte nicht erkannt werden.
java_too_old	Java %s is too old. Minecraft %s requires approximately Java %s.	Java %s ist zu alt. Minecraft %s braucht ungefähr Java %s.
java_detected	Java %s detected.	Java %s erkannt.
old_java_hint	Old Minecraft/Forge versions often work best with Java 8.	Alte Minecraft-/Forge-Versionen laufen oft am besten mit Java 8.
server_dir_prompt	Server directory [%s]: 	Server-Ordner [%s]: 
server_dir_empty	Server directory must not be empty.	Server-Ordner darf nicht leer sein.
directory_not_empty	The directory is not empty. Existing files may be changed.	Der Ordner ist nicht leer. Vorhandene Dateien könnten verändert werden.
continue_anyway	Continue anyway? [y/N]: 	Trotzdem fortfahren? [j/N]: 
aborted	Aborted.	Abgebrochen.
nonempty_requires_force	The target directory is not empty. Only use --force when intended.	Der Zielordner ist nicht leer. Nutze --force nur wenn das wirklich gewollt ist.
root_dir_forbidden	The root directory cannot be used as a server directory.	Das Root-Verzeichnis darf kein Server-Ordner sein.
no_write_access	No write permission for: %s	Keine Schreibrechte für: %s
server_dir_ready	Server directory: %s	Server-Ordner: %s
file_backed_up	Existing file backed up: %s	Vorhandene Datei gesichert: %s
vanilla_download	Fetching Vanilla download from Mojang ...	Hole Vanilla-Download von Mojang ...
vanilla_not_found	Vanilla version %s was not found.	Vanilla-Version %s wurde nicht gefunden.
vanilla_no_jar	There is no Vanilla server JAR for %s.	Für %s gibt es keine Vanilla-Server-JAR.
paper_download	Fetching the newest Paper build ...	Hole neuesten Paper-Build ...
paper_unsupported	Paper does not offer Minecraft %s.	Paper bietet Minecraft %s nicht an.
unknown_error	Unknown error	Unbekannter Fehler
paper_no_build	No Paper builds found for Minecraft %s.	Keine Paper-Builds für Minecraft %s gefunden.
paper_no_jar	The Paper build does not contain a server JAR.	Paper-Build enthält keine Server-JAR.
paper_unstable	There is no stable Paper build for %s. Using %s build %s.	Für %s gibt es keinen stabilen Paper-Build. Nutze %s-Build %s.
fabric_search	Looking for compatible Fabric versions ...	Suche passende Fabric-Versionen ...
fabric_unsupported	Fabric does not support Minecraft %s.	Fabric unterstützt Minecraft %s nicht.
fabric_no_loader	No Fabric Loader found for Minecraft %s.	Kein Fabric Loader für Minecraft %s gefunden.
fabric_no_installer	No Fabric installer version found.	Keine Fabric-Installer-Version gefunden.
forge_search	Looking for a compatible Forge build ...	Suche passenden Forge-Build ...
forge_unsupported	Forge does not offer Minecraft %s.	Forge bietet Minecraft %s nicht an.
forge_download	Downloading Forge %s (%s) ...	Lade Forge %s (%s) ...
forge_installer_missing	Forge installer was not found: %s	Forge-Installer wurde nicht gefunden: %s
forge_checksum_missing	Forge checksum is unavailable.	Forge-Prüfsumme nicht verfügbar.
forge_installing	Forge is installing its server files and libraries ...	Forge installiert jetzt seine Server-Dateien und Bibliotheken ...
forge_install_failed	Forge installation failed. Check your Java version in particular.	Forge-Installation fehlgeschlagen. Prüfe besonders deine Java-Version.
forge_not_startable	Forge ran, but no startable server file was found.	Forge wurde ausgeführt, aber keine startbare Server-Datei gefunden.
forge_jar_missing	No Forge server JAR found for the start script.	Keine Forge-Server-JAR für das Startskript gefunden.
pause	Press Enter to continue ... 	Enter drücken zum Fortfahren ... 
found_servers	Detected servers:	Gefundene Server:
none_found_here	None found below the current directory.	Keine im aktuellen Ordner gefunden.
manual_path	Enter path manually	Pfad manuell eingeben
server_path_prompt	Server path: 	Server-Pfad: 
invalid_server_selection	Invalid server selection.	Ungültige Server-Auswahl.
server_dir_missing	Server directory is missing.	Server-Ordner fehlt.
server_dir_not_exist	Server directory does not exist: %s	Server-Ordner existiert nicht: %s
start_missing	No start.sh found in %s.	Kein start.sh in %s gefunden.
start_chmod_failed	Could not make start.sh executable.	start.sh konnte nicht ausführbar gemacht werden.
management_tools_missing	Missing management tools: %s	Fehlende Management-Programme: %s
server_already_running	Server is already running.	Server läuft bereits.
eula_not_accepted	The EULA is not accepted. Read https://aka.ms/MinecraftEULA and set eula=true.	EULA ist nicht akzeptiert. Lies https://aka.ms/MinecraftEULA und setze eula=true.
server_starting	Starting server in the background ...	Starte Server im Hintergrund ...
server_started	Server started.	Server wurde gestartet.
server_crashed	The server exited immediately. Last log lines:	Server ist direkt wieder beendet worden. Letzte Logzeilen:
server_not_running	Server is not running.	Server läuft nicht.
command_prompt	Minecraft command without /: 	Minecraft-Befehl ohne /: 
empty_command	The command is empty.	Leerer Befehl.
multiline_command	Multiline commands are not allowed.	Mehrzeilige Befehle sind nicht erlaubt.
command_sent	Command sent: %s	Befehl gesendet: %s
server_stopping	Sending stop and waiting for a clean shutdown ...	Sende stop und warte auf sauberes Herunterfahren ...
server_stopped	Server stopped cleanly.	Server wurde sauber gestoppt.
server_unresponsive	The server is still responding after 30 seconds.	Server reagiert nach 30 Sekunden noch.
hard_kill_prompt	Force-stop the server process? [y/N]: 	Server-Prozess hart beenden? [j/N]: 
session_killed	The server process was force-stopped.	Server-Prozess wurde hart beendet.
command_pipe_missing	The server command pipe is unavailable.	Die Command-Pipe des Servers ist nicht verfügbar.
runtime_state_invalid	Unsafe runtime path: %s	Unsicherer Laufzeit-Pfad: %s
console_read_failed	Could not read the console. The server may have just stopped.	Konsole konnte nicht gelesen werden. Der Server wurde eventuell gerade beendet.
showing_latest_log	Server is stopped. Showing logs/latest.log.	Server läuft nicht. Zeige logs/latest.log.
no_console_log	No console output or log file exists yet.	Noch keine Konsole oder Logdatei vorhanden.
console_tty_required	The live console requires a real terminal.	Die Live-Konsole braucht ein echtes Terminal.
console_title	MCSMaker Live Console	MCSMaker Live-Konsole
console_help	Type a Minecraft command and press Enter. /back returns to MCSMaker.	Minecraft-Befehl eingeben und Enter drücken. /back kehrt zu MCSMaker zurück.
console_back_hint	Local commands: /back, /refresh, /help	Lokale Befehle: /back, /refresh, /help
console_returned	Returned to server management.	Zur Serververwaltung zurückgekehrt.
console_server_ended	The server stopped. Returning to MCSMaker.	Der Server wurde gestoppt. Rückkehr zu MCSMaker.
console_help_notice	Use /back to leave this view. Other input is sent to Minecraft.	Mit /back verlässt du diese Ansicht. Andere Eingaben gehen an Minecraft.
console_send_failed	The command could not be sent.	Der Befehl konnte nicht gesendet werden.
status_title	Server status	Server-Status
status_running	RUNNING	LÄUFT
status_stopped	STOPPED	GESTOPPT
status_type	Type	Typ
status_minecraft	Minecraft	Minecraft
status_directory	Directory	Ordner
status_size	Size	Größe
status_addons	Add-ons	Addons
status_process	Process	Prozess
status_uptime	Uptime	Laufzeit
unknown	unknown	unbekannt
tar_missing	tar is missing.	tar fehlt.
backup_pausing	Pausing world saves briefly for a consistent backup ...	Pausiere Welt-Speicherung kurz für ein sauberes Backup ...
backup_save_failed	Could not send all save commands.	Speicherbefehle konnten nicht vollständig gesendet werden.
backup_creating	Creating backup ...	Erstelle Backup ...
backup_created	Backup created: %s	Backup erstellt: %s
backup_failed	Backup failed.	Backup ist fehlgeschlagen.
vanilla_no_addons	Vanilla does not support Paper plugins or Fabric/Forge mods.	Vanilla unterstützt keine Paper-Plugins oder Fabric/Forge-Mods.
unknown_server_type	Could not detect the server type. Add-on search is unavailable.	Server-Typ konnte nicht erkannt werden. Addon-Suche ist nicht möglich.
mc_version_unknown	Minecraft version is unknown.	Minecraft-Version ist unbekannt.
addon_search_prompt	%s search on Modrinth: 	%s-Suche auf Modrinth: 
plugin_label	Plugin	Plugin
plugins_label	plugins	Plugins
mod_label	Mod	Mod
mods_label	mods	Mods
addon_query_empty	The search query is empty.	Suchbegriff ist leer.
addon_searching	Searching for compatible %s for %s %s ...	Suche passende %s für %s %s ...
modrinth_search_failed	Modrinth search failed.	Modrinth-Suche fehlgeschlagen.
no_compatible_hits	No compatible results found.	Keine kompatiblen Treffer gefunden.
modrinth_results	Results on Modrinth:	Treffer auf Modrinth:
downloads_label	Downloads	Downloads
cancel	Cancel	Abbrechen
versions_failed	Could not load versions.	Versionen konnten nicht geladen werden.
no_download_version	No compatible download version found.	Keine passende Download-Version gefunden.
version_no_file	The version contains no file.	Version enthält keine Datei.
download_not_jar	The download is not a JAR file.	Download ist keine JAR-Datei.
addon_installed	%s %s installed: %s	%s %s installiert: %s
dependencies_warning	This add-on reports %s required dependency/dependencies. Check the project's Modrinth page.	Dieses Addon meldet %s benötigte Abhängigkeit(en). Prüfe die Modrinth-Seite des Projekts.
restart_for_addon	The server is still running. Restart it to load the add-on.	Server läuft noch. Starte ihn neu, damit das Addon geladen wird.
installed_addons	Installed %s:	Installierte %s:
none_found	None found.	Keine gefunden.
none_to_disable	No add-ons found to disable.	Keine Addons zum Deaktivieren gefunden.
disable_addon	Disable add-on:	Addon deaktivieren:
addon_disabled	Disabled: %s	Deaktiviert: %s
restart_required	A restart is required for this change.	Für die Änderung ist ein Neustart nötig.
none_disabled	No disabled add-ons found.	Keine deaktivierten Addons gefunden.
enable_addon	Enable add-on:	Addon aktivieren:
addon_enabled	Enabled: %s	Aktiviert: %s
addon_manager	Add-on manager	Addon-Manager
addon_search_install	Search and install on Modrinth	Auf Modrinth suchen und installieren
addon_list	Show installed add-ons	Installierte Addons anzeigen
addon_disable	Disable an add-on	Addon deaktivieren
addon_enable	Enable an add-on	Addon wieder aktivieren
back	Back	Zurück
management_title	Server management	Server-Management
menu_start	Start server	Server starten
menu_console	Open live console	Live-Konsole öffnen
menu_recent	Show recent console lines	Letzte Konsolenzeilen
menu_command	Send command	Command senden
menu_stop	Stop server	Server stoppen
menu_restart	Restart server	Server neustarten
menu_addons	Manage mods/plugins	Mods/Plugins verwalten
menu_backup	Create server backup	Server-Backup erstellen
finished	Done.	Fertig.
directory_label	Directory	Ordner
start_instructions	Start:	Starten:
eula_accepted	EULA: accepted.	EULA: akzeptiert.
eula_pending	The EULA has not been accepted yet.	EULA ist noch nicht akzeptiert.
eula_edit	Read https://aka.ms/MinecraftEULA and then change eula.txt to eula=true.	Lies https://aka.ms/MinecraftEULA und ändere danach eula.txt auf eula=true.
plugins_directory	Plugin directory: %s/plugins	Plugins kommen in: %s/plugins
mods_directory	Mod directory: %s/mods	Mods kommen in: %s/mods
root_warning	You are running the script as root. A dedicated non-root user is safer for an MC server.	Du führst das Skript als root aus. Für einen MC-Server ist ein normaler eigener Benutzer sicherer.
installing	Installing %s for Minecraft %s ...	Installiere %s für Minecraft %s ...
install_complete	Installation complete.	Installation abgeschlossen.
terminal_type_required	Without a terminal, provide --type. Use --help for examples.	Ohne Terminal bitte --type angeben. Nutze --help für Beispiele.
type_required	--type is missing. Use --help for an example.	--type fehlt. Nutze --help für ein Beispiel.
action_failed	Action ended with error code %s.	Aktion beendet (Fehlercode %s).
main_terminal_required	The main menu requires a terminal. Use --help for CLI examples.	Das Hauptmenü braucht ein Terminal. Nutze --help für CLI-Beispiele.
main_question	What would you like to do?	Was möchtest du machen?
main_create	Create a new Minecraft server	Neuen Minecraft-Server erstellen
main_manage	Manage an existing server	Vorhandenen Server verwalten
main_help	Show CLI help	CLI-Hilfe anzeigen
main_language	Change language	Sprache ändern
main_exit	Exit	Beenden
goodbye	See you next server.	Bis zum nächsten Server.
manage_arg_error	manage accepts at most one server directory.	manage akzeptiert höchstens einen Server-Ordner.
subcommand_arg_error	%s accepts at most one server directory.	%s akzeptiert höchstens einen Server-Ordner.
logs_usage	logs expects: logs [DIRECTORY] [LINES]	logs erwartet: logs [ORDNER] [ZEILEN]
command_usage	command expects: command DIRECTORY COMMAND	command erwartet: command ORDNER BEFEHL
addon_usage	addon expects at least one server directory.	addon erwartet mindestens einen Server-Ordner.
addon_query_required	Without a terminal, a query is required: addon DIRECTORY QUERY	Ohne Terminal fehlt der Suchbegriff: addon ORDNER SUCHE
unknown_command	Unknown command: %s. Use --help.	Unbekannter Befehl: %s. Nutze --help.
management_terminal_required	The management menu requires a terminal.	Das Management-Menü braucht ein Terminal.
EOF
}

msg() {
  local key="$1" template
  shift
  if [[ "$LANGUAGE" == "de" ]]; then
    template="${TEXT_DE[$key]:-${TEXT_EN[$key]:-$key}}"
  else
    template="${TEXT_EN[$key]:-$key}"
  fi
  printf -- "$template" "$@"
}

msg_line()     { msg "$@"; printf '\n'; }
info_msg()     { local key="$1"; shift; info "$(msg "$key" "$@")"; }
success_msg()  { local key="$1"; shift; success "$(msg "$key" "$@")"; }
warn_msg()     { local key="$1"; shift; warn "$(msg "$key" "$@")"; }
die_msg()      { local key="$1"; shift; die "$(msg "$key" "$@")"; }

info()    { printf '%s[i]%s %s\n' "$C_BLUE" "$C_RESET" "$*" >&2; }
success() { printf '%s[+]%s %s\n' "$C_GREEN" "$C_RESET" "$*" >&2; }
warn()    { printf '%s[!]%s %s\n' "$C_YELLOW" "$C_RESET" "$*" >&2; }
die()     { printf '%s[%s]%s %s\n' "$C_RED" "$(msg error_label)" "$C_RESET" "$*" >&2; exit 1; }

load_messages

cleanup() {
  if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
    rm -rf -- "$TMP_DIR"
  fi
}

trap cleanup EXIT
trap 'exit 130' INT TERM

save_language_config() {
  local config_dir temporary old_umask
  config_dir=$(dirname -- "$CONFIG_FILE")
  if ! mkdir -p -- "$config_dir"; then
    warn_msg config_save_failed "$CONFIG_FILE"
    return 1
  fi

  old_umask=$(umask)
  umask 077
  temporary=$(mktemp "$config_dir/config.XXXXXXXX") || {
    umask "$old_umask"
    warn_msg config_save_failed "$CONFIG_FILE"
    return 1
  }
  {
    printf '%s\n' '# MCSMaker configuration'
    printf 'language=%s\n' "$LANGUAGE"
  } >"$temporary"
  chmod 0600 "$temporary"
  mv -- "$temporary" "$CONFIG_FILE"
  umask "$old_umask"
}

initialize_config() {
  local configured="" choice="" created=0

  if [[ -f "$CONFIG_FILE" ]]; then
    configured=$(sed -n 's/^[[:space:]]*language[[:space:]]*=[[:space:]]*\(en\|de\)[[:space:]]*$/\1/p' \
      "$CONFIG_FILE" | head -n1)
  else
    created=1
  fi

  case "$configured" in
    en|de) LANGUAGE="$configured" ;;
    *) LANGUAGE="en" ;;
  esac

  if [[ -n "${MCSMAKER_LANG:-}" ]]; then
    case "${MCSMAKER_LANG,,}" in
      en|de) LANGUAGE="${MCSMAKER_LANG,,}" ;;
    esac
  elif ((created)) && [[ -t 0 ]]; then
    printf '\nMCSMaker first start / Erster Start\n'
    printf '  1) English (default)\n'
    printf '  2) Deutsch\n'
    printf 'Choice / Auswahl [1]: '
    read -r choice
    case "$choice" in
      2|de|DE|deutsch|Deutsch) LANGUAGE="de" ;;
      *) LANGUAGE="en" ;;
    esac
  fi

  if ((created)) || [[ -z "$configured" ]]; then
    if save_language_config; then
      success_msg config_created "$CONFIG_FILE"
    fi
  fi
}

change_language() {
  local requested="${1:-}" choice=""
  if [[ -z "$requested" ]]; then
    [[ -t 0 ]] || die_msg invalid_language
    printf '\n%s\n' "$(msg choose_language)"
    printf '  1) %s\n' "$(msg english_default)"
    printf '  2) %s\n' "$(msg german)"
    msg choice
    read -r choice
    case "$choice" in
      1|en|EN|english|English) requested="en" ;;
      2|de|DE|deutsch|Deutsch|german|German) requested="de" ;;
      *) warn_msg invalid_choice; return 1 ;;
    esac
  fi

  case "${requested,,}" in
    en|english) LANGUAGE="en" ;;
    de|deutsch|german) LANGUAGE="de" ;;
    *) die_msg invalid_language ;;
  esac
  save_language_config || return 1
  success_msg language_saved
}

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
  if [[ "$LANGUAGE" == "de" ]]; then
    cat <<EOF
MCSMaker ${SCRIPT_VERSION}

Benutzung:
  ./mc-server-maker.sh
  ./mc-server-maker.sh create --type paper --version 26.1.2 --dir ./mein-server --accept-eula
  ./mc-server-maker.sh manage ./mein-server
  ./mc-server-maker.sh start|stop|restart|status|logs|console ./mein-server
  ./mc-server-maker.sh command ./mein-server "say Server läuft!"
  ./mc-server-maker.sh addon ./mein-server "simple voice chat"
  ./mc-server-maker.sh language de|en

Erstellen:
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

Management:
  manage [ORDNER]          Interaktives Server-Menü
  start [ORDNER]           Server im Hintergrund starten
  stop [ORDNER]            Server sauber stoppen
  restart [ORDNER]         Server neustarten
  status [ORDNER]          Server-Status anzeigen
  logs [ORDNER] [ZEILEN]   Konsole/Logs anzeigen
  console [ORDNER]         MCSMaker-Live-Konsole öffnen (/back zum Zurückgehen)
  command ORDNER BEFEHL    Konsolenbefehl senden
  addon ORDNER [SUCHE]     Mod oder Plugin suchen und installieren
  backup [ORDNER]          Server-Backup erstellen
  language [de|en]         Sprache anzeigen oder ändern

Ohne Optionen startet das komplette interaktive Menü.
Keine screen-/tmux-Session: MCSMaker verwaltet einen normalen Linux-Hintergrundprozess.
Config: ${CONFIG_FILE}
EOF
  else
    cat <<EOF
MCSMaker ${SCRIPT_VERSION}

Usage:
  ./mc-server-maker.sh
  ./mc-server-maker.sh create --type paper --version 26.1.2 --dir ./my-server --accept-eula
  ./mc-server-maker.sh manage ./my-server
  ./mc-server-maker.sh start|stop|restart|status|logs|console ./my-server
  ./mc-server-maker.sh command ./my-server "say Server is running!"
  ./mc-server-maker.sh addon ./my-server "simple voice chat"
  ./mc-server-maker.sh language en|de

Create:
  -t, --type TYPE          paper, forge, fabric, or vanilla
  -v, --version VERSION    Minecraft version or "latest" (default)
  -d, --dir PATH           Target directory
      --min-ram VALUE      Initial RAM, for example 1G or 512M
      --max-ram VALUE      Maximum RAM, for example 4G
      --ram VALUE          Short form of --max-ram
      --accept-eula        Explicitly accept the Minecraft EULA
  -f, --force              Allow installation into a non-empty directory
      --skip-java-check    Skip the installed Java version check
  -h, --help               Show this help

Management:
  manage [DIRECTORY]       Interactive server menu
  start [DIRECTORY]        Start server in the background
  stop [DIRECTORY]         Stop server cleanly
  restart [DIRECTORY]      Restart server
  status [DIRECTORY]       Show server status
  logs [DIRECTORY] [LINES] Show console/log output
  console [DIRECTORY]      Open MCSMaker live console (/back to return)
  command DIRECTORY CMD    Send a console command
  addon DIRECTORY [QUERY]  Search for and install a mod or plugin
  backup [DIRECTORY]       Create a server backup
  language [en|de]         Show or change language

With no arguments, the full interactive menu opens.
No screen/tmux session: MCSMaker manages a regular Linux background process.
Config: ${CONFIG_FILE}
EOF
  fi
}

parse_args() {
  while (($#)); do
    case "$1" in
      -t|--type)
        (($# >= 2)) || die_msg missing_value "$1"
        PLATFORM="$2"
        shift 2
        ;;
      --type=*) PLATFORM="${1#*=}"; shift ;;
      -v|--version)
        (($# >= 2)) || die_msg missing_value "$1"
        REQUESTED_VERSION="$2"
        shift 2
        ;;
      --version=*) REQUESTED_VERSION="${1#*=}"; shift ;;
      -d|--dir)
        (($# >= 2)) || die_msg missing_value "$1"
        SERVER_DIR="$2"
        shift 2
        ;;
      --dir=*) SERVER_DIR="${1#*=}"; shift ;;
      --min-ram)
        (($# >= 2)) || die_msg missing_value "$1"
        MIN_RAM="$2"
        shift 2
        ;;
      --min-ram=*) MIN_RAM="${1#*=}"; shift ;;
      --max-ram|--ram)
        (($# >= 2)) || die_msg missing_value "$1"
        MAX_RAM="$2"
        shift 2
        ;;
      --max-ram=*|--ram=*) MAX_RAM="${1#*=}"; shift ;;
      --accept-eula) ACCEPT_EULA=1; shift ;;
      -f|--force) ALLOW_NONEMPTY=1; shift ;;
      --skip-java-check) SKIP_JAVA_CHECK=1; shift ;;
      -h|--help) usage; exit 0 ;;
      --) shift; (($# == 0)) || die_msg unexpected_args "$*" ;;
      -*) die_msg unknown_option "$1" ;;
      *) die_msg unexpected_arg "$1" ;;
    esac
  done
}

choose_interactively() {
  local show_header="${1:-1}" choice input

  if ((show_header)); then
    show_banner
  fi
  msg_line server_type_question
  printf '  1) Paper    - %s\n' "$(msg paper_description)"
  printf '  2) Forge    - %s\n' "$(msg forge_description)"
  printf '  3) Fabric   - %s\n' "$(msg fabric_description)"
  printf '  4) Vanilla  - %s\n' "$(msg vanilla_description)"
  printf '\n%s' "$(msg selection_1_4)"
  read -r choice

  case "$choice" in
    1|paper|Paper) PLATFORM="paper" ;;
    2|forge|Forge) PLATFORM="forge" ;;
    3|fabric|Fabric) PLATFORM="fabric" ;;
    4|vanilla|Vanilla) PLATFORM="vanilla" ;;
    *) die_msg invalid_choice ;;
  esac

  msg mc_version_prompt
  read -r input
  REQUESTED_VERSION="${input:-latest}"

  msg min_ram_prompt
  read -r input
  MIN_RAM="${input:-1G}"

  msg max_ram_prompt
  read -r input
  MAX_RAM="${input:-4G}"

  printf '\nMinecraft-EULA: https://aka.ms/MinecraftEULA\n'
  msg eula_accept_prompt
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
    *) die_msg invalid_platform ;;
  esac
}

normalize_ram() {
  MIN_RAM="${MIN_RAM^^}"
  MAX_RAM="${MAX_RAM^^}"
  [[ "$MIN_RAM" =~ ^[1-9][0-9]*[MG]$ ]] || die_msg invalid_ram "$MIN_RAM"
  [[ "$MAX_RAM" =~ ^[1-9][0-9]*[MG]$ ]] || die_msg invalid_ram "$MAX_RAM"

  local min_mb max_mb
  min_mb=$(ram_to_mb "$MIN_RAM")
  max_mb=$(ram_to_mb "$MAX_RAM")
  ((min_mb <= max_mb)) || die_msg ram_order
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
  if [[ "$LANGUAGE" == "de" ]]; then
    cat >&2 <<'EOF'
Installiere die fehlenden Tools mit deinem Paketmanager, zum Beispiel:
  Debian/Ubuntu: sudo apt update && sudo apt install curl jq
  Fedora:        sudo dnf install curl jq
  Arch:          sudo pacman -S curl jq
EOF
  else
    cat >&2 <<'EOF'
Install the missing tools with your package manager, for example:
  Debian/Ubuntu: sudo apt update && sudo apt install curl jq
  Fedora:        sudo dnf install curl jq
  Arch:          sudo pacman -S curl jq
EOF
  fi
}

check_dependencies() {
  local missing=()
  command -v curl >/dev/null 2>&1 || missing+=(curl)
  command -v jq >/dev/null 2>&1 || missing+=(jq)

  if ((${#missing[@]})); then
    warn_msg missing_programs "${missing[*]}"
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

modrinth_get() {
  local url="$1"
  curl --fail --location --silent --show-error \
    --retry 3 --retry-delay 2 --connect-timeout 20 \
    --proto '=https' -H "User-Agent: $MODRINTH_USER_AGENT" "$url"
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
  [[ -s "$output" ]] || die_msg download_empty "$url"
}

urlencode() {
  jq -nr --arg value "$1" '$value|@uri'
}

validate_jar() {
  local jar="$1" magic
  [[ -s "$jar" ]] || die_msg jar_empty
  magic=$(od -An -tx1 -N2 "$jar" 2>/dev/null | tr -d '[:space:]')
  [[ "$magic" == "504b" ]] || die_msg not_jar
}

verify_checksum() {
  local algorithm="$1" expected="$2" file="$3" command actual
  [[ -n "$expected" && "$expected" != "null" ]] || return 0

  case "$algorithm" in
    sha1) command="sha1sum" ;;
    sha256) command="sha256sum" ;;
    sha512) command="sha512sum" ;;
    *) die_msg unknown_checksum "$algorithm" ;;
  esac

  if ! command -v "$command" >/dev/null 2>&1; then
    warn_msg checksum_tool_missing "$command"
    return 0
  fi

  actual=$("$command" "$file" | awk '{print $1}')
  [[ "${actual,,}" == "${expected,,}" ]] || die_msg checksum_mismatch
  success_msg checksum_ok
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

  [[ -n "$version" && "$version" != "null" ]] || die_msg latest_not_found "$PLATFORM"
  MC_VERSION="$version"
}

resolve_version() {
  if [[ -z "$REQUESTED_VERSION" || "${REQUESTED_VERSION,,}" == "latest" ]]; then
    info_msg latest_search "$PLATFORM"
    resolve_latest_version
  else
    MC_VERSION="$REQUESTED_VERSION"
  fi

  [[ "$MC_VERSION" =~ ^[0-9A-Za-z._+[:space:]-]+$ ]] || die_msg invalid_mc_version "$MC_VERSION"
  success_msg mc_version_selected "$MC_VERSION"
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
      die_msg forge_java_missing "$required"
    fi
    warn_msg java_missing "$required"
    return
  fi

  if ((SKIP_JAVA_CHECK)); then
    warn_msg java_check_skipped
    return
  fi

  installed=$(installed_java_major || true)
  if [[ -z "$installed" ]]; then
    warn_msg java_unknown
    return
  fi

  if ((installed < required)); then
    if [[ "$PLATFORM" == "forge" ]]; then
      die_msg java_too_old "$installed" "$MC_VERSION" "$required"
    fi
    warn_msg java_too_old "$installed" "$MC_VERSION" "$required"
  else
    success_msg java_detected "$installed"
  fi

  if ((required <= 8 && installed > 8)); then
    warn_msg old_java_hint
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
    msg server_dir_prompt "$default_dir"
    read -r answer
    SERVER_DIR="${answer:-$default_dir}"
  elif [[ -z "$SERVER_DIR" ]]; then
    SERVER_DIR="$default_dir"
  fi

  [[ -n "$SERVER_DIR" ]] || die_msg server_dir_empty
  if directory_has_files "$SERVER_DIR"; then
    was_nonempty=1
  fi

  if ((was_nonempty && ! ALLOW_NONEMPTY)); then
    if ((INTERACTIVE)); then
      warn_msg directory_not_empty
      msg continue_anyway
      read -r answer
      case "$answer" in
        j|J|ja|JA|Ja|y|Y|yes|YES|Yes) ALLOW_NONEMPTY=1 ;;
        *) die_msg aborted ;;
      esac
    else
      die_msg nonempty_requires_force
    fi
  fi

  mkdir -p -- "$SERVER_DIR"
  SERVER_DIR=$(cd -- "$SERVER_DIR" && pwd -P)
  [[ "$SERVER_DIR" != "/" ]] || die_msg root_dir_forbidden
  [[ -w "$SERVER_DIR" ]] || die_msg no_write_access "$SERVER_DIR"

  TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/mcsmaker.XXXXXXXX")
  success_msg server_dir_ready "$SERVER_DIR"
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
  warn_msg file_backed_up "$(basename -- "$backup")"
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

  info_msg vanilla_download
  manifest=$(get_vanilla_manifest)
  metadata_url=$(jq -r --arg version "$MC_VERSION" \
    'first(.versions[] | select(.id == $version) | .url) // empty' <<<"$manifest")
  [[ -n "$metadata_url" ]] || die_msg vanilla_not_found "$MC_VERSION"

  metadata=$(http_get "$metadata_url")
  server_url=$(jq -r '.downloads.server.url // empty' <<<"$metadata")
  sha1=$(jq -r '.downloads.server.sha1 // empty' <<<"$metadata")
  [[ -n "$server_url" ]] || die_msg vanilla_no_jar "$MC_VERSION"

  downloaded="$TMP_DIR/vanilla-server.jar"
  download_file "$server_url" "$downloaded"
  verify_checksum sha1 "$sha1" "$downloaded"
  install_server_jar "$downloaded"
  INSTALL_DETAIL="Vanilla $MC_VERSION"
}

install_paper() {
  local encoded builds build channel server_url sha256 downloaded build_id

  info_msg paper_download
  encoded=$(urlencode "$MC_VERSION")
  builds=$(paper_get "$PAPER_API/projects/paper/versions/${encoded}/builds") || \
    die_msg paper_unsupported "$MC_VERSION"

  if jq -e '.ok == false' >/dev/null 2>&1 <<<"$builds"; then
    die "Paper API: $(jq -r --arg fallback "$(msg unknown_error)" '.message // $fallback' <<<"$builds")"
  fi

  build=$(jq -c 'first(.[] | select(.channel == "STABLE")) // .[0] // empty' <<<"$builds")
  [[ -n "$build" ]] || die_msg paper_no_build "$MC_VERSION"

  channel=$(jq -r '.channel // "UNKNOWN"' <<<"$build")
  build_id=$(jq -r --arg unknown "$(msg unknown)" '.id // .number // $unknown' <<<"$build")
  server_url=$(jq -r '.downloads."server:default".url // empty' <<<"$build")
  sha256=$(jq -r '.downloads."server:default".checksums.sha256 // empty' <<<"$build")
  [[ -n "$server_url" ]] || die_msg paper_no_jar

  if [[ "$channel" != "STABLE" ]]; then
    warn_msg paper_unstable "$MC_VERSION" "$channel" "$build_id"
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

  info_msg fabric_search
  encoded=$(urlencode "$MC_VERSION")
  loader_json=$(http_get "$FABRIC_META/versions/loader/${encoded}") || \
    die_msg fabric_unsupported "$MC_VERSION"
  loader=$(jq -r 'first(.[] | select(.loader.stable == true) | .loader.version) // .[0].loader.version // empty' \
    <<<"$loader_json")
  [[ -n "$loader" ]] || die_msg fabric_no_loader "$MC_VERSION"

  installer_json=$(http_get "$FABRIC_META/versions/installer")
  installer=$(jq -r 'first(.[] | select(.stable == true) | .version) // .[0].version // empty' \
    <<<"$installer_json")
  [[ -n "$installer" ]] || die_msg fabric_no_installer

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
    if [[ "$LANGUAGE" == "de" ]]; then
      printf '\n# Von MCSMaker gesetzter Arbeitsspeicher\n'
    else
      printf '\n# Memory configured by MCSMaker\n'
    fi
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

  info_msg forge_search
  promos=$(get_forge_promotions)
  forge_version=$(jq -r --arg key "${MC_VERSION}-recommended" '.promos[$key] // empty' <<<"$promos")
  forge_channel="recommended"
  if [[ -z "$forge_version" ]]; then
    forge_version=$(jq -r --arg key "${MC_VERSION}-latest" '.promos[$key] // empty' <<<"$promos")
    forge_channel="latest"
  fi
  [[ -n "$forge_version" ]] || die_msg forge_unsupported "$MC_VERSION"

  coordinate=$(forge_coordinate "$MC_VERSION" "$forge_version")
  installer_url="$FORGE_MAVEN/${coordinate}/forge-${coordinate}-installer.jar"
  installer="$TMP_DIR/forge-installer.jar"

  info_msg forge_download "$forge_version" "$forge_channel"
  download_file "$installer_url" "$installer" || \
    die_msg forge_installer_missing "$installer_url"
  validate_jar "$installer"

  sha1=""
  if sha1=$(http_get "${installer_url}.sha1" 2>/dev/null); then
    sha1=$(awk '{print $1; exit}' <<<"$sha1")
    verify_checksum sha1 "$sha1" "$installer"
  else
    warn_msg forge_checksum_missing
  fi

  if ((ALLOW_NONEMPTY)); then
    backup_file "$SERVER_DIR/run.sh"
    backup_file "$SERVER_DIR/user_jvm_args.txt"
  fi

  info_msg forge_installing
  if ! (cd -- "$SERVER_DIR" && "$JAVA_COMMAND" -jar "$installer" --installServer); then
    die_msg forge_install_failed
  fi

  mkdir -p -- "$SERVER_DIR/mods"
  if [[ -f "$SERVER_DIR/run.sh" ]]; then
    chmod +x "$SERVER_DIR/run.sh"
    configure_forge_jvm_args
  else
    legacy_jar=$(find_legacy_forge_jar)
    [[ -n "$legacy_jar" ]] || die_msg forge_not_startable
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
    [[ -n "$legacy_jar" ]] || die_msg forge_jar_missing
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
      if [[ "$LANGUAGE" == "de" ]]; then
        printf '# Akzeptiert über MCSMaker nach Hinweis auf https://aka.ms/MinecraftEULA\neula=true\n' >"$target"
      else
        printf '# Accepted through MCSMaker after linking https://aka.ms/MinecraftEULA\neula=true\n' >"$target"
      fi
    fi
    return
  fi

  if ((ACCEPT_EULA)); then
    if [[ "$LANGUAGE" == "de" ]]; then
      printf '# Akzeptiert über MCSMaker nach Hinweis auf https://aka.ms/MinecraftEULA\neula=true\n' >"$target"
    else
      printf '# Accepted through MCSMaker after linking https://aka.ms/MinecraftEULA\neula=true\n' >"$target"
    fi
  else
    if [[ "$LANGUAGE" == "de" ]]; then
      printf '# Lies zuerst https://aka.ms/MinecraftEULA und setze danach eula=true\neula=false\n' >"$target"
    else
      printf '# Read https://aka.ms/MinecraftEULA first, then set eula=true\neula=false\n' >"$target"
    fi
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
    if [[ "$LANGUAGE" == "de" ]]; then
      printf 'RAM: %s bis %s\n' "$MIN_RAM" "$MAX_RAM"
      printf 'Erstellt: %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)"
    else
      printf 'RAM: %s to %s\n' "$MIN_RAM" "$MAX_RAM"
      printf 'Created: %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)"
    fi
  } >"$target"
}

write_machine_metadata() {
  local target="$SERVER_DIR/.mcsmaker.json" temporary="$TMP_DIR/mcsmaker.json"
  jq -n \
    --arg platform "$PLATFORM" \
    --arg minecraft_version "$MC_VERSION" \
    --arg min_ram "$MIN_RAM" \
    --arg max_ram "$MAX_RAM" \
    --arg mcsmaker_version "$SCRIPT_VERSION" \
    --arg created_at "$(date --iso-8601=seconds 2>/dev/null || date)" \
    '{
      schema: 1,
      platform: $platform,
      minecraft_version: $minecraft_version,
      min_ram: $min_ram,
      max_ram: $max_ram,
      mcsmaker_version: $mcsmaker_version,
      created_at: $created_at
    }' >"$temporary"
  backup_file "$target"
  mv -- "$temporary" "$target"
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
  write_machine_metadata
}

pause_menu() {
  [[ -t 0 ]] || return 0
  printf '\n%s' "$(msg pause)"
  read -r _
}

expand_user_path() {
  case "$1" in
    "~") printf '%s\n' "$HOME" ;;
    "~/"*) printf '%s/%s\n' "$HOME" "${1:2}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

discover_servers() {
  local file directory
  local -A seen=()
  DISCOVERED_SERVERS=()

  if [[ -f "$PWD/start.sh" ]]; then
    DISCOVERED_SERVERS+=("$PWD")
    seen["$PWD"]=1
  fi

  while IFS= read -r -d '' file; do
    directory=$(dirname -- "$file")
    directory=$(cd -- "$directory" && pwd -P)
    if [[ -f "$directory/start.sh" && -z "${seen[$directory]:-}" ]]; then
      DISCOVERED_SERVERS+=("$directory")
      seen["$directory"]=1
    fi
  done < <(
    find "$PWD" -mindepth 1 -maxdepth 4 -type f \
      \( -name '.mcsmaker.json' -o -name 'mcsmaker-info.txt' \) -print0 2>/dev/null
  )
}

choose_server_directory() {
  local choice manual index=1
  discover_servers

  printf '\n%s\n' "$(msg found_servers)"
  if ((${#DISCOVERED_SERVERS[@]})); then
    for manual in "${DISCOVERED_SERVERS[@]}"; do
      printf '  %d) %s\n' "$index" "$manual"
      ((index += 1))
    done
  else
    printf '  %s\n' "$(msg none_found_here)"
  fi
  printf '  m) %s\n' "$(msg manual_path)"
  msg choice
  read -r choice

  if [[ "$choice" =~ ^[0-9]+$ ]] && ((choice >= 1 && choice <= ${#DISCOVERED_SERVERS[@]})); then
    SELECTED_SERVER_DIR="${DISCOVERED_SERVERS[choice - 1]}"
    return
  fi

  if [[ "$choice" == "m" || "$choice" == "M" || ${#DISCOVERED_SERVERS[@]} -eq 0 ]]; then
    msg server_path_prompt
    read -r manual
    SELECTED_SERVER_DIR="$manual"
    return
  fi

  die_msg invalid_server_selection
}

load_managed_metadata() {
  local metadata="$MANAGED_SERVER_DIR/.mcsmaker.json" info_file="$MANAGED_SERVER_DIR/mcsmaker-info.txt"
  MANAGED_PLATFORM=""
  MANAGED_VERSION=""

  if [[ -f "$metadata" ]] && jq -e . "$metadata" >/dev/null 2>&1; then
    MANAGED_PLATFORM=$(jq -r '.platform // empty' "$metadata")
    MANAGED_VERSION=$(jq -r '.minecraft_version // empty' "$metadata")
  elif [[ -f "$info_file" ]]; then
    MANAGED_PLATFORM=$(awk -F': ' '/^Server:/ {print tolower($2); exit}' "$info_file" | awk '{print $1}')
    MANAGED_VERSION=$(awk -F': ' '/^Minecraft:/ {print $2; exit}' "$info_file")
  fi

  if [[ -z "$MANAGED_PLATFORM" ]]; then
    if [[ -d "$MANAGED_SERVER_DIR/plugins" ]]; then
      MANAGED_PLATFORM="paper"
    elif [[ -f "$MANAGED_SERVER_DIR/run.sh" && -d "$MANAGED_SERVER_DIR/mods" ]]; then
      MANAGED_PLATFORM="forge"
    elif [[ -d "$MANAGED_SERVER_DIR/mods" ]]; then
      MANAGED_PLATFORM="fabric"
    else
      MANAGED_PLATFORM="unknown"
    fi
  fi

  MANAGED_PLATFORM="${MANAGED_PLATFORM,,}"
  MANAGED_VERSION="${MANAGED_VERSION:-unknown}"
}

set_managed_server() {
  local requested="${1:-}"

  if [[ -z "$requested" ]]; then
    if [[ -t 0 ]]; then
      choose_server_directory
      requested="$SELECTED_SERVER_DIR"
    elif [[ -f "$PWD/start.sh" ]]; then
      requested="$PWD"
    else
      die_msg server_dir_missing
    fi
  fi

  requested=$(expand_user_path "$requested")
  [[ -d "$requested" ]] || die_msg server_dir_not_exist "$requested"
  MANAGED_SERVER_DIR=$(cd -- "$requested" && pwd -P)
  [[ -f "$MANAGED_SERVER_DIR/start.sh" ]] || die_msg start_missing "$MANAGED_SERVER_DIR"
  if [[ ! -x "$MANAGED_SERVER_DIR/start.sh" ]]; then
    chmod +x "$MANAGED_SERVER_DIR/start.sh" || die_msg start_chmod_failed
  fi

  load_managed_metadata
  MANAGED_STATE_DIR="$MANAGED_SERVER_DIR/.mcsmaker"
  MANAGED_PID_FILE="$MANAGED_STATE_DIR/server.pid"
  MANAGED_INPUT_FIFO="$MANAGED_STATE_DIR/console.in"
  MANAGED_CONSOLE_LOG="$MANAGED_STATE_DIR/console.log"
}

require_management_tools() {
  local missing=() tool
  for tool in nohup mkfifo; do
    command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
  done
  if ((${#missing[@]})); then
    warn_msg management_tools_missing "${missing[*]}"
    return 1
  fi
}

server_pid() {
  local pid=""
  [[ -r "$MANAGED_PID_FILE" ]] || return 1
  IFS= read -r pid <"$MANAGED_PID_FILE" || return 1
  [[ "$pid" =~ ^[1-9][0-9]*$ ]] || return 1
  printf '%s\n' "$pid"
}

server_running() {
  local pid process_directory=""
  pid=$(server_pid) || return 1
  kill -0 "$pid" 2>/dev/null || return 1

  if [[ -L "/proc/$pid/cwd" ]]; then
    process_directory=$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)
    [[ -z "$process_directory" || "$process_directory" == "$MANAGED_SERVER_DIR" ]] || return 1
  fi
  return 0
}

clear_runtime_state() {
  [[ -f "$MANAGED_PID_FILE" ]] && rm -f -- "$MANAGED_PID_FILE"
  [[ -p "$MANAGED_INPUT_FIFO" ]] && rm -f -- "$MANAGED_INPUT_FIFO"
  return 0
}

server_start() {
  local pid temporary_pid
  require_management_tools || return 1
  if server_running; then
    warn_msg server_already_running
    return 0
  fi

  if [[ ! -f "$MANAGED_SERVER_DIR/eula.txt" ]] || \
     ! grep -Eq '^[[:space:]]*eula=true[[:space:]]*$' "$MANAGED_SERVER_DIR/eula.txt"; then
    warn_msg eula_not_accepted
    return 1
  fi

  if [[ -L "$MANAGED_STATE_DIR" || ( -e "$MANAGED_STATE_DIR" && ! -d "$MANAGED_STATE_DIR" ) ]]; then
    warn_msg runtime_state_invalid "$MANAGED_STATE_DIR"
    return 1
  fi
  mkdir -p -- "$MANAGED_STATE_DIR"
  chmod 0700 "$MANAGED_STATE_DIR"
  clear_runtime_state
  if [[ -e "$MANAGED_INPUT_FIFO" || -L "$MANAGED_INPUT_FIFO" ]]; then
    backup_file "$MANAGED_INPUT_FIFO"
  fi
  mkfifo -m 0600 "$MANAGED_INPUT_FIFO"
  if [[ -L "$MANAGED_CONSOLE_LOG" || ( -e "$MANAGED_CONSOLE_LOG" && ! -f "$MANAGED_CONSOLE_LOG" ) ]]; then
    backup_file "$MANAGED_CONSOLE_LOG"
  fi
  touch "$MANAGED_CONSOLE_LOG"
  chmod 0600 "$MANAGED_CONSOLE_LOG"
  printf '\n--- MCSMaker %s | %s ---\n' "$SCRIPT_VERSION" "$(date --iso-8601=seconds 2>/dev/null || date)" \
    >>"$MANAGED_CONSOLE_LOG"

  info_msg server_starting
  nohup bash -c '
    cd -- "$1" || exit 1
    exec 3<>"$2"
    exec ./start.sh <&3 >>"$3" 2>&1
  ' mcsmaker "$MANAGED_SERVER_DIR" "$MANAGED_INPUT_FIFO" "$MANAGED_CONSOLE_LOG" \
    >>"$MANAGED_CONSOLE_LOG" 2>&1 &
  pid=$!
  temporary_pid=$(mktemp "$MANAGED_STATE_DIR/server.pid.XXXXXXXX")
  printf '%s\n' "$pid" >"$temporary_pid"
  chmod 0600 "$temporary_pid"
  mv -- "$temporary_pid" "$MANAGED_PID_FILE"
  sleep 1

  if server_running; then
    success_msg server_started
  else
    warn_msg server_crashed
    if [[ -f "$MANAGED_CONSOLE_LOG" ]]; then
      tail -n 40 "$MANAGED_CONSOLE_LOG"
    elif [[ -f "$MANAGED_SERVER_DIR/logs/latest.log" ]]; then
      tail -n 40 "$MANAGED_SERVER_DIR/logs/latest.log"
    fi
    clear_runtime_state
    return 1
  fi
}

send_command_raw() {
  local command="$1"
  server_running || return 1
  [[ -p "$MANAGED_INPUT_FIFO" ]] || { warn_msg command_pipe_missing; return 1; }
  printf '%s\n' "$command" >"$MANAGED_INPUT_FIFO"
}

server_send_command() {
  local command="${1:-}"
  server_running || { warn_msg server_not_running; return 1; }

  if [[ -z "$command" ]]; then
    msg command_prompt
    read -r command
  fi
  [[ -n "$command" ]] || { warn_msg empty_command; return 1; }
  [[ "$command" != *$'\n'* && "$command" != *$'\r'* ]] || { warn_msg multiline_command; return 1; }
  command="${command#/}"

  send_command_raw "$command" || return 1
  success_msg command_sent "$command"
}

server_stop() {
  local answer second pid=""
  if ! server_running; then
    clear_runtime_state
    warn_msg server_not_running
    return 0
  fi

  info_msg server_stopping
  send_command_raw "stop" || return 1
  for ((second = 0; second < 30; second++)); do
    if ! server_running; then
      clear_runtime_state
      success_msg server_stopped
      return 0
    fi
    sleep 1
  done

  warn_msg server_unresponsive
  if [[ -t 0 ]]; then
    msg hard_kill_prompt
    read -r answer
    case "$answer" in
      j|J|ja|JA|Ja|y|Y|yes|YES|Yes)
        pid=$(server_pid || true)
        if [[ -n "$pid" ]] && server_running; then
          kill "$pid" 2>/dev/null || true
          for ((second = 0; second < 5; second++)); do
            server_running || break
            sleep 1
          done
          server_running && kill -KILL "$pid" 2>/dev/null || true
        fi
        clear_runtime_state
        warn_msg session_killed
        return 0
        ;;
    esac
  fi
  return 1
}

server_restart() {
  if server_running; then
    server_stop || return 1
  fi
  server_start
}

server_recent_console() {
  local lines="${1:-100}"
  [[ "$lines" =~ ^[0-9]+$ ]] || lines=100
  ((lines > 0 && lines <= 5000)) || lines=100

  if [[ -f "$MANAGED_CONSOLE_LOG" ]]; then
    tail -n "$lines" "$MANAGED_CONSOLE_LOG"
  elif [[ -f "$MANAGED_SERVER_DIR/logs/latest.log" ]]; then
    server_running || warn_msg showing_latest_log
    tail -n "$lines" "$MANAGED_SERVER_DIR/logs/latest.log"
  else
    warn_msg no_console_log
  fi
}

draw_live_console() {
  local input="$1" notice="$2" columns rows log_lines border output
  columns=$(tput cols 2>/dev/null || printf '80')
  rows=$(tput lines 2>/dev/null || printf '24')
  [[ "$columns" =~ ^[0-9]+$ ]] || columns=80
  [[ "$rows" =~ ^[0-9]+$ ]] || rows=24
  ((columns < 50)) && columns=50
  ((columns > 180)) && columns=180
  log_lines=$((rows - 10))
  ((log_lines < 5)) && log_lines=5
  ((log_lines > 200)) && log_lines=200
  printf -v border '%*s' "$columns" ''
  border=${border// /-}
  if [[ -f "$MANAGED_CONSOLE_LOG" ]]; then
    output=$(tail -n "$log_lines" "$MANAGED_CONSOLE_LOG" 2>/dev/null || true)
  elif [[ -f "$MANAGED_SERVER_DIR/logs/latest.log" ]]; then
    output=$(tail -n "$log_lines" "$MANAGED_SERVER_DIR/logs/latest.log" 2>/dev/null || true)
  else
    output=""
  fi

  printf '\033[2J\033[H'
  printf '%s%s%s  |  %s\n' "$C_BLUE" "$(msg console_title)" "$C_RESET" "$MANAGED_SERVER_DIR"
  printf '%s\n' "$border"
  if [[ -n "$output" ]]; then
    printf '%s\n' "$output" | tail -n "$log_lines"
  else
    printf '%s\n' "$(msg no_console_log)"
  fi
  printf '%s\n' "$border"
  printf '%s\n' "$(msg console_help)"
  printf '%s%s%s\n' "$C_DIM" "$(msg console_back_hint)" "$C_RESET"
  [[ -n "$notice" ]] && printf '%s%s%s\n' "$C_GREEN" "$notice" "$C_RESET"
  printf '> %s' "$input"
}

server_live_console() {
  local input="" key="" notice="" last_refresh=-1 normalized
  server_running || { warn_msg server_not_running; return 1; }
  [[ -t 0 && -t 1 ]] || { warn_msg console_tty_required; return 1; }

  draw_live_console "$input" "$notice"
  last_refresh=$SECONDS
  while server_running; do
    if ((SECONDS != last_refresh)); then
      draw_live_console "$input" "$notice"
      last_refresh=$SECONDS
    fi

    if IFS= read -rsn1 -t 0.15 key; then
      if [[ -z "$key" ]]; then
        normalized="${input,,}"
        case "$normalized" in
          /back|/exit|/quit)
            printf '\033[2J\033[H'
            success_msg console_returned
            return 0
            ;;
          /refresh|"")
            notice=""
            ;;
          /help)
            notice=$(msg console_help_notice)
            ;;
          *)
            if send_command_raw "${input#/}"; then
              notice=$(msg command_sent "${input#/}")
            else
              notice=$(msg console_send_failed)
            fi
            ;;
        esac
        input=""
      elif [[ "$key" == $'\177' || "$key" == $'\b' ]]; then
        input="${input%?}"
      elif [[ "$key" == [[:print:]] ]] && ((${#input} < 500)); then
        input+="$key"
      fi
      draw_live_console "$input" "$notice"
      last_refresh=$SECONDS
    fi
  done

  printf '\033[2J\033[H'
  clear_runtime_state
  warn_msg console_server_ended
  return 0
}

server_status() {
  local state pid="" elapsed="" disk addon_count=0 display_version
  local addon_directories=()
  state=$(msg status_stopped)
  disk=$(msg unknown)
  display_version="$MANAGED_VERSION"
  [[ "$display_version" == "unknown" ]] && display_version=$(msg unknown)
  if server_running; then
    state=$(msg status_running)
    pid=$(server_pid || true)
    if [[ -n "$pid" ]] && command -v ps >/dev/null 2>&1; then
      elapsed=$(ps -o etime= -p "$pid" 2>/dev/null | xargs || true)
    fi
  fi
  command -v du >/dev/null 2>&1 && disk=$(du -sh "$MANAGED_SERVER_DIR" 2>/dev/null | awk '{print $1}')
  [[ -d "$MANAGED_SERVER_DIR/mods" ]] && addon_directories+=("$MANAGED_SERVER_DIR/mods")
  [[ -d "$MANAGED_SERVER_DIR/plugins" ]] && addon_directories+=("$MANAGED_SERVER_DIR/plugins")
  if ((${#addon_directories[@]})); then
    addon_count=$(find "${addon_directories[@]}" -maxdepth 1 -type f -name '*.jar' -print 2>/dev/null | wc -l | tr -d ' ')
  fi

  printf '\n%s\n' "$(msg status_title)"
  printf '  %-11s %s\n' 'Status:' "$state"
  printf '  %-11s %s\n' "$(msg status_type):" "$MANAGED_PLATFORM"
  printf '  %-11s %s\n' "$(msg status_minecraft):" "$display_version"
  printf '  %-11s %s\n' "$(msg status_directory):" "$MANAGED_SERVER_DIR"
  printf '  %-11s %s\n' "$(msg status_size):" "$disk"
  printf '  %-11s %s\n' "$(msg status_addons):" "$addon_count"
  [[ -n "$pid" ]] && printf '  %-11s %s\n' "$(msg status_process):" "$pid"
  [[ -n "$elapsed" ]] && printf '  %-11s %s\n' "$(msg status_uptime):" "$elapsed"
  return 0
}

server_backup() {
  local backup_dir archive timestamp was_running=0 result=0
  command -v tar >/dev/null 2>&1 || { warn_msg tar_missing; return 1; }

  backup_dir="$MANAGED_SERVER_DIR/backups"
  timestamp=$(date +%Y%m%d-%H%M%S)
  archive="$backup_dir/server-backup-${timestamp}.tar.gz"
  mkdir -p -- "$backup_dir"

  if server_running; then
    was_running=1
    info_msg backup_pausing
    if ! send_command_raw "save-off"; then
      warn_msg backup_save_failed
      return 1
    fi
    if ! send_command_raw "save-all flush"; then
      send_command_raw "save-on" || true
      warn_msg backup_save_failed
      return 1
    fi
    sleep 2
  fi

  info_msg backup_creating
  if ! tar --exclude='./backups' --exclude='./logs' --exclude='./cache' \
    --exclude='./.mcsmaker/console.in' --exclude='./.mcsmaker/server.pid' \
    -C "$MANAGED_SERVER_DIR" -czf "$archive" .; then
    result=1
  fi

  if ((was_running)); then
    send_command_raw "save-on" || true
  fi

  if ((result == 0)); then
    success_msg backup_created "$archive"
  else
    warn_msg backup_failed
  fi
  return "$result"
}

configure_addon_type() {
  case "$MANAGED_PLATFORM" in
    paper)
      ADDON_KIND="plugin"
      ADDON_TARGET_DIR="$MANAGED_SERVER_DIR/plugins"
      ADDON_LOADERS_JSON='["paper","purpur","spigot","bukkit","folia"]'
      ADDON_FACETS=$(jq -cn --arg version "$MANAGED_VERSION" '[
        ["all_project_types:plugin"],
        ["categories:paper","categories:purpur","categories:spigot","categories:bukkit","categories:folia"],
        ["versions:\($version)"],
        ["server_side:required","server_side:optional"]
      ]')
      ;;
    fabric)
      ADDON_KIND="mod"
      ADDON_TARGET_DIR="$MANAGED_SERVER_DIR/mods"
      ADDON_LOADERS_JSON='["fabric"]'
      ADDON_FACETS=$(jq -cn --arg version "$MANAGED_VERSION" '[
        ["all_project_types:mod"],
        ["categories:fabric"],
        ["versions:\($version)"],
        ["server_side:required","server_side:optional"]
      ]')
      ;;
    forge)
      ADDON_KIND="mod"
      ADDON_TARGET_DIR="$MANAGED_SERVER_DIR/mods"
      ADDON_LOADERS_JSON='["forge"]'
      ADDON_FACETS=$(jq -cn --arg version "$MANAGED_VERSION" '[
        ["all_project_types:mod"],
        ["categories:forge"],
        ["versions:\($version)"],
        ["server_side:required","server_side:optional"]
      ]')
      ;;
    vanilla)
      warn_msg vanilla_no_addons
      return 1
      ;;
    *)
      warn_msg unknown_server_type
      return 1
      ;;
  esac
}

ensure_temp_directory() {
  if [[ -z "$TMP_DIR" || ! -d "$TMP_DIR" ]]; then
    TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/mcsmaker.XXXXXXXX")
  fi
}

addon_search_install() {
  local query="${1:-}" search_url response count selection selected project_id title
  local versions_url versions version version_number file download_url raw_filename filename sha512 downloaded
  local required_dependencies game_versions_json

  configure_addon_type || return 1
  check_dependencies
  [[ "$MANAGED_VERSION" != "unknown" ]] || { warn_msg mc_version_unknown; return 1; }

  if [[ -z "$query" ]]; then
    msg addon_search_prompt "$(msg "${ADDON_KIND}_label")"
    read -r query
  fi
  [[ -n "$query" ]] || { warn_msg addon_query_empty; return 1; }

  info_msg addon_searching "$(msg "${ADDON_KIND}s_label")" "$MANAGED_PLATFORM" "$MANAGED_VERSION"
  search_url="$MODRINTH_API/search?query=$(urlencode "$query")&facets=$(urlencode "$ADDON_FACETS")&index=downloads&limit=10"
  response=$(modrinth_get "$search_url") || { warn_msg modrinth_search_failed; return 1; }
  count=$(jq '.hits | length' <<<"$response")
  if ((count == 0)); then
    warn_msg no_compatible_hits
    return 1
  fi

  printf '\n%s\n' "$(msg modrinth_results)"
  while IFS=$'\t' read -r selection title download_url raw_filename; do
    printf '  %s) %s  [%s %s]\n     %s\n' \
      "$selection" "$title" "$download_url" "$(msg downloads_label)" "$raw_filename"
  done < <(
    jq -r '.hits | to_entries[] | [
      (.key + 1),
      .value.title,
      .value.downloads,
      (.value.description | gsub("[\\t\\r\\n]+"; " ") | .[0:110])
    ] | @tsv' <<<"$response"
  )
  printf '  0) %s\n' "$(msg cancel)"
  msg choice
  read -r selection
  [[ "$selection" =~ ^[0-9]+$ ]] || { warn_msg invalid_choice; return 1; }
  ((selection == 0)) && return 0
  ((selection >= 1 && selection <= count)) || { warn_msg invalid_choice; return 1; }

  selected=$(jq -c --argjson index "$((selection - 1))" '.hits[$index]' <<<"$response")
  project_id=$(jq -r '.project_id' <<<"$selected")
  title=$(jq -r '.title' <<<"$selected")

  game_versions_json=$(jq -cn --arg version "$MANAGED_VERSION" '[$version]')
  versions_url="$MODRINTH_API/project/$(urlencode "$project_id")/version?loaders=$(urlencode "$ADDON_LOADERS_JSON")&game_versions=$(urlencode "$game_versions_json")&include_changelog=false"
  versions=$(modrinth_get "$versions_url") || { warn_msg versions_failed; return 1; }
  version=$(jq -c 'first(.[] | select(.version_type == "release")) // .[0] // empty' <<<"$versions")
  [[ -n "$version" ]] || { warn_msg no_download_version; return 1; }
  version_number=$(jq -r '.version_number' <<<"$version")
  file=$(jq -c 'first(.files[] | select(.primary == true)) // .files[0] // empty' <<<"$version")
  [[ -n "$file" ]] || { warn_msg version_no_file; return 1; }

  download_url=$(jq -r '.url' <<<"$file")
  raw_filename=$(jq -r '.filename' <<<"$file")
  filename=$(basename -- "$raw_filename")
  sha512=$(jq -r '.hashes.sha512 // empty' <<<"$file")
  [[ "$filename" == *.jar ]] || { warn_msg download_not_jar; return 1; }

  ensure_temp_directory
  downloaded="$TMP_DIR/$filename"
  download_file "$download_url" "$downloaded" "$MODRINTH_USER_AGENT"
  verify_checksum sha512 "$sha512" "$downloaded"
  validate_jar "$downloaded"

  mkdir -p -- "$ADDON_TARGET_DIR" "$MANAGED_SERVER_DIR/.mcsmaker"
  backup_file "$ADDON_TARGET_DIR/$filename"
  mv -- "$downloaded" "$ADDON_TARGET_DIR/$filename"
  chmod 0644 "$ADDON_TARGET_DIR/$filename"
  printf '%s\t%s\t%s\t%s\t%s\n' \
    "$(date --iso-8601=seconds 2>/dev/null || date)" "$project_id" "$title" "$version_number" "$filename" \
    >>"$MANAGED_SERVER_DIR/.mcsmaker/addons.tsv"

  success_msg addon_installed "$title" "$version_number" "$filename"
  required_dependencies=$(jq '[.dependencies[]? | select(.dependency_type == "required" and .project_id != null)] | length' <<<"$version")
  if ((required_dependencies > 0)); then
    warn_msg dependencies_warning "$required_dependencies"
  fi
  if server_running; then
    warn_msg restart_for_addon
  fi
  return 0
}

addon_files() {
  configure_addon_type >/dev/null || return 1
  [[ -d "$ADDON_TARGET_DIR" ]] || return 0
  find "$ADDON_TARGET_DIR" -maxdepth 1 -type f -name '*.jar' -print0 2>/dev/null
}

addon_list() {
  local file count=0
  configure_addon_type || return 1
  printf '\n%s\n' "$(msg installed_addons "$(msg "${ADDON_KIND}s_label")")"
  while IFS= read -r -d '' file; do
    ((count += 1))
    printf '  %d) %s\n' "$count" "$(basename -- "$file")"
  done < <(addon_files)
  ((count > 0)) || printf '  %s\n' "$(msg none_found)"
}

addon_disable() {
  local files=() file selection destination
  configure_addon_type || return 1
  while IFS= read -r -d '' file; do files+=("$file"); done < <(addon_files)
  ((${#files[@]})) || { warn_msg none_to_disable; return 0; }

  printf '\n%s\n' "$(msg disable_addon)"
  for selection in "${!files[@]}"; do
    printf '  %d) %s\n' "$((selection + 1))" "$(basename -- "${files[selection]}")"
  done
  printf '  0) %s\n' "$(msg cancel)"
  msg choice
  read -r selection
  [[ "$selection" =~ ^[0-9]+$ ]] || return 1
  ((selection == 0)) && return 0
  ((selection >= 1 && selection <= ${#files[@]})) || return 1

  file="${files[selection - 1]}"
  mkdir -p -- "$ADDON_TARGET_DIR/disabled"
  destination="$ADDON_TARGET_DIR/disabled/$(basename -- "$file")"
  backup_file "$destination"
  mv -- "$file" "$destination"
  success_msg addon_disabled "$(basename -- "$file")"
  if server_running; then
    warn_msg restart_required
  fi
  return 0
}

addon_enable() {
  local disabled_dir files=() file selection destination
  configure_addon_type || return 1
  disabled_dir="$ADDON_TARGET_DIR/disabled"
  [[ -d "$disabled_dir" ]] || { warn_msg none_disabled; return 0; }
  while IFS= read -r -d '' file; do files+=("$file"); done < <(
    find "$disabled_dir" -maxdepth 1 -type f -name '*.jar' -print0 2>/dev/null
  )
  ((${#files[@]})) || { warn_msg none_disabled; return 0; }

  printf '\n%s\n' "$(msg enable_addon)"
  for selection in "${!files[@]}"; do
    printf '  %d) %s\n' "$((selection + 1))" "$(basename -- "${files[selection]}")"
  done
  printf '  0) %s\n' "$(msg cancel)"
  msg choice
  read -r selection
  [[ "$selection" =~ ^[0-9]+$ ]] || return 1
  ((selection == 0)) && return 0
  ((selection >= 1 && selection <= ${#files[@]})) || return 1

  file="${files[selection - 1]}"
  destination="$ADDON_TARGET_DIR/$(basename -- "$file")"
  backup_file "$destination"
  mv -- "$file" "$destination"
  success_msg addon_enabled "$(basename -- "$file")"
  if server_running; then
    warn_msg restart_required
  fi
  return 0
}

addon_menu() {
  local choice
  while true; do
    printf '\n%s (%s %s)\n' "$(msg addon_manager)" "$MANAGED_PLATFORM" "$MANAGED_VERSION"
    printf '  1) %s\n' "$(msg addon_search_install)"
    printf '  2) %s\n' "$(msg addon_list)"
    printf '  3) %s\n' "$(msg addon_disable)"
    printf '  4) %s\n' "$(msg addon_enable)"
    printf '  0) %s\n' "$(msg back)"
    msg choice
    read -r choice
    case "$choice" in
      1) addon_search_install || true; pause_menu ;;
      2) addon_list || true; pause_menu ;;
      3) addon_disable || true; pause_menu ;;
      4) addon_enable || true; pause_menu ;;
      0) return ;;
      *) warn_msg invalid_choice ;;
    esac
  done
}

manage_server_menu() {
  local choice command
  [[ -t 0 ]] || die_msg management_terminal_required
  while true; do
    server_status
    printf '\n%s\n' "$(msg management_title)"
    printf '  1) %s\n' "$(msg menu_start)"
    printf '  2) %s\n' "$(msg menu_console)"
    printf '  3) %s\n' "$(msg menu_recent)"
    printf '  4) %s\n' "$(msg menu_command)"
    printf '  5) %s\n' "$(msg menu_stop)"
    printf '  6) %s\n' "$(msg menu_restart)"
    printf '  7) %s\n' "$(msg menu_addons)"
    printf '  8) %s\n' "$(msg menu_backup)"
    printf '  0) %s\n' "$(msg back)"
    msg choice
    read -r choice
    case "$choice" in
      1) server_start || true; pause_menu ;;
      2) server_live_console || true ;;
      3) server_recent_console 120 || true; pause_menu ;;
      4)
        msg command_prompt
        read -r command
        server_send_command "$command" || true
        pause_menu
        ;;
      5) server_stop || true; pause_menu ;;
      6) server_restart || true; pause_menu ;;
      7) addon_menu ;;
      8) server_backup || true; pause_menu ;;
      0) return ;;
      *) warn_msg invalid_choice ;;
    esac
  done
}

print_result() {
  local quoted_dir
  printf -v quoted_dir '%q' "$SERVER_DIR"

  printf '\n%s%s%s %s\n' "$C_GREEN" "$(msg finished)" "$C_RESET" "$INSTALL_DETAIL"
  printf '%s: %s\n\n' "$(msg directory_label)" "$SERVER_DIR"
  printf '%s\n  cd %s\n  ./start.sh\n' "$(msg start_instructions)" "$quoted_dir"

  if grep -Eq '^[[:space:]]*eula=true[[:space:]]*$' "$SERVER_DIR/eula.txt"; then
    printf '\n%s\n' "$(msg eula_accepted)"
  else
    printf '\n%s%s%s\n' "$C_YELLOW" "$(msg eula_pending)" "$C_RESET"
    msg_line eula_edit
  fi

  if [[ "$PLATFORM" == "paper" ]]; then
    msg_line plugins_directory "$SERVER_DIR"
  elif [[ "$PLATFORM" == "forge" || "$PLATFORM" == "fabric" ]]; then
    msg_line mods_directory "$SERVER_DIR"
  fi
}

reset_creation_options() {
  cleanup
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
}

create_server_workflow() {
  normalize_platform
  normalize_ram
  if ((EUID == 0)); then
    warn_msg root_warning
  fi
  check_dependencies
  resolve_version
  check_java
  prepare_server_directory

  info_msg installing "$PLATFORM" "$MC_VERSION"
  install_selected_server
  success_msg install_complete
  print_result
  cleanup
  TMP_DIR=""
}

create_server_main() {
  reset_creation_options
  if (($# == 0)); then
    [[ -t 0 ]] || die_msg terminal_type_required
    INTERACTIVE=1
    choose_interactively
  else
    parse_args "$@"
    [[ -n "$PLATFORM" ]] || die_msg type_required
  fi
  create_server_workflow
}

interactive_create_action() {
  reset_creation_options
  INTERACTIVE=1
  choose_interactively 0
  create_server_workflow
}

interactive_manage_action() {
  set_managed_server
  manage_server_menu
}

run_menu_action() {
  local result
  set +e
  (set -e; "$@")
  result=$?
  set -e
  if ((result != 0)); then
    warn_msg action_failed "$result"
  fi
  return 0
}

main_menu() {
  local choice
  [[ -t 0 ]] || die_msg main_terminal_required

  while true; do
    show_banner
    msg_line main_question
    printf '  1) %s\n' "$(msg main_create)"
    printf '  2) %s\n' "$(msg main_manage)"
    printf '  3) %s\n' "$(msg main_help)"
    printf '  4) %s\n' "$(msg main_language)"
    printf '  0) %s\n' "$(msg main_exit)"
    printf '\n%s' "$(msg choice)"
    read -r choice
    case "$choice" in
      1) run_menu_action interactive_create_action; pause_menu ;;
      2) run_menu_action interactive_manage_action; pause_menu ;;
      3) usage; pause_menu ;;
      4) change_language || true; pause_menu ;;
      0) success_msg goodbye; return ;;
      *) warn_msg invalid_choice; pause_menu ;;
    esac
  done
}

run_management_command() {
  local subcommand="$1" directory="" lines="100" command="" query=""
  shift

  case "$subcommand" in
    manage)
      (($# <= 1)) || die_msg manage_arg_error
      set_managed_server "${1:-}"
      manage_server_menu
      ;;
    start|stop|restart|status|console|backup)
      (($# <= 1)) || die_msg subcommand_arg_error "$subcommand"
      set_managed_server "${1:-}"
      case "$subcommand" in
        start) server_start ;;
        stop) server_stop ;;
        restart) server_restart ;;
        status) server_status ;;
        console) server_live_console ;;
        backup) server_backup ;;
      esac
      ;;
    logs)
      if (($# > 0)) && [[ "$1" =~ ^[0-9]+$ ]] && [[ -f "$PWD/start.sh" ]]; then
        lines="$1"
        shift
      else
        directory="${1:-}"
        (($# == 0)) || shift
        lines="${1:-100}"
        (($# <= 1)) || die_msg logs_usage
      fi
      set_managed_server "$directory"
      server_recent_console "$lines"
      ;;
    command)
      (($# >= 2)) || die_msg command_usage
      directory="$1"
      shift
      command="$*"
      set_managed_server "$directory"
      server_send_command "$command"
      ;;
    addon)
      (($# >= 1)) || die_msg addon_usage
      directory="$1"
      shift
      query="$*"
      if [[ -z "$query" && ! -t 0 ]]; then
        die_msg addon_query_required
      fi
      set_managed_server "$directory"
      addon_search_install "$query"
      ;;
  esac
}

main() {
  if (($# == 0)); then
    main_menu
    return
  fi

  case "$1" in
    -h|--help|help)
      usage
      ;;
    language|lang)
      shift
      (($# <= 1)) || die_msg invalid_language
      if (($# == 0)); then
        if [[ "$LANGUAGE" == "de" ]]; then
          msg_line current_language "$(msg german_name)"
        else
          msg_line current_language "$(msg english_name)"
        fi
      else
        change_language "$1"
      fi
      ;;
    create)
      shift
      create_server_main "$@"
      ;;
    manage|start|stop|restart|status|logs|console|command|addon|backup)
      run_management_command "$@"
      ;;
    -*)
      create_server_main "$@"
      ;;
    *)
      die_msg unknown_command "$1"
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  initialize_config
  main "$@"
fi
