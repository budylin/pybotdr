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
/*    const int n_sp = (int)5;
    const int sp_len = 100;

    char res[n_sp];
    double ref[n_sp];
    double pos[n_sp];
    int i, j;
    double x;
    double w[n_sp];
    for (j = 0; j < n_sp; j++)
    {
        ref[j] = 7;
        pos[j] = 7;
    }
    pos[n_sp / 2] = 100;
    printf("Initialized\n");
    void *ctx = create_context(0, n_sp, 1);
    //process(ctx, ref, res);
    //process(ctx, pos, res);
    free_context(ctx);
    for (i = 0; i < n_sp; i++)
        if (res[i])
        printf("%d's array\n", i);
*/    return 0;
}
