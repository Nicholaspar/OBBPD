# ================================================================
#  Copyright © 2025 Nicholas Parfitt
#  All rights reserved.
#
#  This software is NOT open source.
#  You may NOT:
#    - Copy or reproduce any part of this code
#    - Modify, distribute, or share this software
#    - Use this code in any commercial or personal project
#      without explicit written permission from the author
#
#  Unauthorized use or distribution is strictly prohibited
#  and may result in legal action.
#
#  For permissions or inquiries, contact: Nicholas Parfitt
#
#  Version: V2.0 (TURBO BATCH MODE UPDATE)
# ================================================================

# ------------------------------------------------------
#  1. IMPORTS & PLATFORM DETECTION
# ------------------------------------------------------

import os
import sys
import time
import subprocess
import threading
import queue
from pathlib import Path
from datetime import datetime
import csv
from io import StringIO
import configparser
import shutil
import re

try:
    import msvcrt
    WINDOWS = True
except ImportError:
    WINDOWS = False
    import select
    import tty
    import termios

# ------------------------------------------------------
#  2. CONSTANTS & COLOR CODES
# ------------------------------------------------------

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
GRAY   = "\033[90m"

# ------------------------------------------------------
#  3. SCRIPT DIRECTORY & TITLE BANNER
# ------------------------------------------------------

def get_script_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent

SCRIPT_DIR = get_script_dir()

def print_fancy_title():
    title = r"""
  ___  ____  ____  ____  ____  
 / _ \| __ )| __ )|  _ \|  _ \ 
| | | |  _ \|  _ \| |_) | | | |
| |_| | |_) | |_) |  __/| |_| |
 \___/|____/|____/|_|   |____/ 
"""
    print(f"\n{CYAN}{title}{RESET}\n")

print_fancy_title()

# ------------------------------------------------------
#  4. CONFIGURATION SECTION
# ------------------------------------------------------

CONFIG_FILE = SCRIPT_DIR / "obbpd_config.ini"
config = configparser.ConfigParser()

if not CONFIG_FILE.exists():
    config['Settings'] = {
        'wait_seconds': '11',
        'after_close_delay': '3',
        'batch_size': '10',
        'truncate_length': '25',
        'turbo_mode': 'False',
        'turbo_batch_mode': 'True'  # Added default for turbo batch mode enabled
    }
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)
    print(f"{YELLOW}Created default config file: {CONFIG_FILE}{RESET}")

config.read(CONFIG_FILE)

if not config.sections():
    print(f"{RED}[ERROR] Failed to load configuration from '{CONFIG_FILE}'.{RESET}")
    input("Press Enter to exit…")
    sys.exit(1)

SHOW_LOAD_ORDER_PER_BATCH = config.getboolean('debug', 'show_load_order_per_batch', fallback=False)

def get_config_int(section, key, default):
    try:
        return int(config.get(section, key, fallback=str(default)))
    except ValueError:
        return default

WAIT_SECONDS     = get_config_int("Settings", "wait_seconds",       11)
AFTER_CLOSE_DELAY= get_config_int("Settings", "after_close_delay",  3)
BATCH_SIZE       = get_config_int("Settings", "batch_size",         10)
TRUNCATE_LENGTH  = get_config_int("Settings", "truncate_length",    25)
TURBO_MODE       = config.getboolean("Settings", "turbo_mode",      fallback=False)
TURBO_BATCH_MODE = config.getboolean("Settings", "turbo_batch_mode", fallback=False)

print(f"{CYAN}[CONFIG LOADED]{RESET}")
print(f"{BOLD}wait_seconds:      {WAIT_SECONDS}{RESET}")
print(f"{BOLD}after_close_delay: {AFTER_CLOSE_DELAY}{RESET}")
print(f"{BOLD}batch_size:        {BATCH_SIZE}{RESET}")
print(f"{BOLD}truncate_length:   {TRUNCATE_LENGTH}{RESET}")
print(f"{BOLD}turbo_mode:        {TURBO_MODE}{RESET}")
print(f"{BOLD}turbo_batch_mode:  {TURBO_BATCH_MODE}{RESET}\n")

# ------------------------------------------------------
#  5. PATHS, SESSIONS, AND PLUGIN LISTS
# ------------------------------------------------------

TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
SESSION_BACKUP_DIR = SCRIPT_DIR / "Backups" / f"session_{TIMESTAMP}"
SESSION_LOG_DIR    = SCRIPT_DIR / "Logs"   / f"session_{TIMESTAMP}"
QUARANTINE_DIR     = SCRIPT_DIR / "Quarantine"
ORIGINAL_BACKUP    = SESSION_BACKUP_DIR / "plugins_original_backup.txt"
RESULT_LOG         = SESSION_LOG_DIR    / "plugin_test_results.txt"

PLUGIN_FILE           = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Oblivion Remastered\OblivionRemastered\Content\Dev\ObvData\Data\plugins.txt")
GAME_EXE              = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Oblivion Remastered\OblivionRemastered\Binaries\Win64\obse64_loader.exe")
GAME_PROCESS_NAME     = "OblivionRemastered-Win64-Shipping.exe"

def parse_plugin_list(raw):
    return [p.strip() for p in raw.split(",") if p.strip()]

required_plugins_raw = config.get("CorePlugins", "required", fallback="")
optional_plugins_raw = config.get("CorePlugins", "optional", fallback="")

REQUIRED_PLUGINS = parse_plugin_list(required_plugins_raw) or [
    "Oblivion.esm", "DLCBattlehornCastle.esp", "DLCFrostcrag.esp", "DLCHorseArmor.esp",
    "DLCMehrunesRazor.esp", "DLCOrrery.esp", "DLCShiveringIsles.esp", "DLCSpellTomes.esp",
    "DLCThievesDen.esp", "DLCVileLair.esp", "Knights.esp", "AltarESPMain.esp", "AltarDeluxe.esp"
]
OPTIONAL_PATCHES = parse_plugin_list(optional_plugins_raw) or [
    "Unofficial Oblivion Remastered Patch.esp",
    "Unofficial Oblivion Remastered Patch - Deluxe.esp"
]
PATCH_KEYWORDS = ["patch", "fix", "compat", "merge"]

# ------------------------------------------------------
#  6. DIRECTORY & LOGGING SETUP
# ------------------------------------------------------

def ensure_dirs():
    SESSION_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_LOG_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
ensure_dirs()

log_queue    = queue.Queue()
log_shutdown = threading.Event()

def background_log_writer():
    RESULT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with RESULT_LOG.open("a", encoding="utf-8") as f:
        while not log_shutdown.is_set() or not log_queue.empty():
            try:
                msg = log_queue.get(timeout=0.1)
                f.write(msg + "\n")
                f.flush()
            except queue.Empty:
                continue

log_thread = threading.Thread(target=background_log_writer, daemon=True)
log_thread.start()

def log(text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_queue.put(f"[{timestamp}] {text}")

def shutdown_logging():
    log_shutdown.set()
    if log_thread.is_alive():
        log_thread.join(timeout=5)

# ------------------------------------------------------
#  7. GENERAL UTILITY FUNCTIONS
# ------------------------------------------------------

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def backup_original_plugins():
    if not ORIGINAL_BACKUP.exists() and PLUGIN_FILE.exists():
        try:
            ORIGINAL_BACKUP.write_text(PLUGIN_FILE.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"{GREEN}[BACKUP] Created backup of original plugins.txt{RESET}")
        except Exception as e:
            print(f"{RED}[ERROR] Failed to backup plugins.txt: {e}{RESET}")
            return False
    return True

def restore_latest_backup():
    backup_base = SCRIPT_DIR / "Backups"
    if not backup_base.exists():
        print(f"{RED}[No backup directory found.]{RESET}")
        if input("Continue without restoring backup? (y/n): ").strip().lower() != "y":
            shutdown_logging()
            sys.exit(0)
        return
    sessions = sorted(backup_base.glob("session_*"), reverse=True)
    if not sessions:
        print(f"{RED}[No backup sessions found.]{RESET}")
        if input("Continue without restoring backup? (y/n): ").strip().lower() != "y":
            shutdown_logging()
            sys.exit(0)
        return
    for session in sessions:
        backup_file = session / "plugins_original_backup.txt"
        if backup_file.exists():
            print(f"{YELLOW}Found a previous backup from {session.name}.{RESET}")
            if input("Restore it? (y/n): ").strip().lower() == "y":
                try:
                    PLUGIN_FILE.write_text(backup_file.read_text(encoding="utf-8"), encoding="utf-8")
                    print(f"{GREEN}[Restored] plugins.txt from {session.name}{RESET}")
                except Exception as e:
                    print(f"{RED}[ERROR] Failed to restore backup: {e}{RESET}")
            else:
                print("[Info] Skipped restoration.")
            break
    else:
        print(f"{RED}[No valid backup file found in sessions.]{RESET}")
        if input("Continue without restoring backup? (y/n): ").strip().lower() != "y":
            print(f"{YELLOW}Exiting…{RESET}")
            shutdown_logging()
            sys.exit(0)

def read_plugins(path):
    try:
        return [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
                if line.strip() and not line.startswith("#")]
    except Exception as e:
        print(f"{RED}[ERROR] Failed to read plugins from {path}: {e}{RESET}")
        return []

def write_plugins(current_plugins):
    try:
        if ORIGINAL_BACKUP.exists():
            original_lines = ORIGINAL_BACKUP.read_text(encoding="utf-8").splitlines()
        else:
            original_lines = []
            print(f"{RED}[ERROR] No original backup found.{RESET}")

        original_plugins = [line.strip() for line in original_lines if line.strip() and not line.strip().startswith("#")]
        comments         = [line for line in original_lines if line.strip().startswith("#")]

        detected_required = [p for p in REQUIRED_PLUGINS if p in original_plugins or p in current_plugins]
        detected_optional = [p for p in OPTIONAL_PATCHES if p in original_plugins or p in current_plugins]
        full_required     = detected_required + detected_optional

        all_to_write      = full_required + [p for p in current_plugins if p not in full_required]
        required_plugins  = [p for p in all_to_write if p in detected_required]
        optional_plugins  = [p for p in all_to_write if p in detected_optional]

        written_plugins = set()
        output_lines    = []

        for line in original_lines:
            stripped = line.strip()
            if not stripped:
                output_lines.append("")
            elif stripped.startswith("#"):
                output_lines.append(line)
            elif stripped in all_to_write and stripped not in written_plugins:
                output_lines.append(stripped)
                written_plugins.add(stripped)
        for plugin in required_plugins:
            if plugin not in written_plugins:
                output_lines.append(plugin)
                written_plugins.add(plugin)
        for plugin in optional_plugins:
            if plugin not in written_plugins:
                output_lines.append(plugin)
                written_plugins.add(plugin)

        PLUGIN_FILE.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
        return True
    except Exception as e:
        print(f"{RED}[ERROR] Failed to write plugins.txt: {e}{RESET}")
        return False

def write_plugins_exact(plugin_list):
    try:
        PLUGIN_FILE.write_text("\n".join(plugin_list) + "\n", encoding="utf-8")
        return True
    except Exception as e:
        print(f"{RED}[ERROR] Failed to write plugins.txt in enforced order: {e}{RESET}")
        return False

def enforce_exact_load_order():
    ordered_required = [p.strip() for p in REQUIRED_PLUGINS]
    ordered_optional = [p.strip() for p in OPTIONAL_PATCHES]

    all_current   = read_plugins(PLUGIN_FILE)
    extra_plugins = [
        p for p in all_current
        if p.lower().strip() not in [x.lower() for x in ordered_required + ordered_optional]
    ]
    enforced_order = ordered_required + ordered_optional + extra_plugins

    seen = set()
    final_order = []
    for p in enforced_order:
        norm = p.lower().strip()
        if norm not in seen and p:
            final_order.append(p)
            seen.add(norm)
    write_plugins_exact(final_order)

def get_total_plugins(plugin_path):
    """
    Reads a plugins.txt file and returns a deduped list of all plugin filenames,
    ignoring comments and blank lines.
    """
    try:
        lines = plugin_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        plugins = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
        seen = set()
        deduped = []
        for p in plugins:
            pl = p.lower()
            if pl not in seen:
                deduped.append(p)
                seen.add(pl)
        return deduped
    except Exception as e:
        print(f"{RED}[ERROR] Counting total plugins: {e}{RESET}")
        return []

def get_batch_size(size):
    return (
        25 if size >= 200 else
        20 if size >= 150 else
        15 if size >= 100 else
        10 if size >=  50 else
         5 if size >=  20 else
         3 if size >=  10 else
         2 if size >=   5 else
         1
    )


# ------------------------------------------------------
#  8. GAME PROCESS HANDLING (CRASH DETECT, PAUSE, ETC)
# ------------------------------------------------------

def get_game_pid():
    try:
        if not WINDOWS:
            result = subprocess.run(
                ["pgrep", "-f", GAME_PROCESS_NAME],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
            return None
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {GAME_PROCESS_NAME}", "/FO", "CSV"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return None
        reader = csv.reader(StringIO(result.stdout))
        next(reader, None)
        for row in reader:
            if row and len(row) > 1 and row[0].strip('"').lower() == GAME_PROCESS_NAME.lower():
                return row[1].strip('"')
        return None
    except Exception:
        return None

def force_close_game():
    try:
        pid = get_game_pid()
        if pid:
            if WINDOWS:
                subprocess.run(["taskkill", "/PID", pid, "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["kill", "-9", pid],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            if WINDOWS:
                subprocess.run(["taskkill", "/IM", GAME_PROCESS_NAME, "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["pkill", "-f", GAME_PROCESS_NAME],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if WINDOWS:
            subprocess.run(["taskkill", "/IM", "CrashReportClient.exe", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        time.sleep(0.1 if TURBO_MODE else 0.3)
        if AFTER_CLOSE_DELAY > 0:
            time.sleep(AFTER_CLOSE_DELAY)

    except Exception as e:
        print(f"{RED}[ERROR] Failed to close game/crash-reporter: {e}{RESET}")

def kbhit():
    if WINDOWS:
        return msvcrt.kbhit()
    else:
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        return bool(dr)

def getch():
    if WINDOWS:
        return msvcrt.getch().decode("utf-8", errors="ignore")
    else:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.cbreak(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

def check_for_manual_pause():
    print(f"{GRAY}→ Press any key to pause…{RESET}", end="\r", flush=True)
    if kbhit():
        getch()
        print(f"\n{YELLOW}[PAUSED] Closing game…{RESET}")
        force_close_game()
        print(f"\n{BOLD}[PAUSED] Game was closed.{RESET}")
        print("What would you like to do?\n")
        print(f"{BOLD}[R]{RESET} Resume testing")
        print(f"{BOLD}[V]{RESET} Revert plugins.txt and quit")
        print(f"{BOLD}[Q]{RESET} Quit without reverting")
        while True:
            if kbhit():
                choice = getch().lower()
                if choice == "r":
                    print(f"{GREEN}[RESUMING] Relaunching game…{RESET}")
                    raise RuntimeError("manual_pause_triggered")
                elif choice == "v":
                    if ORIGINAL_BACKUP.exists():
                        try:
                            PLUGIN_FILE.write_text(ORIGINAL_BACKUP.read_text(encoding="utf-8"), encoding="utf-8")
                            print(f"{YELLOW}Reverted plugins.txt to original.{RESET}")
                        except Exception as e:
                            print(f"{RED}Failed to revert: {e}{RESET}")
                    shutdown_logging()
                    sys.exit(0)
                elif choice == "q":
                    print(f"{YELLOW}Exiting without restoring plugins.txt.{RESET}")
                    shutdown_logging()
                    sys.exit(0)
                else:
                    print(f"{RED}Invalid key: '{choice.upper()}'. Press R, V, or Q.{RESET}")

def launch_game():
    try:
        if not GAME_EXE.exists():
            print(f"{RED}[ERROR] Game executable not found: {GAME_EXE}{RESET}")
            return False
        subprocess.Popen([str(GAME_EXE)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.2 if TURBO_MODE else 0.5)
        return True
    except Exception as e:
        print(f"{RED}[ERROR] Failed to launch game: {e}{RESET}")
        return False

def wait_and_check_crash():
    start = time.time()
    for _ in range(30):
        if get_game_pid():
            break
        time.sleep(0.1)
    else:
        print(f"{RED}Game failed to launch. Treating as crash.{RESET}")
        force_close_game()
        return True
    while time.time() - start < WAIT_SECONDS:
        try:
            check_for_manual_pause()
        except RuntimeError as e:
            if str(e) == "manual_pause_triggered":
                raise
        if not get_game_pid():
            force_close_game()
            return True
        time.sleep(0.1 if TURBO_MODE else 0.25)
    force_close_game()
    return False

# ------------------------------------------------------
#  9. BATCH & PLUGIN FILTERING LOGIC
# ------------------------------------------------------

def filter_plugins(all_plugins, skip_keywords=True):
    return [p for p in all_plugins if p.endswith(".esp") and p not in REQUIRED_PLUGINS and
            (not skip_keywords or not any(k in p.lower() for k in PATCH_KEYWORDS))]

def get_patch_plugins(all_plugins):
    return [p for p in all_plugins if any(k in p.lower() for k in PATCH_KEYWORDS)]

# ------------------------------------------------------
#  10. TERMINAL DISPLAY & UI
# ------------------------------------------------------

def sanitize_name(name: str) -> str:
    return name.replace('_', ' ').replace('-', ' ')

def center_colored(text, width):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    visible = ansi_escape.sub('', text)
    padding = max(0, (width - len(visible)) // 2)
    return ' ' * padding + text

def print_display(testing, passed, failed, total_plugins_list, turbo=False):
    clear_screen()
    term_w = shutil.get_terminal_size((80,20)).columns

    if turbo:
        turbo_banner = f"{BOLD}{YELLOW}Turbo Batch Mode: Active{RESET}"
        banner_len = len("Turbo Batch Mode: Active")
        print(" " * max(0, term_w - banner_len - 2) + turbo_banner)

    disp_t = testing[-20:]
    disp_p = passed[-20:]
    disp_f = failed[-20:]
    total = len(total_plugins_list)
    total_passed = len([p for p in passed if p in total_plugins_list])
    total_failed = len([p for p in failed if p in total_plugins_list])
    total_tested = total_passed + total_failed
    remaining    = max(0, total - total_tested)
    print(center_colored(f"{BOLD}{CYAN}Total plugins to Test: {total}{RESET}", term_w))
    status = (
        f"{BOLD}{YELLOW}Tested: {total_tested}  "
        f"{GREEN}Passed: {total_passed}  "
        f"{RED}Failed: {total_failed}  "
        f"{CYAN}Remaining: {remaining}{RESET}"
    )
    print(center_colored(status, term_w))
    print()
    print(f"{BOLD}{GRAY}Currently Testing Batch Size: {len(testing)}{RESET}\n")
    col = 40
    print(f"{BOLD}{'Testing':<{col}}{'Recently Passed':<{col}}{'Failed':<{col}}{RESET}")
    max_len = max(len(disp_t), len(disp_p), len(disp_f))
    def short(name):
        return name if len(name) <= TRUNCATE_LENGTH else name[:TRUNCATE_LENGTH-3] + "..."
    for i in range(max_len):
        t = short(sanitize_name(disp_t[i])) if i < len(disp_t) else ""
        p = short(sanitize_name(disp_p[i])) if i < len(disp_p) else ""
        f = short(sanitize_name(disp_f[i])) if i < len(disp_f) else ""
        print(f"{CYAN}{t:<{col}}{GREEN}{p:<{col}}{RED}{f:<{col}}{RESET}")
    print()

# ------------------------------------------------------
#  Helper: Show final summary and user prompt for quarantine/revert/exit
# ------------------------------------------------------

def show_final_summary_and_prompt(safe, failed):
    clear_screen()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{BOLD}{CYAN}Summary: {GREEN}✅ {len(safe)} passed{RESET}, {RED}❌ {len(failed)} failed{RESET}\n")
    print(f"{BOLD}{GREEN}=== ✅ PASSED PLUGINS ==={RESET}\n{GRAY}🕓 [{ts}]{RESET}")
    if safe:
        for p in safe:
            print(f"{GREEN}{p}{RESET}")
    else:
        print("None")
    print(f"\n{BOLD}{RED}=== ❌ CRASHED PLUGINS ==={RESET}\n{GRAY}🕓 [{ts}]{RESET}")
    if failed:
        for p in failed:
            print(f"{RED}{p}{RESET}")
    else:
        print("None")
    print()

    if failed:
        print(f"{YELLOW}What now?{RESET}")
        print(f"{BOLD}[Q]{RESET} Quarantine failed plugins")
        print(f"{BOLD}[R]{RESET} Revert to original plugins.txt")
        print(f"{BOLD}[E]{RESET} Exit without changes")
        while True:
            choice = input(f"{BOLD}Enter Q, R, or E: {RESET}").strip().lower()
            if choice == "q":
                qp = QUARANTINE_DIR / f"session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
                qp.mkdir(parents=True, exist_ok=True)
                for plugin in failed:
                    src = PLUGIN_FILE.parent / plugin
                    dst = qp / plugin
                    if src.exists():
                        try:
                            shutil.move(str(src), str(dst))
                            print(f"{RED}→ Quarantined: {plugin}{RESET}")
                            log(f"Quarantined: {plugin}")
                        except Exception as e:
                            print(f"{RED}→ Failed to quarantine {plugin}: {e}{RESET}")
                            log(f"Failed to quarantine {plugin}: {e}")
                    else:
                        print(f"{RED}→ Missing: {src}{RESET}")
                        log(f"Missing for quarantine: {plugin}")
                print(f"{GREEN}Quarantine complete.{RESET}")
                break
            elif choice == "r":
                if ORIGINAL_BACKUP.exists():
                    try:
                        PLUGIN_FILE.write_text(ORIGINAL_BACKUP.read_text(encoding="utf-8"), encoding="utf-8")
                        print(f"{YELLOW}Restored original plugins.txt.{RESET}")
                        log("Reverted to original")
                    except Exception as e:
                        print(f"{RED}Restore failed: {e}{RESET}")
                else:
                    print(f"{RED}No original backup.{RESET}")
                break
            elif choice == "e":
                print(f"{YELLOW}Exiting…{RESET}")
                break
            else:
                print(f"{RED}Invalid. Enter Q, R, or E.{RESET}")

# ------------------------------------------------------
#  11. BATCH AND SUB-BATCH LOGIC
# ------------------------------------------------------

def run_batch(batch, safe, tested, failed, total_plugins_list):
    if ORIGINAL_BACKUP.exists():
        backup_lines = ORIGINAL_BACKUP.read_text(encoding="utf-8").splitlines()
    else:
        backup_lines = []
    ordered = list(REQUIRED_PLUGINS) + list(OPTIONAL_PATCHES)
    ordered += [p for p in safe if p not in ordered]
    ordered += batch
    deduped = []
    seen = set()
    for p in ordered:
        key = p.lower().strip()
        if key and key not in seen:
            deduped.append(p)
            seen.add(key)
    try:
        PLUGIN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with PLUGIN_FILE.open("w", encoding="utf-8") as f:
            for line in backup_lines:
                if not line.strip() or line.strip().startswith("#"):
                    f.write(line + "\n")
            for plugin in deduped:
                f.write(plugin + "\n")
    except Exception as e:
        print(f"{RED}[ERROR] Failed to write plugins for batch test: {e}{RESET}")
        return
    print_display(batch, safe, failed, total_plugins_list)
    if not launch_game():
        print(f"{RED}[ERROR] Failed to launch game for batch test{RESET}")
        return
    try:
        crashed = wait_and_check_crash()
    except RuntimeError as e:
        if str(e) == "manual_pause_triggered":
            return run_batch(batch, safe, tested, failed, total_plugins_list)
        else:
            raise
    if not crashed:
        log(f"Safe: {', '.join(batch)}")
        safe.extend(batch)
        tested.extend(batch)
        print_display([], safe, failed, total_plugins_list)
        return
    log(f"Crash: {batch}")
    size = len(batch)
    sub_size = get_batch_size(size)
    for i in range(0, size, sub_size):
        sub = batch[i : i + sub_size]
        ordered_sub = list(REQUIRED_PLUGINS) + list(OPTIONAL_PATCHES)
        ordered_sub += [p for p in safe if p not in ordered_sub]
        ordered_sub += sub
        deduped_sub = []
        seen_sub = set()
        for p in ordered_sub:
            key = p.lower().strip()
            if key and key not in seen_sub:
                deduped_sub.append(p)
                seen_sub.add(key)
        try:
            with PLUGIN_FILE.open("w", encoding="utf-8") as f:
                for line in backup_lines:
                    if not line.strip() or line.strip().startswith("#"):
                        f.write(line + "\n")
                for plugin in deduped_sub:
                    f.write(plugin + "\n")
        except Exception as e:
            print(f"{RED}[ERROR] Failed to write plugins for sub-batch: {e}{RESET}")
            continue
        print_display(sub, safe, failed, total_plugins_list)
        if not launch_game(): break
        try:
            sub_crash = wait_and_check_crash()
        except RuntimeError as e:
            if str(e) == "manual_pause_triggered":
                print(f"{YELLOW}[RESUMED] Retrying sub-batch…{RESET}")
                time.sleep(1)
                sub_crash = True
            else:
                raise
        if not sub_crash:
            log(f"Safe: {', '.join(sub)}")
            safe.extend(sub)
            tested.extend(sub)
            print_display([], safe, failed, total_plugins_list)
        else:
            if len(sub) == 1:
                plugin = sub[0]
                log(f"Broken: {plugin}")
                if plugin not in failed: failed.append(plugin)
                if plugin not in tested: tested.append(plugin)
                print_display([], safe, failed, total_plugins_list)
            else:
                for plugin in sub:
                    ordered_one = list(REQUIRED_PLUGINS) + list(OPTIONAL_PATCHES)
                    ordered_one += [p for p in safe if p not in ordered_one]
                    ordered_one.append(plugin)
                    deduped_one = []
                    seen_one = set()
                    for p in ordered_one:
                        key = p.lower().strip()
                        if key and key not in seen_one:
                            deduped_one.append(p)
                            seen_one.add(key)
                    try:
                        with PLUGIN_FILE.open("w", encoding="utf-8") as f:
                            for line in backup_lines:
                                if not line.strip() or line.strip().startswith("#"):
                                    f.write(line + "\n")
                            for p1 in deduped_one:
                                f.write(p1 + "\n")
                    except Exception as e:
                        print(f"{RED}[ERROR] Failed to write for plugin {plugin}: {e}{RESET}")
                        continue
                    print_display([plugin], safe, failed, total_plugins_list)
                    if not launch_game(): break
                    try:
                        one_crash = wait_and_check_crash()
                    except RuntimeError as e:
                        if str(e) == "manual_pause_triggered":
                            print(f"{YELLOW}[RESUMED] Retrying plugin…{RESET}")
                            time.sleep(1)
                            one_crash = True
                        else:
                            raise
                    if one_crash:
                        log(f"Broken: {plugin}")
                        if plugin not in failed: failed.append(plugin)
                        if plugin not in tested: tested.append(plugin)
                        print_display([], safe, failed, total_plugins_list)
                    else:
                        log(f"Safe: {plugin}")
                        if plugin not in safe: safe.append(plugin)
                        if plugin not in tested: tested.append(plugin)
                        print_display([], safe, failed, total_plugins_list)

# ------------------------------------------------------
#  12. TURBO BATCH MODE (FIXED & INTEGRATED)
# ------------------------------------------------------

def turbo_batch_mode(to_test, patch_plugins, safe, total_plugins_list):
    """
    Turbo batch mode uses main batch size.
    After single plugin fails, tries mega batch with remaining plugins.
    Mega batch pass → ends turbo batch early, but will still offer to re-test failed plugins.
    Mega batch fail → continues isolating plugins.
    After turbo batch ends, prompts for re-test of failed plugins individually.
    """
    tested, failed = [], []
    remaining = to_test + patch_plugins

    for p in list(REQUIRED_PLUGINS) + list(OPTIONAL_PATCHES):
        if p not in safe:
            safe.append(p)
        if p not in tested:
            tested.append(p)

    def print_turbo_display(testing, passed, failed):
        print_display(testing, passed, failed, total_plugins_list, turbo=True)

    while remaining:
        batch_size = BATCH_SIZE  # Use main config batch size here
        batch = remaining[:batch_size]
        test_order = list(REQUIRED_PLUGINS) + list(OPTIONAL_PATCHES)
        test_order += [p for p in safe if p not in test_order]
        test_order += batch
        # Deduplicate
        seen = set()
        deduped = []
        for p in test_order:
            pl = p.lower().strip()
            if pl not in seen and p:
                deduped.append(p)
                seen.add(pl)
        if not write_plugins_exact(deduped):
            print(f"{RED}[TURBO ERROR] Failed to write plugins.txt for turbo batch.{RESET}")
            break
        print_turbo_display(batch, safe, failed)
        if not launch_game():
            print(f"{RED}[TURBO ERROR] Game failed to launch for turbo batch.{RESET}")
            break
        try:
            crashed = wait_and_check_crash()
        except RuntimeError as e:
            if str(e) == "manual_pause_triggered":
                print(f"{YELLOW}[TURBO] Resumed after pause…{RESET}")
                time.sleep(1)
                continue
            else:
                raise
        if not crashed:
            log(f"TURBO Safe: {', '.join(batch)}")
            for p in batch:
                if p not in safe: safe.append(p)
                if p not in tested: tested.append(p)
            remaining = [p for p in remaining if p not in safe]
            continue
        # Batch crashed: sub-batch
        size = len(batch)
        sub_size = get_batch_size(size)
        for i in range(0, size, sub_size):
            sub = batch[i : i + sub_size]
            sub_order = list(REQUIRED_PLUGINS) + list(OPTIONAL_PATCHES)
            sub_order += [p for p in safe if p not in sub_order]
            sub_order += sub
            seen_sub = set()
            deduped_sub = []
            for p in sub_order:
                pl = p.lower().strip()
                if pl not in seen_sub and p:
                    deduped_sub.append(p)
                    seen_sub.add(pl)
            if not write_plugins_exact(deduped_sub):
                print(f"{RED}[TURBO ERROR] Failed to write plugins.txt for turbo sub-batch.{RESET}")
                continue
            print_turbo_display(sub, safe, failed)
            if not launch_game():
                print(f"{RED}[TURBO ERROR] Game failed to launch for turbo sub-batch.{RESET}")
                continue
            try:
                sub_crash = wait_and_check_crash()
            except RuntimeError as e:
                if str(e) == "manual_pause_triggered":
                    print(f"{YELLOW}[TURBO] Resumed after pause…{RESET}")
                    time.sleep(1)
                    sub_crash = True
                else:
                    raise
            if not sub_crash:
                log(f"TURBO Safe: {', '.join(sub)}")
                for p in sub:
                    if p not in safe: safe.append(p)
                    if p not in tested: tested.append(p)
                remaining = [p for p in remaining if p not in safe]
                continue
            # Single plugin tests
            for plugin in sub:
                one_order = list(REQUIRED_PLUGINS) + list(OPTIONAL_PATCHES)
                one_order += [p for p in safe if p not in one_order]
                one_order.append(plugin)
                seen_one = set()
                deduped_one = []
                for p in one_order:
                    pl = p.lower().strip()
                    if pl not in seen_one and p:
                        deduped_one.append(p)
                        seen_one.add(pl)
                if not write_plugins_exact(deduped_one):
                    print(f"{RED}[TURBO ERROR] Failed to write plugins.txt for turbo single.{RESET}")
                    continue
                print_turbo_display([plugin], safe, failed)
                if not launch_game():
                    print(f"{RED}[TURBO ERROR] Game failed to launch for turbo single.{RESET}")
                    continue
                try:
                    one_crash = wait_and_check_crash()
                except RuntimeError as e:
                    if str(e) == "manual_pause_triggered":
                        print(f"{YELLOW}[TURBO] Resumed after pause…{RESET}")
                        time.sleep(1)
                        one_crash = True
                    else:
                        raise
                if one_crash:
                    log(f"TURBO Broken: {plugin}")
                    if plugin not in failed: failed.append(plugin)
                    if plugin not in tested: tested.append(plugin)
                    print_turbo_display([], safe, failed)

                    # === TURBO: MEGA BATCH after each fail ===
                    turbo_remaining = [p for p in remaining if p not in failed and p not in safe]
                    if turbo_remaining:
                        print(f"{CYAN}Turbo: Attempting MEGA batch with {len(turbo_remaining)} remaining...{RESET}")
                        mega_order = list(REQUIRED_PLUGINS) + list(OPTIONAL_PATCHES)
                        mega_order += [p for p in safe if p not in mega_order]
                        mega_order += turbo_remaining
                        seen_mega = set()
                        deduped_mega = []
                        for p in mega_order:
                            pl = p.lower().strip()
                            if pl not in seen_mega and p:
                                deduped_mega.append(p)
                                seen_mega.add(pl)
                        if not write_plugins_exact(deduped_mega):
                            print(f"{RED}[TURBO ERROR] Failed to write plugins.txt for MEGA batch.{RESET}")
                            continue
                        print_turbo_display(turbo_remaining, safe, failed)
                        if not launch_game():
                            print(f"{RED}[TURBO ERROR] Game failed to launch for MEGA batch.{RESET}")
                            continue
                        try:
                            mega_crash = wait_and_check_crash()
                        except RuntimeError as e:
                            if str(e) == "manual_pause_triggered":
                                print(f"{YELLOW}[TURBO] Resumed after pause…{RESET}")
                                time.sleep(1)
                                mega_crash = True
                            else:
                                raise
                        if not mega_crash:
                            print(f"{GREEN}Turbo Mega Batch: Passed. All remaining marked as safe!{RESET}")
                            for p in turbo_remaining:
                                if p not in safe: safe.append(p)
                                if p not in tested: tested.append(p)
                            remaining.clear()

                            # Write plugins.txt with failed commented out
                            try:
                                output = []
                                for p in safe:
                                    output.append(p)
                                output.append("")
                                output.append("##REMOVED PLUGINS##")
                                for p in failed:
                                    output.append(f"#{p} #REMOVED BY OBBPD ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
                                PLUGIN_FILE.write_text("\n".join(output).rstrip("\n") + "\n", encoding="utf-8")
                            except Exception as e:
                                print(f"{RED}Failed to write final plugins.txt: {e}{RESET}")

                            # Re-test failed plugins individually if user wants
                            if failed:
                                print(f"\n{YELLOW}Some plugins still failed after Turbo Mode.{RESET}")
                                resp = input("Would you like to re-test each failed plugin individually with all safe plugins? [Y/n]: ").strip().lower()
                                if resp == "" or resp.startswith("y"):
                                    refailed = []
                                    for plugin in failed:
                                        backup_plugins = get_total_plugins(ORIGINAL_BACKUP if ORIGINAL_BACKUP.exists() else PLUGIN_FILE)
                                        safe_in_backup_order = [p for p in backup_plugins if p in safe]
                                        ordered = list(REQUIRED_PLUGINS) + list(OPTIONAL_PATCHES)
                                        ordered += [p for p in safe_in_backup_order if p not in ordered]
                                        ordered.append(plugin)
                                        seen = set()
                                        deduped = []
                                        for p in ordered:
                                            pl = p.lower().strip()
                                            if pl not in seen and p:
                                                deduped.append(p)
                                                seen.add(pl)
                                        if not write_plugins_exact(deduped):
                                            print(f"{RED}[TURBO RECHECK] Failed to write plugins.txt for {plugin}{RESET}")
                                            refailed.append(plugin)
                                            continue
                                        print(f"{YELLOW}[TURBO RECHECK] Testing: {plugin}...{RESET}")
                                        if not launch_game():
                                            print(f"{RED}[TURBO RECHECK] Game failed to launch for {plugin}{RESET}")
                                            refailed.append(plugin)
                                            continue
                                        try:
                                            crashed = wait_and_check_crash()
                                        except RuntimeError as e:
                                            if str(e) == "manual_pause_triggered":
                                                print(f"{YELLOW}[TURBO RECHECK] Resumed after pause…{RESET}")
                                                time.sleep(1)
                                                crashed = True
                                            else:
                                                raise
                                        if crashed:
                                            print(f"{RED}[TURBO RECHECK] Still fails: {plugin}{RESET}")
                                            refailed.append(plugin)
                                        else:
                                            print(f"{GREEN}[TURBO RECHECK] Plugin now passes: {plugin}{RESET}")
                                            safe.append(plugin)
                                    failed[:] = refailed  # update failed list

                            # Show final summary after re-tests (or immediately if no failed)
                            show_final_summary_and_prompt(safe, failed)
                            return safe, failed
                        else:
                            print(f"{YELLOW}Turbo Mega Batch: crashed. Continue singles...{RESET}")
                    # End mega batch attempt
                else:
                    log(f"TURBO Safe: {plugin}")
                    if plugin not in safe: safe.append(plugin)
                    if plugin not in tested: tested.append(plugin)
                    print_turbo_display([], safe, failed)
            # End singles for sub batch
            remaining = [p for p in remaining if p not in failed and p not in safe]
        # End sub-batch loop

    # Turbo batch ended normally: write final plugins.txt with failed commented out
    print(f"\n{CYAN}Turbo batch mode complete.{RESET}")
    print(f"{GREEN}Safe plugins: {len(safe)}{RESET}")
    print(f"{RED}Failed plugins: {len(failed)}{RESET}")
    try:
        output = []
        for p in safe:
            output.append(p)
        output.append("")
        output.append("##REMOVED PLUGINS##")
        for p in failed:
            output.append(f"#{p} #REMOVED BY OBBPD ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        PLUGIN_FILE.write_text("\n".join(output).rstrip("\n") + "\n", encoding="utf-8")
        print(f"{CYAN}plugins.txt updated with failed plugins commented out.{RESET}")
    except Exception as e:
        print(f"{RED}Failed to write final plugins.txt: {e}{RESET}")

    # Re-test failed plugins individually if user wants
    if failed:
        print(f"\n{YELLOW}Some plugins still failed after Turbo Mode.{RESET}")
        resp = input("Would you like to re-test each failed plugin individually with all safe plugins? [Y/n]: ").strip().lower()
        if resp == "" or resp.startswith("y"):
            refailed = []
            for plugin in failed:
                backup_plugins = get_total_plugins(ORIGINAL_BACKUP if ORIGINAL_BACKUP.exists() else PLUGIN_FILE)
                safe_in_backup_order = [p for p in backup_plugins if p in safe]
                ordered = list(REQUIRED_PLUGINS) + list(OPTIONAL_PATCHES)
                ordered += [p for p in safe_in_backup_order if p not in ordered]
                ordered.append(plugin)
                seen = set()
                deduped = []
                for p in ordered:
                    pl = p.lower().strip()
                    if pl not in seen and p:
                        deduped.append(p)
                        seen.add(pl)
                if not write_plugins_exact(deduped):
                    print(f"{RED}[TURBO RECHECK] Failed to write plugins.txt for {plugin}{RESET}")
                    refailed.append(plugin)
                    continue
                print(f"{YELLOW}[TURBO RECHECK] Testing: {plugin}...{RESET}")
                if not launch_game():
                    print(f"{RED}[TURBO RECHECK] Game failed to launch for {plugin}{RESET}")
                    refailed.append(plugin)
                    continue
                try:
                    crashed = wait_and_check_crash()
                except RuntimeError as e:
                    if str(e) == "manual_pause_triggered":
                        print(f"{YELLOW}[TURBO RECHECK] Resumed after pause…{RESET}")
                        time.sleep(1)
                        crashed = True
                    else:
                        raise
                if crashed:
                    print(f"{RED}[TURBO RECHECK] Still fails: {plugin}{RESET}")
                    refailed.append(plugin)
                else:
                    print(f"{GREEN}[TURBO RECHECK] Plugin now passes: {plugin}{RESET}")
                    safe.append(plugin)
            failed[:] = refailed  # update failed list

    # Show final summary after re-tests (or immediately if no failed)
    show_final_summary_and_prompt(safe, failed)
    finalize_load_order()
    return safe, failed

# ------------------------------------------------------
#  13. MAIN ORCHESTRATOR
# ------------------------------------------------------

def isolate_esps():
    global finalize_needed
    print(f"{CYAN}Starting plugin isolation at {datetime.now().strftime('%Y-%m-%d %H-%M-%S')}{RESET}")

    if not PLUGIN_FILE.exists():
        print(f"{RED}[ERROR] plugins.txt not found at: {PLUGIN_FILE}{RESET}")
        input("Press Enter to exit…")
        finalize_needed=False
        return
    if not GAME_EXE.exists():
        print(f"{RED}[ERROR] Game executable not found at: {GAME_EXE}{RESET}")
        input("Press Enter to exit…")
        finalize_needed=False
        return

    restore_latest_backup()
    if not backup_original_plugins():
        input("Press Enter to exit…")
        finalize_needed=False
        return

    print(f"\n{CYAN}Verifying REQUIRED plugins can boot the game…{RESET}")
    original_plugins = read_plugins(ORIGINAL_BACKUP) if ORIGINAL_BACKUP.exists() else read_plugins(PLUGIN_FILE)
    found_required = [p for p in REQUIRED_PLUGINS if p in original_plugins]
    found_optional = [p for p in OPTIONAL_PATCHES if p in original_plugins]

    print(f"\n{CYAN}Found the following REQUIRED plugins in original load order:{RESET}")
    for plugin in found_required:
        print(f"{GREEN}✓ {plugin}{RESET}")
    missing_required = [p for p in REQUIRED_PLUGINS if p not in original_plugins]
    for plugin in missing_required:
        print(f"{RED}✗ {plugin} (missing){RESET}")
    if found_optional:
        print(f"\n{CYAN}Also found optional patches:{RESET}")
        for plugin in found_optional:
            print(f"{GREEN}✓ {plugin}{RESET}")
    missing_optional = [p for p in OPTIONAL_PATCHES if p not in original_plugins]
    if missing_optional:
        print(f"\n{YELLOW}Missing optional patches:{RESET}")
        for plugin in missing_optional:
            print(f"{YELLOW}– {plugin}{RESET}")
    sanity_plugins = found_required + found_optional

    while True:
        if not write_plugins(sanity_plugins):
            print(f"{RED}[ERROR] Could not write required plugins for sanity check.{RESET}")
            input("Press Enter to exit…")
            finalize_needed=False
            return
        if not launch_game():
            print(f"{RED}[ERROR] Failed to launch game during sanity check.{RESET}")
            input("Press Enter to exit…")
            finalize_needed=False
            return
        try:
            crashed = wait_and_check_crash()
            break
        except RuntimeError as e:
            if str(e)=="manual_pause_triggered":
                print(f"{YELLOW}[RESUMED] Retrying stability check…{RESET}")
                time.sleep(1)
                continue
            else:
                raise

    if crashed:
        print(f"{RED}[CRITICAL] Required plugins cause a crash!{RESET}")
        print("="*60)
        print("Boot load order fix (Config: required plugins and options plugins)".center(60))
        print("="*60)
        if input("\nDo you want to enforce the exact load order for all required and optional plugins? [Y/n]: ").strip().lower().startswith('y'):
            print(f"\n{YELLOW}Re-writing plugins.txt with enforced required + optional load order…{RESET}\n")
            enforce_exact_load_order()
            print(f"{CYAN}Enforced load order written. Retesting required and optional plugins…{RESET}")
            while True:
                if not write_plugins_exact(sanity_plugins):
                    print(f"{RED}[ERROR] Could not write plugins for enforced order sanity check.{RESET}")
                    input("Press Enter to exit…")
                    finalize_needed=False
                    return
                if not launch_game():
                    print(f"{RED}[ERROR] Failed to launch game during enforced order sanity check.{RESET}")
                    input("Press Enter to exit…")
                    finalize_needed=False
                    return
                try:
                    crashed_enf = wait_and_check_crash()
                    break
                except RuntimeError as e:
                    if str(e)=="manual_pause_triggered":
                        print(f"{YELLOW}[RESUMED] Retrying stability check…{RESET}")
                        time.sleep(1)
                        continue
                    else:
                        raise
            if crashed_enf:
                print(f"{RED}[CRITICAL] Even with enforced load order, required plugins still crash.{RESET}")
                input("Press Enter to exit…")
                finalize_needed=False
                return
            else:
                print(f"{GREEN}[OK] Required plugins booted with enforced load order!{RESET}")
        else:
            print(f"{RED}Testing halted.{RESET}")
            input("Press Enter to exit…")
            finalize_needed=False
            return

    print(f"\n{GREEN}[OK] Required plugins booted successfully.{RESET}")
    safe, tested, failed = [], [], []
    all_plugins = read_plugins(ORIGINAL_BACKUP if ORIGINAL_BACKUP.exists() else PLUGIN_FILE)
    if not all_plugins:
        print(f"{RED}[ERROR] No plugins found to test{RESET}")
        input("Press Enter to exit…")
        finalize_needed=False
        return

    all_plugins = list(dict.fromkeys([p.strip() for p in all_plugins if p.strip()]))
    all_esp = [p for p in all_plugins if p.lower().endswith((".esp",".esm"))]
    patch_plugins = get_patch_plugins(all_esp)
    other_plugins = filter_plugins(all_esp)

    def dedup(lst):
        seen=set(); res=[]
        for p in lst:
            k=p.lower().strip()
            if k not in seen:
                seen.add(k); res.append(p)
        return res

    tested_lower={p.lower() for p in tested+safe+failed}
    patch_plugins=[p for p in patch_plugins if p.lower() not in tested_lower]
    to_test=[p for p in other_plugins if p.lower() not in tested_lower]

    to_test=dedup([p for p in to_test if p not in safe])
    patch_plugins=dedup([p for p in patch_plugins if p not in safe])

    total_plugins_list = get_total_plugins(ORIGINAL_BACKUP if ORIGINAL_BACKUP.exists() else PLUGIN_FILE)

    if TURBO_BATCH_MODE:
        safe, failed = turbo_batch_mode(to_test, patch_plugins, safe, total_plugins_list)
        # final summary already shown inside turbo_batch_mode on mega batch pass or after retests
        finalize_needed = False
        return

    if not total_plugins_list:
        print(f"{YELLOW}[INFO] No plugins to test.{RESET}")
        input("Press Enter to exit…")
        finalize_needed=False
        return

    def chunk(data, size):
        return [data[i:i+size] for i in range(0, len(data), size)]

    try:
        safe.extend(sanity_plugins)
        tested.extend(sanity_plugins)
        to_test = [p for p in to_test if p not in safe]
        patch_plugins = [p for p in patch_plugins if p not in safe]

        if SHOW_LOAD_ORDER_PER_BATCH:
            launch_debug_console()

        for idx, batch in enumerate(chunk(to_test, BATCH_SIZE), 1):
            run_batch(batch, safe, tested, failed, total_plugins_list)
            if SHOW_LOAD_ORDER_PER_BATCH:
                print_plugins_state(idx, str(PLUGIN_FILE))

        for idx, batch in enumerate(chunk(patch_plugins, BATCH_SIZE), 1):
            run_batch(batch, safe, tested, failed, total_plugins_list)
            if SHOW_LOAD_ORDER_PER_BATCH:
                print_plugins_state(idx, str(PLUGIN_FILE))

        write_plugins(safe)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[INTERRUPTED] Testing stopped by user{RESET}")
    except Exception as e:
        print(f"\n{RED}[ERROR] Testing failed: {e}{RESET}")

    show_final_summary_and_prompt(safe, failed)

# ------------------------------------------------------
#  14. FINALIZE LOAD ORDER & EXIT
# ------------------------------------------------------

def finalize_load_order():
    from datetime import datetime

    quarantine_sessions = sorted(QUARANTINE_DIR.glob("session_*"), reverse=True)
    if not quarantine_sessions:
        failed_plugins = []
        quarantine_ts = None
    else:
        latest = quarantine_sessions[0]
        session_str = latest.name.replace("session_", "")
        try:
            dt = datetime.strptime(session_str, "%Y-%m-%d_%H-%M-%S")
            quarantine_ts = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            quarantine_ts = None
        failed_plugins = [f.name for f in latest.glob("*.esp")] + [f.name for f in latest.glob("*.esm")]

    try:
        lines_orig = PLUGIN_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as e:
        print(f"{RED}[ERROR] Could not read current plugins.txt: {e}{RESET}")
        return

    vortex_header = None
    if lines_orig and lines_orig[0].strip().lower().startswith("## this file was automatically generated by vortex"):
        vortex_header = lines_orig[0]

    existing_removals = [l for l in lines_orig if l.startswith("#") and "#REMOVED BY OBBPD" in l]

    now = datetime.now()
    banner_ts = now.strftime("%Y-%m-%d %H:%M:%S")
    removed_ts = quarantine_ts or banner_ts

    def ci(x): return x.lower().strip()
    failed_set = {ci(p) for p in failed_plugins}
    enabled = [ln for ln in lines_orig if ln.strip() and not ln.startswith("#")]
    required_block = [p for p in REQUIRED_PLUGINS if ci(p) not in failed_set and p in enabled]
    optional_block = [p for p in OPTIONAL_PATCHES if ci(p) not in failed_set and p in enabled]
    lower_reqopt = {ci(x) for x in required_block + optional_block}
    other_enabled = [p for p in enabled if ci(p) not in failed_set and ci(p) not in lower_reqopt]

    PINNED = ["#AltarGymNavigation.esp", "#TamrielLeveledRegion.esp"]

    new_lines = []
    if vortex_header:
        new_lines.append(vortex_header)
    else:
        new_lines.append("## This file was automatically generated by Vortex. Do not edit this file.")
    new_lines.append("")
    new_lines.append(f"##OBBPD ENFORCED ORDER ({banner_ts})##")
    new_lines.append("")
    for p in required_block + optional_block + other_enabled:
        new_lines.append(p)
    new_lines.append("")
    for c in PINNED:
        new_lines.append(c)
    new_lines.append("")
    new_lines.append("##REMOVED PLUGINS##")
    for entry in existing_removals:
        new_lines.append(entry)
    for p in failed_plugins:
        entry = f"#{p} #REMOVED BY OBBPD ({removed_ts})"
        if entry not in existing_removals:
            new_lines.append(entry)

    try:
        PLUGIN_FILE.write_text("\n".join(new_lines).rstrip("\n") + "\n", encoding="utf-8")
    except Exception as e:
        print(f"{RED}[ERROR] Failed to write final plugins.txt: {e}{RESET}")
        return

    if WINDOWS and PLUGIN_FILE.exists():
        try:
            subprocess.Popen(["notepad.exe", str(PLUGIN_FILE)])
        except:
            pass

    input("Press Enter to exit…")

# ======================================================
#                  MAIN ENTRY POINT
# ======================================================

if __name__ == "__main__":
    finalize_needed=True
    try:
        isolate_esps()
    finally:
        shutdown_logging()
    if finalize_needed:
        finalize_load_order()
