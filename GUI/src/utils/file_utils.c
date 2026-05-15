#include "file_utils.h"
#include "memory.h"
#include "logger.h"
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <shlobj.h>

char *
gf_file_read(const char *path)
{
    if (!path)
        return NULL;

    FILE *f = fopen(path, "rb");
    if (!f) {
        GF_LOG_WARN("Failed to open file for reading: %s", path);
        return NULL;
    }

    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (len <= 0) {
        fclose(f);
        return NULL;
    }

    char *buf = gf_malloc((size_t)len + 1);
    if (!buf) {
        fclose(f);
        return NULL;
    }

    size_t read = fread(buf, 1, (size_t)len, f);
    buf[read] = '\0';
    fclose(f);
    return buf;
}

bool
gf_file_write(const char *path, const char *content)
{
    if (!path || !content)
        return false;

    FILE *f = fopen(path, "w");
    if (!f) {
        GF_LOG_WARN("Failed to open file for writing: %s", path);
        return false;
    }

    fprintf(f, "%s", content);
    fclose(f);
    return true;
}

bool
gf_file_exists(const char *path)
{
    if (!path)
        return false;

    DWORD attr = GetFileAttributesA(path);
    return (attr != INVALID_FILE_ATTRIBUTES &&
            !(attr & FILE_ATTRIBUTE_DIRECTORY));
}

char *
gf_get_exe_dir(void)
{
    char path[MAX_PATH] = {0};
    GetModuleFileNameA(NULL, path, MAX_PATH - 1);

    /* Strip filename to get directory */
    char *last_slash = strrchr(path, '\\');
    if (last_slash)
        *(last_slash + 1) = '\0';

    return gf_strdup(path);
}

char *
gf_path_join(const char *dir, const char *file)
{
    if (!dir || !file)
        return NULL;

    size_t dlen = strlen(dir);
    size_t flen = strlen(file);
    bool needs_sep = (dlen > 0 && dir[dlen - 1] != '\\');

    char *result = gf_malloc(dlen + flen + (needs_sep ? 2 : 1));
    if (!result)
        return NULL;

    strcpy(result, dir);
    if (needs_sep)
        strcat(result, "\\");
    strcat(result, file);
    return result;
}

char *
gf_config_dir(void)
{
    char path[MAX_PATH] = {0};

    /* Try APPDATA first (roaming) */
    if (SUCCEEDED(SHGetFolderPathA(NULL, CSIDL_APPDATA, NULL,
                                   SHGFP_TYPE_CURRENT, path)))
    {
        char *full = gf_path_join(path, "GridFlux");

        /* Ensure directory exists */
        CreateDirectoryA(full, NULL);
        return full;
    }

    /* Fallback: executable directory */
    return gf_get_exe_dir();
}