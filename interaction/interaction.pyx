import numpy as np
cimport numpy as np

CHAR = np.int8
ctypedef np.int8_t CHAR_t

cdef extern from "interaction.h" nogil:
    void *create_context(unsigned n_channel)
    void free_context(void *context)
    void process(void *context, char *out)

cdef class Interaction:
    cdef void *context
    cdef int n_channel
    cdef char *result_p
    def __call__(self, np.ndarray[CHAR_t, ndim=2, mode='c'] data):
        n_channel = data.shape[1]
        print "n_channel in interaction", n_channel
        if (self.context != NULL and
           (self.n_channel != n_channel)):
            free_context(self.context)
            self.context = NULL
        if not self.context:
            self.context = create_context(n_channel)
            self.n_channel = n_channel
            self.result_p = <char *>data.data
        with nogil:
            process(self.context, self.result_p)

    def __dealloc__(self):
        if self.context:
            free_context(self.context)
