#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
TOOL="${APPIMAGETOOL:-appimagetool}"
APPDIR="$(mktemp -d "$ROOT/.appdir.XXXXXX")"
trap 'rm -rf -- "$APPDIR"' EXIT HUP INT TERM

if ! command -v "$TOOL" >/dev/null 2>&1 && [ ! -x "$TOOL" ]; then
    printf 'Install appimagetool or set APPIMAGETOOL to its executable path.\n' >&2
    exit 1
fi

mkdir -p \
    "$APPDIR/usr/share/soundcloud-playlist-downloader" \
    "$APPDIR/usr/share/applications" \
    "$APPDIR/usr/share/icons/hicolor/scalable/apps"
cp "$ROOT/app.py" "$APPDIR/usr/share/soundcloud-playlist-downloader/"
cp "$ROOT/soundcloud-playlist-downloader.desktop" "$APPDIR/usr/share/applications/"
cp "$ROOT/soundcloud-playlist-downloader.svg" \
    "$APPDIR/usr/share/icons/hicolor/scalable/apps/soundcloud-playlist-downloader.svg"
cp "$ROOT/soundcloud-playlist-downloader.desktop" "$APPDIR/"
cp "$ROOT/AppRun" "$APPDIR/"
chmod +x "$APPDIR/AppRun"
ln -s usr/share/icons/hicolor/scalable/apps/soundcloud-playlist-downloader.svg \
    "$APPDIR/soundcloud-playlist-downloader.svg"
ln -s soundcloud-playlist-downloader.svg "$APPDIR/.DirIcon"

ARCH=x86_64 "$TOOL" "$APPDIR" "$ROOT/SoundCloud-Playlist-Downloader-x86_64.AppImage"
chmod +x "$ROOT/SoundCloud-Playlist-Downloader-x86_64.AppImage"
printf 'Built %s\n' "$ROOT/SoundCloud-Playlist-Downloader-x86_64.AppImage"
