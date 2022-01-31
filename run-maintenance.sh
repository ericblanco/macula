#!/bin/bash

cd $(dirname "$0")
if [ -e "env/bin/activate" ] ;
then
    source env/bin/activate
elif [ -e "venv/bin/activate" ] ;
then
    source venv/bin/activate
fi

cd commands
python prune_cache.py
