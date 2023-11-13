#!/bin/bash

CWD=$(pwd)

python2.7 setup.py bdist_egg
python3 setup.py bdist_egg

cp dist/*.egg ~/.config/deluge/plugins

# /Applications/Deluge.app/Contents/MacOS/Deluge -L debug -l $CWD/run.log
deluge -L debug >run.log #-l $CWD/run.log gtk -L debug -l $CWD/gtk_run.log

trap "killall deluge-gtk" EXIT SIGINT

tail -f $CWD/run.log
