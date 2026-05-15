/*
   ____  _ _            _                     _
  / ___|| | | __ _  ___| | _____  __ _ _ __ __| |
  \___ \| | |/ _` |/ __| |/ / __|/ _` | '__/ _` |
   ___) | | | (_| | (__|   <\__ \ (_| | | | (_| |
  |____/|_|_|\__,_|\___|_|\_\___/\__,_|_|  \__,_|

  Logging implementation — Windows Event Log + stderr.
*/

#include "logger.h"
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <time.h>

static const char *level_strings[] = {
    [GF_LOG_TRACE] = "TRACE",
    [GF_LOG_DEBUG] = "DEBUG",
    [GF_LOG_INFO]  = "INFO ",
    [GF_LOG_WARN]  = "WARN ",
    [GF_LOG_ERROR] = "ERROR",
};

/* Runtime log level (default: INFO) */
gf_log_level_t g_log_level = GF_LOG_INFO;

void
gf_log_set_level(gf_log_level_t level)
{
    g_log_level = level;
}

void
gf_log_impl(gf_log_level_t level, const char *file, int line, const char *fmt, ...)
{
    if (level < g_log_level)
        return;

    /* Timestamp */
    time_t now = time(NULL);
    struct tm tm_buf;
    localtime_s(&tm_buf, &now);
    char time_buf[64];
    strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", &tm_buf);

    /* Format the user message */
    char msg[1024];
    va_list args;
    va_start(args, fmt);
    vsnprintf(msg, sizeof(msg), fmt, args);
    va_end(args);

    /* Strip path to just filename */
    const char *short_file = file;
    for (const char *p = file; *p; p++) {
        if (*p == '\\' || *p == '/')
            short_file = p + 1;
    }

    /* Output to stderr */
    fprintf(stderr, "[%s] [%s] %s:%d: %s\n",
            time_buf, level_strings[level], short_file, line, msg);

    /* Also output to Windows debug console if attached */
    char debug_buf[1024];
    snprintf(debug_buf, sizeof(debug_buf), "[%s] [%s] %s:%d: %s\n",
             time_buf, level_strings[level], short_file, line, msg);
    OutputDebugStringA(debug_buf);
}