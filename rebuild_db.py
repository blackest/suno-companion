import sqlite3
import os
import json
import re

# Configuration
VAULT_ROOT = os.getcwd()
LIBRARY_DIR = os.path.join(VAULT_ROOT, 'library')
DB_PATH = os.path.join(VAULT_ROOT, 'suno_master.db')

def build_from_library():
    # 1. Nuke and Rebuild Schema
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('CREATE TABLE tracks (id TEXT PRIMARY KEY, title TEXT, file_name TEXT, created_at TEXT, image_url TEXT, rating REAL, on_distrokid INTEGER, on_youtube INTEGER, has_video INTEGER, album TEXT, audio_url TEXT)')
    cur.execute('CREATE TABLE technical_dna (track_id TEXT, model_version TEXT, duration REAL, weirdness REAL)')
    cur.execute('CREATE TABLE creative_intent (track_id TEXT, lyrics TEXT, input_prompt TEXT)')

    # 2. Scan for .txt metadata files
    txt_files = [f for f in os.listdir(LIBRARY_DIR) if f.endswith('.txt')]
    
    count = 0
    for txt_name in txt_files:
        # Determine the matching audio file (strip .txt)
        audio_filename = txt_name.replace('.txt', '')
        txt_path = os.path.join(LIBRARY_DIR, txt_name)
        
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extract the JSON block from "--- Raw API Response ---"
                json_match = re.search(r'--- Raw API Response ---\n(\{.*\})', content, re.DOTALL)
                if not json_match:
                    continue
                
                data = json.loads(json_match.group(1))
                
                # Extract fields based on provided Suno JSON structure
                track_id = data.get('id')
                title = data.get('title', 'Untitled')
                created_at = data.get('created_at')
                image_url = data.get('image_url', '')
                audio_url = data.get('audio_url', '')
                
                # Custom Vault Metadata
                rating = data.get('vault_rating', 0.0)
                on_dk = 1 if data.get('on_distrokid') else 0
                on_yt = 1 if data.get('on_youtube') else 0
                has_vid = 1 if data.get('has_video') else 0
                album = data.get('album', '')
                
                # Technical Data
                model = data.get('major_model_version', 'v3.5')
                metadata = data.get('metadata', {})
                duration = metadata.get('duration', 0.0)
                
                # Creative Data
                lyrics = metadata.get('prompt', '') # Suno stores lyrics in metadata['prompt']
                input_p = data.get('input_prompt', '') # Top-level or nested

                # 3. Insert into tables
                cur.execute("INSERT INTO tracks VALUES (?,?,?,?,?,?,?,?,?,?,?)", 
                           (track_id, title, audio_filename, created_at, image_url, rating, on_dk, on_yt, has_vid, album, audio_url))
                
                cur.execute("INSERT INTO technical_dna VALUES (?,?,?,?)", 
                           (track_id, model, duration, 0.0)) # Default weirdness to 0.0
                
                cur.execute("INSERT INTO creative_intent VALUES (?,?,?)", 
                           (track_id, lyrics, input_p))
                
                count += 1
        except Exception as e:
            print(f"Error parsing {txt_name}: {e}")

    conn.commit()
    conn.close()
    print(f"Done. {count} tracks indexed from {LIBRARY_DIR}.")

if __name__ == "__main__":
    build_from_library()
