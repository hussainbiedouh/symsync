# 📁 SymSync v3.5

A Windows utility that creates and maintains symbolic links between multiple source directories and a target directory, with real-time synchronization and system tray support! 🔄

## ✨ Features

### Core Features
- 🔗 Creates symbolic links from multiple source directories to a target directory
- 👀 Monitors source directories for changes in real-time with recursive subdirectory watching
- 🔄 Automatically updates links when files are created, modified, moved or deleted
- 🛡️ Runs with administrative privileges for proper link management

### v3 New Features
### v3.5 New Features
- 🛡️ **Auto-Elevation** - Automatically requests admin rights on startup
- 📋 **Activity Log** - View detailed operation history for each link in the dashboard
- ♻️ **Auto-Rescan & Recovery** - Periodically checks targets and restores missing links automatically
- ⏱️ **Adjustable Intervals** - Choose custom rescan durations (1 sec to 1 hour) for each link
- 🎨 **Enhanced UI** - sleek rounded corners, modern container design, and updated branding icon
- 📦 **Self-Contained Executable** - Single file distribution with correct icon and no console window

### v3.0 New Features
- 📋 **Multi-Link Support** - Create multiple independent link configurations in a single instance
- 💾 **Persistent Settings** - Automatically saves/restores settings to `%TEMP%\symsync_settings.json`
- 🔒 **Single Instance** - Prevents multiple instances from running simultaneously
- 🎨 **Modern Light Theme UI** - Clean white/blue design with custom styled buttons
- 🟢🔴 **Visual Status Indicators** - Color-coded link status (green=active, red=inactive)
- ✅ **Duplicate Prevention** - Prevents duplicate target folders across links and duplicate sources within a link
- 📊 **Enhanced Status Display** - Colorful status messages with emojis

## 🚀 Getting Started

1. Run `SymSync.exe` (it will auto-request Administrator rights)
2. Click **"+ New Link"** to create a new link configuration
3. Give your link a name (e.g., "Game Mods")
4. Select a **Target Directory** using the Browse button
5. Click **"+ Add"** to add one or more source directories
6. Adjust the **Rescan Interval** if needed (default: 10 sec)
7. Click **"▶ Start"** to create symlinks and begin monitoring
8. Monitor progress in the **Activity Log** panel
9. Repeat for additional link configurations as needed


## 🖥️ User Interface

```
┌─────────────────────────────────────────────────────────────────┐
│                         SymSync                                 │
├───────────────────┬─────────────────────────────────────────────┤
│   LINKS           │           LINK DETAILS                      │
├───────────────────┼─────────────────────────────────────────────┤
│                   │                                             │
│  [+ New Link]     │  Name: [________________]                   │
│                   │                                             │
│  ● Link 1 (green) │  Target: [_______________] [Browse]         │
│  ○ Link 2 (red)   │                                             │
│                   │  Sources: [+ Add] [- Remove]                │
│                   │  ┌─────────────────────────┐                │
│                   │  │ 📁 folder1              │                │
│                   │  │ 📁 folder2              │                │
│                   │  └─────────────────────────┘                │
│                   │                                             │
│                   │  STATUS: ✅ Watching 2 source(s)            │
│                   │                                             │
│                   │  Rescan Interval: [10 sec ▼]                │
│                   │                                             │
│                   │  [▶ Start]  [■ Stop]  [🗑 Delete]           │
│                   │                                             │
│                   │  ACTIVITY LOG:                              │
│                   │  ┌─────────────────────────┐                │
│                   │  │ [12:00:01] Started...   │                │
│                   │  │ [12:00:11] Restored 1.. │                │
│                   │  └─────────────────────────┘                │
└───────────────────┴─────────────────────────────────────────────┘
```

## 💡 Use Cases

- 🎮 Link game mods folders from multiple locations
- 📂 Create synchronized backup structures
- 🔄 Maintain mirror directories without duplicating files
- 📱 Share files between different applications
- 💿 Combine content from multiple drives into a single view

## ⚙️ Requirements

- Windows operating system
- Administrative privileges
- Python 3.x (for running from source)

### Python Packages (for development)
```
watchdog>=3.0.0
Pillow>=10.0.0
pystray>=0.19.0
```

## 🛠️ Installation

### Option 1: Run the Executable
Simply download and run `SymSync.exe`.

### Option 2: Run from Source
1. Clone this repository
2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the script as Administrator:
   ```bash
   python SymSync.py
   ```

### Build from Source
```bash
pyinstaller --onefile --noconsole --name SymSync --hidden-import=pystray --hidden-import=PIL --icon=icon.ico SymSync.py
```

## 📁 Settings Storage

Settings are automatically saved to:
```
%TEMP%\symsync_settings.json
```

This includes link configurations, sources, targets, active states, logs, and rescan intervals.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0) - see the LICENSE file for details. This means:

- ✅ You can freely use, modify and distribute this software
- ✅ If you distribute modified versions, they must also be open source under GPL-3.0
- ✅ You must include the original copyright notice and license
- ✅ You must state significant changes made to the software
- ✅ You must make the source code available when distributing the software

## ⚠️ Important Notes

- The application requires administrative privileges to create symbolic links
- Only one instance of SymSync can run at a time (check system tray if already running)
- Target directory must be selected before adding source directories
- Each link must have a unique target directory
- The application watches subdirectories recursively for changes
- Closing the main window minimizes to system tray with a stylish "SS" gradient icon
- System tray menu provides options to Restore window or Quit
- Status updates are shown in real-time with colorful indicators
- Window size is 1050x720 pixels with resizable frame (minimum 900x600)

## 📜 Version History

### v3.5 (2026-01-06)
- **Auto-Elevation**: Script/Exe now intelligently requests admin rights
- **Rescan & Recovery**: Automatically checks for and restores deleted/broken links
- **Configurable Intervals**: Per-link dropdown for rescan frequency
- **Activity Logging**: New right-pane log showing detailed operations and timestamps
- **UI Refinement**: Rounded corners (RoundedFrame) and new "SS" purple branding
- **Exe Build**: Proper icon integration and console suppression

### v3.0 (2026-01-05)
- Multi-link support with dual-pane UI
- Persistent settings with auto-restore
- Single instance enforcement
- Modern light theme with colored status indicators
- Duplicate target/source prevention
- Enhanced status display with emojis

### v2.0
- Multiple source directories per target
- System tray integration
- Real-time file monitoring

### v1.0
- Initial release
- Basic symlink creation
