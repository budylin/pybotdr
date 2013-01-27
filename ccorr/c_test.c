#include <stdio.h>
#include "example.h"
#include <math.h>

void loadtxt(double *arr, char *name)
{   
    int i;
    FILE *fp = fopen(name, "r");
    for (i = 0; i < 49140 * 100; i++)
        fscanf(fp, "%lf", arr + i);
    fclose(fp);
}



int main()
{
    const int n_sp = (int)49140;
    const int sp_len = 100;
    
    double out[n_sp];
    int status[n_sp];
    double *arr = malloc(sp_len * n_sp * sizeof(double));
    int i, j;
    double x;
    double pos[n_sp];
    double w[n_sp];
    if(!arr)
    {
        printf("Not enough memory\n");
        return -1;
    }
    loadtxt(arr, "/Users/gleb/Data/2012-09-10T17-17-37.249072/down_0.txt");
//    for (j = 0; j < n_sp; j++)
//    {
//        w[j] = 7;
//        pos[j] = ((double)sp_len) / n_sp * j;
//    }
//    pos[0] = pos[n_sp / 2] - 1.523456;
//    for (j = 0; j < n_sp; j++)
//    {
//        for (i = 0; i < sp_len; i++)
//        {
//            x = i;
//            arr[i + sp_len * j] = exp(-(x - pos[j]) * (x - pos[j]) / w[j] / w[j]);
////            arr[i + sp_len * j] = 1;
//        }
//    }
    printf("Initialized\n");
    void *ctx = create_context(sp_len, n_sp);
    calc_argmax(ctx, arr, out, status);
    free_context(ctx);
    for (i = 0; i < n_sp; i++)
        if (status[i])
        printf("%d's array: maximum at %lf (%lf in fact), status %d\n",
               i, out[i], pos[i] - pos[n_sp / 2], status[i]);
    free(arr);
    return 0;
}
