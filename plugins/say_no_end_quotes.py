class SayQuoteStripper:
    """Removes extraneous quotes at the end of a 'say' command."""
    def __init__(self, connection, options):
        pass

    def from_server(self, line):
        return line

    def from_client(self, line):
        if line.as_str()[0] == '"':
            x = line.as_str().replace("\r\n","").replace("\n","")
            while x[-1] == '"':
                x = x[:-1]
            line.set(x+"\n")
        return line

def setup(proxy):
    proxy.register_filter("say_quote_strip", SayQuoteStripper)
