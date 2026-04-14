# Suno Production Vault 🎹

A simple, local-first web interface to manage, search, and organize your [Suno AI](https://suno.com) songs. It indexes your downloaded tracks and their metadata, allowing you to quickly browse your production history.

Suno Tracks Exporter is a nice little chrome extension and it allows you to take your songs and meta data out of suno to work with locally
but it does so with . mp3 files and .mp3.txt files. 

the main purpose of this project is to allow you to find among your songs say with 'heart' in the song. Also has the different takes and links back to the song on suno. it just makes things easy and fast. The Extension Suno Track Importer is very good , this is for the next step. 

## Features

- **Local-First**: Works with your existing folder of Suno downloads.
- **Searchable**: Instant search through song titles, lyrics, and prompts.
- **Detailed Metadata**: View model versions, duration, and original Suno song IDs.
- **Production Workflow**: Track ratings, status (DistroKid, YouTube, Video), and organize into albums.
- **Suno Integration**: Quick links to view tracks on Suno.com or copy song links.
- **Reveal in Finder**: One-click to find the actual file on your Mac.
- **Automatic Sync**: Refresh your library to automatically index new downloads.

## Prerequisites

- **Python 3.x**
- **Modern Web Browser** (Chrome/Edge recommended for File System Access API)
- **macOS** (The "Reveal in Finder" feature is currently macOS specific)

## Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/mysunodb.git
   cd mysunodb
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare your library**:
   Place your Suno `.mp3` files and their corresponding `.mp3.txt` metadata files in the `library/` folder.

4. **Initialize the database**:
   Run the rebuild script to index your current files:
   ```bash
   python3 rebuild_db.py
   ```

## Usage

1. **Start the local server**:
   ```bash
   python3 server.py
   ```

2. **Open the interface**:
   Navigate to `http://localhost:8001/` in your browser.

3. **Manage your tracks**:
   - Use the search bar to find songs.
   - Click a track to see details, play the audio, or update its status.
   - Use the "Refresh Library" button after adding new files to the `library/` folder.

## License

MIT
