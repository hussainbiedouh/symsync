# Import required modules
import os  # For file system operations
import sys  # For system operations
import ctypes  # For checking admin privileges
import subprocess  # For running system commands
import tkinter as tk  # GUI framework
from tkinter import filedialog, ttk, messagebox, PhotoImage  # GUI components
from watchdog.observers import Observer  # For monitoring file system changes
from watchdog.events import FileSystemEventHandler  # For handling file system events
from PIL import Image, ImageDraw, ImageTk  # For image handling and icons
import pystray  # For system tray integration
import threading  # For running the tray icon in a separate thread
import json  # For settings persistence
import tempfile  # For system temp folder
import uuid  # For unique link IDs
import msvcrt  # For file locking (Windows)
from datetime import datetime  # For timestamps
import time  # For periodic intervals

# Settings and lock file paths
SETTINGS_FILE = os.path.join(tempfile.gettempdir(), "symsync_settings.json")
LOCK_FILE = os.path.join(tempfile.gettempdir(), "symsync.lock")

# Modern LIGHT color palette
COLORS = {
    'bg_primary': '#ffffff',         # White background
    'bg_secondary': '#f8f9fa',       # Light gray background
    'bg_hover': '#e9ecef',           # Hover background
    'accent': '#4361ee',             # Primary accent (blue)
    'accent_hover': '#3a56d4',       # Accent hover
    'accent_light': '#e8ecff',       # Light accent
    'success': '#10b981',            # Success green
    'success_light': '#d1fae5',      # Light green
    'warning': '#f59e0b',            # Warning yellow
    'danger': '#ef4444',             # Danger red
    'danger_light': '#fee2e2',       # Light red
    'text_primary': '#1f2937',       # Dark text
    'text_secondary': '#6b7280',     # Gray text
    'text_muted': '#9ca3af',         # Muted text
    'border': '#e5e7eb',             # Border color
    'border_focus': '#4361ee',       # Focus border
    'card_bg': '#ffffff',            # Card background
    'shadow': '#00000010',           # Shadow color
}


class SingleInstance:
    """Ensures only one instance of the application runs"""
    def __init__(self):
        self.lock_file = None
        self.is_locked = False
    
    def try_lock(self):
        """Try to acquire the lock. Returns True if successful."""
        try:
            self.lock_file = open(LOCK_FILE, 'w')
            msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            self.is_locked = True
            return True
        except (IOError, OSError):
            return False
    
    def release(self):
        """Release the lock"""
        if self.lock_file:
            try:
                if self.is_locked:
                    msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                self.lock_file.close()
            except:
                pass


def is_admin():
    """Check if the script is running with administrative privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def execute_admin_command(command):
    """Execute a command with administrative privileges"""
    try:
        print(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.stderr:
            print(f"Error: {result.stderr}")
            return False
        else:
            print(f"Output: {result.stdout}")
            return True
    except Exception as e:
        print(f"Execution failed: {e}")
        return False


class LinkConfiguration:
    """Represents a single link configuration with multiple sources → one target"""
    def __init__(self, name="New Link", target_path="", link_id=None):
        self.id = link_id or str(uuid.uuid4())[:8]
        self.name = name
        self.target_path = target_path
        self.sources = {}  # source_path -> observer
        self.is_active = False
        self.status = "Not configured"
        self.logs = []  # List of status history
        self.rescan_interval = 10  # Default 10 seconds
        self.last_rescan = 0  # Timestamp of last rescan

    
    def to_dict(self):
        """Serialize to dictionary for JSON storage"""
        return {
            "id": self.id,
            "name": self.name,
            "target_path": self.target_path,
            "sources": list(self.sources.keys()),
            "is_active": self.is_active,
            "logs": self.logs[-50:],  # Keep last 50 logs only
            "rescan_interval": self.rescan_interval
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create LinkConfiguration from dictionary"""
        link = cls(
            name=data.get("name", "New Link"),
            target_path=data.get("target_path", ""),
            link_id=data.get("id")
        )
        for source in data.get("sources", []):
            link.sources[source] = None
        link.is_active = data.get("is_active", False)
        link.logs = data.get("logs", [])
        link.rescan_interval = data.get("rescan_interval", 10)
        return link


class FolderChangeHandler(FileSystemEventHandler):
    """Handles file system events for the watched folder"""
    def __init__(self, source, target, update_status_callback):
        self.source = os.path.normpath(source)
        self.target = target
        self.update_status = update_status_callback
        super().__init__()

    def _is_direct_child(self, path):
        """Check if the path is a direct child of the source directory"""
        path_parts = os.path.normpath(path).split(os.sep)
        source_parts = self.source.split(os.sep)
        
        if len(path_parts) != len(source_parts) + 1:
            return False
            
        for i in range(len(source_parts)):
            if source_parts[i].lower() != path_parts[i].lower():
                return False
                
        return True

    def on_created(self, event):
        if not self._is_direct_child(event.src_path):
            return
            
        target_path = os.path.join(self.target, os.path.basename(event.src_path))
        
        if os.path.lexists(target_path) and event.is_directory and os.path.isdir(target_path):
            self.update_status(f"Merging: {os.path.basename(event.src_path)}")
            merge_directory_contents(event.src_path, target_path, self.update_status)
        else:
            if os.path.lexists(target_path):
                return
                
            if event.is_directory:
                cmd = f'mklink /D "{target_path}" "{event.src_path}"'
            else:
                cmd = f'mklink "{target_path}" "{event.src_path}"'
            
            self.update_status(f"Created: {os.path.basename(event.src_path)}")
            execute_admin_command(cmd)

    def on_deleted(self, event):
        if not self._is_direct_child(event.src_path):
            return
            
        target_path = os.path.join(self.target, os.path.basename(event.src_path))
        if os.path.lexists(target_path):
            if os.path.isdir(target_path):
                cmd = f'rmdir "{target_path}"'
            else:
                cmd = f'del /f "{target_path}"'
            self.update_status(f"Removed: {os.path.basename(event.src_path)}")
            execute_admin_command(cmd)

    def on_modified(self, event):
        if not self._is_direct_child(event.src_path):
            return
            
        if not event.is_directory:
            target_path = os.path.join(self.target, os.path.basename(event.src_path))
            if os.path.lexists(target_path):
                if os.path.isdir(target_path):
                    cmd = f'rmdir "{target_path}"'
                else:
                    cmd = f'del /f "{target_path}"'
                execute_admin_command(cmd)
                
                cmd = f'mklink "{target_path}" "{event.src_path}"'
                self.update_status(f"Updated: {os.path.basename(event.src_path)}")
                execute_admin_command(cmd)

    def on_moved(self, event):
        src_is_direct = self._is_direct_child(event.src_path)
        dest_is_direct = self._is_direct_child(event.dest_path)
        
        if not (src_is_direct or dest_is_direct):
            return
            
        old_target = os.path.join(self.target, os.path.basename(event.src_path))
        new_target = os.path.join(self.target, os.path.basename(event.dest_path))
        
        if src_is_direct and os.path.lexists(old_target):
            if os.path.isdir(old_target):
                cmd = f'rmdir "{old_target}"'
            else:
                cmd = f'del /f "{old_target}"'
            execute_admin_command(cmd)
        
        if dest_is_direct:
            if os.path.lexists(new_target) and event.is_directory and os.path.isdir(new_target):
                self.update_status(f"Merging: {os.path.basename(event.dest_path)}")
                merge_directory_contents(event.dest_path, new_target, self.update_status)
            else:
                if os.path.lexists(new_target):
                    return
                    
                if event.is_directory:
                    cmd = f'mklink /D "{new_target}" "{event.dest_path}"'
                else:
                    cmd = f'mklink "{new_target}" "{event.dest_path}"'
                self.update_status(f"Moved: {os.path.basename(event.dest_path)}")
                execute_admin_command(cmd)


def merge_directory_contents(source_dir, target_dir, update_status):
    """Merge contents of source_dir into target_dir by creating symlinks."""
    success_count = 0
    
    if os.path.islink(target_dir):
        actual_target_dir = os.readlink(target_dir)
    else:
        actual_target_dir = target_dir
    
    if not os.path.exists(actual_target_dir):
        os.makedirs(actual_target_dir)
    
    for item in os.listdir(source_dir):
        source_path = os.path.normpath(os.path.join(source_dir, item))
        symlink_path = os.path.normpath(os.path.join(actual_target_dir, item))
        
        if os.path.lexists(symlink_path):
            if os.path.isdir(source_path) and os.path.isdir(symlink_path):
                success_count += merge_directory_contents(source_path, symlink_path, update_status)
                continue
            else:
                continue
        
        if os.path.isdir(source_path):
            cmd = f'mklink /D "{symlink_path}" "{source_path}"'
        else:
            cmd = f'mklink "{symlink_path}" "{source_path}"'
        
        if execute_admin_command(cmd):
            success_count += 1
    
    return success_count


def create_symlinks_for_source(source, target, update_status):
    """Create symlinks for a single source and start watching."""
    if not os.path.exists(source):
        update_status(f"Source not found: {source}")
        return None
    
    if not os.path.exists(target):
        os.makedirs(target)
    
    # Use the merge logic which effectively creates the symlinks
    # Pass a dummy callback if you don't want verbose spam during this phase, 
    # or pass update_status to let merge recursive calls update status.
    success_count = merge_directory_contents(source, target, update_status)
    
    update_status(f"🔗 Linked {success_count} items from {os.path.basename(source)}")

    event_handler = FolderChangeHandler(source, target, update_status)
    observer = Observer()
    observer.schedule(event_handler, source, recursive=True)
    observer.start()
    
    return observer


class ModernButton(tk.Canvas):
    """A modern styled button with hover effects"""
    def __init__(self, parent, text, command=None, style='primary', width=120, height=36, **kwargs):
        super().__init__(parent, width=width, height=height, 
                        highlightthickness=0, bg=COLORS['bg_primary'], **kwargs)
        
        self.command = command
        self.text = text
        self.width = width
        self.height = height
        self.style = style
        self.enabled = True
        
        self.styles = {
            'primary': {
                'bg': COLORS['accent'],
                'hover': COLORS['accent_hover'],
                'text': '#ffffff'
            },
            'success': {
                'bg': COLORS['success'],
                'hover': '#0ea271',
                'text': '#ffffff'
            },
            'danger': {
                'bg': COLORS['danger'],
                'hover': '#dc2626',
                'text': '#ffffff'
            },
            'secondary': {
                'bg': COLORS['bg_secondary'],
                'hover': COLORS['bg_hover'],
                'text': COLORS['text_primary'],
                'border': COLORS['border']
            }
        }
        
        self.current_bg = self.styles[style]['bg']
        self.draw_button()
        
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.bind('<Button-1>', self.on_click)
    
    def draw_button(self):
        """Draw the rounded button"""
        self.delete('all')
        radius = 6
        
        bg_color = self.current_bg if self.enabled else COLORS['bg_hover']
        
        # Draw border for secondary style
        if self.style == 'secondary' and self.enabled:
            self.create_rounded_rect(1, 1, self.width-1, self.height-1, radius, 
                                    fill=bg_color, outline=COLORS['border'])
        else:
            self.create_rounded_rect(1, 1, self.width-1, self.height-1, radius, 
                                    fill=bg_color, outline='')
        
        text_color = self.styles[self.style]['text'] if self.enabled else COLORS['text_muted']
        self.create_text(self.width//2, self.height//2, text=self.text, 
                        fill=text_color, font=('Segoe UI', 9, 'bold'))
    
    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Create a rounded rectangle"""
        points = [
            x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius,
            x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2,
            x1, y2, x1, y2-radius, x1, y1+radius, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def on_enter(self, event):
        if self.enabled:
            self.current_bg = self.styles[self.style]['hover']
            self.draw_button()
            self.config(cursor='hand2')
    
    def on_leave(self, event):
        if self.enabled:
            self.current_bg = self.styles[self.style]['bg']
            self.draw_button()
    
    def on_click(self, event):
        if self.enabled and self.command:
            self.command()
    
    def set_enabled(self, enabled):
        self.enabled = enabled
        self.current_bg = self.styles[self.style]['bg']
        self.draw_button()
        self.config(cursor='hand2' if enabled else 'arrow')


class ModernEntry(tk.Frame):
    """A modern styled entry with border"""
    def __init__(self, parent, textvariable=None, width=40, **kwargs):
        super().__init__(parent, bg=COLORS['bg_primary'])
        
        self.border_frame = tk.Frame(self, bg=COLORS['border'], padx=1, pady=1)
        self.border_frame.pack(fill=tk.BOTH, expand=True)
        
        self.entry = tk.Entry(self.border_frame, 
                             textvariable=textvariable,
                             font=('Segoe UI', 10),
                             bg=COLORS['bg_primary'],
                             fg=COLORS['text_primary'],
                             insertbackground=COLORS['accent'],
                             relief='flat',
                             width=width)
        self.entry.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        
        self.entry.bind('<FocusIn>', self.on_focus_in)
        self.entry.bind('<FocusOut>', self.on_focus_out)
    
    def on_focus_in(self, event):
        self.border_frame.config(bg=COLORS['accent'])
    
    def on_focus_out(self, event):
        self.border_frame.config(bg=COLORS['border'])
    
    def config(self, **kwargs):
        if 'state' in kwargs:
            self.entry.config(state=kwargs['state'])


class RoundedFrame(tk.Canvas):
    """A Frame-like container with rounded corners"""
    def __init__(self, parent, bg_color=COLORS['card_bg'], radius=15, padding=10, **kwargs):
        super().__init__(parent, highlightthickness=0, bg=parent['bg'], **kwargs)
        
        self.radius = radius
        self.bg_color = bg_color
        self.padding = padding
        
        self.inner_frame = tk.Frame(self, bg=bg_color)
        self.window_item = self.create_window(0, 0, window=self.inner_frame, anchor='nw')
        
        self.bind('<Configure>', self.on_configure)
    
    def on_configure(self, event):
        w, h = event.width, event.height
        self.delete('bg')
        
        # Draw rounded rect background
        self.create_rounded_rect(0, 0, w, h, self.radius, fill=self.bg_color, outline=COLORS['border'], tags='bg')
        self.tag_lower('bg')
        
        # Resize inner frame to fit inside with padding
        # Ensure we don't go negative
        inner_w = max(1, w - (self.padding * 2))
        inner_h = max(1, h - (self.padding * 2))
        
        self.coords(self.window_item, self.padding, self.padding)
        self.itemconfigure(self.window_item, width=inner_w, height=inner_h)
    
    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius,
            x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2,
            x1, y2, x1, y2-radius, x1, y1+radius, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)


class SymSyncApp:
    """Main application class with modern light theme UI"""
    
    def __init__(self, root, single_instance):
        self.root = root
        self.single_instance = single_instance
        self.root.title("SymSync")
        self.root.geometry("1050x720")
        self.root.configure(bg=COLORS['bg_secondary'])
        self.root.minsize(900, 600)
        
        self.links = {}
        self.selected_link_id = None
        self.stop_event = threading.Event()
        
        self.setup_icon()
        self.create_ui()
        self.load_settings()
        
        # Start background rescan thread
        threading.Thread(target=self.rescan_active_links, daemon=True).start()
        
        self.root.bind("<Unmap>", self.minimize_to_tray)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_icon(self):
        """Set up the application and tray icon"""
        tray_img_pil = self.create_tray_image()
        self.tray_img_tk = ImageTk.PhotoImage(tray_img_pil)
        self.root.iconphoto(True, self.tray_img_tk)
    
    def create_tray_image(self):
        """Create a modern tray icon"""
        from PIL import ImageFont
        size = 128
        image = Image.new('RGBA', (size, size), color=(0,0,0,0))
        draw = ImageDraw.Draw(image)
        
        # Blue gradient background
        for y in range(size):
            ratio = y / size
            r = int(67 * (1 - ratio) + 99 * ratio)
            g = int(97 * (1 - ratio) + 102 * ratio)  
            b = int(238 * (1 - ratio) + 241 * ratio)
            draw.line([(0, y), (size, y)], fill=(r, g, b))
        
        radius = 24
        draw.rounded_rectangle([0, 0, size-1, size-1], radius, fill=None,
                             outline=(255,255,255,200), width=4)
        
        try:
            font = ImageFont.truetype("segoeui.ttf", size=72)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", size=72)
            except:
                font = ImageFont.load_default()
        
        text = "SS"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - 5
        
        draw.text((x+2, y+2), text, font=font, fill=(0,0,0,60))
        draw.text((x, y), text, font=font, fill=(255,255,255))
        
        return image.resize((64, 64), Image.Resampling.LANCZOS)
    
    def create_ui(self):
        """Create the main modern UI"""
        main_container = tk.Frame(self.root, bg=COLORS['bg_secondary'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        self.create_header(main_container)
        
        content = tk.Frame(main_container, bg=COLORS['bg_secondary'])
        content.pack(fill=tk.BOTH, expand=True, pady=(15, 0))
        
        self.create_left_pane(content)
        self.create_right_pane(content)
    
    def create_header(self, parent):
        """Create the header with logo and title"""
        header = tk.Frame(parent, bg=COLORS['bg_secondary'], height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title_frame = tk.Frame(header, bg=COLORS['bg_secondary'])
        title_frame.pack(side=tk.LEFT)
        
        # Icon rect
        icon_canvas = tk.Canvas(title_frame, width=40, height=40, 
                               bg=COLORS['bg_secondary'], highlightthickness=0)
        icon_canvas.pack(side=tk.LEFT, padx=(0, 10))
        
        # Draw purple rounded rect
        purple_color = "#6b2c91" # Deep purple
        
        # Draw rounded rect manually or using polygon
        def create_rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
            points = [
                x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius,
                x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2,
                x1, y2, x1, y2-radius, x1, y1+radius, x1, y1,
            ]
            return canvas.create_polygon(points, smooth=True, **kwargs)

        create_rounded_rect(icon_canvas, 2, 2, 38, 38, 8, fill=purple_color, outline='')
        
        # "SS" text in bottom right
        icon_canvas.create_text(34, 34, text="SS", font=('Segoe UI', 11, 'bold'), 
                               fill='white', anchor='se')
        
        title = tk.Label(title_frame, text="SymSync", font=('Segoe UI', 20, 'bold'),
                        bg=COLORS['bg_secondary'], fg=COLORS['text_primary'])
        title.pack(side=tk.LEFT)
        
        subtitle = tk.Label(title_frame, text="Symbolic Link Manager", 
                           font=('Segoe UI', 11),
                           bg=COLORS['bg_secondary'], fg=COLORS['text_muted'])
        subtitle.pack(side=tk.LEFT, padx=(12, 0), pady=(6, 0))
    
    def create_left_pane(self, parent):
        """Create the left pane with links list"""
        # Card container (RoundedFrame)
        left_card = RoundedFrame(parent, bg_color=COLORS['card_bg'], width=250)
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        left_card.pack_propagate(False)
        
        inner = left_card.inner_frame
        # Reuse inner frame for content, no need to pack it again as RoundedFrame handles it
        # Just ensure we add widgets to 'inner'
        
        header = tk.Label(inner, text="LINKS", font=('Segoe UI', 9, 'bold'),
                         bg=COLORS['card_bg'], fg=COLORS['text_muted'])
        header.pack(anchor=tk.W, pady=(0, 12))
        
        self.new_link_btn = ModernButton(inner, text="+ New Link", 
                                         command=self.create_new_link,
                                         style='primary', width=220)
        self.new_link_btn.pack(fill=tk.X, pady=(0, 15))
        
        # Links list
        list_frame = tk.Frame(inner, bg=COLORS['bg_secondary'], 
                             highlightbackground=COLORS['border'], highlightthickness=1)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame, bg=COLORS['bg_secondary'])
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.links_listbox = tk.Listbox(list_frame, 
                                        yscrollcommand=scrollbar.set,
                                        font=('Segoe UI', 10),
                                        bg=COLORS['bg_primary'],
                                        fg=COLORS['text_primary'],
                                        selectbackground=COLORS['accent_light'],
                                        selectforeground=COLORS['text_primary'],
                                        activestyle='none',
                                        relief='flat',
                                        highlightthickness=0,
                                        bd=0)
        self.links_listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        scrollbar.config(command=self.links_listbox.yview)
        
        self.links_listbox.bind('<<ListboxSelect>>', self.on_link_selected)
    
    def create_right_pane(self, parent):
        """Create the right pane with link details"""
        # Card container (RoundedFrame)
        right_card = RoundedFrame(parent, bg_color=COLORS['card_bg'])
        right_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.detail_inner = right_card.inner_frame
         # Reuse inner frame for content
        
        header = tk.Label(self.detail_inner, text="LINK DETAILS", 
                         font=('Segoe UI', 9, 'bold'),
                         bg=COLORS['card_bg'], fg=COLORS['text_muted'])
        header.pack(anchor=tk.W, pady=(0, 15))
        
        form = tk.Frame(self.detail_inner, bg=COLORS['card_bg'])
        form.pack(fill=tk.X)
        
        # Name field
        name_row = tk.Frame(form, bg=COLORS['card_bg'])
        name_row.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(name_row, text="Name", font=('Segoe UI', 10, 'bold'),
                bg=COLORS['card_bg'], fg=COLORS['text_secondary']).pack(anchor=tk.W)
        
        self.name_var = tk.StringVar()
        self.name_entry = ModernEntry(name_row, textvariable=self.name_var, width=50)
        self.name_entry.pack(fill=tk.X, pady=(4, 0))
        self.name_var.trace_add("write", self.on_name_changed)
        
        # Target field
        target_row = tk.Frame(form, bg=COLORS['card_bg'])
        target_row.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(target_row, text="Target Directory", font=('Segoe UI', 10, 'bold'),
                bg=COLORS['card_bg'], fg=COLORS['text_secondary']).pack(anchor=tk.W)
        
        target_input_row = tk.Frame(target_row, bg=COLORS['card_bg'])
        target_input_row.pack(fill=tk.X, pady=(4, 0))
        
        self.target_var = tk.StringVar()
        self.target_entry = ModernEntry(target_input_row, textvariable=self.target_var, width=45)
        self.target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.browse_target_btn = ModernButton(target_input_row, text="Browse", 
                                              command=self.browse_target,
                                              style='secondary', width=80, height=34)
        self.browse_target_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Sources section
        sources_frame = tk.Frame(self.detail_inner, bg=COLORS['card_bg'])
        sources_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        sources_header = tk.Frame(sources_frame, bg=COLORS['card_bg'])
        sources_header.pack(fill=tk.X)
        
        tk.Label(sources_header, text="Source Directories", font=('Segoe UI', 10, 'bold'),
                bg=COLORS['card_bg'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
        
        sources_btn_frame = tk.Frame(sources_header, bg=COLORS['card_bg'])
        sources_btn_frame.pack(side=tk.RIGHT)
        
        self.add_source_btn = ModernButton(sources_btn_frame, text="+ Add", 
                                           command=self.add_source,
                                           style='primary', width=70, height=28)
        self.add_source_btn.pack(side=tk.LEFT, padx=3)
        
        self.remove_source_btn = ModernButton(sources_btn_frame, text="- Remove", 
                                              command=self.remove_source,
                                              style='danger', width=80, height=28)
        self.remove_source_btn.pack(side=tk.LEFT, padx=3)
        
        # Sources list
        sources_list_frame = tk.Frame(sources_frame, bg=COLORS['bg_secondary'],
                                     highlightbackground=COLORS['border'], highlightthickness=1)
        sources_list_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        sources_scrollbar = tk.Scrollbar(sources_list_frame)
        sources_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.sources_listbox = tk.Listbox(sources_list_frame,
                                          yscrollcommand=sources_scrollbar.set,
                                          font=('Segoe UI', 9),
                                          bg=COLORS['bg_primary'],
                                          fg=COLORS['text_primary'],
                                          selectbackground=COLORS['accent_light'],
                                          selectforeground=COLORS['accent'],
                                          activestyle='none',
                                          relief='flat',
                                          highlightthickness=0,
                                          height=4)
        self.sources_listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        sources_scrollbar.config(command=self.sources_listbox.yview)
        
        # Status section
        status_frame = tk.Frame(self.detail_inner, bg=COLORS['bg_secondary'],
                               highlightbackground=COLORS['border'], highlightthickness=1)
        status_frame.pack(fill=tk.X, pady=(15, 0))
        
        status_inner = tk.Frame(status_frame, bg=COLORS['bg_secondary'])
        status_inner.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(status_inner, text="STATUS", font=('Segoe UI', 8, 'bold'),
                bg=COLORS['bg_secondary'], fg=COLORS['text_muted']).pack(anchor=tk.W)
        
        self.status_var = tk.StringVar(value="✨ Select or create a link to begin")
        self.status_label = tk.Label(status_inner, textvariable=self.status_var,
                                    font=('Segoe UI', 10, 'bold'),
                                    bg=COLORS['bg_secondary'], fg=COLORS['accent'],
                                    wraplength=500, justify=tk.LEFT)
        self.status_label.pack(anchor=tk.W, pady=(4, 0))
        
        # Rescan Interval
        rescan_frame = tk.Frame(self.detail_inner, bg=COLORS['card_bg'])
        rescan_frame.pack(fill=tk.X, pady=(20, 0))
        
        tk.Label(rescan_frame, text="Rescan Interval:", font=('Segoe UI', 9, 'bold'),
                bg=COLORS['card_bg'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
        
        self.rescan_options = {
            "1 sec": 1,
            "10 sec": 10,
            "30 sec": 30,
            "1 min": 60,
            "5 min": 300,
            "10 min": 600,
            "30 min": 1800,
            "1 h": 3600
        }
        
        self.rescan_var = tk.StringVar()
        self.rescan_combo = ttk.Combobox(rescan_frame, textvariable=self.rescan_var, 
                                        values=list(self.rescan_options.keys()),
                                        state="readonly", width=15)
        self.rescan_combo.pack(side=tk.LEFT, padx=(10, 0))
        self.rescan_combo.bind("<<ComboboxSelected>>", self.on_rescan_changed)
        
        # Action buttons
        btn_frame = tk.Frame(self.detail_inner, bg=COLORS['card_bg'])
        btn_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.start_btn = ModernButton(btn_frame, text="▶ Start", 
                                      command=self.start_link,
                                      style='success', width=100)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ModernButton(btn_frame, text="■ Stop", 
                                     command=self.stop_link,
                                     style='secondary', width=100)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.delete_btn = ModernButton(btn_frame, text="🗑 Delete", 
                                       command=self.delete_link,
                                       style='danger', width=100)
        self.delete_btn.pack(side=tk.LEFT)

        # Log Section
        log_label = tk.Label(self.detail_inner, text="ACTIVITY LOG", 
                         font=('Segoe UI', 9, 'bold'),
                         bg=COLORS['card_bg'], fg=COLORS['text_muted'])
        log_label.pack(anchor=tk.W, pady=(15, 5))

        log_frame = tk.Frame(self.detail_inner, bg=COLORS['bg_primary'],
                             highlightbackground=COLORS['border'], highlightthickness=1)
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_scrollbar = tk.Scrollbar(log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_listbox = tk.Listbox(log_frame,
                                      yscrollcommand=log_scrollbar.set,
                                      font=('Consolas', 9),
                                      bg=COLORS['bg_primary'],
                                      fg=COLORS['text_secondary'],
                                      selectbackground=COLORS['bg_primary'], # No selection highlight
                                      selectforeground=COLORS['text_secondary'],
                                      relief='flat',
                                      highlightthickness=0,
                                      height=6)
        self.log_listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        log_scrollbar.config(command=self.log_listbox.yview)
        
        self.set_controls_state(False)

    
    def set_controls_state(self, enabled):
        """Enable or disable right pane controls"""
        self.name_entry.config(state=tk.NORMAL if enabled else tk.DISABLED)
        self.target_entry.config(state=tk.NORMAL if enabled else tk.DISABLED)
        self.browse_target_btn.set_enabled(enabled)
        self.add_source_btn.set_enabled(enabled)
        self.remove_source_btn.set_enabled(enabled)
        self.start_btn.set_enabled(enabled)
        self.stop_btn.set_enabled(enabled)
        self.delete_btn.set_enabled(enabled)
        self.rescan_combo.config(state="readonly" if enabled else "disabled")
    
    def refresh_links_list(self):
        """Refresh the links listbox with colored status indicators"""
        self.links_listbox.delete(0, tk.END)
        idx = 0
        for link_id, link in self.links.items():
            # Use prefix to indicate status
            if link.is_active:
                prefix = "● "  # Filled circle
            else:
                prefix = "○ "  # Empty circle
            self.links_listbox.insert(tk.END, f"{prefix}{link.name}")
            
            # Color the text based on status
            if link.is_active:
                self.links_listbox.itemconfig(idx, fg=COLORS['success'])
            else:
                self.links_listbox.itemconfig(idx, fg=COLORS['danger'])
            idx += 1
    
    def refresh_sources_list(self):
        """Refresh the sources listbox for current link"""
        self.sources_listbox.delete(0, tk.END)
        if self.selected_link_id and self.selected_link_id in self.links:
            link = self.links[self.selected_link_id]
            for source in link.sources.keys():
                display = f"📁 {os.path.basename(source)}"
                self.sources_listbox.insert(tk.END, display)
    
    def create_new_link(self):
        """Create a new link configuration"""
        link = LinkConfiguration(name=f"Link {len(self.links) + 1}")
        self.links[link.id] = link
        self.refresh_links_list()
        
        self.links_listbox.selection_clear(0, tk.END)
        self.links_listbox.selection_set(tk.END)
        self.select_link(link.id)
        
        self.save_settings()
    
    def on_link_selected(self, event):
        """Handle link selection in listbox"""
        selection = self.links_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        link_ids = list(self.links.keys())
        if idx < len(link_ids):
            self.select_link(link_ids[idx])
    
    def select_link(self, link_id):
        """Display the selected link in the right pane"""
        if link_id not in self.links:
            return
        
        self.selected_link_id = link_id
        link = self.links[link_id]
        
        self.name_var.set(link.name)
        self.target_var.set(link.target_path)
        self.status_var.set(link.status)
        
        # Set rescan combo
        for text, val in self.rescan_options.items():
            if val == link.rescan_interval:
                self.rescan_var.set(text)
                break
        
        self.refresh_sources_list()
        
        self.log_listbox.delete(0, tk.END)
        for log in link.logs:
            self.log_listbox.insert(tk.END, log)
        self.log_listbox.yview(tk.END)

        
        self.set_controls_state(True)
    
    def on_name_changed(self, *args):
        """Handle name field changes"""
        if self.selected_link_id and self.selected_link_id in self.links:
            self.links[self.selected_link_id].name = self.name_var.get()
            self.refresh_links_list()
            
            link_ids = list(self.links.keys())
            if self.selected_link_id in link_ids:
                idx = link_ids.index(self.selected_link_id)
                self.links_listbox.selection_clear(0, tk.END)
                self.links_listbox.selection_set(idx)
            
            self.save_settings()
    
    def browse_target(self):
        """Browse for target directory"""
        directory = filedialog.askdirectory(title="Select Target Directory")
        if directory:
            # Check if this target is already used by another link
            normalized_dir = os.path.normcase(os.path.normpath(directory))
            for link_id, link in self.links.items():
                if link_id != self.selected_link_id:
                    if link.target_path:
                        existing_target = os.path.normcase(os.path.normpath(link.target_path))
                        if normalized_dir == existing_target:
                            messagebox.showwarning("Duplicate Target", 
                                f"This target folder is already used by link '{link.name}'.\n\n"
                                "Each link must have a unique target folder.")
                            return
            
            self.target_var.set(directory)
            if self.selected_link_id:
                self.links[self.selected_link_id].target_path = directory
                self.save_settings()
    
    def add_source(self):
        """Add a new source directory to the current link"""
        if not self.selected_link_id:
            return
        
        link = self.links[self.selected_link_id]
        
        if not link.target_path:
            messagebox.showwarning("Warning", "Please set the target directory first")
            return
        
        directory = filedialog.askdirectory(title="Select Source Directory")
        if not directory:
            return
        
        if os.path.normcase(os.path.normpath(directory)) == os.path.normcase(os.path.normpath(link.target_path)):
            messagebox.showwarning("Warning", "Source cannot be the same as the target!")
            return
        
        # Check for duplicate source (case-insensitive)
        normalized_dir = os.path.normcase(os.path.normpath(directory))
        for existing_source in link.sources.keys():
            if os.path.normcase(os.path.normpath(existing_source)) == normalized_dir:
                messagebox.showwarning("Duplicate Source", 
                    "This source folder is already added to this link.")
                return
        
        link.sources[directory] = None
        self.refresh_sources_list()
        self.save_settings()
        
        if link.is_active:
            observer = create_symlinks_for_source(directory, link.target_path, self.update_status)
            if observer:
                link.sources[directory] = observer
    
    def remove_source(self):
        """Remove selected source from current link"""
        if not self.selected_link_id:
            return
        
        selection = self.sources_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Please select a source to remove")
            return
        
        link = self.links[self.selected_link_id]
        source_list = list(link.sources.keys())
        source = source_list[selection[0]]
        
        if link.sources.get(source):
            link.sources[source].stop()
            link.sources[source].join()
        
        if messagebox.askyesno("Cleanup", f"Remove symlinks created from this source?"):
            self.cleanup_source_symlinks(source, link.target_path)
        
        del link.sources[source]
        self.refresh_sources_list()
        self.save_settings()
    
    def cleanup_source_symlinks(self, source, target):
        """Remove symlinks from target that point to source"""
        try:
            for item in os.listdir(target):
                full_path = os.path.join(target, item)
                if os.path.islink(full_path):
                    try:
                        link_target = os.readlink(full_path)
                        if os.path.normcase(os.path.normpath(link_target)).startswith(
                            os.path.normcase(os.path.normpath(source))):
                            if os.path.isdir(full_path):
                                cmd = f'rmdir "{full_path}"'
                            else:
                                cmd = f'del /f "{full_path}"'
                            execute_admin_command(cmd)
                    except:
                        pass
        except:
            pass
    
    def update_link_status(self, link_id, message):
        """Update status and logs for a specific link"""
        if link_id not in self.links:
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        link = self.links[link_id]
        link.status = message
        link.logs.append(log_entry)
        
        # Limit logs to 50 entries
        if len(link.logs) > 50:
            link.logs.pop(0)
            
        # Update UI if this is the selected link
        if self.selected_link_id == link_id:
            self.status_var.set(message)
            self.log_listbox.insert(tk.END, log_entry)
            self.log_listbox.yview(tk.END)
    
    def start_link(self):
        """Start watching all sources for the selected link"""
        if not self.selected_link_id:
            return
        
        link = self.links[self.selected_link_id]
        link.target_path = self.target_var.get()
        
        if not link.target_path:
            messagebox.showwarning("Warning", "Please set the target directory")
            return
        
        if not link.sources:
            messagebox.showwarning("Warning", "Please add at least one source directory")
            return
        
        if link.is_active:
            messagebox.showinfo("Info", "This link is already active")
            return
        
        self.update_link_status(link.id, "⏳ Starting...")
        
        update_callback = lambda msg: self.update_link_status(link.id, msg)
        
        for source in list(link.sources.keys()):
            observer = create_symlinks_for_source(source, link.target_path, update_callback)
            if observer:
                link.sources[source] = observer
        
        link.is_active = True
        self.update_link_status(link.id, f"✅ Watching {len(link.sources)} source(s)")
        self.refresh_links_list()
        self.refresh_links_list()
        self.save_settings()
    
    def stop_link(self):
        """Stop watching for the selected link"""
        if not self.selected_link_id:
            return
        
        link = self.links[self.selected_link_id]
        
        if not link.is_active:
            messagebox.showinfo("Info", "This link is not active")
            return
        
        for source, observer in link.sources.items():
            if observer:
                observer.stop()
                observer.join()
            link.sources[source] = None
        
        link.is_active = False
        self.update_link_status(link.id, "⏹️ Stopped")
        self.refresh_links_list()
        self.save_settings()
    
    def delete_link(self):
        """Delete the selected link"""
        if not self.selected_link_id:
            return
        
        if not messagebox.askyesno("Delete Link", "Are you sure you want to delete this link?"):
            return
        
        link = self.links[self.selected_link_id]
        
        for source, observer in link.sources.items():
            if observer:
                observer.stop()
                observer.join()
        
        if link.target_path and os.path.exists(link.target_path):
            if messagebox.askyesno("Cleanup", "Remove all symlinks created in the target?"):
                for source in link.sources.keys():
                    self.cleanup_source_symlinks(source, link.target_path)
        
        del self.links[self.selected_link_id]
        self.selected_link_id = None
        
        self.refresh_links_list()
        self.refresh_links_list()
        self.sources_listbox.delete(0, tk.END)
        self.log_listbox.delete(0, tk.END)
        self.set_controls_state(False)
        self.name_var.set("")
        self.target_var.set("")
        self.status_var.set("✨ Select or create a link to begin")
        
        self.save_settings()
    
    def save_settings(self):
        """Save all link configurations to temp file"""
        try:
            data = {"links": [link.to_dict() for link in self.links.values()]}
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving: {e}")
    
    def load_settings(self):
        """Load link configurations from temp file"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                
                for link_data in data.get("links", []):
                    link = LinkConfiguration.from_dict(link_data)
                    self.links[link.id] = link
                    
                    if link.is_active and link.target_path and link.sources:
                        link.is_active = False
                        for source in list(link.sources.keys()):
                            observer = create_symlinks_for_source(
                                source, link.target_path,
                                lambda msg, l=link: self.update_link_status(l.id, msg)
                            )
                            if observer:
                                link.sources[source] = observer
                        link.is_active = True
                        # Don't overwrite status here as it's set by callback or loaded
                
                self.refresh_links_list()
        except Exception as e:
            print(f"Error loading: {e}")
    
    def on_rescan_changed(self, event):
        """Handle rescan interval change"""
        if self.selected_link_id and self.selected_link_id in self.links:
            text = self.rescan_var.get()
            interval = self.rescan_options.get(text, 10)
            self.links[self.selected_link_id].rescan_interval = interval
            self.save_settings()

    def rescan_active_links(self):
        """Periodically rescan active links to restore deleted items"""
        while not self.stop_event.is_set():
            current_time = time.time()
            
            # Helper to check stop event while sleeping
            for _ in range(10): 
                if self.stop_event.is_set(): return
                time.sleep(0.1)

            try:
                # Use list() to avoid runtime error if dict changes size
                for link in list(self.links.values()):
                    if not link.is_active:
                        continue
                        
                    # Check if it's time to rescan this link
                    if current_time - link.last_rescan < link.rescan_interval:
                        continue
                        
                    link.last_rescan = current_time
                    
                    for source in list(link.sources.keys()):
                        try:
                            # We check safely in case user stopped/deleted link mid-loop
                            if not self.links.get(link.id): break
                            
                            count = merge_directory_contents(
                                source, 
                                link.target_path, 
                                lambda msg: self.update_link_status(link.id, msg)
                            )
                            
                            if count > 0:
                                self.update_link_status(link.id, f"♻️ Rescan restored {count} item(s)")
                                
                        except Exception as e:
                            print(f"Rescan error for {link.name}: {e}")
                            
            except Exception as e:
                print(f"Rescan loop error: {e}")

    def minimize_to_tray(self, event=None):
        """Minimize to system tray"""
        if self.root.state() == 'iconic':
            self.root.withdraw()
            threading.Thread(target=self.start_tray_icon, daemon=True).start()
    
    def start_tray_icon(self):
        """Create and run the tray icon"""
        image = self.create_tray_image()
        self.tray_icon = pystray.Icon("SymSync", image, "SymSync", menu=pystray.Menu(
            pystray.MenuItem("Restore", self.restore_window),
            pystray.MenuItem("Quit", self.quit_app)
        ))
        self.tray_icon.run()
    
    def restore_window(self, icon, item):
        """Restore from tray"""
        self.root.deiconify()
        self.root.state('normal')
        icon.stop()
    
    def quit_app(self, icon, item):
        """Quit application"""
        icon.stop()
        self.cleanup_and_exit()
    
    def cleanup_and_exit(self):
        """Clean up and exit"""
        self.stop_event.set()
        for link in self.links.values():
            for observer in link.sources.values():
                if observer:
                    observer.stop()
                    observer.join()
        self.single_instance.release()
        self.root.destroy()
    
    def on_closing(self):
        """Handle window close"""
        if messagebox.askokcancel("Quit", "Do you really want to quit?"):
            self.cleanup_and_exit()
        else:
            self.root.iconify()


def elevate():
    """Relaunch the script with administrative privileges"""
    try:
        if getattr(sys, 'frozen', False):
            # If running as compiled exe
            executable = sys.executable
            params = ' '.join(['"' + arg + '"' for arg in sys.argv[1:]])
            cmd = f'{params}'
        else:
            # If running as script
            executable = sys.executable
            script = os.path.abspath(sys.argv[0])
            params = ' '.join(['"' + arg + '"' for arg in sys.argv[1:]])
            cmd = f'"{script}" {params}'
        
        # Execute the script as admin
        # 0: hwnd (null)
        # "runas": verb for elevation
        # executable: path to interpreter or exe
        # cmd: parameters
        # None: directory (current)
        # 1: nShow (SW_SHOWNORMAL)
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, cmd, None, 1)
        
        if int(ret) > 32:
            return True
        else:
            return False
    except Exception as e:
        print(f"Elevation failed: {e}")
        return False


if __name__ == "__main__":
    # Check for admin privileges first
    if not is_admin():
        if elevate():
            sys.exit(0)
        else:
            messagebox.showerror("Administrator Required", 
                                "SymSync needs administrator privileges to create symbolic links.\n\n"
                                "Failed to elevate. Please run manualy as administrator.")
            sys.exit(1)

    # Check for single instance
    single_instance = SingleInstance()
    if not single_instance.try_lock():
        root = tk.Tk()
        root.withdraw() # Hide root window for simple message
        messagebox.showwarning("Already Running", 
                              "SymSync is already running.\n\n"
                              "Check the system tray for the running instance.")
        root.destroy()
        sys.exit(0)
    
    # Run the application
    root = tk.Tk()
    app = SymSyncApp(root, single_instance)
    root.mainloop()
