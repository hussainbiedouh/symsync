# 📁 SymSync

A Windows utility that creates and maintains symbolic links between multiple source directories and a target directory, with real-time synchronization and system tray support! 🔄

## ✨ Features

- 🔗 Creates symbolic links from multiple source directories to a target directory
- 👀 Monitors source directories for changes in real-time with recursive subdirectory watching
- 🔄 Automatically updates links when files are created, modified, moved or deleted
- 🎨 Clean and intuitive GUI interface with light blue theme
- 🛡️ Runs with administrative privileges for proper link management
- 📊 Shows detailed status updates for each operation
- 🎯 Easily add and remove watched source directories
- 🔄 Seamlessly change target directory with option to clean up old links

## 🚀 Getting Started

1. Run the application as Administrator (required for creating symbolic links)
2. Select your target directory using the Browse button 🔍
3. Click "+ Add Source" to select source directories to watch
4. The application will create links and continue monitoring for changes
5. Use the "-" button next to each source to stop watching and remove its links

## 💡 Use Cases

- 🎮 Link game mods folders from multiple locations
- 📂 Create synchronized backup structures
- 🔄 Maintain mirror directories without duplicating files
- 📱 Share files between different applications

## ⚙️ Requirements

- Windows operating system
- Administrative privileges
- Python 3.x
- Required packages: 
  - watchdog>=3.0.0 (file system monitoring)
  - Pillow>=10.0.0 (image handling)
  - pystray>=0.19.0 (system tray support)
  - tkinter>=8.6 (GUI framework)

## 🛠️ Installation

1. Clone this repository
2. Install required packages:
   ```bash
   pip install -r requirements.txt
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
- Target directory must be selected before adding source directories
- The application watches subdirectories recursively for changes
- Closing the main window minimizes to system tray with a stylish "SS" gradient icon
- System tray menu provides options to Restore window or Quit
- Status updates are shown in real-time for all link operations
- Window size is 600x400 pixels with resizable frame
- Sources can be added and removed dynamically
- Target directory can be changed with option to clean up old links
