import tkinter as tk
from tkinter import Text, scrolledtext
import threading
import time
import pyautogui
import pytesseract
from PIL import ImageGrab, ImageOps
from plyer import notification
from multiprocessing import Process, set_start_method
import keyboard
import sys
import os
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Scan Sentry Application')
parser.add_argument('--headless', '-H', action='store_true', help='Run in headless mode without GUI')
parser.add_argument('--config', '-c', help='Path to configuration file')
args = parser.parse_args()

# Set Tesseract path (Windows)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Constants
TARGET_WORDS = ["Troublemaker", "Sssssss"]
OCR_CONFIG = "--psm 6"

# Global variables
scan_count_var = None
scan_interval=0.1
region_points = {}
scanning = False
scanner_thread = None
overlay_active = False
overlay_process = None
is_headless = args.headless
config_file = args.config
reverse_logic_var = None 

# Function to log in both GUI and headless modes
def log(msg):
    print(f"{time.strftime('%H:%M:%S')} - {msg}")
    if not is_headless and 'status_display' in globals() and status_display:
        status_display.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {msg}\n")
        status_display.see(tk.END)

def show_notification(title, message):
    try:
        notification.notify(title=title, message=message, app_name="Scan Sentry", timeout=3)
    except Exception as e:
        log(f"Notification error: {str(e)}")

def preprocess_image(image):
    try:
        gray = ImageOps.grayscale(image)
        return gray.point(lambda x: 0 if x < 160 else 255, '1')
    except Exception as e:
        log(f"Image processing error: {str(e)}")
        return image  # Return original image as fallback

def region_defined():
    return ('top_left' in region_points and 
            'bottom_right' in region_points and 
            region_points['top_left'] is not None and 
            region_points['bottom_right'] is not None)

def check_screen_and_act(region):
    try:
        screenshot = ImageGrab.grab(bbox=region)
        processed = preprocess_image(screenshot)
        text = pytesseract.image_to_string(processed, config=OCR_CONFIG)
        log(f"[+] OCR Result: {text.strip()}")

        found_any = False
        for word in TARGET_WORDS:
            if word.lower() in text.lower():
                found_any = True
                break

        # Determine if reverse logic is enabled
        reverse = False
        if reverse_logic_var is not None:
            # GUI mode
            reverse = reverse_logic_var.get()
        elif hasattr(sys, 'reverse_logic') and sys.reverse_logic:
            # Headless mode 
            reverse = True

        if reverse:
            if not found_any:
                pyautogui.press('g')
                log("[Reverse] No target words found → pressing G")
            else:
                log("[Reverse] Target word found, no action.")
        else:
            if found_any:
                pyautogui.press('g')
                log("[+] Found target word → pressing G")
            else:
                log("[-] No target words found.")
        pyautogui.press('down')
    except Exception as e:
        log(f"Error in screen check: {str(e)}")

def set_point(corner, wait=3):    
    global overlay_active
    toggled = False
    if overlay_active:
        close_overlay()
        overlay_active = False
        toggled = True
    
    if wait > 0:
        log(f"Move your mouse to the {corner.replace('_', ' ').upper()} (you have {wait} seconds)...")
        time.sleep(wait)
    
    pos = pyautogui.position()    
    region_points[corner] = (pos.x, pos.y)
    
    log(f"{corner.replace('_', ' ').title()} set to {region_points[corner]}")
    
    if toggled:
        # Only show overlay if both points are set
        if region_defined():
            show_overlay_rect()
        else:
            log("Still need to set both region corners to show overlay.")
    
    # Save region points to config file in headless mode
    if is_headless:
        save_config()

def validate_region():
    """Ensure the region coordinates are correctly ordered."""
    if not region_defined():
        return False
    
    x1, y1 = region_points['top_left']
    x2, y2 = region_points['bottom_right']
    
    # Ensure x1,y1 is top-left and x2,y2 is bottom-right
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    
    region_points['top_left'] = (x1, y1)
    region_points['bottom_right'] = (x2, y2)
    return True

def start_scanning():
    global scanning, scanner_thread, overlay_active
    
    if not region_defined():
        log("Please set both region corners first.")
        show_notification("Error", "Region not defined. Set corners first.")
        return
    
    if scanning:
        log("Already scanning.")
        return

    if overlay_active:
        close_overlay()
        overlay_active = False
        log("Overlay deactivated.")
    
    validate_region()  # Ensure region coordinates are correct
    
    region = (
        region_points['top_left'][0],
        region_points['top_left'][1],
        region_points['bottom_right'][0],
        region_points['bottom_right'][1]
    )
    
    # Get scan limit from GUI if available
    scan_limit = 0
    if scan_count_var is not None:
        try:
            scan_limit = int(scan_count_var.get())
        except Exception:
            scan_limit = 0  # Default to infinite if invalid

    log(f"Scanning region {region} for '{TARGET_WORDS}' (limit: {scan_limit if scan_limit else 'infinite'})")
    show_notification("Started", "Scanning started.")

    scanning = True  # Set flag before starting thread

    def loop():
        count = 0
        while scanning:
            try:
                check_screen_and_act(region)
                count += 1
                if scan_limit > 0 and count >= scan_limit:
                    log(f"Scan limit reached ({scan_limit}). Stopping scan.")
                    stop_scanning()
                    break
                time.sleep(scan_interval)
            except Exception as e:
                log(f"Error in scanner thread: {str(e)}")
                time.sleep(1)  # Slow down on errors

    scanner_thread = threading.Thread(target=loop, daemon=True)
    scanner_thread.start()

def stop_scanning():
    global scanning, overlay_active

    if scanning:
        scanning = False
        log("Scanning stopped.")
        show_notification("Stopped", "Scanning has been stopped.")
        # Wait for thread to end naturally, no need to join since it's daemon
    else:
        log("Not currently scanning.")

    if overlay_active:
        close_overlay()
        overlay_active = False
        log("Overlay deactivated.")

# ---------- Overlay Logic ----------
def run_overlay(x1, y1, x2, y2):
    try:
        from PyQt5.QtWidgets import QApplication, QWidget
        from PyQt5.QtGui import QPainter, QColor, QPen
        from PyQt5.QtCore import Qt, QRect
        
        # Ensure proper coordinates
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)

        class Overlay(QWidget):
            def __init__(self, rect):
                super().__init__()
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
                self.setAttribute(Qt.WA_TranslucentBackground)
                self.setGeometry(rect)
                self.rect = QRect(0, 0, rect.width(), rect.height())
                self.show()

            def paintEvent(self, event):
                painter = QPainter(self)
                pen = QPen(QColor(255, 0, 0), 4)  # Red outline for visibility
                painter.setPen(pen)
                painter.setBrush(Qt.transparent)
                painter.drawRect(self.rect)

        app = QApplication(sys.argv if not QApplication.instance() else [])
        rect = QRect(x1, y1, x2 - x1, y2 - y1)
        overlay = Overlay(rect)
        app.exec_()
    except Exception as e:
        print(f"Overlay error: {e}")  # Print directly since we're in a separate process

def show_overlay_rect():
    global overlay_active, overlay_process
    
    if not region_defined():
        log("Please set both region corners first.")
        return

    # Close any existing overlay
    close_overlay()
    
    if scanning:
        log("Cannot show overlay while scanning.")
        return
    
    # Validate and normalize region
    if not validate_region():
        log("Invalid region configuration.")
        return
    
    x1, y1 = region_points['top_left']
    x2, y2 = region_points['bottom_right']

    try:
        overlay_process = Process(target=run_overlay, args=(x1, y1, x2, y2))
        overlay_process.daemon = True
        overlay_process.start()
        overlay_active = True
        log("Overlay activated.")
    except Exception as e:
        log(f"Overlay failed: {str(e)}")

def close_overlay():
    global overlay_process, overlay_active
    
    if overlay_process and overlay_process.is_alive():
        try:
            overlay_process.terminate()
            overlay_process.join(timeout=1)
            if overlay_process.is_alive():
                overlay_process.kill()
        except Exception as e:
            log(f"Error closing overlay: {str(e)}")
    
    overlay_process = None
    overlay_active = False

def toggle_overlay():
    global overlay_active
    
    if overlay_active:
        close_overlay()
        log("Overlay deactivated.")
    else:
        # This was the main issue - need to validate region first
        if region_defined():
            show_overlay_rect()
        else:
            log("Please set both region corners first.")
            show_notification("Error", "Region not defined. Set corners first.")

# ---------- Configuration Functions ----------
def save_config():
    """Save current configuration to file"""
    if not config_file:
        log("No config file specified. Configuration not saved.")
        return
    
    try:
        with open(config_file, 'w') as f:
            if 'top_left' in region_points:
                f.write(f"top_left={region_points['top_left'][0]},{region_points['top_left'][1]}\n")
            if 'bottom_right' in region_points:
                f.write(f"bottom_right={region_points['bottom_right'][0]},{region_points['bottom_right'][1]}\n")
            f.write(f"target_words={','.join(TARGET_WORDS)}\n")
            if reverse_logic_var is not None:
                f.write(f"reverse_logic={int(reverse_logic_var.get())}\n")
        log(f"Configuration saved to {config_file}")
    except Exception as e:
        log(f"Error saving configuration: {str(e)}")

def load_config():
    """Load configuration from file"""
    global TARGET_WORDS, region_points
    
    if not config_file or not os.path.exists(config_file):
        log("No config file found. Using default settings.")
        return
    
    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'top_left':
                    x, y = map(int, value.split(','))
                    region_points['top_left'] = (x, y)
                    log(f"Loaded top_left: {x}, {y}")
                
                elif key == 'bottom_right':
                    x, y = map(int, value.split(','))
                    region_points['bottom_right'] = (x, y)
                    log(f"Loaded bottom_right: {x}, {y}")
                
                elif key == 'target_words':
                    TARGET_WORDS = value.split(',')
                    log(f"Loaded target words: {TARGET_WORDS}")

                elif key == 'reverse_logic':
                    if reverse_logic_var is not None:
                        reverse_logic_var.set(bool(int(value)))
                    else:
                        # For headless mode, set an attribute on sys
                        setattr(sys, 'reverse_logic', bool(int(value)))
                    log(f"Loaded reverse logic: {bool(int(value))}")

                elif key == 'scan_interval':
                    scan_interval = value
                    log(f"Loaded scan interval: {scan_interval}")

        log(f"Configuration loaded from {config_file}")
    except Exception as e:
        log(f"Error loading configuration: {str(e)}")

# ---------- Headless Mode ----------
def run_headless():
    log("Starting in headless mode...")
    
    # Load configuration if specified
    if config_file:
        load_config()
    
    # Register global hotkeys
    setup_hotkeys()
    
    show_notification("Scan Sentry", "Running in headless mode. Use hotkeys to control.")
    
    if region_defined():
        log("Region already defined from config. Ready to start scanning.")
        log(f"Top-left: {region_points['top_left']}")
        log(f"Bottom-right: {region_points['bottom_right']}")
    else:
        log("Region not defined. Use F7 and F8 to set region corners.")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Received keyboard interrupt. Exiting...")
        stop_scanning()
        close_overlay()
        sys.exit(0)

# ---------- Setup Hotkeys ----------
def setup_hotkeys():
    try:
        keyboard.add_hotkey('f7', lambda: set_point('top_left', wait=0))
        keyboard.add_hotkey('f8', lambda: set_point('bottom_right', wait=0))
        keyboard.add_hotkey('f9', start_scanning)
        keyboard.add_hotkey('f10', stop_scanning)
        keyboard.add_hotkey('f11', toggle_overlay)
        keyboard.add_hotkey('f12', lambda: os._exit(0) if is_headless else None)  # Emergency exit in headless mode
        log("Hotkeys registered successfully.")
    except Exception as e:
        log(f"Error setting up hotkeys: {str(e)}")

# ---------- GUI Setup ----------
def setup_gui():
    global root, status_display, region_status, scanner_status, scan_count_var, reverse_logic_var
    
    # Initialize GUI
    root = tk.Tk()
    root.title("Scan Sentry")
    root.geometry("300x400")
    root.attributes("-topmost", True)

    # Grid config for responsiveness
    root.columnconfigure(0, weight=1)
    root.rowconfigure(2, weight=1)  # log area expands

    # Log display (Text box with scrollbar)
    status_display = scrolledtext.ScrolledText(root, height=10, wrap=tk.WORD)
    status_display.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

    # ---------- GUI Layout ----------
    tk.Label(root, text="Scan Sentry", font=("Arial", 16, "bold")).grid(row=0, column=0, pady=5)

    button_frame = tk.Frame(root)
    button_frame.grid(row=1, column=0, padx=10, pady=2, sticky="ew")

    button_frame.columnconfigure((0, 1), weight=1)

    # First row
    tk.Button(button_frame, text="Set Top-Left (F7)", command=lambda: set_point('top_left')).grid(row=0, column=0, padx=5, pady=2, sticky="ew")
    tk.Button(button_frame, text="Set Bottom-Right (F8)", command=lambda: set_point('bottom_right')).grid(row=0, column=1, padx=5, pady=2, sticky="ew")

    # Second row
    tk.Button(button_frame, text="Start Scanning (F9)", command=start_scanning, bg="green", fg="white").grid(row=1, column=0, padx=5, pady=2, sticky="ew")
    tk.Button(button_frame, text="Stop Scanning (F10)", command=stop_scanning, bg="red", fg="white").grid(row=1, column=1, padx=5, pady=2, sticky="ew")

    # Third row
    tk.Button(button_frame, text="Toggle Overlay (F11)", command=toggle_overlay).grid(row=2, column=0, columnspan=2, padx=5, pady=2, sticky="ew")

    # Fourth row (config)
    tk.Button(button_frame, text="Save Config", command=save_config).grid(row=3, column=0, padx=5, pady=2, sticky="ew")
    tk.Button(button_frame, text="Load Config", command=lambda: [load_config(), update_status()]).grid(row=3, column=1, padx=5, pady=2, sticky="ew")
        
    # Fifth row (scan count input, centered)
    tk.Label(button_frame, text="Scan Limit:").grid(row=4, column=0, sticky="e", padx=5, pady=2)
    scan_count_var = tk.StringVar(value="0")
    scan_count_entry = tk.Entry(button_frame, textvariable=scan_count_var, width=6)
    scan_count_entry.grid(row=4, column=1, sticky="w", padx=5, pady=2)
    #tk.Label(button_frame, text="(0 = infinite)").grid(row=5, column=0, columnspan=2, sticky="n", pady=(0, 0))

    # Sixth row (reverse logic checkbox)
    reverse_logic_var = tk.BooleanVar(value=False)
    tk.Checkbutton(button_frame, text="Reverse Logic", variable=reverse_logic_var).grid(
        row=6, column=0, columnspan=2, pady=(2, 0), sticky="n"
    )


    # Status indicators
    status_frame = tk.Frame(root)
    status_frame.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
    status_frame.columnconfigure((0, 1), weight=1)

    region_status = tk.Label(status_frame, text="Region: Not Set", fg="red")
    region_status.grid(row=0, column=0, sticky="w")

    scanner_status = tk.Label(status_frame, text="Scanner: Inactive", fg="red")
    scanner_status.grid(row=0, column=1, sticky="e")

    # Exit handler
    root.protocol("WM_DELETE_WINDOW", on_close)
    
    # Register hotkeys
    setup_hotkeys()
    
    # Update status function
    def update_status():
        # Update region status
        if region_defined():
            region_status.config(text="Region: Set", fg="green")
        else:
            region_status.config(text="Region: Not Set", fg="red")
        
        # Update scanner status
        if scanning:
            scanner_status.config(text="Scanner: Active", fg="green")
        else:
            scanner_status.config(text="Scanner: Inactive", fg="red")
        
        # Schedule next update
        root.after(500, update_status)
    
    # Start status update loop
    update_status()
    
    # Load configuration if specified
    if config_file:
        load_config()
        
    log("GUI ready. Use the buttons or F7–F11 keys.")
    
    # Start main loop
    root.mainloop()

# Exit handler
def on_close():
    stop_scanning()
    close_overlay()
    log("Exiting...")
    
    if not is_headless:
        root.destroy()
    
    os._exit(0)  # Force exit to kill all threads

# ---------- Main Entry Point ----------
if __name__ == "__main__":
    try:
        set_start_method("spawn")
    except RuntimeError:
        # Already set or not available
        pass
    
    # Load configuration if specified
    if config_file:
        load_config()
    
    if is_headless:
        run_headless()
    else:
        setup_gui()
