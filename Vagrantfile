# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
    # The vanilla ones don't have vboxsf / virtualbox guest additions.  Probably an echo
    # of the whole debian/GNU software purity thing, which is... nice in an idealistic
    # sense.  But we need shared folders.  Fortunately they provide a box that will
    # help out with that:
    config.vm.box = "debian/contrib-testing64"
    config.vm.box_check_update = true

    # Change the host: port to where you want to connect into the proxy from outside
    config.vm.network "forwarded_port", guest: 1234, host: 8080, host_ip: "127.0.0.1"
    
    # Runs once, to install dependencies and system service:
    config.vm.provision "shell", inline: <<-SHELL
        apt-get update
        apt-get install -y git python3 python3-pip tf5
        pip3 install robotframework
        
        cd /vagrant
        
        sudo -u vagrant bash <<EOF
if [[ ! -f ssl/cert.pem ]]; then
  cd ssl; ./gen_keys.sh; cd ..
fi
EOF
    SHELL
    
    # Runs every load.  We do it this way because /vagrant isn't mounted on boot
    # when systemctl enable inside the VM would start it.
    config.vm.provision "shell", run: "always", inline: <<-SHELL
        SERVICES_DIR=/etc/systemd/system
        
        if [[ ! -f $SERVICES_DIR/tcphydra.service ]]; then
            cat >$SERVICES_DIR/tcphydra.service <<EOF
[Unit]
Description=TCP line proxy

[Service]
Type=simple
User=vagrant
Group=vagrant
WorkingDirectory=/vagrant
ExecStart=/bin/bash /vagrant/start.sh

[Install]
WantedBy=multi-user.target
EOF
        fi

        if [[ ! -f /vagrant/password.json ]]; then
            echo "[!!!!] MANUAL INTERVENTION REQUIRED: You need to run the proxy once by hand (in `vagrant ssh`) to set a password.  It won't be started automatically until you do.  `sudo systemctl start tcphydra.service` in the VM to run it in the background."
            exit
        fi
        
        systemctl start tcphydra.service
    SHELL
end