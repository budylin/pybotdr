#define STATUS_OK 0

#ifdef __cplusplus
extern "C" {
#endif
void *create_context(unsigned n_channel);
void free_context(void *context);
void process(void *context, char *res);
#ifdef __cplusplus
}
#endif
