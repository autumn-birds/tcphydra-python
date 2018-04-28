This program proxies line-based TCP streams.  More specifically, you can connect to [MUD](https://en.wikipedia.org/wiki/MUD)-like servers through it; the connection is persisted even if your client crashes and remains singular even if you connect many clients.

It also lets you write and use plugins to do fancier stuff.

```
$ cp config.example.json config.json
$ nano config.json
$ cd ssl; ./gen_keys.sh; cd ..
$ python3 proxy.py
```

You must provide at least an item of information (country code or an arbitrary organization name both work) to create the self-signed SSL certificate, but you can make all the other fields blank.

This code runs on Python 3.6.  Older versions may not work.  Python 3.4 does not work.
