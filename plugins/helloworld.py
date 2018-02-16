
def mycmd(args, client):
    client.tell_ok("Hi there!  I'm a command from a plugin!")

def setup(proxy):
    proxy.register_command("hi", mycmd)

