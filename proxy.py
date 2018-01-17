# vim:tabstop=3 shiftwidth=3 expandtab autoindent

# 'Telnet' multiplexer for MUDs, etc. Python 3.

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


class TextLine:
   def __init__(self, string, encoding):
      assert type(string) == bytes or type(string) == str
      self.__enc = encoding

      if type(string) == bytes:
         self.__raw = string
      else:
         self.__raw = string.encode(encoding)

   def as_str(self):
      """Try to 'safely', but lossily, decode the raw line into an ordinary string,
      according to the encoding given."""
      s = ""
      r = self.__raw

      while len(r) > 0:
         try:
            s += r.decode(self.__enc)
            r = ''
         except UnicodeDecodeError as e:
            s += r[:e.start].decode(self.__enc)

            for byte in self.__enc[e.start:e.end]:
               s += '?(' + __repr__(byte) + ')'

            r = r[e.end:]

   def as_bytes(self):
      return self.__raw


class LineBufferingSocketContainer:
   def __init__(self, socket = None):
      self.__b_send_buffer = b''
      self.__b_recv_buffer = b''

      self.connected = False

      self.socket = None

      self.encoding = ENCODING
      self.linesep = LINE_SEPARATOR

      if socket != None:
         self.attach_socket(socket)

   def write_str(self):
      assert type(data) == str

      self.__b_send_buffer += data.encode(self.encoding)

      self.flush()

   def write_line(self, line):
      assert type(line) == TextLine

      self.__b_send_buffer += line.as_bytes()

      self.flush()

   def write(self, data):
      assert type(data) == bytes

      self.__b_send_buffer += data

      self.flush()

   def flush(self):
      assert self.socket != None
      assert self.connected

      while len(self.__b_send_buffer) > 0 and self.linesep in self.__b_send_buffer:
         try:
            t = self.__b_send_buffer.index(self.linesep)
            n_bytes = self.socket.send(self.__b_send_buffer[:t+1])
            self.__b_send_buffer = self.__b_send_buffer[n_bytes:]
         except BlockingIOError:
            break

   def read(self):
      assert self.connected
      assert self.socket != None

      has_eof = False

      try:
         data = b''
         while True:
            data = self.socket.recv(RECV_MAX)
            self.__b_recv_buffer += data
            if len(data) < RECV_MAX:
               # May need to watch out for len(data)==0 which might mean the remote side
               # closed the connection?
               if len(data) == 0:
                  has_eof = True
               break
            data = b''
      except BlockingIOError:
         pass

      q = []

      # The best we can do for a record separator in this case is a byte or byte sequence that
      # means 'newline'. We go with one byte for now for simplicity & because it works with
      # UTF-8/ASCII at least, which comprises most things we're interested in.

      while self.linesep in self.__b_recv_buffer:
         t = self.__b_recv_buffer.index(self.linesep)
         q += [TextLine(self.__b_recv_buffer[:t+1], self.encoding)]
         self.__b_recv_buffer = self.__b_recv_buffer[t+1:]

      return (q, has_eof)

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
   try:
      def do_accept(socket, mask):
         connection, address = socket.accept() # and hope it works
         print("Accepting " + repr(connection) + " from " + repr(address) + " (mask="+repr(mask)+").")
         connections[connection] = LineBufferingSocketContainer(connection)
         sel.register(connection, selectors.EVENT_READ, do_read)

      def do_read(socket, mask):
         if socket in connections:
            (lines, eof) = connections[socket].read()

            if eof:
               print("Got an EOF.")
               connections[socket].handle_disconnect()
               socket.close()
               sel.unregister(socket)
               del connections[socket]

            for line in lines:
               for s in connections:
                  connections[s].write_line(line)

      server = socket.socket()
      server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      server.bind(("localhost", 1234))
      server.listen(100)
      server.setblocking(False)
      sel.register(server, selectors.EVENT_READ, do_accept)

      while True:
         events = sel.select()
         for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)

   except KeyboardInterrupt:
      print(repr(connections))
      print("Exiting uncleanly. Bye...")
