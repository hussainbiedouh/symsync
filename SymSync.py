# Import required modules
import os  # For file system operations
import ctypes  # For checking admin privileges
import subprocess  # For running system commands
import tkinter as tk  # GUI framework
from tkinter import filedialog, ttk, messagebox, PhotoImage  # GUI components
from watchdog.observers import Observer  # For monitoring file system changes
from watchdog.events import FileSystemEventHandler  # For handling file system events
from PIL import Image, ImageDraw, ImageTk  # For image handling and icons
import pystray  # For system tray integration
import threading  # For running the tray icon in a separate thread

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
        print(f"Executing command: {command}")  # Debug: Show the command being executed
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.stderr:
            print(f"Error: {result.stderr}")  # Debug: Print error output from the command
            return False
        else:
            print(f"Output: {result.stdout}")
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
        
        # Debug: Check existence of source file/folder and parent of target link
        print(f"[DEBUG] Attempting to link:")
        print(f"   Source: {source_path} (exists? {os.path.exists(source_path)})")
        parent_dir = os.path.dirname(target_path)
        print(f"   Target parent directory: {parent_dir} (exists? {os.path.exists(parent_dir)})")

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

###############################################################################
# NEW HELPER FUNCTIONS FOR MULTIPLE SOURCES

def create_symlinks_for_source(source, target, status_text):
    """Create symlinks for a given source's contents in a dedicated subfolder of target."""
    if not os.path.exists(source):
        status_text.set(f"Source directory '{source}' does not exist")
        return None, None

    # Directly use the target folder for symlinks
    target_sub = target

    success_count = 0
    for item in os.listdir(source):
        source_path = os.path.normpath(os.path.join(source, item))
        symlink_path = os.path.normpath(os.path.join(target_sub, item))
        
        # Debug: Check existence of source file/folder and parent of symlink
        print(f"[DEBUG] Attempting to link for source '{source}':")
        print(f"   Source: {source_path} (exists? {os.path.exists(source_path)})")
        parent_dir = os.path.dirname(symlink_path)
        print(f"   Symlink parent directory: {parent_dir} (exists? {os.path.exists(parent_dir)})")

        if os.path.lexists(symlink_path):
            status_text.set(f"Skipping '{symlink_path}', already exists")
            continue

        if os.path.isdir(source_path):
            cmd = f'mklink /D "{symlink_path}" "{source_path}"'
        else:
            cmd = f'mklink "{symlink_path}" "{source_path}"'
        
        status_text.set(f"Creating link: {cmd}")
        if execute_admin_command(cmd):
            success_count += 1

    status_text.set(f"Operation completed! Created {success_count} links for source '{source}'")
    
    # Start a watchdog observer for this source pointing to its subfolder
    event_handler = FolderChangeHandler(source, target_sub, status_text)
    observer = Observer()
    observer.schedule(event_handler, source, recursive=True)
    observer.start()

    status_text.set(status_text.get() + "\nNow watching for changes...")
    return observer, target_sub

# Global dictionaries to track active watchers and UI items
source_watchers = {}
source_rows = {}

def add_source():
    """Triggered by the '+' button to add a new source to be watched."""
    global source_watchers, source_rows
    if not target_var.get():
        messagebox.showwarning("Warning", "Please select the target directory first")
        return
    new_source = filedialog.askdirectory(title="Select Source Directory")
    if not new_source:
        return
    # Ensure the selected source is not the same as the target directory
    if os.path.normcase(os.path.normpath(new_source)) == os.path.normcase(os.path.normpath(target_var.get())):
        messagebox.showwarning("Warning", "Source cannot be the same as the target!")
        return
    if new_source in source_watchers:
        messagebox.showinfo("Info", f"Source '{new_source}' is already being watched")
        return
    
    # Create UI row inside the sources_frame
    row_frame = ttk.Frame(sources_frame, style="Custom.TFrame")
    row_frame.pack(fill='x', pady=2)
    label = ttk.Label(row_frame, text=new_source, style="Custom.TLabel")
    label.pack(side=tk.LEFT, padx=5, expand=True, anchor=tk.W)
    remove_btn = ttk.Button(row_frame, text="-", style="Custom.TButton",
                            command=lambda: remove_source(new_source))
    remove_btn.pack(side=tk.RIGHT, padx=5)
    source_rows[new_source] = row_frame

    # Create symlinks for the new source and start its watchdog observer
    observer, _ = create_symlinks_for_source(new_source, target_var.get(), status_var)
    if observer is not None:
        source_watchers[new_source] = observer

def remove_source(source):
    """Stop watching a source and remove its created symlinks from the target."""
    global source_watchers, source_rows
    # Stop the watchdog observer if active
    if source in source_watchers:
        observer = source_watchers[source]
        observer.stop()
        observer.join()
        del source_watchers[source]
    
    # Remove symlinks in the target directory that belong to this source
    target_directory = target_var.get()
    for item in os.listdir(target_directory):
         full_path = os.path.join(target_directory, item)
         if os.path.islink(full_path):
             try:
                 link_target = os.readlink(full_path)
                 # Check if the symlink's target starts with the removed source path (case-insensitive)
                 if os.path.normcase(os.path.normpath(link_target)).startswith(os.path.normcase(os.path.normpath(source))):
                     if os.path.isdir(full_path):
                         cmd = f'rmdir "{full_path}"'
                     else:
                         cmd = f'del /f "{full_path}"'
                     execute_admin_command(cmd)
             except Exception as e:
                 print(f"Error reading symlink: {full_path} - {e}")

    # Remove the UI row for this source
    if source in source_rows:
        source_rows[source].destroy()
        del source_rows[source]
    
    status_var.set(f"Stopped watching source '{source}' and removed its links.")

# New helper functions to handle target change cleanup
def cleanup_target_symlinks(target):
    """Remove all symlinks from the target directory."""
    for item in os.listdir(target):
         full_path = os.path.join(target, item)
         if os.path.islink(full_path):
              if os.path.isdir(full_path):
                  cmd = f'rmdir "{full_path}"'
              else:
                  cmd = f'del /f "{full_path}"'
              execute_admin_command(cmd)

def change_target():
    """Handle target directory change by asking user to remove symlinks in the current target."""
    new_target = filedialog.askdirectory(title="Select Target Directory")
    if new_target:
         old_target = target_var.get()
         # If there is an old target and it differs from the new one, ask for cleanup
         if old_target and os.path.normcase(os.path.normpath(old_target)) != os.path.normcase(os.path.normpath(new_target)):
              answer = messagebox.askyesno("Confirm", "Do you want to remove the symlinks that are already made in the current target?")
              if answer:
                   cleanup_target_symlinks(old_target)
         target_var.set(new_target)
         
         # For each active source, update symlinks in the new target if they don't already exist.
         # Stop the previous watchdog observer and reinitialize it for the new target.
         for src, obs in list(source_watchers.items()):
              obs.stop()
              obs.join()
              # Re-create symlinks for this source in the new target.
              # The underlying function will skip creation of symlinks that are already present.
              observer, _ = create_symlinks_for_source(src, new_target, status_var)
              if observer is not None:
                   source_watchers[src] = observer
              else:
                   # Optionally remove the source if creation fails.
                   remove_source(src)

def create_tray_image():
    """Create a beautiful tray icon with letters 'SS'."""
    from PIL import Image, ImageDraw, ImageFont
    # Create a larger image for better quality
    size = 128
    image = Image.new('RGBA', (size, size), color=(0,0,0,0))
    draw = ImageDraw.Draw(image)
    
    # Create a gradient background
    for y in range(size):
        r = int(100 + (y/size) * 50)  # Subtle red gradient
        g = int(50 + (y/size) * 30)   # Subtle green gradient
        b = int(200 + (y/size) * 55)  # Strong blue gradient
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    
    # Draw rounded corners
    radius = 20
    draw.rounded_rectangle([0, 0, size-1, size-1], radius, fill=None,
                         outline=(255,255,255,128), width=3)
    
    # Add 'SS' text with larger font size 🔍
    try:
        font = ImageFont.truetype("arial.ttf", size=80)  # Increased from 60 to 80
    except:
        font = ImageFont.load_default()
    
    # Center the text
    text = "SS"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    # Draw text with white color and slight shadow
    draw.text((x+2, y+2), text, font=font, fill=(0,0,0,128))  # Shadow
    draw.text((x, y), text, font=font, fill=(255,255,255))  # Main text
    
    # Resize to final dimensions while maintaining quality
    return image.resize((64, 64), Image.Resampling.LANCZOS)

def restore_window(icon, item):
    """Callback to restore the app window from the tray."""
    root.deiconify()
    root.state('normal')
    icon.stop()

def quit_app(icon, item):
    """Callback to quit the application using the tray icon."""
    icon.stop()
    root.destroy()

def start_tray_icon():
    """Create and run the tray icon."""
    image = create_tray_image()
    tray_icon = pystray.Icon("Folder Linker", image, "Folder Linker", menu=pystray.Menu(
        pystray.MenuItem("Restore", restore_window),
        pystray.MenuItem("Quit", quit_app)
    ))
    tray_icon.run()

def minimize_to_tray(event=None):
    """When minimized, hide the window and show the system tray icon."""
    if root.state() == 'iconic':
        root.withdraw()
        threading.Thread(target=start_tray_icon, daemon=True).start()

def on_closing():
    """Override close event: ask for confirmation and, if not quitting, minimize to tray."""
    if messagebox.askokcancel("Quit", "Do you really want to quit?"):
        root.destroy()
    else:
        root.iconify()

if __name__ == "__main__":
    # Check for admin privileges
    if not is_admin():
        messagebox.showerror("Error", "This script needs to be run as administrator")
    else:
        # Create main window
        root = tk.Tk()
        root.title("Folder Linker")
        root.geometry("600x400")  # Increased height for the new layout

        # Set the application icon to be the same as the tray icon 💡
        tray_img_pil = create_tray_image()
        tray_img_tk = ImageTk.PhotoImage(tray_img_pil)
        root.iconphoto(True, tray_img_tk)
        root._icon = tray_img_tk  # Store a reference to prevent GC

        # Configure GUI styles
        style = ttk.Style()
        style.configure("Custom.TFrame", background="#f0f0ff")
        style.configure("Custom.TButton", padding=5, font=('Helvetica', 9, 'bold'))
        style.configure("Custom.TLabel", font=('Helvetica', 9))
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10", style="Custom.TFrame")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Target directory selection (Row 0)
        target_var = tk.StringVar()
        ttk.Label(main_frame, text="Target:", style="Custom.TLabel").grid(row=0, column=0, sticky=tk.W, pady=2)
        target_entry = ttk.Entry(main_frame, textvariable=target_var, width=50)
        target_entry.grid(row=0, column=1, padx=2)
        ttk.Button(main_frame, text="Browse", style="Custom.TButton",
                  command=change_target
                  ).grid(row=0, column=2)
        
        # Watched Sources frame (Row 1)
        sources_frame = ttk.LabelFrame(main_frame, text="Watched Sources", style="Custom.TFrame", padding="5")
        sources_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # + Add Source button (Row 2)
        add_source_btn = ttk.Button(main_frame, text="+ Add Source", style="Custom.TButton", command=add_source)
        add_source_btn.grid(row=2, column=0, columnspan=3, pady=5)
        
        # Status display (Row 3)
        status_var = tk.StringVar(value="Ready to add sources")
        status_label = ttk.Label(main_frame, textvariable=status_var, wraplength=580, style="Custom.TLabel")
        status_label.grid(row=3, column=0, columnspan=3, pady=10)
        
        # Configure grid weights for proper resizing
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Bind the minimize event to minimize_to_tray and override the close event
        root.bind("<Unmap>", minimize_to_tray)
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Start the application
        root.mainloop()
