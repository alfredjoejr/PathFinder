import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys

class AILauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("PathFinder Control Center")
        self.root.geometry("400x260")
        self.root.configure(padx=20, pady=20)

        # Base Directory (Assuming this launcher is saved in the ASHEN root folder)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Target Folders
        self.mapper_dir = os.path.join(self.base_dir, "mapper")
        self.actuator_dir = os.path.join(self.base_dir, "ActuatorProgram")
        
        # UI Elements
        tk.Label(root, text="PathFinder — Game Control", font=("Arial", 14, "bold")).pack(pady=(0, 20))

        # Local Scripts
        self.btn_map = tk.Button(root, text="VALORANT", width=30, height=2, 
                                 command=self.run_map)
        self.btn_map.pack(pady=5)



        self.btn_actuator = tk.Button(root, text="RACING", width=30, height=2,
                                         command=self.run_actuator)
        self.btn_actuator.pack(pady=5)

        # Status Label
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = tk.Label(root, textvariable=self.status_var, fg="gray", font=("Arial", 9))
        self.status_label.pack(side=tk.BOTTOM, pady=10)

    def run_script(self, script_name, folder_path):
        """ Executes the script from the specified folder using the active virtual environment """
        script_path = os.path.join(folder_path, script_name)
        
        if not os.path.exists(script_path):
            messagebox.showerror("Error", f"File not found:\n{script_path}\n\nMake sure launcher.py is saved in the root ASHEN folder.")
            return

        self.status_var.set(f"Launching {script_name}...")
        self.root.update()

        try:
            # sys.executable ensures it uses your (env) Python
            subprocess.Popen([sys.executable, script_path], cwd=folder_path)
            self.status_var.set(f"{script_name} is running in the background.")
        except Exception as e:
            messagebox.showerror("Execution Error", str(e))
            self.status_var.set("Ready")

    def run_map(self):
        # Route to mapper/mapRunner.py
        self.run_script("mapRunner.py", self.mapper_dir)


    def run_actuator(self):
        # Route to ActuatorProgram/actuator_gui.py
        self.run_script("actuator_gui.py", self.actuator_dir)

if __name__ == "__main__":
    root = tk.Tk()
    app = AILauncher(root)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()