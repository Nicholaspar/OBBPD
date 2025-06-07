# 🧩 OBBPD - Oblivion Broken Batch Plugin Detector

> A diagnostic safety tool for **Oblivion Remastered** that automatically tests mod plugins in batches, detects crashes, and identifies `.esp`/`.esm` files causing instability.

---

## 📜 About

**OBBPD** (Oblivion Broken Batch Plugin Detector) is a Python-based utility developed to help modders, players, and reviewers isolate crashing plugins in large load orders. By automating batch testing and log management, OBBPD saves hours of manual troubleshooting and produces a clean, minimal load order.

This project is made specifically for **internal diagnostic use** and **Nexus Mods safety review**.

---

## 🧠 How It Works

OBBPD reads your current `plugins.txt` file and:

1. **Backs it up** into a timestamped session folder.
2. **Verifies required plugins** are stable and launchable.
3. **Splits all other plugins into batches** for testing.
4. Launches the game for each batch, watching for:
   - Crashes
   - Hangs
   - Manual interruptions
5. On crash, it automatically:
   - Retests in **smaller sub-batches**
   - Isolates broken plugin(s)
   - Logs results

At the end, you're given the option to:
- Restore original load order
- Quarantine broken plugins
- Keep the clean, stable loadout

---

## 🧩 Key Features

- ✅ **Batch & Sub-Batch Testing** of `.esp` and `.esm` files
- ✅ **Crash Detection** through process monitoring
- ✅ **Patch-Aware Logic** – skips compatibility patches until core mods pass
- ✅ **Custom Load Order Enforcement** for required/optional plugins
- ✅ **Turbo Mode** for speed testing
- ✅ **Terminal UI** with live plugin status
- ✅ **Log Files & Backups** created per session
- ✅ **Quarantine Support** – broken plugins are stored safely
- ✅ **Manual Pause & Resume** controls
- ✅ **Final Mega-Batch Recheck** to confirm full stability

---

## 🗂 Folder Structure (Auto-created)

OBBPD/
├── obbpd.py
├── obbpd_config.ini
├── Backups/
│ └── session_2025-06-07_14-21-00/
├── Logs/
│ └── session_2025-06-07_14-21-00/
├── Quarantine/
│ └── session_2025-06-07_14-21-00/

yaml
Copy
Edit

---

## ⚙️ Configuration (`obbpd_config.ini`)

This file is created automatically on first run if missing.

### Example:
```ini
[Settings]
wait_seconds = 11
after_close_delay = 3
batch_size = 10
truncate_length = 25
turbo_mode = False

[CorePlugins]
required = Oblivion.esm, Knights.esp, AltarESPMain.esp
optional = Unofficial Oblivion Remastered Patch.esp
Options:
Option	Description
wait_seconds	How long to wait after game launch
after_close_delay	Delay after game closes
batch_size	How many plugins to test at once
truncate_length	Shortens plugin names in the UI
turbo_mode	Enables fast cycle times
required	Always-loaded core plugins
optional	Important but non-essential patches

🚀 How to Use
1. Run in the same folder as your Config.ini

2. Run the script
bash
Copy
Edit
python obbpd.py

3. Follow the prompts
Confirm backup or restore of previous session

Watch testing batches run automatically

View the terminal UI as it logs progress

Choose how to handle failed plugins (quarantine / revert / keep)

💻 Requirements
Windows OS (10/11)

Python 3.7+

Steam or GOG version of Oblivion Remastered

A valid and writable plugins.txt

OBSE loader installed and used as entry point

💾 Files Managed
File	Purpose
plugins.txt	Modified during testing
obbpd_config.ini	User settings
Backups/	Original load orders per session
Logs/	Plugin test results
Quarantine/	Broken plugins (if quarantined)

📑 Nexus Mods Use Case
This project was designed for Nexus Mods staff and modders to verify plugin stability and isolate incompatibilities in large Oblivion mod lists.

You are encouraged to:

Clone this repo for code review

Run tests on your own load order

View detailed logs and summaries in the terminal or log files

📌 Developer Notes
All critical file operations are protected by backups

Logs are written via a background thread (non-blocking)

Game process is launched via OBSE64 loader and monitored directly

Supports both .esp and .esm files

Handles Vortex-generated plugin headers

🔐 License & Terms
kotlin
Copy
Edit
Copyright © 2025 Nicholas Parfitt  
All rights reserved.

This software is NOT open source. You may NOT:
- Copy or reproduce any part of this code
- Modify, distribute, or share this software
- Use this code in any commercial or personal project  
  without explicit written permission from the author

Unauthorized use or distribution is strictly prohibited  
and may result in legal action.

For permissions or inquiries, contact: Nicholas Parfitt
📫 Contact
If you are a Nexus Mods reviewer or need permission for safe use/testing:

Author: Nicholas Parfitt
Intended Use: Diagnostic / Safety Review Only
Do Not Distribute, Upload, or Fork without permission

