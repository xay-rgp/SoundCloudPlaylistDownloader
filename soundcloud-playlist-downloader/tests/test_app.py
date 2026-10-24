import unittest
from app import download_command, valid_playlist_url


class PlaylistTests(unittest.TestCase):
    def test_playlist_links(self):
        for host in ('soundcloud.com', 'www.soundcloud.com', 'm.soundcloud.com'):
            self.assertTrue(valid_playlist_url(f'https://{host}/artist/sets/mix?si=shared'))

    def test_rejects_incomplete_and_untrusted_links(self):
        for value in ('', 'https://soundcloud.com/artist/sets/',
                      'https://soundcloud.com/sets', 'http://soundcloud.com/a/sets/b',
                      'https://soundcloud.com.evil.test/a/sets/b',
                      'https://evil.test/a/sets/b', 'https://soundcloud.com/a/track',
                      'https://user@soundcloud.com/a/sets/b',
                      'https://soundcloud.com:bad/a/sets/b', 'https://[invalid'):
            with self.subTest(value=value):
                self.assertFalse(valid_playlist_url(value))

    def test_command_preserves_paths_and_metadata(self):
        url = 'https://soundcloud.com/a/sets/b?si=shared&source=test'
        command = download_command(url, '/tmp/My Music')
        self.assertEqual(command[-1], url)
        self.assertEqual(command[command.index('-o') + 1],
                         '/tmp/My Music/%(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s')
        for option in ('--yes-playlist', '--embed-thumbnail', '--embed-metadata'):
            self.assertIn(option, command)
        self.assertEqual(command[command.index('--audio-format') + 1], 'mp3')


if __name__ == '__main__':
    unittest.main()
