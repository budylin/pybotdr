import numpy as np
cimport numpy as np


FLOAT = np.float64
ctypedef np.float64_t FLOAT_t 
CHAR = np.int8
INT = np.int
ctypedef np.int_t INT_t


cdef extern from "secondary.h" nogil:
    void *create_context(unsigned start, unsigned n_channel, int window_width,
                         double *decays, double *levels)
    void free_context(void *context)
    void process(void *context, double *array, char *out, double *diffs)

cdef class Secondary:
    cdef void *context
    cdef int n_channel
    cdef int start 
    cdef int window_width
    cdef np.ndarray result
    cdef readonly np.ndarray diffs
    cdef readonly np.ndarray results
    cdef np.ndarray status
    cdef char *result_p
    cdef double *diffs_p
    cdef list decs
    cdef list levs

    def __call__(self, np.ndarray[FLOAT_t, ndim=1, mode='c'] data,
                 int start, int n_channel, int window_width,
                 list decs, list levs):
        cdef np.ndarray[FLOAT_t, ndim=1] decs_arr
        cdef np.ndarray[FLOAT_t, ndim=1] levs_arr
        if (self.context != NULL and
           (self.n_channel != n_channel or decs != self.decs or
            levs != self.levs or start != self.start or
            self.window_width != window_width)):
            free_context(self.context)
            self.context = NULL
        if not self.context:

            decs_arr = np.array(decs, dtype=FLOAT)
            levs_arr = np.array(levs, dtype=FLOAT)
            self.context = create_context(start, n_channel, window_width,
                                          <double *>decs_arr.data,
                                          <double *>levs_arr.data)
            self.start = start
            self.n_channel = n_channel
            self.window_width = window_width
            self.decs = decs[:]
            self.levs = levs[:]
            self.results = np.zeros((12, n_channel), dtype=CHAR)
            self.diffs = np.zeros((4, n_channel), dtype=FLOAT)
            self.result_p = <char *>self.results.data
            self.diffs_p = <FLOAT_t *>(self.diffs.data)
        with nogil:
            process(self.context, <FLOAT_t *>data.data,
                    self.result_p, self.diffs_p)
        return self.result

    def __dealloc__(self):
        if self.context:
            free_context(self.context)
