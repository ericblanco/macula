#!/bin/bash

set -e

apt-get update
apt-get install -y git python-dev python-virtualenv libblas-dev liblapack-dev libatlas-base-dev gfortran libpq-dev libsqlite3-dev libpng12-dev
mkdir -p /opt
cd /opt

if [ -d "/vagrant" -a -d "/home/vagrant" ] ;
then
    echo "Using /vagrant as git clone source"
    git clone /vagrant macula
else
    echo "Using github.com:threatstream/macula.git as git clone source"
    git clone git@github.com:threatstream/macula.git
fi

cd macula
virtualenv env
source env/bin/activate
pip install -r requirements.txt
