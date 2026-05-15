/*
   ____  _ _            _
  / ___|| | | __ _  ___| | _____
  \___ \| | |/ _` |/ __| |/ / __|
   ___) | | | (_| | (__|   <\__ \
  |____/|_|_|\__,_|\___|_|\_\___/

  Logging — single-header, level-gated, platform-aware.
*/

#ifndef GRIDFLUX_LOGGER_H
#define GRIDFLUX_LOGGER_H

#include <stdio.h>
#include <stdarg.h>

/* Log levels */
typedef enum {
    GF_LOG_TRACE = 0,
    GF_LOG_DEBUG,
    GF_LOG_INFO,
    GF_LOG_WARN,
    GF_LOG_ERROR,
    GF_LOG_LEVEL_COUNT
} gf_log_level_t;

/* Current compile-time threshold (can be overridden at build) */
#ifndef GF_LOG_LEVEL
#define GF_LOG_LEVEL GF_LOG_INFO
#endif

/* Core logging function */
void gf_log_impl(gf_log_level_t level, const char *file, int line, const char *fmt, ...);

/* Set the runtime log level (0=TRACE, 5=ERROR). */
void gf_log_set_level(gf_log_level_t level);

/* Runtime log level — extern for macro access */
extern gf_log_level_t g_log_level;

/* Per-level macros that compile out below threshold AND check runtime level */
#define GF_LOG_TRACE(...) do { \
    if (GF_LOG_TRACE >= GF_LOG_LEVEL && GF_LOG_TRACE >= g_log_level) \
        gf_log_impl(GF_LOG_TRACE, __FILE__, __LINE__, __VA_ARGS__); \
} while(0)

#define GF_LOG_DEBUG(...) do { \
    if (GF_LOG_DEBUG >= GF_LOG_LEVEL && GF_LOG_DEBUG >= g_log_level) \
        gf_log_impl(GF_LOG_DEBUG, __FILE__, __LINE__, __VA_ARGS__); \
} while(0)

#define GF_LOG_INFO(...)  do { \
    if (GF_LOG_INFO >= GF_LOG_LEVEL && GF_LOG_INFO >= g_log_level) \
        gf_log_impl(GF_LOG_INFO, __FILE__, __LINE__, __VA_ARGS__); \
} while(0)

#define GF_LOG_WARN(...)  do { \
    if (GF_LOG_WARN >= GF_LOG_LEVEL && GF_LOG_WARN >= g_log_level) \
        gf_log_impl(GF_LOG_WARN, __FILE__, __LINE__, __VA_ARGS__); \
} while(0)

#define GF_LOG_ERROR(...) do { \
    if (GF_LOG_ERROR >= GF_LOG_LEVEL && GF_LOG_ERROR >= g_log_level) \
        gf_log_impl(GF_LOG_ERROR, __FILE__, __LINE__, __VA_ARGS__); \
} while(0)

#endif /* GRIDFLUX_LOGGER_H */