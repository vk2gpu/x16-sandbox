.EXPORT_ALL_VARIABLES:
CC65_HOME=/usr/share/cc65
CA65_INC=/usr/share/cc65/asminc
CC65_INC=/usr/share/cc65/include

all:
	#acme -f cbm --cpu 65c02 -DMACHINE_C64=0 -o mode4-demo.prg mode4-demo.asm
	#ca65 g --cpu 65SC02 -DMACHINE_C64=0 -o mode4-demo.prg mode4-demo.asm
	cl65 -t cx16 -Oi -o main.prg -l main.asm main.c


clean:
	rm -f *.prg disk.d64
