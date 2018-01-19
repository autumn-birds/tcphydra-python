# vim:tabstop=3 shiftwidth=3 expandtab autoindent

# 'Telnet' multiplexer for MUDs, etc. Python 3.

# Things we should be doing someday:
#  - actually understand the underlying protocols (Telnet, etc.) to keep clients from
#    getting into inconsistent states

import sys
import threading
import socket
import selectors


ENCODING = 'utf-8'  # (default)
LINE_SEPARATOR = 10 # (default) ASCII/UTF-8 newline

COMMAND_PREFIX = ','
MESSAGE_PREFIX_OK = '%% '
MESSAGE_PREFIX_ERR = '!! '

RECV_MAX = 4096 # bytes


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
            print("Decoding, hit bad spot: " + repr(e))
            s += r[:e.start].decode(self.__enc)

            for byte in r[e.start:e.end]:
               print(byte)
               s += '?(' + str(byte) + ')'

            r = r[e.end:]

      print("return "+repr(s))
      return s

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

   def write_str(self, data):
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
            print("BlockingIOError")
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
   def __init__(self, host, port):
      super().__init__()

      assert type(host) == str
      assert type(port) == int
      self.host = host
      self.port = port

      self.subscribers = []

      self.connecting_in_thread = False

   def handle_data(self, data):
      for sub in self.subscribers:
         sub.write_line(data)

   def handle_disconnect(self):
      super().handle_disconnect(self)
      for sub in self.subscribers:
         sub.tell_err("Remote server closed connection.")

   def subscribe(self, supplicant):
      assert type(supplicant) == LocalClient
      if supplicant not in self.subscribers:
         self.subscribers.append(supplicant)

   def unsubscribe(self, supplicant):
      assert type(supplicant) == LocalClient
      while supplicant in self.subscribers:
         self.subscribers.remove(supplicant)

   def tell_all(self, msg):
      assert type(msg) == str
      for sub in self.subscribers:
         sub.tell_ok(msg)

   def warn_all(self, msg):
      assert type(msg) == str
      for sub in self.subscribers:
         sub.tell_err(msg)


class LocalClient(LineBufferingSocketContainer):
   def __init__(self, socket):
      super().__init__()

      self.attach_socket(socket)
      self.subscribedTo = None

   def tell_ok(self, msg):
      self.write_str(MESSAGE_PREFIX_OK + msg + "\r\n")

   def tell_err(self, msg):
      self.write_str(MESSAGE_PREFIX_ERR + msg + "\r\n")

   def unsubscribe(self):
      if type(self.subscribedTo) == RemoteServer:
         self.subscribedTo.unsubscribe(self)

   def subscribe(self, other):
      assert type(other) == RemoteServer
      self.subscribedTo = other

   def handle_data(self, data):
      if self.subscribedTo == None:
         self.tell_err("Not subscribedTo anything.")
         return

      if self.subscribedTo.connected:
         self.subscribedTo.write_line(data)
      else:
         self.tell_err("Remote server not connected.")

   def handle_disconnect(self):
      super().handle_disconnect()

      if self.subscribedTo != None:
         self.subscribedTo.unsubscribe(self)


LOCK = threading.Lock()
sel = selectors.DefaultSelector()
socket_wrappers = {}


servers = {}             # index of available servers by display name
server_sockets = []

def handle_line_server(socket, line):
   assert socket in server_sockets

   print("SERVER: "+line.as_str())
   socket_wrappers[socket].handle_data(line)
   return False # don't continue trying states

def do_start_connection(server):
   global server_sockets

   print("Starting to connect.\n")

   # This will always be ran in a thread -- to prevent long-blocking connection
   # attempts from hanging the whole program (e.g., when a server is down,
   # tinyfugue can spend quite a while waiting for a connection attempt to
   # come through...)

   # The main program will set connecting_in_thread synchronously *before*
   # calling this thread, so we don't need to worry about accidental multiple
   # connection attempts.

   # It would probably be better to try to figure out asynchronous connect() or
   # something eventually.

   # Will also (probably?) want to handle starting SSL, if necessary, later.

   try:
      assert type(server) == RemoteServer
      assert server.socket == None
      assert not server.connected

      C = socket.create_connection((server.host, server.port))

      LOCK.acquire()
      server.attach_socket(C)
      socket_wrappers[C] = server
      server_sockets += [C]
      sel.register(C, selectors.EVENT_READ)

   except ConnectionRefusedError:
      server.warn_all("Connection attempt failed: Connection refused")

   except (socket.error, socket.herror, socket.gaierror, socket.timeout) as err:
      server.warn_all("Connection attempt failed: " + repr(err))

   except:
      kind, value, traceback = sys.exc_info()
      server.warn_all("Connection attempt failed: " + repr(value))
      print("NON-SOCKET CONNECTION ERROR\n===========================\n\n" + repr(traceback))

   finally:
      server.connecting_in_thread = False
      LOCK.release()
      return

def start_connection(server):
   assert type(server) == RemoteServer

   if not server.connecting_in_thread and not server.connected:
      server.connecting_in_thread = True
      t_connect = threading.Thread(target = do_start_connection, args = [server])
      t_connect.start()
      return True

   else:
      return False


client_sockets = []
client_commands = {}

def handle_line_client(socket, line):
   assert socket in client_sockets

   s = line.as_str().replace('\r\n', '').replace('\n', '')
   c = socket_wrappers[socket]

   if s[:len(COMMAND_PREFIX)] == COMMAND_PREFIX:
      try:
         if ' ' in s:
            cmd = s[len(COMMAND_PREFIX):s.index(' ')]
            args = s[s.index(' ')+1:]
         else:
            cmd = s[len(COMMAND_PREFIX):]
            args = ''

         if cmd in client_commands:
            client_commands[cmd](args, c)
         else:
            c.tell_err("Command `"+cmd+"' not found.")

      except:
         kind, value, traceback = sys.exc_info()
         c.tell_err("Error during command processing: " + repr(value))
         print("COMMAND PROCESSING ERROR\n========================\n\n" + repr(traceback))

   else:
      c.handle_data(line)

   return False # don't continue trying states


def do_client_join(args, client):
   assert type(client) == LocalClient

   if args in servers:
      client.unsubscribe()
      servers[args].subscribe(client)
      client.subscribe(servers[args])
      client.tell_ok("Subscribed to server `"+args+"'.")
      return True
   else:
      client.tell_err("No such server `"+args+"'.")
      return False

client_commands["j"] = do_client_join

def do_client_connect(args, client):
   assert type(client) == LocalClient

   if do_client_join(args, client):
      start_connection(servers[args])
      return True #(ish)
   else:
      return False

client_commands["J"] = do_client_connect

def do_client_debug(args, client):
   assert type(client) == LocalClient

   try:
      client.tell_ok(repr(eval(args)))
   except:
      kind, value, traceback = sys.exc_info()
      client.tell_err(repr(value))

client_commands["e"] = do_client_debug


states = [(server_sockets, handle_line_server),
          #(preauth, handle_line_preauth),
          (client_sockets, handle_line_client)]


def run():
   servers["local"] = RemoteServer("localhost", 4000)

   try:
      def do_accept(socket, mask):
         global client_sockets

         connection, address = socket.accept() # and hope it works
         print("Accepting " + repr(connection) + " from " + repr(address) + " (mask="+repr(mask)+").")
         socket_wrappers[connection] = LocalClient(connection)
         client_sockets += [connection]
         print(repr(socket_wrappers[connection]))
         sel.register(connection, selectors.EVENT_READ)

      server = socket.socket()
      server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      server.bind(("localhost", 1234))
      server.listen(100)
      server.setblocking(False)
      sel.register(server, selectors.EVENT_READ)

      while True:
         LOCK.acquire()
         events = sel.select(timeout = 1)
         for key, mask in events:
            s = key.fileobj
            if s == server:
               do_accept(s, mask)
            else:
               if s in socket_wrappers:
                  ss = socket_wrappers[s]
               else:
                  ss = None

               if ss == None:
                  print("NOTE: Read on unregistered socket")
                  break

               (lines, eof) = ss.read()
               print(repr(lines))

               if eof:
                  sel.unregister(s)
                  ss.handle_disconnect()
                  for state in states:
                     if s in state[0]:
                        del state[0][state[0].index(s)]
                  if s in socket_wrappers:
                     del socket_wrappers[s]

               for line in lines:
                  for state in states:
                     if s in state[0]:
                        result = state[1](s, line)
                        if result:
                           break # to next line
         LOCK.release()

   except KeyboardInterrupt:
      print(repr(connections))
      print("Exiting uncleanly. Bye...")


if __name__ == '__main__':
   run()
