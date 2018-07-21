import unittest

import ansi

class TestANSIProcessing(unittest.TestCase):
    def test_all_text(self):
        self.assertEqual(
                ansi.parse_ANSI("hello world"),
                ["hello world"])

    def test_set_fg(self):
        self.assertEqual(
                ansi.parse_ANSI("\x1B[33mHello world!"),
                [{'fg': 3}, "Hello world!"])

    def test_set_twice(self):
        self.assertEqual(
                ansi.parse_ANSI("\x1B[33mHello \x1B[45mworld!"),
                [{'fg': 3}, "Hello ", {'fg': 3, 'bg': 5}, "world!"])

    def test_set_reset(self):
        self.assertEqual(
                ansi.parse_ANSI("\x1B[33mHello \x1B[0;45mworld\x1Bc!"),
                [{'fg': 3}, "Hello ", {'bg': 5}, "world", {}, "!"])

    def test_a_real_example(self):
        self.assertEqual(
                ansi.parse_ANSI('\x1b[34m[OOC]\x1b[0m\x1b[0m Someone says, "test"\x1b[0m\x1b[0m\r\n'),
                [{'fg': 4}, '[OOC]', {}, ' Someone says, "test"\r\n'])

    def test_a_hard_real_example(self):
        self.assertEqual(
                ansi.parse_ANSI('\x1b[31mCo\x1b[0m\x1b[34mlo\x1b[0m\x1b[32mr \x1b[0m\x1b[36mTe\x1b[0m\x1b[33mst\x1b[0m\x1b[47m\x1b[30m!\x1b[0m\x1b[0m\r\n'),
                [{'fg': 1}, "Co", {'fg': 4}, "lo", {'fg': 2}, "r ", {'fg': 6}, "Te", {'fg': 3}, "st", {'bg': 7, 'fg': 0}, "!", {}, "\r\n"])

    def test_xterm256_foreground(self):
        self.assertEqual(
                ansi.parse_ANSI('\x1b[38;5;250mThis should be fg=250.\x1b[0m'),
                [{'fg': 250}, "This should be fg=250.", {}])

    def test_xterm256_background(self):
        self.assertEqual(
                ansi.parse_ANSI('\x1b[48;5;250mThis should be bg=250.\x1b[0m'),
                [{'bg': 250}, "This should be bg=250.", {}])

    def test_xterm256_both(self):
        self.assertEqual(
                ansi.parse_ANSI('\x1b[48;5;250mThis should be bg=250 \x1b[48;5;245;38;5;22m(and this should be fg=22 bg=245)\x1b[0m.'),
                [{'bg': 250}, "This should be bg=250 ",
                 {'fg': 22, 'bg': 245}, "(and this should be fg=22 bg=245)",
                 {}, "."])

    def test_xterm256_complicated_real_example(self):
        # This test comes from an Evennia instance.  It's part of the test pattern
        # for xterm256 colors, hence the relative unreadability.
        self.assertEqual(
                ansi.parse_ANSI('\x1b[38;5;50m|054\x1b[0m \x1b[38;5;86m|154\x1b[0m \x1b[38;5;122m|254\x1b[0m \x1b[38;5;158m|354\x1b[0m \x1b[38;5;194m|454\x1b[0m \x1b[38;5;230m|554\x1b[0m \x1b[38;5;197m\x1b[48;5;50m|[054\x1b[0m \x1b[38;5;161m\x1b[48;5;86m|[154\x1b[0m \x1b[38;5;125m\x1b[48;5;122m|[254\x1b[0m \x1b[38;5;89m\x1b[48;5;158m|[354\x1b[0m \x1b[38;5;53m\x1b[48;5;194m|[454\x1b[0m \x1b[38;5;17m\x1b[48;5;230m|[554\x1b[0m \r\n'),
                [{'fg': 50}, '|054',
                 {}, ' ',
                 {'fg': 86}, '|154',
                 {}, ' ',
                 {'fg': 122}, '|254',
                 {}, ' ',
                 {'fg': 158}, '|354',
                 {}, ' ',
                 {'fg': 194}, '|454',
                 {}, ' ',
                 {'fg': 230}, '|554',
                 {}, ' ',
                 {'fg': 197, 'bg': 50}, '|[054',
                 {}, ' ',
                 {'fg': 161, 'bg': 86}, '|[154',
                 {}, ' ',
                 {'fg': 125, 'bg': 122}, '|[254',
                 {}, ' ',
                 {'fg': 89, 'bg': 158}, '|[354',
                 {}, ' ',
                 {'fg': 53, 'bg': 194}, '|[454',
                 {}, ' ',
                 {'fg': 17, 'bg': 230}, '|[554',
                 {}, ' \r\n'])

if __name__ == '__main__':
    unittest.main()
