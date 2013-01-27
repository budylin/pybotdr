import numpy as np
cimport numpy as np


FLOAT = np.float64
ctypedef np.float64_t FLOAT_t 
INT = np.int
ctypedef np.int_t INT_t


cdef extern from "example.h" nogil:
    void *create_context(unsigned sp_len, unsigned n_sp)
    void free_context(void *context)
#    void calc_argmax(void *context, double *array, double *out, int *status)
# this is a workaround for cython bug 
    void calc_argmax(void *context, double *array, double *out, INT_t *status)

cdef class Argmax:
    cdef void *context
    cdef tuple lastshape
    cdef np.ndarray result
    cdef np.ndarray status
    cdef FLOAT_t *result_p
    cdef INT_t *status_p

    def __call__(self, np.ndarray[FLOAT_t, ndim=2, mode='c'] data):
        shape = (data.shape[0], data.shape[1])
        sp_len = shape[1]
        n_sp = shape[0]
        if self.context != NULL and self.lastshape != shape:
            free_context(self.context)
            self.context = NULL
        if not self.context:
            self.context = create_context(sp_len, n_sp)
            self.lastshape = shape
            self.result = np.zeros(n_sp, dtype=FLOAT)
            self.result_p = <FLOAT_t *>self.result.data
            self.status = np.zeros(n_sp, dtype=INT)
            self.status_p = <INT_t *>self.status.data
        with nogil:
            calc_argmax(self.context, <FLOAT_t *>data.data,
                        self.result_p, self.status_p)    
        return (self.result, self.status)

    def __dealloc__(self):
        if self.context:
            free_context(self.context)
