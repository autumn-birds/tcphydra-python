# vim:tabstop=3 shiftwidth=3 expandtab autoindent

# 'Telnet' multiplexer for MUDs, etc.

# Convention: Normal Python strings EVERYWHERE, only convert to bytes when about to call
# send/receive on an actual socket.

# Things we should be doing someday:
#  - actually understand the underlying protocols (Telnet, etc.) to keep clients from
#    getting into inconsistent states

import socket
import selectors


ENCODING = 'utf-8'
LINE_SEPARATOR = 10 # ASCII/UTF-8 newline
RECV_MAX = 4096 # bytes


sel = selectors.DefaultSelector()
servers = {}             # index of available servers by display name
connections = {}         # index of currently connected server & client objects by socket


class LineBufferingSocketContainer:
   def __init__(self):
      self.__send_buffer = ''

      self.__b_send_buffer = b''
      self.__b_recv_buffer = b''

      self.connected = False

      self.socket = None

      self.encoding = ENCODING
      self.linesep = LINE_SEPARATOR

   def write(self, data=None):
      # Should quietly buffer any overflow, then (try to) write as many complete 
      # lines as it can
      # Fail on !self.connected
      # If data=None, then just try to write anything left in the buffer into the
      # socket
      assert self.connected

      if data != None:
         assert type(data) == str
         self.__send_buffer += data

      while len(self.__send_buffer) > 0:
         x = 0
         while x < len(self.__send_buffer):
            if self.__send_buffer[x] == '\n':
               self.__b_send_buffer += self.__send_buffer[:x+1].encode(self.encoding)
               self.__send_buffer = self.__send_buffer[x+1:]
               break
            x += 1
         if x >= len(self.__send_buffer):
            break # no more newlines

      print(repr(self.__b_send_buffer))

      if len(self.__b_send_buffer) > 0:
         assert self.socket != None
         try:
            n_bytes = self.socket.write(self.__b_send_buffer)
            self.__b_send_buffer = self.__b_send_buffer[n_bytes:]
         except BlockingIOError:
            pass

   def read(self):
      # Should read all it can, but return None if there's not a complete
      # line yet (or [] -- return list of lines?)
      # Fail on !self.connected
      assert self.connected
      assert self.socket != None

      try:
         data = b''
         while True:
            data = self.socket.read(RECV_MAX)
            self.__b_recv_buffer += data
            if len(data) < RECV_MAX:
               # May need to watch out for len(data)==0 which might mean the remote side
               # closed the connection?
               break
            data = b''
      except BlockingIOError:
         pass

      q = []

      # Currently, we just assume a particular byte separates lines.

      # This isn't the very best plan available, but it's better than blindly trying to decode
      # whatever chunk we have at the moment and then separate it, because of multi-byte
      # characters in some encodings: The network is allowed to only send us however many
      # bytes it wants, and there might be a partial character in there.

      # The best we can do for a record separator in this case is a byte or byte sequence that
      # means 'newline'. We go with one byte for now for simplicity & because it works with
      # UTF-8/ASCII at least, which comprises most things we're interested in.

      while len(self.__b_recv_buffer) > 0:
         x = 0
         while x < len(self.__b_recv_buffer):
            if self.__b_recv_buffer[x] == self.linesep:
               q += [self.__b_recv_buffer[:x+1].decode(self.encoding)]
               self.__b_recv_buffer = self.__b_recv_buffer[x+1:]
               break
            x += 1
         if x >= len(self.__b_recv_buffer):
            break # no more newlines

      return q

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
   x = LineBufferingSocketContainer()
   x.connected = True
   x.write("Hello world")
   x.write("\nthis is a test\npartial line")
   x.write("\n")
   # run()
