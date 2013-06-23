all: libcorrmax.so pycorrmax.so libsecondary.so pysecondary.so \
	 libinteraction.so pyinteraction.so

libcorrmax.so:
	cd ccorr; make libcorrmax.so; cd ..; ln -sf ccorr/libcorrmax.so libcorrmax.so 

pycorrmax.so:
	cd ccorr; make pycorrmax.so; cd ..; ln -sf ccorr/pycorrmax.so pycorrmax.so 

libsecondary.so:
	cd secondary; make libsecondary.so; cd ..; ln -sf secondary/libsecondary.so libsecondary.so 

pysecondary.so:
	cd secondary; make pysecondary.so; cd ..; ln -sf secondary/pysecondary.so pysecondary.so 

libinteraction.so:
	cd interaction; make libinteraction.so; cd ..; ln -sf interaction/libinteraction.so libinteraction.so 

pyinteraction.so:
	cd interaction; make pyinteraction.so; cd ..; ln -sf interaction/pyinteraction.so pyinteraction.so 

clean:
	rm *.so
