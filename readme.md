# 📁 SymSync

A Windows utility that creates and maintains symbolic links between directories, with real-time synchronization 🔄

## ✨ Features

- 🔗 Creates symbolic links from a source directory to a target directory
- 👀 Monitors source directory for changes in real-time with recursive subdirectory watching
- 🔄 Automatically updates links when files are created, modified, moved or deleted
- 🛡️ Runs with administrative privileges for proper link management
- 📊 Shows detailed status updates for each operation

## 🚀 Getting Started

1. Run the application as Administrator (required for creating symbolic links)
2. Select your source directory using the Browse button 🔍
3. Select your target directory using the Browse button 🔍
4. Click "Create Links" to start the process
5. The application will create links and continue monitoring for changes

## 💡 Use Cases

- 🎮 Link game mods folders to multiple locations
- 📂 Create synchronized backup structures
- 🔄 Maintain mirror directories without duplicating files
- 📱 Share files between different applications

## ⚙️ Requirements

- Windows operating system
- Administrative privileges
- Python 3.x
- Required packages: 
  - tkinter (GUI framework)
  - watchdog (file system monitoring)
  - pystray (system tray support)
  - Pillow (image handling)

## 🛠️ Installation

1. Clone this repository
2. Install required packages:
   ```bash
   pip install watchdog pystray Pillow
   ```
3. Run the script:
   ```bash
   python symsync.py
   ```

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
- Both source and target directories must exist before creating links
- The application watches subdirectories recursively for changes
- Closing the main window minimizes to system tray with a blue-purple gradient icon
- System tray menu provides options to Show window or Exit
- Status updates are shown in real-time for all link operations
- Window size is 600x300 pixels with resizable frame
