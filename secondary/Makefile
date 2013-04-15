FREAKING_COMPILE_QT_FLAGS = -pipe -g -Wall -W -O2 -D_REENTRANT  -DQT_NO_DEBUG -DQT_THREAD_SUPPORT -DQT_SHARED -DQT_TABLET_SUPPORT -I/usr/share/qt3/mkspecs/default -I. -I/usr/include/glib-2.0 -I/usr/lib/glib-2.0/include -I/usr/include/qt3
BSENSOR = -L./bsensor/btest

all: pysecondary.so libsecondary.so

example.o: example.cpp example.h
	g++  -std=c++0x -O2  -ffast-math -mfpmath=sse -g -fpic -c -Wall -Wextra -pedantic -Winline  example.cpp

libsecondary.so: example.o 
	g++  -std=c++0x -O2  -ffast-math -mfpmath=sse -g -shared -o libsecondary.so -fpic example.o 
 
pysecondary.so: libsecondary.so example.h secondary_setup.py secondary.pyx
	CC=gcc python secondary_setup.py build_ext --inplace

c_test: libsecondary.so c_test.c
	gcc -O2 -g -L. -Wall c_test.c -o c_test -lsecondary -lm

run_c_test: c_test
	LD_LIBRARY_PATH=$$LD_LIBRARY_PATH:. ./c_test

py_test: pysecondary.so libsecondary.so
	python test.py

clean:
	rm -f *.o *.so c_test secondary.c
