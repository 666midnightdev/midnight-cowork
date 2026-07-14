import os
import sys
import urllib.request
import zipfile
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_ZIP_URL = "https://nodejs.org/dist/v20.11.0/node-v20.11.0-win-x64.zip"
NODE_DIR = os.path.join(BASE_DIR, "node_bin")
ZIP_PATH = os.path.join(BASE_DIR, "node-portable.zip")
WHATSAPP_DIR = os.path.join(BASE_DIR, "whatsapp")

def download_node():
    if os.path.exists(NODE_DIR):
        print("Node.js portable folder already exists. Skipping download.")
        return True
    
    print("Mendownload Node.js portable (sekitar 30MB)... Harap tunggu.")
    try:
        urllib.request.urlretrieve(NODE_ZIP_URL, ZIP_PATH)
        print("Download selesai! Mengekstrak...")
        
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(BASE_DIR)
            
        # Rename extracted directory to node_bin
        extracted_name = "node-v20.11.0-win-x64"
        extracted_dir = os.path.join(BASE_DIR, extracted_name)
        if os.path.exists(extracted_dir):
            os.rename(extracted_dir, NODE_DIR)
            
        print("Node.js portable berhasil disiapkan.")
        
        # Cleanup zip file
        if os.path.exists(ZIP_PATH):
            os.remove(ZIP_PATH)
            
        return True
    except Exception as e:
        print(f"Gagal mendownload Node.js: {e}")
        return False

def install_whatsapp_deps():
    print("Mengonfigurasi berkas package.json...")
    os.makedirs(WHATSAPP_DIR, exist_ok=True)
    
    package_json = os.path.join(WHATSAPP_DIR, "package.json")
    package_content = """{
  "name": "whatsapp-baileys-bridge",
  "version": "1.0.0",
  "description": "WhatsApp Baileys bridge for Midnight Cowork",
  "main": "index.js",
  "dependencies": {
    "@whiskeysockets/baileys": "^6.6.0",
    "@hapi/boom": "^10.0.1",
    "axios": "^1.6.5",
    "express": "^4.18.2",
    "qrcode": "^1.5.3"
  }
}"""
    with open(package_json, "w", encoding="utf-8") as f:
        f.write(package_content)
        
    print("Menginstal dependensi npm (@whiskeysockets/baileys, express, qrcode, dll)...")
    
    # Paths to local node and npm
    node_exe = os.path.join(NODE_DIR, "node.exe")
    npm_cmd = os.path.join(NODE_DIR, "npm.cmd")
    
    if not os.path.exists(node_exe) or not os.path.exists(npm_cmd):
        print("Node.js executable tidak ditemukan. Gagal menginstal dependensi.")
        return False
        
    try:
        # Prepend NODE_DIR to PATH env var so npm lifecycle scripts can run 'node'
        env = os.environ.copy()
        env["PATH"] = NODE_DIR + os.pathsep + env.get("PATH", "")
        
        # Run npm install using the local node environment
        subprocess.check_call([npm_cmd, "install"], cwd=WHATSAPP_DIR, env=env)
        print("Seluruh dependensi WhatsApp berhasil diinstal!")
        return True
    except Exception as e:
        print(f"Gagal menginstal dependensi npm: {e}")
        return False

if __name__ == "__main__":
    print("=== Memulai Pemasangan Node.js & Baileys WhatsApp Bridge ===")
    if download_node():
        install_whatsapp_deps()
    print("=== Selesai ===")
