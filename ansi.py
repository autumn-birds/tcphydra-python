# vim: ts=3:sw=3:expandtab

import copy

ANSI_ESC = "\x1B"
ANSI_ST = "\x1B\\"                                # ST = String Terminator

class ANSIParsingError(Exception):
   pass

def parse_ANSI(text):
    """Decompose a string that contains ANSI color codes into a
    list of the general form
    
       [{'fg': 2}, "text with foreground 2", {}, "text with default colors"]
    
    That is to say, contiguous chunks of the string (viewed from the
    same-color-properties perspective) are stored as strings,
    and changes in the color properties are stored as a dictionary
    containing all the color properties that have been set, which affects
    everything after it until the next dictionary."""

    assert type(text) == str

    state = "TEXT"
    acc = []

    def accumulate_text(text):
       if len(acc) == 0 or type(acc[-1]) != str:
          acc.append(text)
       else:
          acc[-1] = acc[-1] + text

    cursor = 0
    last_colors = {}

    while cursor < len(text):
       character = text[cursor]

       if state == "TEXT":
          if character == ANSI_ESC:
             state = "ANSI_ESC"
          else:
             # TODO: Grab the whole chunk of text to the next ESC at once
             accumulate_text(character)
          cursor += 1
             
       elif state == "ANSI_ESC":
          if character == "[":
             state = "ANSI_CSI"
          elif character == "c":      # ( resets everything )
             acc.append({})
             state = "TEXT"
          elif character in ['X', '_', '^', ']', 'P']:
             state = "ANSI_STRING_COMMAND"
          else:
             # ... we have no idea.
             # TODO: Should we raise an error here or just fail silently?
             state = "TEXT"

          cursor += 1

       elif state == "ANSI_STRING_COMMAND":
          # We just ignore all the string commands.
          endofstr = text[cursor:].find(ANSI_ST) + cursor
          if endofstr == -1:
             cursor = len(text)
          else:
             cursor = endofstr + len(ANSI_ST)

       elif state == "ANSI_CSI":
          endofcode = text[cursor:].find('m') + cursor
          if endofcode == -1:
             raise ANSIParsingError("Unbounded CSI")

          codes = text[cursor:endofcode]

          if codes.find(":") != -1:
             raise ANSIParsingError("Unspported separator (':') found")

          colors = copy.copy(last_colors)
          for code in codes.split(';'):
             code = int(code)
             if code >= 30 and code <= 37:
                # Sets foreground color
                colors['fg'] = code - 30

             elif code >= 40 and code <= 47:
                # Sets background color
                colors['bg'] = code - 40

             elif code >= 90 and code <= 97:
                # Sets intense foreground color (nonstandard)
                colors['fg'] = code - 90 + 8 # see wikipedia and/or old impl.

             elif code >= 100 and code <= 107:
                # Sets intense background color (nonstandard)
                colors['bg'] = code - 100 + 8

             elif code == 38 or code == 48:
                # Sets an extended xterm256 color
                # (TO BE IMPLEMENTED)
                raise ANSIParsingError("Do not yet support xterm256 colors")

             elif code == 0:
                # Resets attributes
                for attr in ['fg', 'bg']:
                   if attr in colors:
                      del colors[attr]

          if colors != last_colors:
             last_colors = copy.copy(colors)
             if len(acc) >= 1 and type(acc[-1]) == dict:
                # update
                acc[-1] = colors
             else:
                acc.append(colors)

          cursor = endofcode + 1
          state = "TEXT"

    return acc
