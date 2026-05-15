/*
   ____  _ _                    _       _
  / ___|| | | ___  ___ ___   __| | __ _| |_
  \___ \| | |/ _ \/ __/ _ \ / _` |/ _` | __|
   ___) | | |  __/ (_| (_) | (_| | (_| | |_
  |____/|_|_|\___|\___\___/ \__,_|\__,_|\__|

  Small utility math functions used by resize and layout.
*/

#ifndef GRIDFLUX_MATH_UTILS_H
#define GRIDFLUX_MATH_UTILS_H

#include "../core/types.h"

/* Divide a rect into n equal columns, return the width of each. */
static inline int gf_divide_width(const gf_rect_t *r, uint32_t n)
{
    if (n == 0) return 0;
    return (int)((r->w - (int)(n - 1) * 4) / n);
}

/* Divide a rect into n equal rows, return the height of each. */
static inline int gf_divide_height(const gf_rect_t *r, uint32_t n)
{
    if (n == 0) return 0;
    return (int)((r->h - (int)(n - 1) * 4) / n);
}

/* Check if a point {x,y} lies inside a rect. */
static inline bool gf_point_in_rect(const gf_point_t *p, const gf_rect_t *r)
{
    return p->x >= r->x && p->x < r->x + r->w &&
           p->y >= r->y && p->y < r->y + r->h;
}

/* Clamp an integer between lo and hi inclusive. */
static inline int gf_clamp(int val, int lo, int hi)
{
    return val < lo ? lo : (val > hi ? hi : val);
}

/* Linear interpolation between a and b at fraction t [0,1]. */
static inline int gf_lerp(int a, int b, float t)
{
    return (int)(a + (b - a) * t);
}

#endif /* GRIDFLUX_MATH_UTILS_H */