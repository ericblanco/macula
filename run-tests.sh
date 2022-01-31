#!/bin/bash

export MACULA_DOMAIN_MODEL='data/test-domain.model'
export MACULA_IP_MODEL='data/test-domain.model'

cd $(dirname "$0")
if [ -e "env/bin/activate" ] ;
then
    source env/bin/activate
elif [ -e "venv/bin/activate" ] ;
then
    source venv/bin/activate
fi

python -m unittest discover
