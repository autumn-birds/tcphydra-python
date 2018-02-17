class TestFilter:
    def __init__(self, connection, options):
        print("Init with options {}".format(repr(options)))

    def from_server(self, line):
        print("Got a line of text: {}".format(line.as_str()))

        if line.as_str()[0] == 'K' or line.as_str()[0] == 'J':
            print("l[0]=K, mutating")
            line.set('X' + line.as_str()[1:])

        return line

def setup(proxy):
    proxy.register_filter("test", TestFilter)
