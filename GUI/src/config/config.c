/*
   ____  _ ____
  / ___|| |  _ \ _ __ ___  __ _ _ __
 | |  _ | | |_) | '__/ _ \/ _` | '_ \
 | |_| || |  __/| | |  __/ (_| | | | |
  \____||_|_|   |_|  \___|\__,_|_| |_|

  GridFlux config implementation — JSON parser (minimal, no deps)
*/

#include "config.h"
#include "rules.h"
#include "../utils/memory.h"
#include "../utils/logger.h"
#include "../utils/file_utils.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ══════════════════════════════════════════════════════════════
   JSON helpers (minimal, no external deps)
   ══════════════════════════════════════════════════════════════ */

static char *gf_json_get_string(const char *json, const char *key,
                                 char *out, size_t out_size)
{
    char search[256];
    snprintf(search, sizeof(search), "\"%s\"", key);

    const char *pos = strstr(json, search);
    if (!pos) return NULL;

    pos = strchr(pos + strlen(search), ':');
    if (!pos) return NULL;
    pos++;

    while (*pos == ' ' || *pos == '\t') pos++;

    if (*pos != '"') return NULL;
    pos++;

    const char *end = strchr(pos, '"');
    if (!end) return NULL;

    size_t len = (size_t)(end - pos);
    if (len >= out_size) len = out_size - 1;

    memcpy(out, pos, len);
    out[len] = '\0';
    return out;
}

static int gf_json_get_int(const char *json, const char *key, int def)
{
    char search[256];
    snprintf(search, sizeof(search), "\"%s\"", key);

    const char *pos = strstr(json, search);
    if (!pos) return def;

    pos = strchr(pos + strlen(search), ':');
    if (!pos) return def;
    pos++;

    while (*pos == ' ' || *pos == '\t') pos++;

    return atoi(pos);
}

static bool gf_json_get_bool(const char *json, const char *key, bool def)
{
    char search[256];
    snprintf(search, sizeof(search), "\"%s\"", key);

    const char *pos = strstr(json, search);
    if (!pos) return def;

    pos = strchr(pos + strlen(search), ':');
    if (!pos) return def;
    pos++;

    while (*pos == ' ' || *pos == '\t') pos++;

    if (strncmp(pos, "true", 4) == 0) return true;
    if (strncmp(pos, "false", 5) == 0) return false;
    return atoi(pos) != 0;
}

static const char *gf_json_array_begin(const char *json, const char *key,
                                        const char **end_ptr)
{
    char search[256];
    snprintf(search, sizeof(search), "\"%s\"", key);

    const char *pos = strstr(json, search);
    if (!pos) return NULL;

    pos = strchr(pos + strlen(search), ':');
    if (!pos) return NULL;
    pos++;

    while (*pos == ' ' || *pos == '\t') pos++;

    if (*pos != '[') return NULL;
    pos++;

    while (*pos == ' ' || *pos == '\t') pos++;

    *end_ptr = strchr(pos, ']');
    if (!*end_ptr) return NULL;

    return pos;
}

static void gf_json_get_uint_array(const char *json, const char *key,
                                   uint32_t *out, uint32_t max_count,
                                   uint32_t def)
{
    const char *arr_end = NULL;
    const char *arr = gf_json_array_begin(json, key, &arr_end);

    for (uint32_t i = 0; i < max_count; i++)
        out[i] = def;

    if (!arr || arr >= arr_end)
        return;

    const char *p = arr;
    uint32_t idx = 0;
    while (p < arr_end && idx < max_count)
    {
        while (p < arr_end && (*p == ' ' || *p == '\t' || *p == ',' || *p == '\n' || *p == '\r'))
            p++;
        if (p >= arr_end)
            break;

        long value = strtol(p, (char **)&p, 10);
        out[idx++] = value > 0 ? (uint32_t)value : def;
    }
}

static void gf_json_get_string_array(const char *json, const char *key,
                                     char out[][GF_MAX_TASK_COMMAND],
                                     uint32_t max_count)
{
    const char *arr_end = NULL;
    const char *arr = gf_json_array_begin(json, key, &arr_end);

    for (uint32_t i = 0; i < max_count; i++)
        out[i][0] = '\0';

    if (!arr || arr >= arr_end)
        return;

    const char *p = arr;
    uint32_t idx = 0;
    while (p < arr_end && idx < max_count)
    {
        while (p < arr_end && (*p == ' ' || *p == '\t' || *p == ',' || *p == '\n' || *p == '\r'))
            p++;
        if (p >= arr_end || *p != '"')
            break;
        p++;

        size_t j = 0;
        while (p < arr_end && *p && *p != '"' && j + 1 < GF_MAX_TASK_COMMAND)
        {
            if (*p == '\\' && p + 1 < arr_end)
            {
                p++;
                if (*p == 'n')
                    out[idx][j++] = '\n';
                else
                    out[idx][j++] = *p;
                p++;
                continue;
            }
            out[idx][j++] = *p++;
        }
        out[idx][j] = '\0';
        if (*p == '"')
            p++;
        idx++;
    }
}

static void gf_json_get_bool_array(const char *json, const char *key,
                                   bool *out, uint32_t max_count,
                                   bool def)
{
    const char *arr_end = NULL;
    const char *arr = gf_json_array_begin(json, key, &arr_end);

    for (uint32_t i = 0; i < max_count; i++)
        out[i] = def;

    if (!arr || arr >= arr_end)
        return;

    const char *p = arr;
    uint32_t idx = 0;
    while (p < arr_end && idx < max_count)
    {
        while (p < arr_end && (*p == ' ' || *p == '\t' || *p == ',' || *p == '\n' || *p == '\r'))
            p++;
        if (p >= arr_end)
            break;

        if (strncmp(p, "true", 4) == 0)
        {
            out[idx++] = true;
            p += 4;
        }
        else if (strncmp(p, "false", 5) == 0)
        {
            out[idx++] = false;
            p += 5;
        }
        else
        {
            out[idx++] = atoi(p) != 0;
            while (p < arr_end && *p && *p != ',')
                p++;
        }
    }
}

/* ══════════════════════════════════════════════════════════════
   Config load / save
   ══════════════════════════════════════════════════════════════ */

static void _escape_json_string(char *out, size_t out_size, const char *in)
{
    size_t j = 0;
    for (size_t i = 0; in[i] && j + 1 < out_size; i++) {
        if (in[i] == '"' || in[i] == '\\') {
            if (j + 2 < out_size) { out[j++] = '\\'; out[j++] = in[i]; }
        } else {
            out[j++] = in[i];
        }
    }
    out[j] = '\0';
}

gf_err_t
gf_config_load(const char *path, gf_config_t **out_cfg)
{
    if (!path || !out_cfg) return GF_ERROR_INVALID_PARAMETER;

    char *content = gf_file_read(path);
    if (!content) {
        GF_LOG_WARN("Config file not found, using defaults: %s", path);
        return gf_config_default(out_cfg);
    }

    gf_config_t *cfg = gf_calloc(1, sizeof(gf_config_t));
    if (!cfg) { gf_free(content); return GF_ERROR_MEMORY_ALLOCATION; }

    cfg->rows           = (uint32_t)gf_json_get_int(content, "rows", GF_DEFAULT_ROWS);
    cfg->cols           = (uint32_t)gf_json_get_int(content, "cols", GF_DEFAULT_COLS);
    cfg->gap            = (uint32_t)gf_json_get_int(content, "gap", GF_DEFAULT_GAP);
    cfg->border_width   = (uint32_t)gf_json_get_int(content, "border_width", 2);
    gf_json_get_uint_array(content, "row_weights", cfg->row_weights, GF_MAX_GRID_TRACKS, 1);
    gf_json_get_uint_array(content, "col_weights", cfg->col_weights, GF_MAX_GRID_TRACKS, 1);
    cfg->enable_borders = gf_json_get_bool(content, "enable_borders", true);
    cfg->auto_tile      = gf_json_get_bool(content, "auto_tile", true);
    cfg->follow_focus   = gf_json_get_bool(content, "follow_focus", true);
    cfg->lock_grids     = gf_json_get_bool(content, "lock_grids", false);
    cfg->auto_launch_tasks = gf_json_get_bool(content, "auto_launch_tasks", false);
    cfg->workspace_count = (uint32_t)gf_json_get_int(content, "workspace_count", 3);
    gf_json_get_string_array(content, "startup_tasks", cfg->startup_tasks, GF_MAX_GRID_CELLS);
    if (strcmp(cfg->startup_tasks[0], "http://127.0.0.1:3000/index3.html") == 0)
        strncpy(cfg->startup_tasks[0], "http://localhost:3000/index4.html", GF_MAX_TASK_COMMAND - 1);
    if (strcmp(cfg->startup_tasks[0], "http://127.0.0.1:3000/index4.html") == 0)
        strncpy(cfg->startup_tasks[0], "http://localhost:3000/index4.html", GF_MAX_TASK_COMMAND - 1);
    if (strcmp(cfg->startup_tasks[1], "http://127.0.0.1:3000/index2.html") == 0)
        strncpy(cfg->startup_tasks[1], "http://localhost:3000/index2.html", GF_MAX_TASK_COMMAND - 1);
    gf_json_get_bool_array(content, "startup_task_f11", cfg->startup_task_f11, GF_MAX_GRID_CELLS, false);

    const char *ws_arr_end;
    const char *ws_arr = gf_json_array_begin(content, "workspace_names", &ws_arr_end);
    if (ws_arr && ws_arr < ws_arr_end) {
        const char *p = ws_arr;
        uint32_t idx = 0;
        while (p < ws_arr_end && idx < GF_MAX_WORKSPACES) {
            while (*p == ' ' || *p == '\t') p++;
            if (*p != '"') { p++; continue; }
            p++;
            const char *end = strchr(p, '"');
            if (!end) break;
            size_t len = (size_t)(end - p);
            if (len >= 64) len = 63;
            memcpy(cfg->workspace_names[idx], p, len);
            cfg->workspace_names[idx][len] = '\0';
            idx++;
            p = end + 1;
        }
        if (idx > 0) cfg->workspace_count = idx;
    }

    const char *rules_arr_end;
    const char *rules_arr = gf_json_array_begin(content, "window_rules", &rules_arr_end);
    if (rules_arr && rules_arr < rules_arr_end) {
        const char *p = rules_arr;
        uint32_t idx = 0;
        while (p < rules_arr_end && idx < GF_MAX_RULES) {
            while (*p == ' ' || *p == '\t' || *p == '{' || *p == ',') p++;
            if (*p == '}') { p++; continue; }
            if (*p == 0) break;

            /* Expect: { "wm_class": "...", "workspace_id": N } */
            char key_buf[128];
            const char *colon = strchr(p, ':');
            if (!colon) break;
            size_t klen = (size_t)(colon - p);
            if (klen >= sizeof(key_buf)) { p = colon + 1; continue; }
            memcpy(key_buf, p, klen);
            key_buf[klen] = '\0';

            char clean_key[128];
            const char *ks = key_buf;
            if (*ks == '"') ks++;
            size_t ks_len = strlen(ks);
            if (ks_len > 0 && ks[ks_len-1] == '"')
                ((char*)ks)[ks_len-1] = '\0';
            strncpy(clean_key, ks, sizeof(clean_key)-1);
            clean_key[sizeof(clean_key)-1] = '\0';

            p = colon + 1;
            while (*p == ' ' || *p == '\t') p++;

            if (strcmp(clean_key, "wm_class") == 0) {
                if (*p == '"') {
                    p++;
                    const char *vend = strchr(p, '"');
                    if (vend) {
                        size_t vlen = (size_t)(vend - p);
                        if (vlen >= 128) vlen = 127;
                        memcpy(cfg->window_rules[idx].wm_class, p, vlen);
                        cfg->window_rules[idx].wm_class[vlen] = '\0';
                        p = vend + 1;
                    }
                }
                while (*p && *p != ':') p++;
                if (*p == ':') {
                    p++;
                    while (*p == ' ' || *p == '\t') p++;
                    cfg->window_rules[idx].workspace_id = atoi(p);
                }
                idx++;
            } else {
                while (*p && *p != ',' && *p != '}') p++;
            }
        }
        cfg->window_rules_count = idx;
    }

    gf_free(content);

    if (cfg->rows == 0) cfg->rows = GF_DEFAULT_ROWS;
    if (cfg->cols == 0) cfg->cols = GF_DEFAULT_COLS;
    if (cfg->gap == 0)   cfg->gap  = GF_DEFAULT_GAP;

    *out_cfg = cfg;
    GF_LOG_INFO("Config loaded: rows=%u cols=%u gap=%u rules=%u",
                cfg->rows, cfg->cols, cfg->gap, cfg->window_rules_count);
    return GF_SUCCESS;
}

gf_err_t
gf_config_save(const char *path, const gf_config_t *cfg)
{
    if (!path || !cfg) return GF_ERROR_INVALID_PARAMETER;

    char buf[131072];
    size_t pos = 0;

    pos += snprintf(buf + pos, sizeof(buf) - pos,
        "{\n"
        "  \"rows\": %u,\n"
        "  \"cols\": %u,\n"
        "  \"gap\": %u,\n"
        "  \"border_width\": %u,\n",
        cfg->rows, cfg->cols, cfg->gap, cfg->border_width);

    pos += snprintf(buf + pos, sizeof(buf) - pos, "  \"row_weights\": [");
    for (uint32_t i = 0; i < GF_MAX_GRID_TRACKS; i++)
        pos += snprintf(buf + pos, sizeof(buf) - pos, "%u%s",
            cfg->row_weights[i] ? cfg->row_weights[i] : 1,
            (i + 1 < GF_MAX_GRID_TRACKS) ? ", " : "");
    pos += snprintf(buf + pos, sizeof(buf) - pos, "],\n");

    pos += snprintf(buf + pos, sizeof(buf) - pos, "  \"col_weights\": [");
    for (uint32_t i = 0; i < GF_MAX_GRID_TRACKS; i++)
        pos += snprintf(buf + pos, sizeof(buf) - pos, "%u%s",
            cfg->col_weights[i] ? cfg->col_weights[i] : 1,
            (i + 1 < GF_MAX_GRID_TRACKS) ? ", " : "");
    pos += snprintf(buf + pos, sizeof(buf) - pos,
        "],\n"
        "  \"enable_borders\": %s,\n"
        "  \"auto_tile\": %s,\n"
        "  \"follow_focus\": %s,\n"
        "  \"lock_grids\": %s,\n"
        "  \"auto_launch_tasks\": %s,\n"
        "  \"workspace_count\": %u,\n"
        "\n"
        "  \"workspace_names\": [\n",
        cfg->enable_borders ? "true" : "false",
        cfg->auto_tile      ? "true" : "false",
        cfg->follow_focus   ? "true" : "false",
        cfg->lock_grids     ? "true" : "false",
        cfg->auto_launch_tasks ? "true" : "false",
        cfg->workspace_count);

    for (uint32_t i = 0; i < cfg->workspace_count; i++) {
        pos += snprintf(buf + pos, sizeof(buf) - pos,
            "    \"%s\"%s\n",
            cfg->workspace_names[i],
            (i + 1 < cfg->workspace_count) ? "," : "");
    }

    pos += snprintf(buf + pos, sizeof(buf) - pos,
        "  ],\n"
        "\n"
        "  \"startup_tasks\": [\n");

    uint32_t task_count = cfg->rows * cfg->cols;
    if (task_count > GF_MAX_GRID_CELLS)
        task_count = GF_MAX_GRID_CELLS;

    for (uint32_t i = 0; i < task_count; i++) {
        char escaped[GF_MAX_TASK_COMMAND * 2];
        _escape_json_string(escaped, sizeof(escaped), cfg->startup_tasks[i]);
        pos += snprintf(buf + pos, sizeof(buf) - pos,
            "    \"%s\"%s\n",
            escaped,
            (i + 1 < task_count) ? "," : "");
    }

    pos += snprintf(buf + pos, sizeof(buf) - pos,
        "  ],\n"
        "\n"
        "  \"startup_task_f11\": [\n");

    for (uint32_t i = 0; i < task_count; i++) {
        pos += snprintf(buf + pos, sizeof(buf) - pos,
            "    %s%s\n",
            cfg->startup_task_f11[i] ? "true" : "false",
            (i + 1 < task_count) ? "," : "");
    }

    pos += snprintf(buf + pos, sizeof(buf) - pos,
        "  ],\n"
        "\n"
        "  \"window_rules\": [\n");

    for (uint32_t i = 0; i < cfg->window_rules_count; i++) {
        char escaped[256];
        _escape_json_string(escaped, sizeof(escaped), cfg->window_rules[i].wm_class);
        pos += snprintf(buf + pos, sizeof(buf) - pos,
            "    { \"wm_class\": \"%s\", \"workspace_id\": %d }%s\n",
            escaped, cfg->window_rules[i].workspace_id,
            (i + 1 < cfg->window_rules_count) ? "," : "");
    }

    pos += snprintf(buf + pos, sizeof(buf) - pos, "  ]\n}\n");

    if (pos >= sizeof(buf) - 1) {
        GF_LOG_ERROR("Config buffer overflow");
        return GF_ERROR_GENERIC;
    }

    if (!gf_file_write(path, buf))
        return GF_ERROR_GENERIC;

    GF_LOG_INFO("Config saved to %s", path);
    return GF_SUCCESS;
}

gf_err_t
gf_config_default(gf_config_t **out_cfg)
{
    if (!out_cfg) return GF_ERROR_INVALID_PARAMETER;

    gf_config_t *cfg = gf_calloc(1, sizeof(gf_config_t));
    if (!cfg) return GF_ERROR_MEMORY_ALLOCATION;

    cfg->rows             = 2;
    cfg->cols             = 1;
    cfg->gap              = 0;
    cfg->border_width     = 0;
    cfg->enable_borders   = false;
    cfg->auto_tile        = true;
    cfg->follow_focus     = true;
    cfg->lock_grids       = false;
    cfg->auto_launch_tasks = true;
    cfg->workspace_count  = 1;

    for (uint32_t i = 0; i < GF_MAX_GRID_TRACKS; i++)
    {
        cfg->row_weights[i] = 1;
        cfg->col_weights[i] = 1;
    }
    cfg->row_weights[0] = 3;
    cfg->row_weights[1] = 7;

    for (uint32_t i = 0; i < GF_MAX_GRID_CELLS; i++)
        cfg->startup_task_f11[i] = false;
    strncpy(cfg->startup_tasks[0], "http://localhost:3000/index4.html", GF_MAX_TASK_COMMAND - 1);
    strncpy(cfg->startup_tasks[1], "http://localhost:3000/index2.html", GF_MAX_TASK_COMMAND - 1);
    cfg->startup_task_f11[0] = true;
    cfg->startup_task_f11[1] = true;

    const char *def_names[] = { "Kiosk" };
    for (uint32_t i = 0; i < 1 && i < GF_MAX_WORKSPACES; i++)
        strncpy(cfg->workspace_names[i], def_names[i], 63);

    cfg->window_rules_count = 0;

    *out_cfg = cfg;
    GF_LOG_INFO("Default config: rows=%u cols=%u gap=%u", cfg->rows, cfg->cols, cfg->gap);
    return GF_SUCCESS;
}

void
gf_config_free(gf_config_t *cfg)
{
    gf_free(cfg);
}

static char config_path[1024] = {0};

const char *
gf_config_get_path(void)
{
    if (config_path[0] != '\0')
        return config_path;

    char *dir = gf_config_dir();
    char *full = gf_path_join(dir, "config.json");

    size_t len = strlen(full);
    if (len >= sizeof(config_path)) len = sizeof(config_path) - 1;
    memcpy(config_path, full, len);
    config_path[len] = '\0';

    gf_free(full);
    gf_free(dir);
    return config_path;
}
