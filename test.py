import unittest

# I know, I know ... one isn't supposed to pollute the global scope or
# whatever ...
# It seems justifiable in this case though given that all we care about
# is testing things in the global scope of `proxy'.
from proxy import *


class TestAnsiEscapeCodeProcessing(unittest.TestCase):
    def setUp(self):
        self.a = AnsiDisplayState()

    def test_fg(self):
        self.a.apply_escape_codes("\x1B[31m")
        self.assertEqual(self.a.fg, 1)

        self.a.apply_escape_codes("\x1B[39m")
        self.assertEqual(self.a.fg, 1)

        self.a.apply_escape_codes("\x1B[33m")
        self.assertEqual(self.a.fg, 3)

        self.a.apply_escape_codes("\x1B[30m")
        self.assertEqual(self.a.fg, 0)

    def test_bg(self):
        self.a.apply_escape_codes("\x1B[41m")
        self.assertEqual(self.a.bg, 1)
        self.a.apply_escape_codes("\x1B[48m")
        self.assertEqual(self.a.bg, 1)
        self.a.apply_escape_codes("\x1B[40m")
        self.assertEqual(self.a.bg, 0)

    def test_reset(self):
        self.a.apply_escape_codes("\x1B[41m") #;32;0m
        self.a.apply_escape_codes("\x1B[32m") #;32;0m

        self.a.apply_escape_codes("\x1B[0m") #;32;0m

        self.assertEqual(self.a.fg, None)
        self.assertEqual(self.a.bg, None)
        self.assertEqual(self.a.bold, False)

    def test_semicolons(self):
        self.a.apply_escape_codes("\x1B[36;47m")
        self.assertEqual(self.a.fg, 6)
        self.assertEqual(self.a.bg, 7)

        self.a.apply_escape_codes("\x1B[36;47;20;88;40;32;0m")

    def test_xterm256(self):
        self.a.apply_escape_codes("\x1B[38;5;100m")
        self.assertEqual(self.a.fg, 100)

        self.a.apply_escape_codes("\x1B[48;5;100m")
        self.assertEqual(self.a.bg, 100)

        with self.assertRaises(ValueError):
            self.a.apply_escape_codes("\x1B[48;5;999m")


if __name__ == '__main__':
    unittest.main()
