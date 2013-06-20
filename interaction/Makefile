FREAKING_COMPILE_QT_FLAGS = -pipe -g -Wall -W -O2 -D_REENTRANT  -DQT_NO_DEBUG -DQT_THREAD_SUPPORT -DQT_SHARED -DQT_TABLET_SUPPORT -I/usr/share/qt3/mkspecs/default -I. -I/usr/include/glib-2.0 -I/usr/lib/glib-2.0/include -I/usr/include/qt3
BSENSOR = -L./bsensor/btest

all: pyinteraction.so libinteraction.so

interaction.o: interaction.cpp interaction.h
	g++  -std=c++0x -O2  -g -fpic -c -Wall interaction.cpp

libinteraction.so: interaction.o 
	g++  -std=c++0x -O2  -g -shared -o libinteraction.so -fpic interaction.o 
 
pyinteraction.so: libinteraction.so interaction.h interaction_setup.py interaction.pyx
	CC=gcc python interaction_setup.py build_ext --inplace

clean:
	rm -f *.o *.so c_test interaction.c
