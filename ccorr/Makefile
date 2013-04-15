all: pycorrmax.so

example.o: example.c example.h
	gcc -O3  -ffast-math -mfpmath=sse -g -fpic -c -Wall -Winline  example.c

libcorrmax.so: example.o 
	gcc -O3  -ffast-math -mfpmath=sse -g -shared -o libcorrmax.so -fpic example.o 
 
pycorrmax.so: libcorrmax.so example.h argmax.pyx argmax_setup.py
	CC=gcc python argmax_setup.py build_ext --inplace

c_test: libcorrmax.so c_test.c
	gcc -O2 -g -L. -Wall c_test.c -o c_test -lcorrmax -lm

.PHONY: run_c_test py_test clean

run_c_test: c_test
	LD_LIBRARY_PATH=$$LD_LIBRARY_PATH:. ./c_test

py_test: libcorrmax.so pycorrmax.so
	python test.py

clean:
	rm -f *.o *.so c_test argmax.c
