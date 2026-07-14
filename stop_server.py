import os
import sys
import signal
import subprocess

current_dir = os.path.dirname(os.path.abspath(__file__))
pid_file = os.path.join(current_dir, "server.pid")

# 1. Kill WhatsApp bridge running on port 8001 (if any)
if sys.platform == "win32":
    try:
        output = subprocess.check_output("netstat -ano | findstr :8001", shell=True).decode()
        for line in output.strip().split("\n"):
            if "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 5:
                    wa_pid = parts[-1]
                    subprocess.run(["taskkill", "/PID", wa_pid, "/F", "/T"], capture_output=True)
                    print(f"WhatsApp bridge with PID {wa_pid} stopped successfully.")
    except Exception:
        pass

# 2. Kill Main FastAPI Server
if os.path.exists(pid_file):
    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())
        
        # Kill the process
        if sys.platform == "win32":
            # Force kill the PID tree (/T)
            subprocess.run(["taskkill", "/PID", str(pid), "/F", "/T"], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
            
        print(f"Midnight Cowork server with PID {pid} stopped successfully.")
    except Exception as e:
        print(f"Error stopping server: {e}")
        
    try:
        os.remove(pid_file)
    except Exception:
        pass
else:
    print("server.pid not found. Is the server running?")
