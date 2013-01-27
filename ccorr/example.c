#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include "example.h"
#define min(a, b) ((a) < (b) ? (a) : (b))
#define max(a, b) ((a) > (b) ? (a) : (b))
#define PROBE_INDEX 2000


typedef struct {
    unsigned sp_len;
    unsigned n_sp;
    double *df;
    double *corr;
    double *corr_tmp;
} context_t;

void *create_context(unsigned sp_len, unsigned n_sp)
{
    printf("Creating context, sp_len: %d, n_sp: %d\n", sp_len, n_sp);
    context_t *context;
    context = (context_t *)malloc(sizeof(context_t));
    context->sp_len = sp_len;
    context->n_sp = n_sp;
    context->df = (double *)malloc(n_sp * (sp_len - 1) * sizeof(double));
    context->corr = (double *)malloc((2 * sp_len + 3) * sizeof(double));
    context->corr_tmp = (double *)malloc((2 * sp_len + 3) * sizeof(double));
    return (void *)context;
}

void free_context(void *context)
{
    context_t *ctx = (context_t *)context;
    printf("Freeing context\n");
    free(ctx->corr);
    free(ctx->corr_tmp);
    free(ctx->df);
    free(ctx);
}

static int
sgn(double x)
{
    return (x > 0) - (x < 0);
}

static void
corr_part_nodes_inc(double fi, double gn, double dfi, double dgn,
               double dn_1, double coeffs[4])
{
    coeffs[0] += fi * gn;
}

static void
corr_nodes_inc(double fi, double gn, double dfi, double dgn,
               double dn_1, double coeffs[4])
{
    coeffs[0] += fi * gn + (fi * dgn + gn * dfi) / 2. + dfi * dgn / 3.;
}

static void
corr_inc(double fi, double gn, double dfi, double dgn,
          double dgn_1, double coeffs[4])
{
    coeffs[0] += fi * gn + (fi * dgn + gn * dfi) / 2. + dfi * dgn / 3.;
    coeffs[1] += -(fi + dfi / 2.) * dgn;
    coeffs[2] += (dgn - dgn_1) * fi / 2;
    coeffs[3] += (dgn - dgn_1) * dfi / 6;
}

static void
dcorr(double fi, double gn, double dfi, double dgn,
      double dgn_1, double coeffs[4])
{
    coeffs[0] = fi * gn + (fi * dgn + gn * dfi) / 2. + dfi * dgn / 3.;
    coeffs[1] = -(fi + dfi / 2.) * dgn;
    coeffs[2] = (dgn - dgn_1) * fi / 2;
    coeffs[3] = (dgn - dgn_1) * dfi / 6;
}

static double
coeffs_to_corr(double coeffs[4], double frac)
{
    double n;
    frac = modf(sgn(frac) * frac, &n);
    return  coeffs[0] + coeffs[1] * frac + coeffs[2] * frac * frac + \
            coeffs[3] * frac * frac * frac;
}


static void
correlate_coeff(const double *F, const double *G, const double *dF,
                const double *dG, const int len, double tau,
                void(*coeff_inc)(double, double, double, double, double,
                                 double coeff[4]),
                double tau_coeffs[4])
{
    unsigned floor;
    int i, n;
    double f_pre, df_pre;
    double f_post, df_post, g_post, dg_post, dg_1_post;
    const double *f, *g, *df, *dg;
    /* Let's use fact that corr(-tau)[f,g] = corr(tau)[g,f] */
    if (tau < 0)
    {
        f = G;
        g = F;
        df = dG;
        dg = dF;
        tau = -tau;
    }
    else
    {
        f = F;
        g = G;
        df = dF;
        dg = dG;
    }
    /* Now tau is positive */

    if (tau >= len + 1)
        return;

    floor = (unsigned)tau;
    if (floor == len)
    {
        f_pre = f[floor - 1];
        df_pre = -f[floor - 1];
    }
    else if (floor > 0)
    {
        f_pre = f[floor - 1];
        df_pre = df[floor - 1];
    }
    else if (floor == 0)
    {
        f_pre = 0;
        df_pre = f[0];
    }
    coeff_inc(f_pre, 0, df_pre, g[0], 0, tau_coeffs);

    if (floor < len - 1)
        coeff_inc(f[floor], g[0], df[floor], dg[0], g[0],
                              tau_coeffs);

    for (i = floor + 1, n = 1; i < len - 1; i++, n++)
    {
        coeff_inc(f[i], g[n], df[i], dg[n], dg[n - 1], tau_coeffs);
    }

    if (floor == len)
    {
        f_post = 0;
        df_post = 0;
        g_post = 0;
        dg_post = 0;
        dg_1_post = 0;
    }
    else if (floor == len - 1)
    {
        f_post = f[len - 1];
        df_post = -f[len - 1];
        g_post = g[0];
        dg_post = dg[0];
        dg_1_post = g[0];
    }
    else if (floor > 0)
    {
        f_post = f[len - 1];
        df_post = -f[len - 1];
        g_post = g[len - floor - 1];
        dg_post = dg[len - floor - 1];
        dg_1_post = dg[len - floor - 2];
    }
    else if (floor == 0)
    {
        f_post = f[len - 1];
        df_post = -f[len - 1];
        g_post = g[len - 1];
        dg_post = -g[len - 1];
        dg_1_post = dg[len - 2];
    }
    coeff_inc(f_post, g_post, df_post, dg_post, dg_1_post,
              tau_coeffs);
}

static void
corr_part_nodes_coeff(const double *F, const double *G,
                 const double *dF, const double *dG,
                 const int len, double tau, double coeffs[4])
{
    coeffs[0] = coeffs[1] = coeffs[2] = coeffs[3] = 0;
    correlate_coeff(F, G, dF, dG, len, tau, corr_part_nodes_inc, coeffs);
}

static void
corr_nodes_coeff(const double *F, const double *G,
                 const double *dF, const double *dG,
                 const int len, double tau, double coeffs[4])
{
    coeffs[0] = coeffs[1] = coeffs[2] = coeffs[3] = 0;
    correlate_coeff(F, G, dF, dG, len, tau, corr_nodes_inc, coeffs);
}

static void
corr_gen_coeff(const double *F, const double *G,
               const double *dF, const double *dG,
               const int len, double tau, double coeffs[4])
{
    coeffs[0] = coeffs[1] = coeffs[2] = coeffs[3] = 0;
    correlate_coeff(F, G, dF, dG, len, tau, corr_inc, coeffs);
}

static double
corr_part_nodes(const double *F, const double *G,
           const double *dF, const double *dG,
           const int len, double tau)
{
    double coeffs[4] = {0, 0, 0, 0};
    corr_part_nodes_coeff(F, G, dF, dG, len, tau, coeffs);
    return coeffs_to_corr(coeffs, tau);
}

static double
corr_nodes(const double *F, const double *G,
           const double *dF, const double *dG,
           const int len, double tau)
{
    double coeffs[4] = {0, 0, 0, 0};
    corr_nodes_coeff(F, G, dF, dG, len, tau, coeffs);
    return coeffs_to_corr(coeffs, tau);
}

static double
corr_gen(const double *F, const double *G,
         const double *dF, const double *dG,
         const int len, double tau)
{
    double coeffs[4] = {0, 0, 0, 0};
    corr_gen_coeff(F, G, dF, dG, len, tau, coeffs);
    return coeffs_to_corr(coeffs, tau);
}


static void
diff(const double *f, double *df, unsigned len)
{
    unsigned i;
    for (i = 0; i < len - 1; i++)
        df[i] = f[i + 1] - f[i];
 }

// Returns number of roots. Array roots contains roots if possible
static int
sq_solve(double a, double b, double c, double roots[2])
{
    double D;
    if (a == 0 && b == 0 && c == 0) // Any x is a root
        return -1;
    if (a == 0 && b == 0) // No roots
        return 0;
    if (a == 0)
    {
        roots[0] = -c / b;
        return 1;
    }
    D = b * b - 4 * a * c;
    if (D < 0)
        return 0;
    if (D == 0)
    {
        roots[0] = -b / 2 / a;
        return 1;
    }
    if (b < 0)
    {
        roots[1] = -(b - sqrt(D)) / 2 / a;
        roots[0] = c * 2 / -(b - sqrt(D));
    }
    else
    {
        roots[0] = -(b + sqrt(D)) / 2 / a;
        roots[1] = c * 2 / -(b + sqrt(D));
    }
    return 2;
}

void calc_argmax(void *context, double *array, double *out, int *status)
{
    context_t *ctx = (context_t *)context;
    unsigned n_sp = ctx->n_sp;
    unsigned sp_len = ctx->sp_len;
    int i, j, k, m;
    double d;
    FILE *fp;
    unsigned probe_index = PROBE_INDEX;
    double deltas[] = {-1 - 1e-7, -1 + 1e-7, -1e-7, 1e-7, 1 - 1e-7, 1 + 1e-7};
    double max_corr, max_pos, max_corr_plus, max_corr_minus, new_max;
    double second_step_max;
    double second_step_pos;
    double *corr = ctx->corr;
    double *tmp = ctx->corr_tmp;
    double *probe, *dprobe, *subarr, *dsubarr;
    double shift;
    double coeffs[4], roots[2];
    int n_roots;
    double max_shift = sp_len + 1;
    for (i = 0; i < n_sp; i++)
        diff(array + i * sp_len, ctx->df + i * (sp_len - 1), sp_len);
    for (j = 0; j < n_sp; j++)
    {
        max_pos = 0;
        max_corr = 0;
        subarr = array + j * sp_len;
        probe = array + probe_index * sp_len;
        dsubarr = ctx->df + j * (sp_len - 1);
        dprobe = ctx->df + probe_index * (sp_len - 1);
        for (m = 0; m < 2 * max_shift + 1; m += 1)
        {
            tmp[m] = corr_part_nodes(subarr, probe, dsubarr,
                              dprobe, sp_len, m - max_shift);
        }
        corr[0] = tmp[0];
        corr[2 * (int)max_shift] = tmp[2 * (int)max_shift];

        for(m = 1; m < 2 * max_shift; m += 1)
        {
            corr[m] = (tmp[m - 1] + tmp[m + 1]) / 6 + 2 * tmp[m] / 3;
        }
/*
        if (j == 0)
        {
            fp = fopen("node_part.dat", "w");
            for (m = 0; m < 2 * max_shift + 1; m += 1)
            {
                fprintf(fp, "%g %g\n", m - max_shift, corr[m]);
            }
            fclose(fp);
        }
*/
        for (m = 0; m < 2 * max_shift + 1; m += 1)
        {
            if (corr[m] > max_corr)
            {
                max_corr = corr[m];
                max_pos = -max_shift + (double)m;
            }
        }

        second_step_max = max_corr;
        second_step_pos = max_pos;
        for (i = 0 ; i < 6; i+= 1)
        {
            d = deltas[i];
//            printf("\nd = %lf, max_pos + d = %lf\n", d, max_pos + d);
            /* It should be noted6 that coeffs and roots produced by next two
            lines corresponds to corr(g, f) if (max_pos - m < 0) */
            corr_gen_coeff(subarr, probe, dsubarr, dprobe,
                           sp_len, max_pos + d, coeffs);
            n_roots = sq_solve(coeffs[3] * 3, coeffs[2] * 2, coeffs[1], roots);
//            printf("n_roots = %d\n", n_roots);
            for (k = 0; k < n_roots; k++)
            {
//                printf("\tr[%d] = %g\t", k, roots[k]);
                if (0 <= roots[k] && roots[k] < 1)
                {
                    if (max_pos + d < 0)
                        roots[k] =  -roots[k];
                    new_max = corr_gen(subarr, probe, dsubarr, dprobe, sp_len,
                                       max_pos + roots[k] + d);
//                    printf("node_max = %g, new_max = %g\n", max_corr, new_max);
                    if (new_max > second_step_max)
                    {
                        second_step_max = new_max;
                        second_step_pos = max_pos + roots[k] + d;
                    }
                }
//            printf("\n");
            }
        }
        max_corr = second_step_max;
        max_pos = second_step_pos;

        out[j] = max_pos;
        max_corr_plus = corr_gen(subarr, probe, dsubarr, dprobe, sp_len,
                                 max_pos + 1e-4);
        max_corr_minus = corr_gen(subarr, probe, dsubarr, dprobe, sp_len,
                                  max_pos - 1e-4);
        status[j] = max_corr < max_corr_minus || max_corr < max_corr_plus;
        if (status[j])
            printf("%g, %g, %g\n", max_corr, max_corr - max_corr_plus, max_corr - max_corr_minus);
    }
}

