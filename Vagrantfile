# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  # All Vagrant configuration is done here. The most common configuration
  # options are documented and commented below. For a complete reference,
  # please see the online documentation at vagrantup.com.

  # Every Vagrant virtual environment requires a box to build off of.
  config.vm.define "ubuntu" do |server|
    #server.vm.box = "hashicorp/precise64" # Ubuntu 12.04
    server.vm.box = "ubuntu/trusty64" # Ubuntu 14.04
    server.vm.network "private_network", ip: "10.254.254.100"
    
    server.vm.provision :shell, inline: 'echo ubuntu > /etc/hostname'
    server.vm.provision :shell, inline: 'echo "127.0.1.1 ubuntu" >> /etc/hosts'
    server.vm.provision :shell, inline: 'hostname ubuntu'
  end

  config.vm.provider "virtualbox" do |vb|
     vb.customize ["modifyvm", :id, "--memory", "2048"]
  end
end
