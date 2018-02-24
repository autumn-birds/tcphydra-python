import unittest

# I know, I know ... one isn't supposed to pollute the global scope or
# whatever ...
# It seems justifiable in this case though given that all we care about
# is testing things in the global scope of `proxy'.
from proxy import *


class TestAnsiEscapeCodeProcessing(unittest.TestCase):
    def test_nop(self):
        state = {'a': 'b'}
        state2 = parse_ANSI('', state)
        self.assertEqual(state, state2)

    def test_nonsense(self):
        state = {'a': 'b'}
        state2 = parse_ANSI('aesofhlk jasdlfkja ehlfoias efsldfjk', state)
        self.assertEqual(state, state2)
        state2 = parse_ANSI('Someone says, "Lorem ipsum quod ecit dolor..."', state)
        self.assertEqual(state, state2)

    def test_fg(self):
        state = parse_ANSI("\x1B[31m")
        self.assertEqual(state['foreground'], 1)

        state = parse_ANSI("\x1B[39m", state)
        self.assertEqual(state['foreground'], 1)

        state = parse_ANSI("\x1B[33m", state)
        self.assertEqual(state['foreground'], 3)

        state = parse_ANSI("\x1B[30m", state)
        self.assertEqual(state['foreground'], 0)

    def test_bg(self):
        state = parse_ANSI("\x1B[41m")
        self.assertEqual(state['background'], 1)

        state = parse_ANSI("\x1B[49m", state)
        self.assertEqual(state['background'], 1)

        state = parse_ANSI("\x1B[43m", state)
        self.assertEqual(state['background'], 3)

        state = parse_ANSI("\x1B[40m", state)
        self.assertEqual(state['background'], 0)

    def test_reset(self):
        state = parse_ANSI("\x1B[41m")
        state = parse_ANSI("\x1B[32m", state)

        self.assertEqual(state['foreground'], 2)
        self.assertEqual(state['background'], 1)

        state = parse_ANSI("\x1B[0m", state)

        self.assertEqual(state['foreground'], None)
        self.assertEqual(state['background'], None)

    def test_semicolons(self):
        state = parse_ANSI("\x1B[36;47m")

        self.assertEqual(state['foreground'], 6)
        self.assertEqual(state['background'], 7)

        state = parse_ANSI("\x1B[36;47;20;88;40;32;0m", state)

        self.assertEqual(state['foreground'], None)
        self.assertEqual(state['background'], None)

    def test_xterm256(self):
        state = parse_ANSI("\x1B[38;5;100m")
        self.assertEqual(state['foreground'], 100)

        state = parse_ANSI("\x1B[48;5;100m")
        self.assertEqual(state['background'], 100)

#       with self.assertRaises(ValueError):
        state = parse_ANSI("\x1B[48;5;999m", state)
        self.assertEqual(state['background'], 100)

    def test_xterm256_with_extras(self):
        state = parse_ANSI("\x1B[48;5;250;31m")
        self.assertEqual(state['background'], 250)
        self.assertEqual(state['foreground'], 1)


#class TestAnsiEscapeCodeProcessing(unittest.TestCase):
#   def setUp(self):
#       self.a = AnsiDisplayState()
#
#   def test_fg(self):
#       self.a.apply_escape_codes("\x1B[31m")
#       self.assertEqual(self.a.fg, 1)
#
#       self.a.apply_escape_codes("\x1B[39m")
#       self.assertEqual(self.a.fg, 1)
#
#       self.a.apply_escape_codes("\x1B[33m")
#       self.assertEqual(self.a.fg, 3)
#
#       self.a.apply_escape_codes("\x1B[30m")
#       self.assertEqual(self.a.fg, 0)
#
#   def test_bg(self):
#       self.a.apply_escape_codes("\x1B[41m")
#       self.assertEqual(self.a.bg, 1)
#       self.a.apply_escape_codes("\x1B[48m")
#       self.assertEqual(self.a.bg, 1)
#       self.a.apply_escape_codes("\x1B[40m")
#       self.assertEqual(self.a.bg, 0)
#
#   def test_reset(self):
#       self.a.apply_escape_codes("\x1B[41m") #;32;0m
#       self.a.apply_escape_codes("\x1B[32m") #;32;0m
#
#       self.a.apply_escape_codes("\x1B[0m") #;32;0m
#
#       self.assertEqual(self.a.fg, None)
#       self.assertEqual(self.a.bg, None)
#       self.assertEqual(self.a.bold, False)
#
#   def test_semicolons(self):
#       self.a.apply_escape_codes("\x1B[36;47m")
#       self.assertEqual(self.a.fg, 6)
#       self.assertEqual(self.a.bg, 7)
#
#       self.a.apply_escape_codes("\x1B[36;47;20;88;40;32;0m")
#
#   def test_xterm256(self):
#       self.a.apply_escape_codes("\x1B[38;5;100m")
#       self.assertEqual(self.a.fg, 100)
#
#       self.a.apply_escape_codes("\x1B[48;5;100m")
#       self.assertEqual(self.a.bg, 100)
#
#       with self.assertRaises(ValueError):
#           self.a.apply_escape_codes("\x1B[48;5;999m")


if __name__ == '__main__':
    unittest.main()
