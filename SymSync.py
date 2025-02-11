# Import required modules
import os  # For file system operations
import ctypes  # For checking admin privileges
import subprocess  # For running system commands
import tkinter as tk  # GUI framework
from tkinter import filedialog, ttk, messagebox, PhotoImage  # GUI components
from watchdog.observers import Observer  # For monitoring file system changes
from watchdog.events import FileSystemEventHandler  # For handling file system events
from PIL import Image, ImageDraw, ImageTk  # For image handling and icons

def is_admin():
    """Check if the script is running with administrative privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def execute_admin_command(command):
    """Execute a command with administrative privileges
    Args:
        command (str): Command to execute
    Returns:
        bool: True if command executed successfully, False otherwise
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.stderr:
            print(f"Error: {result.stderr}")
            return False
        else:
            print(f"{result.stdout}")
            return True
    except Exception as e:
        print(f"Execution failed: {e}")
        return False

class FolderChangeHandler(FileSystemEventHandler):
    """Handles file system events for the watched folder"""
    def __init__(self, source, target, status_text):
        """Initialize the handler
        Args:
            source (str): Source directory path
            target (str): Target directory path 
            status_text (StringVar): For updating GUI status
        """
        self.source = source
        self.target = target
        self.status_text = status_text
        super().__init__()

    def on_created(self, event):
        """Handle file/directory creation events"""
        if event.is_directory:
            cmd = f'mklink /D "{os.path.join(self.target, os.path.basename(event.src_path))}" "{event.src_path}"'
        else:
            cmd = f'mklink "{os.path.join(self.target, os.path.basename(event.src_path))}" "{event.src_path}"'
        
        self.status_text.set(f"Creating link for new item: {cmd}")
        execute_admin_command(cmd)

    def on_deleted(self, event):
        """Handle file/directory deletion events"""
        target_path = os.path.join(self.target, os.path.basename(event.src_path))
        if os.path.lexists(target_path):  # Use lexists to check for broken symlinks
            if os.path.isdir(target_path):
                cmd = f'rmdir "{target_path}"'
            else:
                cmd = f'del /f "{target_path}"'
            self.status_text.set(f"Removing link: {cmd}")
            execute_admin_command(cmd)

    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory:
            target_path = os.path.join(self.target, os.path.basename(event.src_path))
            if os.path.lexists(target_path):  # Use lexists to check for broken symlinks
                if os.path.isdir(target_path):
                    cmd = f'rmdir "{target_path}"'
                else:
                    cmd = f'del /f "{target_path}"'
                execute_admin_command(cmd)
                
                cmd = f'mklink "{target_path}" "{event.src_path}"'
                self.status_text.set(f"Updating link: {cmd}")
                execute_admin_command(cmd)

    def on_moved(self, event):
        """Handle file/directory move/rename events"""
        old_target = os.path.join(self.target, os.path.basename(event.src_path))
        new_target = os.path.join(self.target, os.path.basename(event.dest_path))
        if os.path.lexists(old_target):  # Use lexists to check for broken symlinks
            if os.path.isdir(old_target):
                cmd = f'rmdir "{old_target}"'
            else:
                cmd = f'del /f "{old_target}"'
            execute_admin_command(cmd)
            
            if event.is_directory:
                cmd = f'mklink /D "{new_target}" "{event.dest_path}"'
            else:
                cmd = f'mklink "{new_target}" "{event.dest_path}"'
            self.status_text.set(f"Moving link: {cmd}")
            execute_admin_command(cmd)

def create_symlinks(source, target, status_text):
    """Create symbolic links from source to target directory
    Args:
        source (str): Source directory path
        target (str): Target directory path
        status_text (StringVar): For updating GUI status
    """
    if not os.path.exists(source):
        status_text.set(f"Source directory '{source}' does not exist")
        return
    if not os.path.exists(target):
        os.makedirs(target)

    success_count = 0
    for item in os.listdir(source):
        source_path = os.path.normpath(os.path.join(source, item))
        target_path = os.path.normpath(os.path.join(target, item))
        
        if os.path.lexists(target_path):  # Use lexists to check for broken symlinks
            status_text.set(f"Skipping '{target_path}', already exists")
            continue

        if os.path.isdir(source_path):
            cmd = f'mklink /D "{target_path}" "{source_path}"'
        else:
            cmd = f'mklink "{target_path}" "{source_path}"'
        
        status_text.set(f"Creating link: {cmd}")
        if execute_admin_command(cmd):
            success_count += 1
    
    status_text.set(f"Operation completed! Created {success_count} links\nNow watching for changes...")

    # Set up watchdog observer with recursive=True to watch subdirectories
    event_handler = FolderChangeHandler(source, target, status_text)
    observer = Observer()
    observer.schedule(event_handler, source, recursive=True)
    observer.start()

if __name__ == "__main__":
    # Check for admin privileges
    if not is_admin():
        messagebox.showerror("Error", "This script needs to be run as administrator")
    else:
        # Create main window
        root = tk.Tk()
        root.title("Folder Linker")
        root.geometry("600x300")
        
        # Create a fancy gradient icon for the application
        image = Image.new('RGB', (64, 64))
        draw = ImageDraw.Draw(image)
        for y in range(64):
            r = int(255 * (1 - y/64))
            g = int(100 + (155 * y/64))
            b = int(255 * y/64)
            draw.line([(0, y), (63, y)], fill=(r, g, b))
        
        # Configure GUI styles
        style = ttk.Style()
        style.configure("Custom.TFrame", background="#f0f0ff")
        style.configure("Custom.TButton", padding=5, font=('Helvetica', 9, 'bold'))
        style.configure("Custom.TLabel", font=('Helvetica', 9))
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10", style="Custom.TFrame")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Source directory selection
        source_var = tk.StringVar()
        ttk.Label(main_frame, text="Source:", style="Custom.TLabel").grid(row=0, column=0, sticky=tk.W, pady=2)
        source_entry = ttk.Entry(main_frame, textvariable=source_var, width=50)
        source_entry.grid(row=0, column=1, padx=2)
        ttk.Button(main_frame, text="Browse", style="Custom.TButton",
                  command=lambda: source_var.set(filedialog.askdirectory(title="Select Source Directory"))
                  ).grid(row=0, column=2)
        
        # Target directory selection
        target_var = tk.StringVar()
        ttk.Label(main_frame, text="Target:", style="Custom.TLabel").grid(row=1, column=0, sticky=tk.W, pady=2)
        target_entry = ttk.Entry(main_frame, textvariable=target_var, width=50)
        target_entry.grid(row=1, column=1, padx=2)
        ttk.Button(main_frame, text="Browse", style="Custom.TButton",
                  command=lambda: target_var.set(filedialog.askdirectory(title="Select Target Directory"))
                  ).grid(row=1, column=2)
        
        # Status display
        status_var = tk.StringVar(value="Ready to create links")
        status_label = ttk.Label(main_frame, textvariable=status_var, wraplength=580, style="Custom.TLabel")
        status_label.grid(row=2, column=0, columnspan=3, pady=10)
        
        def start_linking():
            """Start the linking process after validating inputs"""
            if not source_var.get() or not target_var.get():
                messagebox.showwarning("Warning", "Please select both directories first")
                return
            create_symlinks(source_var.get(), target_var.get(), status_var)
        
        # Create links button
        ttk.Button(main_frame, text="Create Links", style="Custom.TButton",
                  command=start_linking
                  ).grid(row=3, column=0, columnspan=3, pady=5)
        
        # Configure grid weights for proper resizing
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Set window icon
        photo_image = ImageTk.PhotoImage(image)
        root.iconphoto(True, photo_image)
        
        # Start the application
        root.mainloop()
