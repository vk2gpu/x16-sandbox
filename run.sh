#!/bin/bash

make
pushd ../x16-emulator
./x16emu -prg ../testbed/main.prg -run -debug -gif vera.gif #080d #

popd
