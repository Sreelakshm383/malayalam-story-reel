#!/bin/bash
# usage: film/preview.sh <shot> <frame> [scale]
out=build/preview; mkdir -p $out
xvfb-run -a -s "-screen 0 1280x1024x24" blender -b --factory-startup -P film/render.py -- $1 --start $2 --end $(($2+1)) --scale ${3:-50} --samples 16 --out $out/$1 2>&1 | grep -E "FRAME|Error|Traceback|File \"/home|^\w+Error" | grep -v distutils
