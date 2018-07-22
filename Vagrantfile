# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
    # The vanilla ones don't have vboxsf / virtualbox guest additions.  Probably an echo
    # of the whole debian/GNU software purity thing, which is... nice in an idealistic
    # sense.  But we need shared folders.  Fortunately they provide a box that will
    # help out with that:
    config.vm.box = "debian/contrib-testing64"
    
    config.vm.box_check_update = true
    config.vm.network "forwarded_port", guest: 8080, host: 8080, host_ip: "127.0.0.1"
    
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
        
        cat >/etc/systemd/system/tcphydra.service <<EOF
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

        systemctl enable tcphydra
        
        echo "[!!!!!] Service for proxy installed. You must reboot the VM or start the service by hand for it to take effect."
        echo "[!!!!!] If there is no password.json in the main directory, you must run the proxy once by hand to ensure a password file is generated. (Use ./start.sh in /vagrant after vagrant ssh.)"
    SHELL
end