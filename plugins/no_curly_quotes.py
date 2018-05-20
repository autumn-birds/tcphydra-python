# vim: tabstop=3:shiftwidth=3:expandtab:autoindent

# Extracted from the 'Quotation mark' Wikipedia page.

import logging

REPLACEMENTS = {
      '\u2018': "'",
      '\u2019': "'",
      '\u201a': ",",
      '\u201b': "'",
      '\u201c': '"',
      '\u201d': '"',
      '\u201e': '',
      '\u201f': '"',
      '\uff02': '"',
      '\uff07': "'"
}

class CurlyQuoteFilter:
   """Changes all the extended unicode quotes into their plain-ASCII
   counterparts in the user's input.
   
   Could potentially filter other things too, but for now this is
   all it does."""
   def __init__(self, connection, options):
      pass

   def from_server(self, line):
      return line

   def from_client(self, line):
      c = line.as_str()
      logging.debug("... c before replacement: {}".format(repr(c)))
      for bad, good in REPLACEMENTS.items():
         c = c.replace(bad, good)
      logging.debug("... c after replacement: {}".format(repr(c)))
      line.set(c)
      return line

def setup(proxy):
   proxy.register_filter("no_curly_quotes", CurlyQuoteFilter)
