#define STATUS_OK 0


void *create_context(unsigned sp_len, unsigned n_sp);
void free_context(void *context);
void calc_argmax(void *context, double *array, double *out, int *status);
