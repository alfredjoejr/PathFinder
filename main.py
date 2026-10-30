import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys

class AILauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("PathFinder Control Center")
        self.root.geometry("400x370")
        self.root.configure(padx=20, pady=20)

        # Base Directory (Assuming this launcher is saved in the ASHEN root folder)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Target Folders
        self.mapper_dir = os.path.join(self.base_dir, "mapper")
        self.racing_dir = os.path.join(self.base_dir, "racing")
        self.pacman_dir = os.path.join(self.base_dir, "pacman")
        
        # UI Elements
        tk.Label(root, text="PathFinder — Game Control", font=("Arial", 14, "bold")).pack(pady=(0, 15))

        # Local Scripts
        self.btn_map = tk.Button(root, text="VALORANT", width=30, height=2, 
                                 command=self.run_map)
        self.btn_map.pack(pady=4)

        self.btn_actuator = tk.Button(root, text="RACING", width=30, height=2,
                                      command=self.run_actuator)
        self.btn_actuator.pack(pady=4)

        # Pac-Man Submenu Frame
        self.pacman_frame = tk.LabelFrame(root, text="PAC-MAN", font=("Arial", 10, "bold"), padx=10, pady=8)
        self.pacman_frame.pack(pady=10, fill="x")

        self.btn_pacman_manual = tk.Button(self.pacman_frame, text="Manual Mode (Play)", width=15, height=1,
                                           command=self.run_pacman_manual)
        self.btn_pacman_manual.pack(side=tk.LEFT, padx=5, expand=True)

        self.btn_pacman_auto = tk.Button(self.pacman_frame, text="Auto Mode (Autopilot)", width=17, height=1,
                                         command=self.run_pacman_auto)
        self.btn_pacman_auto.pack(side=tk.RIGHT, padx=5, expand=True)

        # Status Label
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = tk.Label(root, textvariable=self.status_var, fg="gray", font=("Arial", 9))
        self.status_label.pack(side=tk.BOTTOM, pady=6)

    def run_script(self, script_name, folder_path, extra_args=None):
        """ Executes the script from the specified folder using the active virtual environment """
        script_path = os.path.join(folder_path, script_name)
        
        if not os.path.exists(script_path):
            messagebox.showerror("Error", f"File not found:\n{script_path}\n\nMake sure the file exists.")
            return

        self.status_var.set(f"Launching {script_name}...")
        self.root.update()

        try:
            cmd = [sys.executable, script_path]
            if extra_args:
                cmd.extend(extra_args)
            subprocess.Popen(cmd, cwd=folder_path)
            self.status_var.set(f"{script_name} is running in the background.")
        except Exception as e:
            messagebox.showerror("Execution Error", str(e))
            self.status_var.set("Ready")

    def run_map(self):
        # Route to mapper/valorant_runner.py
        self.run_script("valorant_runner.py", self.mapper_dir)

    def run_actuator(self):
        # Route to racing/racing_runner.py
        self.run_script("racing_runner.py", self.racing_dir)

    def run_pacman_manual(self):
        # Launch Pac-Man local game for manual playing
        self.run_script("pacman_game.py", self.pacman_dir)

    def run_pacman_auto(self):
        # Route to pacman/pacman_runner.py (Full CV & ESP32 Auto-Pilot GUI)
        self.run_script("pacman_runner.py", self.pacman_dir)

if __name__ == "__main__":
    root = tk.Tk()
    app = AILauncher(root)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
