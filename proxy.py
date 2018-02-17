# vim:tabstop=3 shiftwidth=3 expandtab autoindent

# 'Telnet' multiplexer for MUDs, etc. Python 3.

# Things we should be doing someday:
#  - actually understand the underlying protocols (Telnet)
#      - this turns out to be kind of necessary


import sys
import threading

import socket
import ssl
import selectors

import json

import pkgutil
import importlib


CONFIG_FILE = 'config.json'


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

#     if type(string) == bytes:
#        self.__raw = string
#     else:
#        self.__raw = string.encode(encoding)
      self.set(string)

   def set(self, string):
      """(Temporary method for testing.)"""
      if type(string) == bytes:
         self.__raw = string
      else:
         self.__raw = string.encode(self.__enc)

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

            for byte in r[e.start:e.end]:
               s += '?(' + str(byte) + ')'

            r = r[e.end:]

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
         except (BlockingIOError, ssl.SSLWantReadError, ssl.SSLWantWriteError):
            print("Note: BlockingIOError in flush() call")
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
               # If the length of data returned by a read() call is 0, that actually means the
               # remote side closed the connection.  If there's actually no data to be read,
               # you get a BlockingIOError or one of its SSL-based cousins instead.
               if len(data) == 0:
                  has_eof = True
               break
            data = b''

      except (BlockingIOError, ssl.SSLWantReadError, ssl.SSLWantWriteError):
         pass

      except ConnectionResetError:
         has_eof = True

      q = []

      # Telnet codes are a problem.  TODO: Improve this super hacky solution, which just involves
      # ... completely removing them from the input stream (except for IAC IAC / 255 255.)

      stripped = b''

      IAC = 255
      DONT = 254
      DO = 253
      WONT = 252
      WILL = 251

      in_command = False

      # Speaking of awful hacks, this is probably not very efficient at all:

      x = 0
      while x < len(self.__b_recv_buffer):
         if in_command:
            if self.__b_recv_buffer[x] == IAC:
               stripped += bytes([IAC])
               in_command = False
            elif self.__b_recv_buffer[x] <= DONT and self.__b_recv_buffer[x] >= WILL:
               pass
            else:
               in_command = False
         else:
            if self.__b_recv_buffer[x] == IAC:
               in_command = True
            else:
               stripped += self.__b_recv_buffer[x:x+1]
         x += 1

      # The best we can do for a record separator in this case is a byte or byte sequence that
      # means 'newline'. We go with one byte for now for simplicity & because it works with
      # UTF-8/ASCII at least, which comprises most things we're interested in.

      while self.linesep in stripped:
         t = stripped.index(self.linesep)
         q += [TextLine(stripped[:t+1], self.encoding)]
         stripped = stripped[t+1:]

      self.__b_recv_buffer = stripped

      # Make sure it starts in in_command mode again next time around in case the read() call
      # left us in the middle of a command, which I don't think is *likely* but could happen.
      # (The rest of the command will get tacked on after the IAC, which will ensure
      # the thing goes back into command mode immediately prior.)

      if in_command:
         self.__b_send_buffer += bytes([IAC])

      return (q, has_eof)

   def attach_socket(self, socket):
      socket.setblocking(False)
      self.socket = socket
      self.connected = True

   def handle_disconnect(self):
      self.socket = None
      self.connected = False


class FilterSpecificationError(Exception):
   pass


class FilteredSocket(LineBufferingSocketContainer):
   # Doesn't actually filter *itself* (yet?)
   # Would probably need to override some methods of the parent class.
   # (It may be impracticable to self-filter here anyway because the filters need to
   # know whether their text came from a server or a client and this class is too
   # abstract to know that. But this seemed like the best way to avoid code duplication.)
   def __init__(self):
      super().__init__()
      self.filters = []

   def add_filters(self, filters, prototypes):
      """Add filters to self according to the specification in `filters` (same format as
      configuration file), drawing from the filter prototypes/classes in the dictinoary
      `prototypes`.  Can raise FilterSpecificationError."""

      if type(filters) != list:
         raise FilterSpecificationError("Filters must be specified as list of [name,opts] pairs")

      for f in filters:
         if type(f) != list or len(f) != 2 or type(f[0]) != str or type(f[1]) != dict:
            raise FilterSpecificationError("Format to specify a filter is ['filtername',{'option':'val',...}]")

         filter_name = f[0]
         filter_opts = f[1]

         if filter_name not in prototypes:
            print("Error: No such filter `{}'".format(filter_name))
            return

         filter_class = prototypes[filter_name]

         self.filters.append(filter_class(self, filter_opts))


class RemoteServer(FilteredSocket):
   def __init__(self, host, port):
      super().__init__()

      assert type(host) == str
      assert type(port) == int
      self.host = host
      self.port = port

      self.subscribers = []

      self.connecting_in_thread = False
      self.use_SSL = False

   def handle_data(self, data):
      for sub in self.subscribers:
         sub.write_line(data)

   def handle_disconnect(self):
      super().handle_disconnect()
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


class LocalClient(FilteredSocket):
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


class Proxy:
   def __init__(self, cfg):
      self.LOCK = threading.Lock()
      self.sel = selectors.DefaultSelector()
      self.socket_wrappers = {}

      self.tls_ctx_remote = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
      self.tls_ctx_local  = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
      self.tls_ctx_remote.verify_mode = ssl.CERT_OPTIONAL
      self.tls_ctx_remote.check_hostname = False
      self.tls_ctx_local.load_cert_chain("ssl/cert.pem")

      self.servers = {}             # index of available servers by display name
      self.server_sockets = []

      self.client_sockets = []
      self.client_commands = {}

      self.states = [(self.server_sockets, self.handle_line_server),
                     #(preauth, handle_line_preauth),
                     (self.client_sockets, self.handle_line_client)]

      self.register_command("e", self.do_client_debug)
      self.register_command("J", self.do_client_connect)
      self.register_command("j", self.do_client_join)

      self.cfg = cfg

      self.filter_prototypes = {}

   def register_command(self, cmdname, cmd):
      #assert type(cmd) == function
      if cmdname not in self.client_commands:
         self.client_commands[cmdname] = cmd
      else:
         print("Note: Attempt to overwrite command `{}' failed".format(cmdname))

   def register_filter(self, name, impl):
      #assert exists impl.from_client, "Error: `{}' filter implementation needs from_client()".format(name)
      #assert exists impl.from_server, "Error: `{}' filter implementation needs from_server()".format(name)

      if name not in self.filter_prototypes:
         self.filter_prototypes[name] = impl
      else:
         print("Note: Attempted to overwrite filter type `{}' failed".format(name))

   ###
   ### STATE: server
   ###

   def handle_line_server(self, socket, line):
      assert socket in self.server_sockets

      svr = self.socket_wrappers[socket]
      ln = line

      for f in svr.filters:
         ln = f.from_server(ln)

         if ln is None:
            return

      self.socket_wrappers[socket].handle_data(ln)
      return False # don't continue trying states

   def do_start_connection(self, server):
      print("Starting to connect to server {}:{}.".format(server.host, server.port))

      # This will always be ran in a thread -- to prevent long-blocking connection
      # attempts from hanging the whole program (e.g., when a server is down,
      # tinyfugue can spend quite a while waiting for a connection attempt to
      # come through...)

      # The main program will set connecting_in_thread synchronously *before*
      # calling this thread, so we don't need to worry about accidental multiple
      # connection attempts.

      # It would probably be better to try to figure out asynchronous connect() or
      # something eventually.

      try:
         assert type(server) == RemoteServer
         assert server.socket == None
         assert not server.connected

         rlock = False

         C = socket.create_connection((server.host, server.port))

         if server.use_SSL:
            C = self.tls_ctx_remote.wrap_socket(C)

         self.LOCK.acquire()
         rlock = True
         server.attach_socket(C)
         self.socket_wrappers[C] = server
         self.server_sockets += [C]
         self.sel.register(C, selectors.EVENT_READ)

      except ConnectionRefusedError:
         server.warn_all("Connection attempt failed: Connection refused")

      except ssl.SSLError as e:
         server.warn_all("Connection attempt failed, SSL error: {}", repr(e))

      except (socket.error, socket.herror, socket.gaierror, socket.timeout) as err:
         server.warn_all("Connection attempt failed, network error: {}".format(repr(err)))

      except:
         kind, value, traceback = sys.exc_info()
         server.warn_all("Connection attempt failed, other error: {}".format(repr(value)))
         print("NON-SOCKET CONNECTION ERROR\n===========================\n\n" + repr(traceback))

      finally:
         server.connecting_in_thread = False
         if rlock:
            self.LOCK.release()
         return

   def start_connection(self, server):
      assert type(server) == RemoteServer

      if not server.connecting_in_thread and not server.connected:
         server.connecting_in_thread = True
         t_connect = threading.Thread(target = self.do_start_connection, args = [server])
         t_connect.start()
         return True

      else:
         return False

   ###
   ### STATE: client
   ###

   def handle_line_client(self, socket, line):
      assert socket in self.client_sockets

      s = line.as_str().replace('\r\n', '').replace('\n', '')
      c = self.socket_wrappers[socket]

      for f in c.filters:
         s = f.from_client(s)

         if s is None:
            return

      if s[:len(COMMAND_PREFIX)] == COMMAND_PREFIX:
         try:
            if ' ' in s:
               cmd = s[len(COMMAND_PREFIX):s.index(' ')]
               args = s[s.index(' ')+1:]
            else:
               cmd = s[len(COMMAND_PREFIX):]
               args = ''

            if cmd in self.client_commands:
               self.client_commands[cmd](args, c)
            else:
               c.tell_err("Command `{}' not found.".format(cmd))

         except:
            kind, value, traceback = sys.exc_info()
            c.tell_err("Error during command processing: {}".format(repr(value)))
            print("COMMAND PROCESSING ERROR\n========================\n\n" + repr(traceback))

      else:
         c.handle_data(line)

      return False # don't continue trying states

   def do_client_join(self, args, client):
      assert type(client) == LocalClient

      if args in self.servers:
         client.unsubscribe()
         self.servers[args].subscribe(client)
         client.subscribe(self.servers[args])
         client.tell_ok("Subscribed to server `{}'.".format(args))
         return True
      else:
         client.tell_err("No such server `{}'.".format(args))
         return False

   def do_client_connect(self, args, client):
      assert type(client) == LocalClient

      if self.do_client_join(args, client):
         self.start_connection(self.servers[args])
         return True #(ish)
      else:
         return False

   def do_client_debug(self, args, client):
      assert type(client) == LocalClient

      try:
         client.tell_ok(repr(eval(args)))
      except:
         kind, value, traceback = sys.exc_info()
         client.tell_err(repr(value))

   ###
   ### MAIN LOOP
   ###

   def run(self):
      # I'm not sure how much sense it makes to do this here and not in __init__ but oh well.
      for name, proto in self.cfg['servers'].items(): # (k, v)
         self.servers[name] = RemoteServer(proto['host'], proto['port'])

         if 'encoding' in proto:
            self.servers[name].encoding = proto['encoding']
         if 'ssl' in proto and proto['ssl'] is True:
            self.servers[name].use_SSL = True

         server_filters = self.cfg.get('filter_servers', [])
         try:
            self.servers[name].add_filters(server_filters, self.filter_prototypes)
            self.servers[name].add_filters(proto.get('filters', []), self.filter_prototypes)
         except FilterSpecificationError as e:
            print("Error setting up filters: {}".format(str(e)))

      try:
         def do_accept(socket, mask):
            print("Accepting new client...")

            # When SSL is turned on, this can block waiting for the client to send an SSL handshake.
            # Maybe consider running it in a thread, too?  (That's a lot of threading though.  And
            # clients are more under our control than remote servers are.)
            try:
               connection, address = socket.accept() # and hope it works
            except ssl.SSLError as e:
               print("SSL error in do_accept(): {}".format(e))
               return
            except:
               kind, val, traceback = sys.exc_info()
               print("Error in do_accept(): {}".format(val))
               return

            print("Accepted {} from {} (mask={}).".format(repr(connection), repr(address), repr(mask)))
            self.socket_wrappers[connection] = LocalClient(connection)
            self.client_sockets += [connection]
            self.sel.register(connection, selectors.EVENT_READ)

         server = socket.socket()
         server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
         server.bind(("0.0.0.0", 1234))

         server = self.tls_ctx_local.wrap_socket(server, server_side=True)

         server.listen(100)
         server.setblocking(False)
         self.sel.register(server, selectors.EVENT_READ)

         print("Listening.")

         while True:
            events = self.sel.select(timeout = 1)

            self.LOCK.acquire()

            for key, mask in events:
               s = key.fileobj
               if s == server:
                  do_accept(s, mask)
               else:
                  if s in self.socket_wrappers:
                     ss = self.socket_wrappers[s]
                  else:
                     ss = None

                  if ss == None:
                     print("NOTE: Read on unregistered socket")
                     # Almost certainly causes an infinite loop. Should consider raising an error.
                     break

                  (lines, eof) = ss.read()

                  if eof:
                     self.sel.unregister(s)
                     ss.handle_disconnect()
                     for state in self.states:
                        if s in state[0]:
                           del state[0][state[0].index(s)]
                     if s in self.socket_wrappers:
                        del self.socket_wrappers[s]

                  for line in lines:
                     for state in self.states:
                        if s in state[0]:
                           result = state[1](s, line)
                           if result:
                              break # to next line

            self.LOCK.release()

      except KeyboardInterrupt:
         print("Exiting uncleanly. Bye...")


###
### STARTUP / initialization
###

if __name__ == '__main__':
   cfg = {}
   try:
      with open(CONFIG_FILE, 'r') as f:
         cfg = json.load(f)
   except FileNotFoundError:
      print("Configuration file `{}' not found.  Please create it and try again.".format(CONFIG_FILE))
      exit()

   proxy = Proxy(cfg)

   pluginDir = cfg.get('plugin_directory', "plugins")
   plugin_err_fatal = cfg.get('plugin_errors_fatal', True)

   plugins = {}
   for P in pkgutil.iter_modules([pluginDir]):
      try:
         plugin = P.name
         m = importlib.import_module("{}.{}".format(pluginDir, plugin))
         m.setup(proxy)
         plugins[plugin] = m
         print("Loaded plugin {}".format(plugin))
      except:
         kind, value, traceback = sys.exc_info()
         print("Error loading plugin {}: {}".format(plugin, repr(value)))
         print("-------------------- TRACEBACK:")
         print(traceback)
         if plugin_err_fatal:
            exit()

   proxy.run()

