# Plugins

**NB: This file isn't really documentation as much as it is a clumsy attempt at figuring out how this would work before I implemented it. Not saying the current way works better, but the code itself calls some things by different names and in general is not described by the below.**

An extension mechanism.

If connecting from multiple places is the most useful part of running a proxy, this might be the other most useful part -- being able to easily write code that interacts with the connections.

## Requirements

- Intercept text coming from the remote server(s).  Be able to mutate it (if necessary) or act on it (e.g. by sending something back to the server, telling the user something, logging it, etc.)
  - Use cases: logging, triggers, pretty-printing / formatting / colorizing, etcetera.
  - Be able to assign this per-server (e.g. disable logging for some server.)
  - Be able to assign this per-client (e.g. hide certain lines, but only in this window.)
- Intercept text coming from client(s) and act on and/or mutate it.
  - Use cases: automate typing boring bits, tweak/add command syntax, etc.
- Register new commands, callable by any client, which run arbitrary Python code with access to the client and its current server connection if any (and/or the entire plugin interface if applicable.)

## Design

A **plugin** is a singular, high-level entity that provides some functionality.

A plugin's initialization function is called when the plugin is loaded and passed a single object of a type akin to, e.g., `Proxy` or similar.  This object provides at least functions to register the three types of functionality described below.

Plugins can provide the following kinds of functionality:

- **Adapter**
  - A named mechanism attachable to an arbitrary number of servers and/or clients, instantiated individually per connection.  This mechanism is defined as a class that provides two methods `from_client` and `from_server` which are called once for every line of text sent by the client and server sides of the connection, respectively.  Each method must return either the `TextLine` it was given with any modifications, which will 'fall through' to the next adapter in the line, or `None`, which will arrest processing of the line and cause it to be discarded completely.
  - The class `__init__` method is called with two additional arguments: the server or client object the adapter is being attached to, and a dictionary of options.
    - Options are specified in the configuration file.
  - No adapters are set by default unless otherwise specified in the configuration file.  The configuration file should offer options for specifying adapters to be attached to every world by default, to every client by default, and to individual worlds.
  - The syntax for specifying these would be something like `["xlogs",{"logdir":"/home/me/logs"}, "visibletimestamps",{}]`.
  - The order of processing must be the same as the order specified in the file.
  - System messages (those messages specifically sent by the core or other plugins, e.g., status messages) should be exempt(?) from being processed by plugins in this way.
  - *Potential* extra option: Return a list of `TextLine`s instead of one, causing each element in the list to be further processed normally.
- **Command**
  - This mechanism provides a single named function callable by any client with an arbitrary, optional textual argument.  The function is passed three arguments: The client that called it, the server that client is connected to (or `None`), and the argument, which may be an arbitrary string (including the empty string.)
  - The server and client objects available to this function may provide functions to attach new adapters to them, allowing e.g. a `log-to-file` command.
- **Timer**
  - A bit of code that is run on a regular basis.  This code should have access to all the client and server objects (maybe as part of the `Plugin` API mentioned above?)  This allows things like alerts, reminders, warning about some external state, etc.

Plugins are implemented as Python modules. On startup, the proxy automatically (attempts to) load and call the initialization functions of all modules present in the *plugin directory*, which is configurable, but should default to `plugins` or something otherwise reasonable in the same directory as the proxy's python file.

Plugins that need to keep state (e.g. for coordinating between command invocations or different client/server object pairs) should keep some global state in their module.
