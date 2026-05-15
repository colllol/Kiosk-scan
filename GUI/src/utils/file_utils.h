#ifndef GRIDFLUX_FILE_UTILS_H
#define GRIDFLUX_FILE_UTILS_H

#include <stdbool.h>

/* Read an entire text file. Caller must gf_free() the returned buffer. */
char *gf_file_read(const char *path);

/* Write a text file. Overwrites if exists. */
bool gf_file_write(const char *path, const char *content);

/* Check if a file exists. */
bool gf_file_exists(const char *path);

/* Get the directory containing the executable. Caller must gf_free(). */
char *gf_get_exe_dir(void);

/* Join two path components. Caller must gf_free(). */
char *gf_path_join(const char *dir, const char *file);

/* Get config directory (e.g. %APPDATA%/GridFlux or ~/.config/gridflux).
   Caller must gf_free(). */
char *gf_config_dir(void);

#endif /* GRIDFLUX_FILE_UTILS_H */