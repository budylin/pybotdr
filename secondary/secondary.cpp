#include <vector>
#include <algorithm>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include "secondary.h"
/*
#include "./bsensor/btest/bsensor.h"
#include "./bsensor/btest/DDUtils.h"
*/
#define FILTERSCOUNT 12
#define DECAYSCOUNT 4
#define LEVELSCOUNT 3
//#define NORMALIZE 1
#undef SECONDARY

struct context_t {
    unsigned start;
    unsigned n_channel;
    int isfirst;
    int window_width;
    static void *sensor;
    char filterIsTransmited[FILTERSCOUNT];
    std::vector<double> references[DECAYSCOUNT];
    std::vector<double> current, prev;
    std::vector<double> tmp, tmp2;
    std::vector<double> decays;
    std::vector<double> levels;
};
void *context_t::sensor = NULL;


void *
create_context(unsigned start, unsigned n_channel, int window_width,
               double *decays, double *levels)
{

    int i;
    printf("Creating secondary context\n");
    context_t *context;
    context = new context_t;
    context->start = start;
    context->n_channel = n_channel;
    context->window_width = window_width;
    printf("\tstart for secondary %u\n", start);
    printf("\tn_channel for secondary %u\n", n_channel);
    context->isfirst = 1;
#ifdef SECONDARY
    if (!context->sensor)
        context->sensor = createSensor((char *)"1001",(char *)"config.ini");
#endif
    for (i = 0; i < FILTERSCOUNT; i++)
        context->filterIsTransmited[i] = 1;
    context->tmp.resize(n_channel);
    context->decays.assign(decays, decays + DECAYSCOUNT);
    context->levels.assign(levels, levels + LEVELSCOUNT);
    printf("\tdecs: %f, %f, %f, %f\n", decays[0], decays[1],
           decays[2], decays[3]);
    printf("\tlevs: %f, %f, %f\n", levels[0], levels[1], levels[2]);
    return (void *)context;
}

void
free_context(void *context)
{
    context_t *ctx = (context_t *)context;
    printf("Freeing secondary context\n");
    delete ctx;
}

static void
blackman(int N, std::vector<double> &window)
{
    const double alpha = 0.16;
    const double a0 = (1 - alpha) / 2;
    const double a1 = 0.5;
    const double a2 = alpha / 2;
    const double pi = M_PI;
    int n;
    double sum = 0;
    window.resize(N);
    for (n = 0; n < N; n++)
    {
        window[n] = a0 - a1 * cos(2 * pi * n / (N - 1));
        window[n] += a2 * cos(4 * pi * n / (N - 1));

        sum += window[n];
    }
    for (n = 0; n < N; n++)
    {
        window[n] /= sum;
    }
}


/* Has size of data.size() */
/* window.size() is assumed to be even */
static void
convolve(const std::vector<double> &data, const std::vector<double> &window,
         std::vector<double> &conv)
{
    int i;
    const int ws = window.size();
    const int ds = data.size();
    conv.resize(data.size());
    for (i = 0; i < ws / 2; i++)
    {
        conv[i] = std::inner_product(window.begin() + ws / 2 - i, window.end(),
                                     data.begin(), (double)0);
    }
    for (i = ws / 2; i < ds - ws / 2;  i++)
    {
        conv[i] = std::inner_product(window.begin(), window.end(),
                                     data.begin() + (i - ws / 2), (double)0);
    }
    for (i = ds - ws / 2; i < ds; i++)
    {
        conv[i] = std::inner_product(data.begin() + (i - ws / 2),
                                     data.end(), window.begin(), (double)0);
    }
}

static void
sub_trend(std::vector<double> &data, int window_width)
{
    std::vector<double> window, conv;
    blackman(window_width, window);
    convolve(data, window, conv);
    std::transform(data.begin(), data.end(), conv.begin(), data.begin(),
                   std::minus<double>());
}

static void
feedback(std::vector<double> &y, const std::vector<double> &x, double decay)
{
    double alpha = pow(.5, (double)1 / decay);
    std::transform(y.begin(), y.end(), y.begin(),
                   [&](double yi) { return yi * alpha; });
    std::transform(y.begin(), y.end(), x.begin(), y.begin(),
                   [&](double yi, double xi) { return yi + (1 - alpha) * xi; });

}

static double
dispersion(const std::vector<double> &x, std::vector<double> &tmp)
{
    tmp.assign(x.begin(), x.end());
    std::sort(tmp.begin(), tmp.end());
    return (-tmp[x.size() / 6] + tmp[x.size() * 5 / 6]) / 2;
}

/* We assume that for some reason x_i = beta * reference_i + delta_i,
where delta is real difference, beta is a consequence of some undesired
deviations. We'll find alpha: sum_i (alpha * x_i - refernce_i)**2 -> min
and multiply x by alpha. */
void
normalize(std::vector<double> &x, const std::vector<double> &reference)
{
    double alpha, num, denum, init=0.;
    num = std::inner_product(x.begin(), x.end(), reference.begin(), init);
    denum = std::inner_product(x.begin(), x.end(), x.begin(), init);
    if (denum < 1e-7)
        return;
    alpha = num / denum;
    if (fabs(alpha) < 0.5)
        return;
    std::transform(x.begin(), x.end(), x.begin(),
                   [&](double xi) { return xi * alpha; });
}


void
process(void *context, double *array, char *out, double *diffs)
{
    context_t *ctx = (context_t *)context;
    double sigma;
#if SECONDARY
    DSensorDataRecord *record;
#endif
    int i, j, k, z;
    if (ctx->isfirst)
    {
        ctx->isfirst = 0;
        for (j = 0; j < DECAYSCOUNT; j++)
        {
            ctx->references[j].assign(array + ctx->start,
                                     array + ctx->start + ctx->n_channel);
            sub_trend(ctx->references[j], ctx->window_width);
        }
        ctx->prev.assign(ctx->references[0].begin(), ctx->references[0].end());
    }
    else
    {
        ctx->current.assign(array + ctx->start,
                            array + ctx->start + ctx->n_channel);
#ifdef NORMALIZE
        normalize(ctx->current, ctx->prev);
#endif
        sub_trend(ctx->current, ctx->window_width);

#ifdef SECONDARY
        record = createDSensorDataRecord(ctx->n_channel, FILTERSCOUNT,
                                         ctx->filterIsTransmited);
#endif
        for (j = 0; j < DECAYSCOUNT; j++)
        {
            feedback(ctx->references[j], ctx->prev, ctx->decays[j]);
            std::transform(ctx->current.begin(), ctx->current.end(),
                           ctx->references[j].begin(),
                           ctx->tmp.begin(),
                           std::minus<double>());
/* Hwat?? Looks like an awful blunder
            std::transform(ctx->current.begin(), ctx->current.end(),
                           ctx->current.begin(),
                           [](double x) {return x * x;});
*/
            sigma = dispersion(ctx->tmp, ctx->tmp2);
            std::copy(ctx->tmp.begin(), ctx->tmp.end(),
                      diffs + j * ctx->n_channel);
#if SECONDARY
            for (k = 0; k < LEVELSCOUNT; k++)
            {
                z = j + k * DECAYSCOUNT;
                std::transform(ctx->tmp.begin(),
                    ctx->tmp.end(),
                    record->filtersData[z],
                    [&](double x) -> char
                    {
                        return (char)(fabs(x) > sigma * ctx->levels[k]);
                    });
            }
#endif
        }
        ctx->prev.assign(ctx->current.begin(), ctx->current.end());
//        addNewMeasure(ctx->sensor, record);
    }
}

