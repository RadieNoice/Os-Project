import psutil
import time
import csv
import datetime
import os
import threading
import tkinter as tk
from tkinter import filedialog

default_location = r"C:\Users\dhili\OneDrive\Desktop\Os Project\logs"

# -----------------------
# Helper: Append Data to CSV
# -----------------------
def append_to_csv(new_data, filename="process_data.csv", location=default_location):
    """
    Appends the provided process data to the CSV file at the given location.
    If the file does not exist, it creates the file and writes the header.
    """
    if not new_data:
        return

    # Ensure the location directory exists; if not, create it.
    if not os.path.exists(location):
        os.makedirs(location)

    # Build the full file path.
    full_path = os.path.join(location, filename)
    file_exists = os.path.isfile(full_path)
    fieldnames = list(new_data[0].keys())

    with open(full_path, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()  # Write header if file doesn't exist.
        writer.writerows(new_data)

    print(f"Appended {len(new_data)} rows to {full_path}")

# -----------------------
# Background Data Collector
# -----------------------
class DataCollectorThread(threading.Thread):
    def __init__(self, sampling_interval=5, stop_event=None, filename="process_data.csv", location=default_location):
        super().__init__()
        self.sampling_interval = sampling_interval
        self.stop_event = stop_event or threading.Event()
        self.filename = filename
        self.location = location
        self.data = []  # Optional: store all collected data in memory

    def run(self):
        while not self.stop_event.is_set():
            new_rows = []
            # Capture the current timestamp
            timestamp = datetime.datetime.now().isoformat()
            # Iterate over all running processes with basic info
            for proc in psutil.process_iter(attrs=['pid', 'name']):
                try:
                    pid = proc.info['pid']
                    name = proc.info['name']
                    # Get the CPU usage percentage (normalized by the number of cores)
                    cpu_usage = proc.cpu_percent(interval=0.1) / psutil.cpu_count()
                    # Get the memory usage in MB
                    memory_usage = proc.memory_info().rss / (1024 * 1024)
                    # Create a record for the current process
                    row = {
                        "timestamp": timestamp,
                        "pid": pid,
                        "name": name,
                        "cpu_usage": cpu_usage,
                        "memory_usage_MB": memory_usage
                    }
                    new_rows.append(row)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            # Optionally, store in memory (if you need a complete copy)
            self.data.extend(new_rows)
            # Append the newly collected rows to the CSV file every iteration.
            append_to_csv(new_rows, filename=self.filename, location=self.location)
            time.sleep(self.sampling_interval)

# -----------------------
# Tkinter GUI Setup
# -----------------------
collector_thread = None
stop_event = None

def choose_directory():
    """Allows the user to select a directory via a dialog."""
    directory = filedialog.askdirectory()
    if directory:
        location_entry.delete(0, tk.END)
        location_entry.insert(0, directory)

def start_collection():
    """Starts the data collection thread."""
    global collector_thread, stop_event
    # Use the user-specified location for CSV saving.
    location = location_entry.get()
    stop_event = threading.Event()
    collector_thread = DataCollectorThread(sampling_interval=5, stop_event=stop_event,
                                             filename="process_data.csv", location=location)
    collector_thread.start()
    status_label.config(text="Status: Collecting data...")
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)

def stop_collection():
    """Stops data collection."""
    global collector_thread, stop_event
    if stop_event and collector_thread:
        stop_event.set()         # Signal the thread to stop.
        collector_thread.join()  # Wait for the thread to finish.
        status_label.config(text="Status: Data collection stopped.")
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)

# Create the main Tkinter window.
root = tk.Tk()
root.title("Process Data Collector")

# Directory selection frame.
location_label = tk.Label(root, text="CSV Save Directory:")
location_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
location_entry = tk.Entry(root, width=50)
location_entry.grid(row=0, column=1, padx=5, pady=5)
# Default location (adjust if needed)

location_entry.insert(0, default_location)
browse_button = tk.Button(root, text="Browse", command=choose_directory)
browse_button.grid(row=0, column=2, padx=5, pady=5)

# Start and Stop buttons.
start_button = tk.Button(root, text="Start", command=start_collection)
start_button.grid(row=1, column=0, padx=5, pady=5)
stop_button = tk.Button(root, text="Stop", command=stop_collection, state=tk.DISABLED)
stop_button.grid(row=1, column=1, padx=5, pady=5)

# Status label.
status_label = tk.Label(root, text="Status: Idle")
status_label.grid(row=2, column=0, columnspan=3, padx=5, pady=5)

# Start the Tkinter event loop.
root.mainloop()
