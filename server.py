import http.server
import socketserver
import subprocess
import urllib.parse
import os
import json
import sqlite3
import re
import socket
import platform

try:
    from mutagen.id3 import ID3, TIT2
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    print("Warning: Mutagen not installed. ID3 tagging disabled.")

PORT = 8001
LIBRARY_DIR = "library"
DB_PATH = "suno_master.db"

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class SunoVaultHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/refresh':
            try:
                print("Refreshing database from library...")
                # Run the rebuild_db.py script
                result = subprocess.run(["python3", "rebuild_db.py"], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "output": result.stdout}).encode())
                    print("Database rebuild successful.")
                else:
                    self.send_error(500, f"Rebuild failed: {result.stderr}")
            except Exception as e:
                print(f"Error during refresh: {e}")
                self.send_error(500, str(e))
        elif self.path.startswith('/reveal?file='):
            try:
                # Extract filename from query parameter
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                file_name = params.get('file', [None])[0]
                
                if not file_name:
                    self.send_error(400, "Missing file parameter")
                    return

                # Security: prevent directory traversal
                file_name = os.path.basename(file_name)
                full_path = os.path.join(os.getcwd(), LIBRARY_DIR, file_name)
                
                if not os.path.exists(full_path) and not full_path.endswith('.mp3'):
                    full_path += '.mp3'

                if os.path.exists(full_path):
                    system = platform.system()
                    if system == "Darwin": # macOS
                        print(f"Revealing in Finder: {full_path}")
                        subprocess.run(["open", "-R", full_path])
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(b"OK")
                    elif system == "Linux": # Pi / Ubuntu
                        print(f"Running on Linux - 'Reveal' not available in headless mode: {full_path}")
                        self.send_error(501, "Reveal only works on macOS")
                    else:
                        self.send_error(501, "Reveal not supported on this platform")
                else:
                    self.send_error(404, f"File not found: {file_name}")
            except Exception as e:
                print(f"Error in reveal: {e}")
                self.send_error(500, str(e))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/update_track':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)
                
                track_id = data.get('id')
                if not track_id:
                    self.send_error(400, "Missing track id")
                    return

                # Fields that can be updated
                updatable = ['title', 'rating', 'album', 'on_distrokid', 'on_youtube', 'has_video']
                
                # 1. Update Database
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                cursor.execute("SELECT file_name FROM tracks WHERE id = ?", (track_id,))
                row = cursor.fetchone()
                if not row:
                    self.send_error(404, "Track not found")
                    conn.close()
                    return
                
                audio_file = row[0]
                
                # Build dynamic SQL update
                update_fields = []
                params = []
                for field in updatable:
                    if field in data:
                        update_fields.append(f"{field} = ?")
                        params.append(data[field])
                
                if update_fields:
                    sql = f"UPDATE tracks SET {', '.join(update_fields)} WHERE id = ?"
                    params.append(track_id)
                    cursor.execute(sql, params)
                    conn.commit()
                conn.close()

                # 2. Update .mp3.txt file on disk
                txt_path = os.path.join(os.getcwd(), LIBRARY_DIR, audio_file + ".txt")
                if os.path.exists(txt_path):
                    with open(txt_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    pattern = r'(--- Raw API Response ---\n)(\{.*\})'
                    match = re.search(pattern, content, re.DOTALL)
                    if match:
                        json_str = match.group(2)
                        metadata = json.loads(json_str)
                        
                        # Sync all relevant fields to JSON
                        if 'title' in data: metadata['title'] = data['title']
                        if 'rating' in data: metadata['vault_rating'] = data['rating']
                        if 'album' in data: metadata['album'] = data['album']
                        if 'on_distrokid' in data: metadata['on_distrokid'] = bool(data['on_distrokid'])
                        if 'on_youtube' in data: metadata['on_youtube'] = bool(data['on_youtube'])
                        if 'has_video' in data: metadata['has_video'] = bool(data['has_video'])
                        
                        updated_json = json.dumps(metadata, indent=4)
                        new_content = content[:match.start(2)] + updated_json + content[match.end(2):]
                        
                        with open(txt_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Synced track data to file: {txt_path}")

                # 3. If title changed, update ID3 (only if mutagen available)
                if 'title' in data and MUTAGEN_AVAILABLE:
                    mp3_path = os.path.join(os.getcwd(), LIBRARY_DIR, audio_file)
                    if os.path.exists(mp3_path):
                        try:
                            audio = ID3(mp3_path)
                            audio["TIT2"] = TIT2(encoding=3, text=data['title'])
                            audio.save()
                        except Exception as id3_err:
                            print(f"ID3 Tagging failed: {id3_err}")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode())
                print(f"Successfully updated track {track_id}")
            except Exception as e:
                print(f"Error in update_track: {e}")
                self.send_error(500, str(e))
        else:
            self.send_error(404)

    # Enable CORS for development
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

if __name__ == "__main__":
    # Ensure we are in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    ip = get_ip()
    print("-" * 40)
    print(f"🚀 Suno Vault started!")
    print(f"🏠 Local URL:  http://localhost:{PORT}")
    print(f"🌐 Network URL: http://{ip}:{PORT}")
    print(f"📁 Root Path:   {os.getcwd()}")
    print("-" * 40)
    
    # Allow address reuse to avoid "Address already in use" errors on restart
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), SunoVaultHandler) as httpd:
        httpd.serve_forever()
