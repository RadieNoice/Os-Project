import json
import psutil
import time
import csv
import datetime
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Configuration file handling
CONFIG_FILE = os.path.join(os.getenv('APPDATA'), 'ProcessMonitorConfig.json')

def get_default_location():
    """Get the default location from config file or return system default"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('last_location', get_fallback_location())
        return get_fallback_location()
    except Exception:
        return get_fallback_location()

def get_fallback_location():
    """Fallback to original default if everything fails"""
    return os.path.join(os.path.expanduser('~'), 'Desktop', 'Os Project', 'logs')

def save_location(location):
    """Save the selected location to config file"""
    config = {'last_location': location}
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Error saving config: {e}")

# -----------------------
# Helper: Append Data to CSV
# -----------------------
def append_to_csv(new_data, filename="process_data.csv", location=None):
    """Appends process data to CSV with error handling."""
    if not new_data:
        return

    try:
        if not os.path.exists(location):
            os.makedirs(location)

        full_path = os.path.join(location, filename)
        file_exists = os.path.isfile(full_path)
        fieldnames = list(new_data[0].keys())

        with open(full_path, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(new_data)

        print(f"Appended {len(new_data)} rows to {full_path}")
    except Exception as e:
        messagebox.showerror("File Error", f"Error writing to CSV:\n{str(e)}")

# -----------------------
# Background Data Collector
# -----------------------
class DataCollectorThread(threading.Thread):
    def __init__(self, sampling_interval=5, stop_event=None, 
                 filename="process_data.csv", location=None):
        super().__init__()
        self.sampling_interval = sampling_interval
        self.stop_event = stop_event or threading.Event()
        self.filename = filename
        self.location = location or get_default_location()
        self.data = []

    def run(self):
        while not self.stop_event.is_set():
            new_rows = []
            timestamp = datetime.datetime.now().isoformat()
            
            for proc in psutil.process_iter(attrs=['pid', 'name']):
                try:
                    cpu_usage = proc.cpu_percent(interval=0.1) / psutil.cpu_count()
                    memory_usage = proc.memory_info().rss / (1024 * 1024)
                    
                    new_rows.append({
                        "timestamp": timestamp,
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu_usage": cpu_usage,
                        "memory_usage_MB": memory_usage
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            self.data.extend(new_rows)
            append_to_csv(new_rows, filename=self.filename, location=self.location)
            time.sleep(self.sampling_interval)

# -----------------------
# Enhanced Tkinter GUI
# -----------------------
class ProcessMonitorApp:
    def __init__(self, root):
        self.root = root
        self.collector_thread = None
        self.stop_event = None
        self.setup_ui()
        
    def setup_ui(self):
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TButton', padding=6, relief='flat')
        self.style.configure('Red.TButton', foreground='red')
        self.style.configure('Green.TButton', foreground='green')
        self.style.configure('Status.TLabel', padding=10, font=('Arial', 10))

        # Main container
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Directory selection
        dir_frame = ttk.LabelFrame(main_frame, text=" Save Location ", padding=10)
        dir_frame.grid(row=0, column=0, sticky='we', pady=5)
        
        self.location_entry = ttk.Entry(dir_frame, width=50)
        self.location_entry.grid(row=0, column=0, padx=5)
        self.location_entry.insert(0, get_default_location())
        
        ttk.Button(dir_frame, text="Browse", command=self.choose_directory)\
            .grid(row=0, column=1, padx=5)

        # Settings
        settings_frame = ttk.LabelFrame(main_frame, text=" Settings ", padding=10)
        settings_frame.grid(row=1, column=0, sticky='we', pady=5)
        
        ttk.Label(settings_frame, text="Filename:").grid(row=0, column=0, sticky='e')
        self.filename_entry = ttk.Entry(settings_frame, width=25)
        self.filename_entry.grid(row=0, column=1, padx=5, pady=2)
        self.filename_entry.insert(0, "process_data.csv")
        
        ttk.Label(settings_frame, text="Interval (sec):").grid(row=1, column=0, sticky='e')
        self.interval_spin = ttk.Spinbox(settings_frame, from_=1, to=60, width=5)
        self.interval_spin.grid(row=1, column=1, padx=5, pady=2, sticky='w')
        self.interval_spin.set(5)

        # Controls
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, pady=10)
        
        self.start_btn = ttk.Button(control_frame, text="Start Monitoring", 
                                  command=self.start_collection, style='Green.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop Monitoring", 
                                 command=self.stop_collection, style='Red.TButton', state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Status
        self.status_label = ttk.Label(main_frame, text="Status: Ready", style='Status.TLabel')
        self.status_label.grid(row=3, column=0)
        
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, sticky='we', pady=10)

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        dir_frame.columnconfigure(0, weight=1)

    def choose_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.location_entry.delete(0, tk.END)
            self.location_entry.insert(0, directory)
            save_location(directory)

    def start_collection(self):
        location = self.location_entry.get()
        filename = self.filename_entry.get()
        
        if not os.path.isdir(location):
            messagebox.showerror("Error", "Invalid directory path!")
            return
            
        try:
            interval = int(self.interval_spin.get())
            if interval < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid interval (1-60 seconds)")
            return

        save_location(location)  # Save the location when starting
        
        self.stop_event = threading.Event()
        self.collector_thread = DataCollectorThread(
            sampling_interval=interval,
            stop_event=self.stop_event,
            filename=filename,
            location=location
        )
        
        self.collector_thread.start()
        self.status_label.config(text="Status: Collecting data...", foreground='green')
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress.start()

    def stop_collection(self):
        if self.stop_event and self.collector_thread:
            self.stop_event.set()
            self.collector_thread.join()
            self.status_label.config(text="Status: Stopped", foreground='red')
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.progress.stop()

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Process Monitor Pro")
    root.geometry("600x400")
    app = ProcessMonitorApp(root)
    root.mainloop()