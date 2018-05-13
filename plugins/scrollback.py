# vim: tabstop=3:shiftwidth=3:expandtab:autoindent

import collections

# We'll maintain the histories indexed by-connection:
histories = {}

# The actual history-reading needs to be done by a filter.
class MemoryFilter:
   def __init__(self, connection, options):
      global histories

      self.key = connection
      histories[self.key] = collections.deque(maxlen=options['length'])

   def from_server(self, line):
      global histories

      histories[self.key].append(line)

      return line

# To show scrollback ...
def do_recall_scrollback(args, client):
   if client.subscribedTo in histories:
      history = histories[client.subscribedTo].copy()
      while True:
         try:
            client.write_line(history.popleft())
         except IndexError:
            break
      client.tell_ok("Done with scrollback.")

   else:
      client.tell_err("No scrollback seems to exist for your current world.")

def setup(proxy):
   proxy.register_filter("scrollback", MemoryFilter)
   proxy.register_command("recall", do_recall_scrollback)
   proxy.register_command("r", do_recall_scrollback)
