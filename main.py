import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys

class AILauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Model Control Center")
        self.root.geometry("400x250")
        self.root.configure(padx=20, pady=20)

        # Base Directory (Assuming this launcher is saved in the ASHEN root folder)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Target Folders
        self.mapper_dir = os.path.join(self.base_dir, "mapper")
        self.aimax_dir = os.path.join(self.base_dir, "AiMaxSteeringModel")
        
        # UI Elements
        tk.Label(root, text="AI Steering & Navigation", font=("Arial", 14, "bold")).pack(pady=(0, 20))

        # Local Scripts
        self.btn_map = tk.Button(root, text="Run mapRunner.py", width=30, height=2, 
                                 command=self.run_map)
        self.btn_map.pack(pady=5)

        self.btn_steer = tk.Button(root, text="Run Steering Model", width=30, height=2, 
                                      command=self.run_steering)
        self.btn_steer.pack(pady=5)

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

    def run_steering(self):
        # Pop-up dialog for CPU vs GPU selection
        answer = messagebox.askyesnocancel(
            "Hardware Selection", 
            "Which version of the steering model would you like to run?\n\n"
            "YES = GPU Version (runner.py)\n"
            "NO = CPU Version (runner2.py)\n"
            "CANCEL = Abort launch"
        )
        
        if answer is True:
            # User clicked YES -> GPU
            self.run_script("runner.py", self.aimax_dir)
        elif answer is False:
            # User clicked NO -> CPU
            self.run_script("runner2.py", self.aimax_dir)
        else:
            # User clicked Cancel or closed the window
            self.status_var.set("Steering model launch aborted.")

if __name__ == "__main__":
    root = tk.Tk()
    app = AILauncher(root)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()