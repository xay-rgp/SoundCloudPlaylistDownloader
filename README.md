# SoundCloud Playlist Downloader

A native Linux desktop app that uses `yt-dlp` and FFmpeg to download a SoundCloud playlist as MP3 files with available metadata and cover art. A single native GTK window keeps your playlist link, destination, progress, and download details together; it does not open a browser.

## Requirements

- Python 3
- `yt-dlp`
- FFmpeg
- A desktop session, GTK 3, and Python GObject (`python3-gi` and `gir1.2-gtk-3.0` on Debian/Ubuntu)

On many Linux distributions, yt-dlp and FFmpeg are available through the system package manager. Otherwise install them using their official instructions.

## Run from source

```bash
cd ~/soundcloud-playlist-downloader
python3 app.py
```

Paste an HTTPS SoundCloud playlist URL, choose a destination folder, and click **Download playlist**. The app remembers your destination for next time. Use **Dark mode** in the header to switch between light and dark appearances; your choice is saved immediately. Cancel and progress controls appear only while a download is running. Each playlist is saved in its own subfolder, with tracks named by playlist order and title.

Track status appears in the window; expand **Details** for the full output. **Cancel** stops the current download and keeps completed files. Run the same playlist again to resume supported partial downloads. **Open folder** opens your file manager. Settings are stored under `$XDG_CONFIG_HOME/soundcloud-playlist-downloader` (normally `~/.config/soundcloud-playlist-downloader`).

## Build the AppImage

Install `appimagetool`, then run:

```bash
./build-appimage.sh
```

This creates `SoundCloud-Playlist-Downloader-x86_64.AppImage` in this directory. Launch it from your file manager or terminal. The AppImage includes the app and icon; Python 3, `yt-dlp`, FFmpeg, GTK 3, and Python GObject must be installed on the system.

Close the window to quit. If a download is running, closing first cancels it; close again after cancellation finishes. Downloads require access to the tracks and are subject to SoundCloud's terms and applicable copyright law.
