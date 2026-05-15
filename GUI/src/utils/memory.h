/*
   ____  _ _     _           _
  / ___|| | | __| | ___  ___| |_
  \___ \| | |/ _` |/ _ \/ __| __|
   ___) | | | (_| |  __/\__ \ |_
  |____/|_|_|\__,_|\___||___/\__|

  Memory utilities — aligned allocations, zero-init wrappers.
*/

#ifndef GRIDFLUX_MEMORY_H
#define GRIDFLUX_MEMORY_H

#include <stddef.h>
#include <stdlib.h>
#include <string.h>

/* Allocate + zero-initialise */
static inline void *gf_calloc(size_t count, size_t size) {
    void *p = calloc(count, size);
    return p;
}

/* Allocate without zeroing */
static inline void *gf_malloc(size_t size) {
    return malloc(size);
}

/* Re-allocate */
static inline void *gf_realloc(void *ptr, size_t size) {
    return realloc(ptr, size);
}

/* Free memory allocated by GridFlux helpers. */
static inline void gf_free(void *ptr) {
    free(ptr);
}

/* Duplicate a string (caller must gf_free) */
static inline char *gf_strdup(const char *s) {
    if (!s) return NULL;
    size_t len = strlen(s) + 1;
    char *d = gf_malloc(len);
    if (d) memcpy(d, s, len);
    return d;
}

#endif /* GRIDFLUX_MEMORY_H */
