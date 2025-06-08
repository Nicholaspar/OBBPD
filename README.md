Known + Fixed Issues:

• Broken load order not getting adjusted. (FIXED V1.1)
• The plugin counter “Remaining” does not update properly. (FIXED V1.2)
• Turbo batching mode fully ready for V2.0 (COMPLETED V2.0 READY)
• Removed unused debug window code. (REMOVED 2.0)

• Some antivirus programs may flag the EXE as a false positive (see notice below).
OBBPD v2.0 – Oblivion Broken Batch Plugin DetectorCrash Isolation and Diagnostic Tool for Oblivion Remastered Modlists
Version: 2.0
Author: Nicholas Parfitt
© 2025 Nicholas Parfitt. All rights reserved.
⚠️ IMPORTANT: Virus Scanner False PositivesOBBPD v2.0 is a custom-built EXE.
Some antivirus or security software may flag it as suspicious or a “generic trojan” due to its automation, scripting, and ability to launch external programs for game testing.
This is a known and common issue with small-batch EXE tools built with PyInstaller and similar utilities.
OBBPD does NOT contain any malicious code.
If you downloaded it from the official source or directly from Nicholas Parfitt, you can safely whitelist it in your antivirus.
🚀 What is OBBPD?OBBPD stands for Oblivion Broken Batch Plugin Detector.
It helps Oblivion Remastered players and modders automatically and quickly find which .esp or .esm files are crashing their game—even in huge modlists.
How it works:
• Tests your load order in automated batches
• Detects crashes at launch
• Narrows down broken plugins
• Quarantines or comments out problem files
• Rebuilds your load order with only safe mods
🆕 What’s New in v2.0?Turbo Batch Mode:
Super-fast troubleshooting. When a plugin crashes, it’s removed and a mega-batch of all remaining plugins is attempted. Ends early if possible.
Core Plugins Always Passed:
All required and optional plugins (set in the config) are always listed as “passed” if they pass the initial check.
Smarter Patch/Fix Handling:
Patch/fix/compatibility plugins are tested after the main mods, so load order is correct.
Improved Session Folders:
Every run creates timestamped backup, log, and quarantine folders for easy reverts and history.
Enhanced Logging & UI:
Full logs, grouped and timestamped. Three-column fullscreen UI (Testing | Passed | Failed) with batch progress.
Fully Configurable:
All key options (batch size, turbo, plugins, display) are controlled in obbpd_config.ini.
📦 Distribution & Legal NoticeThis software is closed-source and distributed as an EXE.
You may NOT modify, share, reverse-engineer, or distribute this tool without written permission from Nicholas Parfitt.
For support, feedback, or permissions:
Contact Nicholas Parfitt.
🧰 Requirements• Windows 10 or 11
• OBSE64 (Oblivion Script Extender 64-bit) installed
• OblivionRemastered-Win64-Shipping.exe
• A valid plugins.txt (not overwritten by Vortex during testing)
🛠 How It Works1. Backup and Restore:
Backs up your current plugins.txt before any changes
Restore original load order any time
2. Sanity Check:
Tests all required and optional plugins first
Any crash here means a core mod or patch is broken
3. Batch & Turbo Batch Testing:
Standard Mode: Plugins are tested in batches (batch size in config). If a batch fails, it’s split or tested individually.
Turbo Batch Mode: As soon as a plugin fails, it’s removed and a mega-batch is attempted with all remaining plugins. If it passes, you’re done!
4. Patch/Fix Plugins:
Patch/fix/compatibility plugins are tested after main mods to keep load order stable.
5. Quarantine and Final Load Order:
Broken plugins are moved to Quarantine (session folder) or commented out in plugins.txt with a timestamp and “REMOVED BY OBBPD”.
📁 Folder StructureEach session creates subfolders for perfect organization:
Backups/session_YYYY-MM-DD_HH-MM-SS — Original plugins.txt
Logs/session_YYYY-MM-DD_HH-MM-SS — Batch/test logs
Quarantine/session_YYYY-MM-DD_HH-MM-SS — Broken .esp/.esm files
⚙ Configuration (obbpd_config.ini)Example:

[CorePlugins]required = Oblivion.esm, DLCBattlehornCastle.esp, DLCFrostcrag.esp, DLCHorseArmor.esp, DLCMehrunesRazor.esp, DLCOrrery.esp, DLCShiveringIsles.esp, DLCSpellTomes.esp, DLCThievesDen.esp, DLCVileLair.esp, Knights.esp, AltarESPMain.esp, AltarDeluxe.espoptional = Unofficial Oblivion Remastered Patch.esp, Unofficial Oblivion Remastered Patch - Deluxe.esp[Settings]wait_seconds = 10after_close_delay = 2batch_size = 50truncate_length = 25turbo_mode = Falseturbo_batch_mode = True

🖥️ UI & ControlsDisplay:
Fullscreen, three columns:
Testing
Recently Passed
Failed
Shows batch progress, stats, and current batch size.
While testing:
• Press any key to pause
• R: Resume
• V: Revert to original load order and quit
• Q: Quit and keep current state
📝 plugins.txt Output ExampleVortex-compatible formatting.
Required and optional files always at the top
All safe plugins listed in load order
Broken plugins commented out with timestamp and “REMOVED BY OBBPD”
Example:

##OBBPD ENFORCED ORDER (2025-06-07 18:00:00)##
Oblivion.esm
DLCShiveringIsles.esp
BetterCities.esp
##REMOVED PLUGINS###BrokenFollower.esp #REMOVED BY OBBPD (2025-06-07 18:00:00)

📋 End-of-Run SummaryAt the end of each session, OBBPD will:
Show total passed, failed, and remaining plugins
Offer to quarantine failed files, restore the original plugin list, or exit and keep the new load order
Save logs and session states to subfolders
🛑 Vortex Users NoteIf you use Vortex:
Vortex will overwrite plugins.txt!
To use OBBPD safely:
• Temporarily disable Vortex’s deployment/auto-deploy• Run Oblivion directly (not from Vortex) using OBSE64• Let OBBPD finish, then manually import your plugins.txt back into Vortex
❓ TroubleshootingGame won’t launch?
Check your game path and required plugins. OBSE64 must be used.
Script exits early?
A required plugin is missing or broken.
No plugins tested?
Make sure your plugins.txt has enabled (non-comment) lines.
Game keeps reverting/crashing?
Run LOOT before and after making changes in Vortex.
Vortex will notify you after re-deploying that files have been removed after OBBPD has quarantined bad plugins. This is normal—always disable breaking mods in Vortex before moving forward.
Created by:
Nicholas Parfitt
Enjoy Oblivion Remastered safely and quickly!
Thanks for using OBBPD v2.0.
