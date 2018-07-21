This program proxies line-based TCP streams.  More specifically, you can connect to [MUD](https://en.wikipedia.org/wiki/MUD)-like servers through it; the connection is persisted even if your client crashes and remains singular even if you connect many clients.

It also lets you write and use plugins to do fancier stuff.

```
$ cp config.example.json config.json
$ nano config.json
$ cd ssl; ./gen_keys.sh; cd ..
$ ./start.sh
```

You must provide at least an item of information (country code or an arbitrary organization name both work) to create the self-signed SSL certificate, but you can make all the other fields blank.

This code runs on Python 3.6.  Older versions may not work.  Python 3.4 does not work.

## copyright

There is currently no license, open source or otherwise.  **This does not mean you may use or modify the code in your project.**

## setup as a systemd service

You can use `systemctl show --property=UnitPath` to tell where systemd loads unit files from, which may be useful as a debug measure. The standard location for sysadmins to place their files is `/etc/systemd/system/` according to [ArchWiki](https://wiki.archlinux.org/index.php/Systemd#Writing_unit_files).

Presumably this would work for other init systems as well, just replace the systemd specific parts.

Disclaimer: I am not a Real Sysadmin.

```
# useradd tcphydra
# usermod -L tcphydra
# mkdir /home/tcphydra && chown -R tcphydra /home/tcphydra
# su tcphydra
$ cd
$ git clone <git repo with tcphydra code you want to install> .
$ cp config.example.json config.json
           ( edit your configuration file, or copy in an existing one instead )
$ cd ssl; sh gen-keys.sh; cd ..
           ( input details; you need at least one piece of information here )
$ ./start.sh
           ( first run requires you to create a password keyboard-interactively; kill the proxy with ^C afterwards )
$ exit
```

Create a unit file in the appropriate place -- in my case I used `/etc/systemd/system/tcphydra.service` (you don't want to put this in the subdirectory `multi-user.target.wants`):

```
[Unit]
Description=TCP line proxy

[Service]
Type=simple
User=tcphydra
Group=tcphydra
WorkingDirectory=/home/tcphydra
ExecStart=/home/tcphydra/start.sh

[Install]
WantedBy=multi-user.target
```

Run `# systemctl start tcphydra.service` and if desired `# systemctl enable tcphydra.service`. `# systemctl status tcphydra.service` to check. `# journalctl -e` is useful sometimes if a service is failing and you can't figure out why.
