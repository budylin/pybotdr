#include <algorithm>
#include <stdlib.h>
#include <stdio.h>
#include "interaction.h"
#include "./bsensor/btest/bsensor.h"
#include "./bsensor/btest/DDUtils.h"

#define FILTERSCOUNT 12
#define DECAYSCOUNT 4
#define LEVELSCOUNT 3

struct context_t {
    unsigned n_channel;
    static void *sensor;
    char filterIsTransmited[FILTERSCOUNT];
};
void *context_t::sensor = NULL;


void *
create_context(unsigned n_channel)
{

    printf("Creating interaction context\n");
    context_t *context;
    context = new context_t;
    context->n_channel = n_channel;
    if (!context->sensor)
        context->sensor = createSensor((char *)"1001",(char *)"config.ini");
    for (i = 0; i < FILTERSCOUNT; i++)
        context->filterIsTransmited[i] = 1;
    return (void *)context;
}

void
free_context(void *context)
{
    context_t *ctx = (context_t *)context;
    printf("Freeing interaction context\n");
    delete ctx;
}

void
process(void *context, char *res)
{
    context_t *ctx = (context_t *)context;
    DSensorDataRecord *record;
    int j, k, z;
    record = createDSensorDataRecord(ctx->n_channel, FILTERSCOUNT,
                                     ctx->filterIsTransmited);
    for (j = 0; j < DECAYSCOUNT; j++)
    {
        for (k = 0; k < LEVELSCOUNT; k++)
        {
            z = j + k * DECAYSCOUNT;
            std::transform(res + ctx->n_channel * z,
                ctx->n_channel * (z + 1),
                record->filtersData[z],
                [&](char x) -> char { return x; });
        }
    }
    addNewMeasure(ctx->sensor, record);
}

