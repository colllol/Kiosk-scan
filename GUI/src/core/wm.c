#include "wm.h"
#include "wm_internal.h"
#include "layout.h"
#include "../config/config.h"
#include "../config/rules.h"
#include "../utils/logger.h"
#include "../utils/memory.h"
#include "../platform/platform.h"
#include <string.h>
#include <stdlib.h>

/* ── Internal helpers ────────────────────────────────────────── */

gf_workspace_state_t *
gf_wm_get_workspace_state(gf_wm_t *wm, gf_ws_id_t ws_id)
{
    if (ws_id < 0 || (uint32_t)ws_id >= wm->workspace_count)
        return NULL;
    return &wm->workspaces[ws_id];
}

gf_err_t
gf_wm_ensure_workspace_state(gf_wm_t *wm, gf_ws_id_t ws_id)
{
    gf_workspace_state_t *ws = gf_wm_get_workspace_state(wm, ws_id);
    if (!ws)
        return GF_ERROR_INVALID_PARAMETER;

    if (ws->layout.cells == NULL)
    {
        gf_rect_t bounds;
        if (wm->platform->screen_get_bounds(wm->display, &bounds) != GF_SUCCESS)
        {
            bounds = (gf_rect_t){0, 0, 1920, 1080};
        }

        uint32_t rows = wm->config->rows;
        uint32_t cols = wm->config->cols;

        if (gf_layout_init(&ws->layout, rows, cols, &bounds, wm->config->gap) != GF_SUCCESS)
        {
            GF_LOG_ERROR("Failed to init layout for workspace %d", ws_id);
            return GF_ERROR_GENERIC;
        }
        gf_layout_set_weights(&ws->layout,
                              wm->config->row_weights,
                              wm->config->col_weights);

        ws->id = ws_id;
        ws->locked = false;
        ws->maximized_only = false;
        ws->windows.items = NULL;
        ws->windows.count = 0;
        ws->windows.capacity = 0;
    }
    return GF_SUCCESS;
}

/* Apply a single cell's geometry to its assigned window */
void
gf_wm_apply_layout_cell(gf_wm_t *wm, gf_workspace_state_t *ws,
                        uint32_t row, uint32_t col)
{
    gf_cell_t *cell = &ws->layout.cells[row * ws->layout.cols + col];
    if (!cell->occupied || !cell->window)
        return;

    gf_rect_t *geom = &cell->rect;
    uint32_t flags = GF_GEOMETRY_APPLY_PADDING;
    uint32_t index = row * ws->layout.cols + col;

    if (index < GF_MAX_GRID_CELLS &&
        wm->config->startup_task_lock_buttons[index])
    {
        flags |= GF_GEOMETRY_LOCK_CAPTION_BUTTONS;
    }

    wm->platform->window_set_geometry(wm->display, cell->window, geom,
                                       flags, wm->config);
}

/* Tile all windows in a workspace according to the grid layout */
gf_err_t
gf_wm_tile_workspace(gf_wm_t *wm, gf_ws_id_t ws_id)
{
    gf_workspace_state_t *ws = gf_wm_get_workspace_state(wm, ws_id);
    if (!ws)
        return GF_ERROR_INVALID_PARAMETER;

    if (ws->locked)
    {
        GF_LOG_DEBUG("Workspace %d is locked, skipping tile", ws_id);
        return GF_SUCCESS;
    }

    /* Ensure layout exists */
    if (gf_wm_ensure_workspace_state(wm, ws_id) != GF_SUCCESS)
        return GF_ERROR_GENERIC;

    /* Clear all occupied flags but keep cell pointers */
    gf_layout_clear(&ws->layout);

    /* Assign each managed window to cells in row-major order */
    uint32_t idx = 0;
    for (uint32_t i = 0; i < ws->windows.count; i++)
    {
        gf_handle_t win = ws->windows.items[i].id;
        if (!wm->platform->window_is_valid(wm->display, win))
            continue;

        if (ws->maximized_only)
        {
            /* In maximized-only mode, skip non-maximized windows */
            if (!wm->platform->window_is_maximized(wm->display, win))
                continue;
        }

        uint32_t r, c;
        if (gf_layout_next_pos(&ws->layout, &r, &c) == GF_SUCCESS)
        {
            gf_layout_assign(&ws->layout, r, c, win);
            gf_wm_apply_layout_cell(wm, ws, r, c);
            idx++;
        }
        else
        {
            GF_LOG_WARN("Workspace %d grid full, cannot tile window %zu", ws_id, i);
        }
    }

    GF_LOG_DEBUG("Tiled %u windows in workspace %d", idx, ws_id);
    return GF_SUCCESS;
}

/* ── Lifecycle ──────────────────────────────────────────────── */

gf_err_t
gf_wm_create(gf_wm_t **out_wm)
{
    if (!out_wm)
        return GF_ERROR_INVALID_PARAMETER;

    gf_wm_t *wm = gf_calloc(1, sizeof(gf_wm_t));
    if (!wm)
        return GF_ERROR_MEMORY_ALLOCATION;

    wm->focused_window = 0;
    wm->borders_enabled = true;
    wm->resize_active = false;
    wm->ipc_running = false;
    wm->active_workspace = 0;
    wm->workspace_count = 0;
    wm->all_windows.items = NULL;
    wm->all_windows.count = 0;
    wm->all_windows.capacity = 0;

    *out_wm = wm;
    return GF_SUCCESS;
}

gf_err_t
gf_wm_init(gf_wm_t *wm, gf_platform_t *platform, gf_config_t *cfg)
{
    if (!wm || !platform || !cfg)
        return GF_ERROR_INVALID_PARAMETER;

    wm->platform = platform;
    wm->config = cfg;
    wm->borders_enabled = cfg->enable_borders;
    wm->workspace_count = cfg->workspace_count;

    if (wm->workspace_count == 0 || wm->workspace_count > GF_MAX_WORKSPACES)
        wm->workspace_count = 1;

    /* Initialize platform */
    if (platform->init(platform, &wm->display) != GF_SUCCESS)
    {
        GF_LOG_ERROR("Platform init failed");
        return GF_ERROR_PLATFORM_ERROR;
    }

    /* Initialize workspaces */
    for (uint32_t i = 0; i < wm->workspace_count; i++)
    {
        gf_workspace_state_t *ws = &wm->workspaces[i];
        ws->id = (gf_ws_id_t)i;
        ws->locked = cfg->lock_grids;
        ws->maximized_only = false;
        ws->windows.items = NULL;
        ws->windows.count = 0;
        ws->windows.capacity = 0;

        /* Init layout if grid dimensions are valid */
        if (cfg->rows > 0 && cfg->cols > 0)
        {
            gf_rect_t bounds;
            if (platform->screen_get_bounds(wm->display, &bounds) == GF_SUCCESS)
            {
                gf_layout_init(&ws->layout, cfg->rows, cfg->cols,
                               &bounds, cfg->gap);
                gf_layout_set_weights(&ws->layout,
                                      cfg->row_weights,
                                      cfg->col_weights);
            }
        }
    }

    /* Initialize keymap (workspace switching shortcuts) */
    if (platform->keymap_init)
        platform->keymap_init(platform, wm->display);

    /* Initialize dock hidden state */
    platform->dock_hide(platform);

    /* Enumerate initial windows */
    wm->active_workspace = 0;
    gf_wm_tile_all(wm);

    GF_LOG_INFO("WM initialized: workspaces=%u, borders=%s",
                wm->workspace_count, wm->borders_enabled ? "on" : "off");
    return GF_SUCCESS;
}

void
gf_wm_destroy(gf_wm_t *wm)
{
    if (!wm)
        return;

    if (wm->platform)
    {
        if (wm->platform->keymap_cleanup)
            wm->platform->keymap_cleanup(wm->platform);

        wm->platform->dock_restore(wm->platform);
        wm->platform->cleanup(wm->display, wm->platform);
        wm->platform->platform_destroy(wm->platform);
    }

    /* Free workspace layouts and window lists */
    for (uint32_t i = 0; i < wm->workspace_count; i++)
    {
        gf_layout_destroy(&wm->workspaces[i].layout);
        gf_free(wm->workspaces[i].windows.items);
    }

    gf_free(wm->all_windows.items);
    gf_free(wm);
}

/* ── Window operations ──────────────────────────────────────── */

gf_err_t
gf_wm_add_window(gf_wm_t *wm, gf_handle_t window, gf_ws_id_t ws_id)
{
    if (!wm || !window)
        return GF_ERROR_INVALID_PARAMETER;

    gf_workspace_state_t *ws = gf_wm_get_workspace_state(wm, ws_id);
    if (!ws)
        return GF_ERROR_INVALID_PARAMETER;

    /* Ensure workspace layout exists */
    if (gf_wm_ensure_workspace_state(wm, ws_id) != GF_SUCCESS)
        return GF_ERROR_GENERIC;

    /* Check if already present */
    for (uint32_t i = 0; i < ws->windows.count; i++)
    {
        if (ws->windows.items[i].id == window)
            return GF_SUCCESS;
    }

    /* Add to workspace window list */
    if (ws->windows.count >= ws->windows.capacity)
    {
        uint32_t new_cap = ws->windows.capacity == 0 ? 16 : ws->windows.capacity * 2;
        gf_win_info_t *new_items = gf_realloc(ws->windows.items,
                                               new_cap * sizeof(gf_win_info_t));
        if (!new_items)
            return GF_ERROR_MEMORY_ALLOCATION;
        ws->windows.items = new_items;
        ws->windows.capacity = new_cap;
    }

    gf_win_info_t *info = &ws->windows.items[ws->windows.count++];
    info->id = window;
    info->workspace_id = ws_id;
    info->is_valid = true;
    info->name[0] = '\0';
    info->last_modified = time(NULL);

    /* Get window geometry */
    wm->platform->window_get_geometry(wm->display, window, &info->geometry);
    if (wm->platform->window_get_class)
        wm->platform->window_get_class(wm->display, window, info->name, sizeof(info->name));

    GF_LOG_INFO("Added window %p to workspace %d", window, ws_id);

    /* Re-tile workspace */
    gf_wm_tile_workspace(wm, ws_id);
    return GF_SUCCESS;
}

gf_err_t
gf_wm_remove_window(gf_wm_t *wm, gf_handle_t window)
{
    if (!wm || !window)
        return GF_ERROR_INVALID_PARAMETER;

    for (uint32_t ws = 0; ws < wm->workspace_count; ws++)
    {
        gf_workspace_state_t *state = &wm->workspaces[ws];
        for (uint32_t i = 0; i < state->windows.count; i++)
        {
            if (state->windows.items[i].id == window)
            {
                /* Shift remaining */
                for (uint32_t j = i; j < state->windows.count - 1; j++)
                    state->windows.items[j] = state->windows.items[j + 1];

                state->windows.count--;
                GF_LOG_INFO("Removed window %p from workspace %d", window, ws);
                gf_wm_tile_workspace(wm, (gf_ws_id_t)ws);
                return GF_SUCCESS;
            }
        }
    }

    return GF_SUCCESS; /* Window not tracked is not an error */
}

gf_err_t
gf_wm_move_window(gf_wm_t *wm, gf_handle_t window, gf_ws_id_t target_ws)
{
    if (!wm || !window)
        return GF_ERROR_INVALID_PARAMETER;

    if (target_ws < 0 || (uint32_t)target_ws >= wm->workspace_count)
        return GF_ERROR_INVALID_PARAMETER;

    gf_workspace_state_t *target = gf_wm_get_workspace_state(wm, target_ws);
    if (!target || target->locked)
        return GF_ERROR_WORKSPACE_LOCKED;

    if (target->maximized_only)
    {
        if (!wm->platform->window_is_maximized(wm->display, window))
            return GF_ERROR_WORKSPACE_MAXIMIZED;
    }

    /* Remove from current workspace */
    gf_wm_remove_window(wm, window);

    /* Add to target workspace */
    gf_err_t result = gf_wm_add_window(wm, window, target_ws);
    if (result != GF_SUCCESS)
        return result;

    /* Switch to target workspace if not already there */
    if (wm->active_workspace != target_ws)
        gf_wm_switch_workspace(wm, target_ws);

    return GF_SUCCESS;
}

/* ── Tiling ─────────────────────────────────────────────────── */

gf_err_t
gf_wm_tile_all(gf_wm_t *wm)
{
    if (!wm)
        return GF_ERROR_INVALID_PARAMETER;

    for (uint32_t i = 0; i < wm->workspace_count; i++)
        gf_wm_tile_workspace(wm, (gf_ws_id_t)i);

    return GF_SUCCESS;
}

gf_err_t
gf_wm_refresh_workspace(gf_wm_t *wm, gf_ws_id_t ws_id)
{
    return gf_wm_tile_workspace(wm, ws_id);
}

/* ── Focus ──────────────────────────────────────────────────── */

gf_err_t
gf_wm_focus_window(gf_wm_t *wm, gf_handle_t window)
{
    if (!wm || !window)
        return GF_ERROR_INVALID_PARAMETER;

    wm->focused_window = window;
    return GF_SUCCESS;
}

gf_handle_t
gf_wm_get_focused(gf_wm_t *wm)
{
    return wm ? wm->focused_window : 0;
}

gf_err_t
gf_wm_cycle_focus(gf_wm_t *wm, int direction)
{
    if (!wm)
        return GF_ERROR_INVALID_PARAMETER;

    gf_workspace_state_t *ws = gf_wm_get_workspace_state(wm, wm->active_workspace);
    if (!ws || ws->windows.count == 0)
        return GF_SUCCESS;

    /* Find current focused index */
    int focused_idx = -1;
    for (uint32_t i = 0; i < ws->windows.count; i++)
    {
        if (ws->windows.items[i].id == wm->focused_window)
        {
            focused_idx = (int)i;
            break;
        }
    }

    int next = (focused_idx + direction) % (int)ws->windows.count;
    if (next < 0) next += (int)ws->windows.count;

    wm->focused_window = ws->windows.items[next].id;

    if (wm->platform->window_bring_to_top)
    {
        wm->platform->window_bring_to_top(wm->display, wm->focused_window);
    }

    GF_LOG_DEBUG("Focus cycled to window %p at index %d", wm->focused_window, next);
    return GF_SUCCESS;
}

/* ── Workspace ──────────────────────────────────────────────── */

gf_ws_id_t
gf_wm_get_active_workspace(gf_wm_t *wm)
{
    return wm ? wm->active_workspace : 0;
}

gf_err_t
gf_wm_switch_workspace(gf_wm_t *wm, gf_ws_id_t ws_id)
{
    if (!wm)
        return GF_ERROR_INVALID_PARAMETER;

    if (ws_id < 0 || (uint32_t)ws_id >= wm->workspace_count)
        return GF_ERROR_INVALID_PARAMETER;

    if (wm->workspaces[ws_id].locked)
        return GF_ERROR_WORKSPACE_LOCKED;

    wm->active_workspace = ws_id;

    /* Ensure layout is initialized */
    gf_wm_ensure_workspace_state(wm, ws_id);

    /* Re-tile the target workspace */
    gf_wm_tile_workspace(wm, ws_id);

    GF_LOG_INFO("Switched to workspace %d", ws_id);
    return GF_SUCCESS;
}

gf_err_t
gf_wm_workspace_lock(gf_wm_t *wm, gf_ws_id_t ws_id)
{
    if (!wm)
        return GF_ERROR_INVALID_PARAMETER;

    gf_workspace_state_t *ws = gf_wm_get_workspace_state(wm, ws_id);
    if (!ws)
        return GF_ERROR_INVALID_PARAMETER;

    if (ws->locked)
        return GF_ERROR_ALREADY_LOCKED;

    ws->locked = true;
    GF_LOG_INFO("Workspace %d locked", ws_id);
    return GF_SUCCESS;
}

gf_err_t
gf_wm_workspace_unlock(gf_wm_t *wm, gf_ws_id_t ws_id)
{
    if (!wm)
        return GF_ERROR_INVALID_PARAMETER;

    gf_workspace_state_t *ws = gf_wm_get_workspace_state(wm, ws_id);
    if (!ws)
        return GF_ERROR_INVALID_PARAMETER;

    if (!ws->locked)
        return GF_ERROR_ALREADY_UNLOCKED;

    ws->locked = false;
    GF_LOG_INFO("Workspace %d unlocked", ws_id);
    return GF_SUCCESS;
}

/* ── Window info helpers ────────────────────────────────────── */

gf_err_t
gf_wm_window_class(gf_wm_t *wm, gf_handle_t window,
                   char *buf, size_t bufsize)
{
    if (!wm || !window)
        return GF_ERROR_INVALID_PARAMETER;

    if (wm->platform->window_get_class)
    {
        wm->platform->window_get_class(wm->display, window, buf, bufsize);
        return GF_SUCCESS;
    }

    return GF_ERROR_GENERIC;
}

gf_win_list_t *
gf_wm_windows(gf_wm_t *wm)
{
    return wm ? &wm->all_windows : NULL;
}

gf_ws_list_t *
gf_wm_workspaces(gf_wm_t *wm)
{
    if (!wm) return NULL;

    static gf_ws_list_t result;
    result.count = wm->workspace_count;
    result.capacity = GF_MAX_WORKSPACES;
    result.active_workspace = wm->active_workspace;

    for (uint32_t i = 0; i < wm->workspace_count; i++)
    {
        gf_workspace_state_t *ws = &wm->workspaces[i];
        result.items[i].id = ws->id;
        strncpy(result.items[i].name,
                wm->config->workspace_names[i], 63);
        result.items[i].window_count = ws->windows.count;
        result.items[i].capacity = (uint32_t)gf_layout_next_pos(&ws->layout, &(uint32_t){0}, &(uint32_t){0}) == GF_SUCCESS ? 1 : 0;
        result.items[i].has_maximized_state = ws->maximized_only;
        result.items[i].available_space = (int)(ws->layout.rows * ws->layout.cols - ws->windows.count);
    }

    return &result;
}

gf_platform_t *
gf_wm_platform(gf_wm_t *wm)
{
    return wm ? wm->platform : NULL;
}

gf_display_t *
gf_wm_display(gf_wm_t *wm)
{
    return wm ? &wm->display : NULL;
}

/* ── Border management ──────────────────────────────────────── */

gf_err_t
gf_wm_toggle_borders(gf_wm_t *wm)
{
    if (!wm)
        return GF_ERROR_INVALID_PARAMETER;

    wm->borders_enabled = !wm->borders_enabled;

    if (!wm->borders_enabled)
        wm->platform->border_cleanup(wm->platform);

    return GF_SUCCESS;
}

gf_err_t
gf_wm_update_borders(gf_wm_t *wm)
{
    if (!wm || !wm->borders_enabled)
        return GF_SUCCESS;

    wm->platform->border_update(wm->platform, wm->config);
    return GF_SUCCESS;
}
