#define STATUS_OK 0

#ifdef __cplusplus
extern "C" {
#endif
void *create_context(unsigned start, unsigned n_channel, int window_width,
                     double *decays, double *levels);
void free_context(void *context);
void process(void *context, double *array, char *out);
#ifdef __cplusplus
}
#endif
