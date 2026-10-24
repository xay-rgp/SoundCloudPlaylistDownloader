#!/usr/bin/env python3
"""A small native desktop home for SoundCloud playlist downloads."""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
from urllib.parse import urlparse


def valid_playlist_url(value):
    try:
        parsed = urlparse(value)
        parts = parsed.path.strip('/').split('/')
        return (parsed.scheme == 'https'
                and parsed.hostname in {'soundcloud.com', 'www.soundcloud.com', 'm.soundcloud.com'}
                and not parsed.username and not parsed.password
                and parsed.port in (None, 443)
                and len(parts) == 3 and parts[1] == 'sets'
                and bool(parts[0]) and bool(parts[2]))
    except ValueError:
        return False


def download_command(url, directory):
    return ['yt-dlp', '--newline', '--no-color', '--yes-playlist', '-x',
            '--audio-format', 'mp3', '--embed-metadata', '--embed-thumbnail',
            '-o', os.path.join(directory, '%(playlist_title)s',
                               '%(playlist_index)02d - %(title)s.%(ext)s'), url]


def main():
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, Gdk, GLib, Pango
    except (ImportError, ValueError) as error:
        raise SystemExit('Install Python GObject and GTK 3 (python3-gi and gir1.2-gtk-3.0 on Debian/Ubuntu).') from error

    if not Gtk.init_check()[0]:
        raise SystemExit('Could not connect to a desktop display. Run this app from your desktop session.')

    class Downloader(Gtk.Window):
        def __init__(self):
            super().__init__(title='SoundCloud Playlist Downloader')
            self.set_default_size(540, 400)
            self.set_border_width(24)
            self.set_name("downloader")
            self.set_icon_name('audio-x-generic')
            self.active = False
            self.cancel_event = threading.Event()
            self.config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'soundcloud-playlist-downloader' / 'settings.json'
            self.folder = str(Path.home() / 'Music')
            self.dark = Gtk.Settings.get_default().get_property('gtk-application-prefer-dark-theme')
            try:
                settings = json.loads(self.config.read_text())
                saved = settings.get('directory')
                if isinstance(settings.get('dark_mode'), bool):
                    self.dark = settings['dark_mode']
                if isinstance(saved, str) and Path(saved).is_dir():
                    self.folder = saved
            except (OSError, ValueError, AttributeError):
                pass
            self.css = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), self.css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self.apply_theme()
            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
            self.add(root)
            header = Gtk.Box(spacing=16)
            root.pack_start(header, False, False, 0)
            header.pack_start(self.label('SoundCloud downloader', 'title'), True, True, 0)
            self.theme_toggle = Gtk.ToggleButton(label='Dark mode')
            self.theme_toggle.set_active(self.dark)
            self.theme_toggle.set_tooltip_text('Use a dark appearance')
            self.theme_toggle.connect('toggled', self.toggle_theme)
            header.pack_end(self.theme_toggle, False, False, 0)
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            root.pack_start(card, False, False, 0)
            card.pack_start(self.label('Playlist link', 'field-label'), False, False, 0)
            self.url = Gtk.Entry()
            self.url.set_placeholder_text('https://soundcloud.com/artist/sets/playlist')
            self.url.set_tooltip_text('Paste a public HTTPS SoundCloud playlist link.')
            self.url.connect('changed', self.validate)
            self.url.connect('activate', lambda *_: self.start() if self.start_button.get_sensitive() else None)
            card.pack_start(self.url, False, False, 0)
            self.hint = self.label('', 'error')
            self.hint.set_no_show_all(True)
            card.pack_start(self.hint, False, False, 0)
            card.pack_start(self.label('Save to', 'field-label'), False, False, 0)
            row = Gtk.Box(spacing=12)
            self.folder_label = self.label(self.folder, 'muted')
            self.folder_label.set_line_wrap(False)
            self.folder_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            self.folder_label.set_tooltip_text(self.folder)
            row.pack_start(self.folder_label, True, True, 0)
            self.browse = Gtk.Button(label='Change…')
            self.browse.connect('clicked', self.choose_folder)
            row.pack_start(self.browse, False, False, 0)
            card.pack_start(row, False, False, 0)
            actions = Gtk.Box(spacing=10)
            root.pack_start(actions, False, False, 0)
            self.start_button = Gtk.Button(label='Download playlist')
            self.start_button.get_style_context().add_class('primary')
            self.start_button.connect('clicked', self.start)
            actions.pack_start(self.start_button, True, True, 0)
            self.cancel_button = Gtk.Button(label='Cancel')
            self.cancel_button.set_sensitive(False)
            self.cancel_button.set_no_show_all(True)
            self.cancel_button.hide()
            self.cancel_button.connect('clicked', self.cancel)
            actions.pack_start(self.cancel_button, False, False, 0)
            self.status = self.label('MP3 · Artwork & metadata', 'muted')
            root.pack_start(self.status, False, False, 0)
            self.progress = Gtk.ProgressBar()
            self.progress.set_no_show_all(True)
            root.pack_start(self.progress, False, False, 0)
            footer = Gtk.Box(spacing=12)
            root.pack_start(footer, False, False, 0)
            self.open_button = Gtk.Button(label='Open folder')
            self.open_button.set_relief(Gtk.ReliefStyle.NONE)
            self.open_button.set_valign(Gtk.Align.START)
            self.open_button.connect('clicked', self.open_folder)
            footer.pack_end(self.open_button, False, False, 0)
            details = Gtk.Expander(label='Details')
            self.log = Gtk.TextBuffer()
            view = Gtk.TextView(buffer=self.log)
            view.set_editable(False)
            view.set_cursor_visible(False)
            view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            scroll = Gtk.ScrolledWindow()
            scroll.set_min_content_height(130)
            scroll.add(view)
            details.add(scroll)
            footer.pack_start(details, True, True, 0)
            self.connect('delete-event', self.close)
            self.validate()
            self.show_all()
            self.url.grab_focus()

        def save_settings(self):
            try:
                self.config.parent.mkdir(parents=True, exist_ok=True)
                self.config.write_text(json.dumps({'directory': self.folder, 'dark_mode': self.dark}))
            except OSError:
                pass

        def toggle_theme(self, button):
            self.dark = button.get_active()
            self.apply_theme()
            self.save_settings()

        def apply_theme(self):
            Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme', self.dark)
            colors = (['#191b1f', '#24272d', '#ededee', '#a4a9b2', '#393e47', '#ff854d', '#141619', '#ff9292']
                      if self.dark else
                      ['#fafafa', '#ffffff', '#25282e', '#626873', '#d9dce1', '#b83d08', '#ffffff', '#b3261e'])
            css = """
                #downloader { background: @bg; color: @fg; }
                #downloader .title { font-size: 19px; font-weight: bold; }
                #downloader .muted { color: @muted; }
                #downloader .field-label { font-weight: bold; }
                #downloader entry, #downloader button {
                    background: @surface; background-image: none; color: @fg;
                    border: 1px solid @border; border-radius: 6px;
                    padding: 8px 12px; box-shadow: none; text-shadow: none;
                }
                #downloader entry:focus, #downloader button:focus { border-color: @accent; }
                #downloader button:hover { border-color: @accent; }
                #downloader button:checked { color: @accent; border-color: @accent; }
                #downloader .primary { background: @accent; color: @onaccent; border-color: @accent; font-weight: bold; }
                #downloader button:disabled { background: @surface; color: @muted; border-color: @border; }
                #downloader entry:disabled { color: @muted; }
                #downloader progressbar trough { background: @border; border: none; min-height: 3px; }
                #downloader progressbar progress { background: @accent; border: none; min-height: 3px; }
                #downloader .error { color: @error; }
                #downloader textview text { background: @surface; color: @fg; }
                #downloader expander { color: @muted; }
            """
            for name, color in zip(['bg', 'surface', 'fg', 'muted', 'border', 'accent', 'onaccent', 'error'], colors):
                css = css.replace('@' + name, color)
            self.css.load_from_data(css.encode())

        def label(self, text, style):
            widget = Gtk.Label(label=text, xalign=0)
            widget.get_style_context().add_class(style)
            widget.set_line_wrap(True)
            widget.set_max_width_chars(68)
            return widget

        def validate(self, *_):
            value = self.url.get_text().strip()
            valid = valid_playlist_url(value)
            self.start_button.set_sensitive(valid and not self.active)
            self.hint.set_text('Use an HTTPS SoundCloud link: /artist/sets/playlist.')
            self.hint.set_visible(bool(value) and not valid)

        def choose_folder(self, *_):
            dialog = Gtk.FileChooserDialog(title='Choose where to save your playlists', parent=self,
                                          action=Gtk.FileChooserAction.SELECT_FOLDER)
            dialog.add_buttons('Cancel', Gtk.ResponseType.CANCEL, 'Select folder', Gtk.ResponseType.OK)
            if Path(self.folder).is_dir():
                dialog.set_current_folder(self.folder)
            if dialog.run() == Gtk.ResponseType.OK:
                self.folder = dialog.get_filename()
                self.folder_label.set_text(self.folder)
                self.folder_label.set_tooltip_text(self.folder)
                self.save_settings()
            dialog.destroy()

        def start(self, *_):
            if self.active or not valid_playlist_url(self.url.get_text().strip()):
                return
            missing = [name for name in ('yt-dlp', 'ffmpeg', 'ffprobe') if not shutil.which(name)]
            if missing:
                self.status.set_text('Install missing tools: ' + ', '.join(missing))
                return
            try:
                Path(self.folder).mkdir(parents=True, exist_ok=True)
                if not os.access(self.folder, os.W_OK):
                    raise OSError('This folder is not writable.')
            except OSError as error:
                self.status.set_text(f'Choose another folder: {error}')
                return
            self.save_settings()
            self.active = True
            self.cancel_event.clear()
            self.url.set_sensitive(False)
            self.browse.set_sensitive(False)
            self.cancel_button.set_sensitive(True)
            self.cancel_button.show()
            self.progress.show()
            self.validate()
            self.log.set_text('')
            self.progress.set_fraction(0)
            self.status.set_text('Connecting to SoundCloud…')
            GLib.timeout_add(120, self.pulse)
            command = download_command(self.url.get_text().strip(), self.folder)
            threading.Thread(target=self.download, args=(command,), daemon=True).start()

        def pulse(self):
            if not self.active:
                return False
            self.progress.pulse()
            return True

        def download(self, command):
            try:
                with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, errors='replace', start_new_session=True) as process:
                    def stop_if_requested():
                        while process.poll() is None:
                            if self.cancel_event.wait(0.15):
                                try:
                                    os.killpg(process.pid, signal.SIGTERM)
                                    try:
                                        process.wait(timeout=3)
                                    except subprocess.TimeoutExpired:
                                        os.killpg(process.pid, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                                return
                    threading.Thread(target=stop_if_requested, daemon=True).start()
                    for line in process.stdout:
                        GLib.idle_add(self.append_log, line.rstrip())
                    code = process.wait()
                GLib.idle_add(self.finished, code, '')
            except OSError as error:
                GLib.idle_add(self.finished, -1, str(error))

        def append_log(self, line):
            self.log.insert(self.log.get_end_iter(), line + '\n')
            if self.log.get_line_count() > 400:
                self.log.delete(self.log.get_start_iter(), self.log.get_iter_at_line(100))
            if not self.cancel_event.is_set():
                match = re.search(r'Downloading item (\d+) of (\d+)', line)
                if match:
                    self.status.set_text(f'Downloading track {match[1]} of {match[2]}…')
                elif line.startswith('[ExtractAudio]'):
                    self.status.set_text('Preparing MP3 audio…')
                elif line.startswith('[EmbedThumbnail]'):
                    self.status.set_text('Adding cover art…')
            return False

        def finished(self, code, error):
            self.active = False
            self.url.set_sensitive(True)
            self.browse.set_sensitive(True)
            self.cancel_button.set_sensitive(False)
            self.cancel_button.hide()
            self.progress.hide()
            self.validate()
            if self.cancel_event.is_set():
                self.status.set_text('Download canceled. Completed tracks are saved.')
            elif code == 0:
                self.status.set_text('Playlist saved. Enjoy listening!')
            else:
                self.status.set_text('Download failed. Check the details below and try again.')
                if error:
                    self.append_log(error)
            self.progress.set_fraction(1 if code == 0 and not self.cancel_event.is_set() else 0)
            return False

        def cancel(self, *_):
            self.cancel_event.set()
            self.cancel_button.set_sensitive(False)
            self.status.set_text('Canceling download…')

        def open_folder(self, *_):
            try:
                Gtk.show_uri_on_window(self, Path(self.folder).as_uri(), Gdk.CURRENT_TIME)
            except GLib.Error as error:
                self.status.set_text(f'Could not open folder: {error.message}')

        def close(self, *_):
            if self.active:
                self.cancel()
                self.status.set_text('Canceling download… Close the window once it stops.')
                return True
            Gtk.main_quit()
            return False

    Downloader()
    Gtk.main()


if __name__ == '__main__':
    main()
