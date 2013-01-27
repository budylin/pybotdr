all: module

shared: example.c example.h
	gcc -O3  -ffast-math -mfpmath=sse -g -fpic -c -Wall -Winline  example.c
	gcc -O3  -ffast-math -mfpmath=sse -g -shared -o libcorrmax.so -fpic example.o 
 
module: shared argmax.pyx
	CC=gcc python argmax_setup.py build_ext --inplace

c_test: shared
	gcc -O2 -g -L. -Wall c_test.c -o c_test -lcorrmax -lm

run_c_test: c_test
	LD_LIBRARY_PATH=$$LD_LIBRARY_PATH:. ./c_test

py_test: module
	python test.py

clean:
	rm -f *.o *.so c_test argmax.c
