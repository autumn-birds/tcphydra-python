import xmlwriter
import ansi

import datetime
import time
import logging

import os

open_logs = []

class LoggingFilter:
    def __init__(self, connection, options):
        print("Init with options {}".format(repr(options)))
        self.filename_template = options['filename']
        self.filename = None
        self.filehandle = None
        self.xml = None

        # This is kind of hacky, but I don't know of a good way to get
        # access to the main code's types from within the modules it
        # imports, so I can't directly see if we're getting the right
        # types here...  (You can do `import proxy` but you seem to get
        # a new copy of everything.)
        try:
            self.connection_name = connection.name
        except AttributeError:
            self.connection_name = "client"

        # (Try to) make sure there's a directory to put logs in.
        directory = os.path.dirname(self.get_new_filename())
        if directory != "":
            os.makedirs(directory, exist_ok=True)

    def get_new_filename(self):
        return self.filename_template \
                   .replace('DATE', time.strftime("%Y-%m-%d_%H%M")) \
                   .replace('CONNECTION', self.connection_name)

    def open(self):
        global open_logs

        if self.filehandle is not None:
            raise ValueError("Cannot open log when already open")

        self.filename = self.get_new_filename()

        try:
            self.filehandle = open(self.filename, 'x')
        except FileExistsError:
            logging.error("Can't create logfile {}: it exists".format(self.filename))
            raise
        except FileNotFoundError:
            # This happens when it can't find the directory to put it in.
            logging.error("Can't create logfile {}: file not found (does the parent directory exist?)")
            raise
        except PermissionError:
            logging.error("Can't create logfile {}: you don't have permission")
            raise

        self.xml = xmlwriter.XmlTagOutputter(indent='   ')

        def addtext(text):
            self.filehandle.write(text)

        self.xml.write_callback = addtext
        self.xml.buffer = False

        self.xml.open_tag("log")

        if self not in open_logs:
            open_logs.append(self)

    def close(self):
        global open_logs

        if self.filehandle is None:
            raise ValueError("Cannot close log when already closed")

        self.xml.close_all()
        self.filehandle.close()
        self.filehandle = None
        self.xml = None

        while self in open_logs:
            open_logs.remove(self)

    def from_server(self, line):
        if self.filehandle is None:
            self.open()

        passthrough = line

        self.xml.open_tag("line", {'date': datetime.datetime.utcnow().isoformat()})

        try:
            # We replace '\r' and '\n' because the raw line as sent from the server
            # may / will have some kind of trailing newline, and we don't want that
            # in the logs -- the lines are already separated for us as it is.
            line = ansi.parse_ANSI(line.as_str().replace('\r','').replace('\n',''))

        except ansi.ANSIParsingError as e:
            logging.warning("Error while trying to parse ANSI colors: {}".format(str(e)))
            # [1:-1] removes the quotes from the repr() representation, effectively
            # escaping any 'funny' characters that might be in the string.  In this
            # case, we want to make sure we escape ANSI codes (since we failed to parse
            # the ANSI codes), and repr() does that.
            #
            # ... still, this might possibly be not the best solution.
            line = [repr(line.as_str())[1:-1]]

        pending_text = None
        pending_colors = None

        for chunk in line:
            if type(chunk) is dict:
                if pending_colors is not None and pending_text is not None:
                    self.xml.inline_tag("text", pending_colors, pending_text)
                    pending_text = None

                pending_colors = chunk

            elif type(chunk) is str:
                if pending_text is None:
                    pending_text = chunk
                else:
                    pending_text += chunk

            else:
                raise TypeError("Unexpected type in parsed line of text")

        if pending_text is not None:
            if pending_colors is None:
                pending_colors = {}
            logging.debug("pending_colors = {}; pending_text = {}".format(repr(pending_colors), repr(pending_text)))
            self.xml.inline_tag("text", pending_colors, pending_text)

        self.xml.close_tag()
        self.filehandle.flush()

        return passthrough

    def from_client(self, line):
        return line

    def server_connect(self, connected):
        if connected:
            self.filename = self.get_new_filename()
            self.open()
        else:
            self.close()

def setup(proxy):
    proxy.register_filter("xlogs", LoggingFilter)

def teardown(proxy):
    for log in open_logs:
        log.close()
