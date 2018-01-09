# vim:tabstop=3 shiftwidth=3 expandtab autoindent

# Telnet multiplexer for MUDs, etc.

# Convention: Normal Python strings EVERYWHERE, only convert to bytes when about to call
# send/receive on an actual socket.

import socket
import selectors

sel = selectors.DefaultSelector()
servers = {}             # index of available servers by display name
connections = {}         # index of currently connected server & client objects by socket


class LineBufferingSocketContainer:
   def __init__(self):
      self.__send_buffer = ''
      self.__recv_buffer = ''
      self.connected = False
      self.socket = None

   def write(self, data=None):
      # Should quietly buffer any overflow, then (try to) write as many complete 
      # lines as it can
      # Fail on !self.connected
      # If data=None, then just try to write anything left in the buffer into the
      # socket
      pass

   def read(self):
      # Should read all it can, but return None if there's not a complete
      # line yet (or [] -- return list of lines?)
      # Fail on !self.connected
      pass

   def attach_socket(self, socket):
      socket.setblocking(False)
      self.socket = socket
      self.connected = True

   def handle_disconnect(self):
      self.socket = None
      self.connected = False


class RemoteServer(LineBufferingSocketContainer):
   def __init__(self, address):
      super().__init__(self)

      self.addr = address           # TODO: parse into host/port
      self.subscribers = []

   def handle_data(self, data):
      for sub in self.subscribers:
         sub.write(data)

   def handle_disconnect(self):
      super().handle_disconnect(self)
      for sub in self.subscribers:
         sub.write("Remote server closed connection.\n")

   def subscribe(self, supplicant):
      if supplicant not in self.subscribers:
         self.subscribers.append(supplicant)

   def unsubscribe(self, supplicant):
      while supplicant in self.subscribers:
         self.subscribers.remove(supplicant)

class LocalClient(LineBufferingSocketContainer):
   def __init__(self, socket):
      super().__init__(self)

      self.attach_socket(socket)
      self.subscribedTo = None

   def handle_data(self, data):
      if self.subscribedTo != None and self.subscribedTo.connected:
         self.subscribedTo.write(data)
      else:
         self.write("Not connected?\n")

   def handle_disconnect(self):
      super().handle_disconnect(self)

      if self.subscribedTo != None:
         self.subscribedTo.unsubscribe(self)


def run():
   # select() loop
   pass

if __name__ == '__main__':
   # (...read configuration, set things up, etcetera...)
   run()
