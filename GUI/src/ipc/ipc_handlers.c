/*
   ____        _             _       _
  |  _ \ _   _| | ___  _   _| | __ _| |_ ___
  | | | | | | | |/ _ \| | | | |/ _` | __/ _ \
  | |_| | |_| | | (_) | |_| | | (_| | ||  __/
  |____/ \__,_|_|\___/ \__,_|_|\__,_|\__\___|

  IPC command handlers — parses incoming commands and
  dispatches to the appropriate WM function.
*/

#include "ipc_handlers.h"
#include "../core/wm.h"
#include "../core/wm_internal.h"
#include "../core/layout.h"
#include "../core/debug.h"
#include "../core/types.h"
#include "../platform/platform.h"
#include "../ipc/ipc.h"
#include "../config/config.h"
#include "../utils/logger.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

/* ── Command table entry ────────────────────────────────────── */
typedef struct {
    const char *name;
    gf_err_t  (*handler)(gf_wm_t *wm, const char *args,
                          char *response, size_t resp_size);
} gf_cmd_entry_t;

/* ── Forward declarations of command handlers ───────────────── */
static gf_err_t cmd_ping
    (gf_wm_t *wm, const char *args, char *resp, size_t rsz);
static gf_err_t cmd_status
    (gf_wm_t *wm, const char *args, char *resp, size_t rsz);
static gf_err_t cmd_tile
    (gf_wm_t *wm, const char *args, char *resp, size_t rsz);
static gf_err_t cmd_cycle
    (gf_wm_t *wm, const char *args, char *resp, size_t rsz);
static gf_err_t cmd_switch
    (gf_wm_t *wm, const char *args, char *resp, size_t rsz);
static gf_err_t cmd_toggle_borders
    (gf_wm_t *wm, const char *args, char *resp, size_t rsz);
static gf_err_t cmd_set_grid
    (gf_wm_t *wm, const char *args, char *resp, size_t rsz);
static gf_err_t cmd_lock_grids
    (gf_wm_t *wm, const char *args, char *resp, size_t rsz);
static gf_err_t cmd_dump
    (gf_wm_t *wm, const char *args, char *resp, size_t rsz);
static gf_err_t cmd_reload
    (gf_wm_t *wm, const char *args, char *resp, size_t rsz);

/* ── Command registry ───────────────────────────────────────── */

static const gf_cmd_entry_t COMMANDS[] = {
    { "ping",            cmd_ping },
    { "status",          cmd_status },
    { "tile",            cmd_tile },
    { "cycle",           cmd_cycle },
    { "switch",          cmd_switch },
    { "toggle-borders",  cmd_toggle_borders },
    { "set-grid",        cmd_set_grid },
    { "lock-grids",      cmd_lock_grids },
    { "dump",            cmd_dump },
    { "reload",          cmd_reload },
};

#define CMD_COUNT (sizeof(COMMANDS) / sizeof(COMMANDS[0]))

/* ── Command parsing helpers ────────────────────────────────── */

static const char *
skip_ws(const char *p)
{
    while (*p == ' ' || *p == '\t') p++;
    return p;
}

static const char *
next_token(const char *p, char *buf, size_t bufsize)
{
    p = skip_ws(p);
    if (!*p) return p;

    const char *end = p;
    while (*end && *end != ' ' && *end != '\t') end++;

    size_t len = end - p;
    if (len >= bufsize) len = bufsize - 1;
    memcpy(buf, p, len);
    buf[len] = '\0';

    return (*end == '\0') ? end : end + 1;
}

/* ── Command implementations ────────────────────────────────── */

static gf_err_t
cmd_ping(gf_wm_t *wm, const char *args, char *resp, size_t rsz)
{
    (void)wm; (void)args;
    snprintf(resp, rsz, "pong gridflux %s", GRIDFLUX_VERSION);
    return GF_SUCCESS;
}

static gf_err_t
cmd_status(gf_wm_t *wm, const char *args, char *resp, size_t rsz)
{
    (void)args;
    gf_ws_id_t active = gf_wm_get_active_workspace(wm);
    gf_handle_t focused = gf_wm_get_focused(wm);

    snprintf(resp, rsz,
             "active_workspace=%d focused=0x%p borders=%s auto_tile=%s follow_focus=%s lock_grids=%s",
             active, focused,
             wm->borders_enabled ? "on" : "off",
             wm->config->auto_tile ? "on" : "off",
             wm->config->follow_focus ? "on" : "off",
             wm->config->lock_grids ? "on" : "off");
    return GF_SUCCESS;
}

static gf_err_t
cmd_tile(gf_wm_t *wm, const char *args, char *resp, size_t rsz)
{
    (void)args;
    gf_err_t rc = gf_wm_tile_all(wm);
    if (rc == GF_SUCCESS)
        snprintf(resp, rsz, "OK all workspaces tiled");
    else
        snprintf(resp, rsz, "ERROR tile failed: %d", rc);
    return rc;
}

static gf_err_t
cmd_cycle(gf_wm_t *wm, const char *args, char *resp, size_t rsz)
{
    char dir_str[16] = {0};
    args = next_token(args, dir_str, sizeof(dir_str));

    int direction = (dir_str[0] == '+' || dir_str[0] == '\0') ? 1 : -1;
    gf_err_t rc = gf_wm_cycle_focus(wm, direction);
    if (rc == GF_SUCCESS)
        snprintf(resp, rsz, "OK focus cycled %s",
                 direction > 0 ? "forward" : "backward");
    else
        snprintf(resp, rsz, "ERROR cycle failed: %d", rc);
    return rc;
}

static gf_err_t
cmd_switch(gf_wm_t *wm, const char *args, char *resp, size_t rsz)
{
    char ws_str[16] = {0};
    args = next_token(args, ws_str, sizeof(ws_str));

    long ws_id = strtol(ws_str, NULL, 10);
    if (ws_id < 0 || ws_id >= (long)wm->workspace_count)
    {
        snprintf(resp, rsz, "ERROR workspace %ld out of range [0,%u)",
                 ws_id, wm->workspace_count);
        return GF_ERROR_INVALID_PARAMETER;
    }

    gf_err_t rc = gf_wm_switch_workspace(wm, (gf_ws_id_t)ws_id);
    if (rc == GF_SUCCESS)
        snprintf(resp, rsz, "OK switched to workspace %ld", ws_id);
    else
        snprintf(resp, rsz, "ERROR switch failed: %d", rc);
    return rc;
}

static gf_err_t
cmd_toggle_borders(gf_wm_t *wm, const char *args, char *resp, size_t rsz)
{
    (void)args;
    gf_err_t rc = gf_wm_toggle_borders(wm);
    if (rc == GF_SUCCESS)
        snprintf(resp, rsz, "OK borders %s",
                 wm->borders_enabled ? "enabled" : "disabled");
    else
        snprintf(resp, rsz, "ERROR toggle failed: %d", rc);
    return rc;
}

static gf_err_t
cmd_set_grid(gf_wm_t *wm, const char *args, char *resp, size_t rsz)
{
    char rows_str[16] = {0}, cols_str[16] = {0};
    args = next_token(args, rows_str, sizeof(rows_str));
    args = next_token(args, cols_str, sizeof(cols_str));

    if (!rows_str[0] || !cols_str[0])
    {
        snprintf(resp, rsz, "Usage: set-grid <rows> <cols>");
        return GF_ERROR_INVALID_PARAMETER;
    }

    long rows = strtol(rows_str, NULL, 10);
    long cols = strtol(cols_str, NULL, 10);

    if (rows < 1 || rows > 16 || cols < 1 || cols > 16)
    {
        snprintf(resp, rsz, "ERROR rows/cols must be 1-16");
        return GF_ERROR_INVALID_PARAMETER;
    }

    wm->config->rows = (uint32_t)rows;
    wm->config->cols = (uint32_t)cols;
    gf_config_save(gf_config_get_path(), wm->config);

    /* Re-init all workspace layouts */
    for (uint32_t i = 0; i < wm->workspace_count; i++)
    {
        gf_layout_destroy(&wm->workspaces[i].layout);
        gf_rect_t bounds;
        if (wm->platform->screen_get_bounds(wm->display, &bounds) == GF_SUCCESS)
        {
            gf_layout_init(&wm->workspaces[i].layout,
                           (uint32_t)rows, (uint32_t)cols,
                           &bounds, wm->config->gap);
            gf_layout_set_weights(&wm->workspaces[i].layout,
                                  wm->config->row_weights,
                                  wm->config->col_weights);
        }
        gf_wm_tile_workspace(wm, (gf_ws_id_t)i);
    }

    snprintf(resp, rsz, "OK grid set to %lux%lu", rows, cols);
    return GF_SUCCESS;
}

static gf_err_t
cmd_lock_grids(gf_wm_t *wm, const char *args, char *resp, size_t rsz)
{
    char mode[16] = {0};
    args = next_token(args, mode, sizeof(mode));

    if (!mode[0])
    {
        snprintf(resp, rsz, "Usage: lock-grids <on|off>");
        return GF_ERROR_INVALID_PARAMETER;
    }

    bool locked = strcmp(mode, "on") == 0 || strcmp(mode, "1") == 0 ||
                  strcmp(mode, "true") == 0;
    if (!locked && strcmp(mode, "off") != 0 && strcmp(mode, "0") != 0 &&
        strcmp(mode, "false") != 0)
    {
        snprintf(resp, rsz, "Usage: lock-grids <on|off>");
        return GF_ERROR_INVALID_PARAMETER;
    }

    wm->config->lock_grids = locked;
    for (uint32_t i = 0; i < wm->workspace_count; i++)
        wm->workspaces[i].locked = locked;

    gf_config_save(gf_config_get_path(), wm->config);
    snprintf(resp, rsz, "OK grids %s", locked ? "locked" : "unlocked");
    return GF_SUCCESS;
}

static gf_err_t
cmd_dump(gf_wm_t *wm, const char *args, char *resp, size_t rsz)
{
    (void)args; (void)resp; (void)rsz;
    gf_debug_dump_wm(wm);
    return GF_SUCCESS;
}

static gf_err_t
cmd_reload(gf_wm_t *wm, const char *args, char *resp, size_t rsz)
{
    (void)args;
    const char *config_path = gf_config_get_path();

    gf_config_free(wm->config);
    gf_err_t rc = gf_config_load(config_path, &wm->config);
    if (rc == GF_SUCCESS)
    {
        /* Re-tile everything with new settings */
        wm->borders_enabled = wm->config->enable_borders;
        wm->workspace_count = wm->config->workspace_count;

        for (uint32_t i = 0; i < wm->workspace_count; i++)
        {
            gf_layout_destroy(&wm->workspaces[i].layout);
            memset(&wm->workspaces[i].layout, 0, sizeof(gf_layout_grid_t));
            gf_wm_ensure_workspace_state(wm, (gf_ws_id_t)i);
            gf_wm_tile_workspace(wm, (gf_ws_id_t)i);
        }

        snprintf(resp, rsz, "OK config reloaded from %s", config_path);
    }
    else
    {
        /* Restore a default config so we don't crash */
        gf_config_default(&wm->config);
        snprintf(resp, rsz, "ERROR failed to reload config: %d", rc);
    }
    return rc;
}

/* ── Main dispatch entry point ──────────────────────────────── */

gf_ipc_response_t
gf_ipc_dispatch(gf_wm_t *wm, const char *command)
{
    gf_ipc_response_t resp = {GF_IPC_SUCCESS, {0}};

    if (!command || !command[0])
    {
        return gf_ipc_error("Empty command");
    }

    /* Parse command name */
    char cmd_name[64] = {0};
    const char *args = next_token(command, cmd_name, sizeof(cmd_name));

    /* Find handler */
    for (size_t i = 0; i < CMD_COUNT; i++)
    {
        if (strcmp(COMMANDS[i].name, cmd_name) == 0)
        {
            gf_err_t rc = COMMANDS[i].handler(wm, args,
                                              resp.message, sizeof(resp.message));
            resp.status = (rc == GF_SUCCESS) ? GF_IPC_SUCCESS : GF_IPC_ERROR_GENERIC;
            return resp;
        }
    }

    snprintf(resp.message, sizeof(resp.message),
             "Unknown command: %s", cmd_name);
    resp.status = GF_IPC_ERROR_INVALID_COMMAND;
    return resp;
}
