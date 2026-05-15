#include "debug.h"
#include "wm_internal.h"
#include "../utils/logger.h"
#include <stdio.h>

void
gf_debug_dump_wm(const gf_wm_t *wm)
{
    if (!wm)
    {
        GF_LOG_WARN("Debug dump: wm is NULL");
        return;
    }

    GF_LOG_INFO("══════════════════════════════════════════");
    GF_LOG_INFO("  GridFlux WM State Dump");
    GF_LOG_INFO("══════════════════════════════════════════");
    GF_LOG_INFO("  Active workspace : %d", wm->active_workspace);
    GF_LOG_INFO("  Workspace count  : %u", wm->workspace_count);
    GF_LOG_INFO("  Focused window   : %p", wm->focused_window);
    GF_LOG_INFO("  Borders enabled  : %s", wm->borders_enabled ? "yes" : "no");
    GF_LOG_INFO("  Resize active    : %s", wm->resize_active ? "yes" : "no");
    GF_LOG_INFO("  IPC running      : %s", wm->ipc_running ? "yes" : "no");

    char name[256] = {0};
    if (wm->config)
    {
        GF_LOG_INFO("  Config: rows=%u cols=%u gap=%d",
                    wm->config->rows, wm->config->cols, wm->config->gap);
        GF_LOG_INFO("  Auto-tile: %s  Follow-focus: %s",
                    wm->config->auto_tile ? "on" : "off",
                    wm->config->follow_focus ? "on" : "off");
        for (uint32_t i = 0; i < wm->config->workspace_count; i++)
        {
            GF_LOG_INFO("  Workspace[%u] name: \"%s\"",
                        i, wm->config->workspace_names[i]);
        }
    }

    gf_debug_dump_workspace(wm, wm->active_workspace);

    GF_LOG_INFO("══════════════════════════════════════════");
}

void
gf_debug_dump_workspace(const gf_wm_t *wm, gf_ws_id_t ws_id)
{
    if (!wm) return;

    gf_workspace_state_t *ws = gf_wm_get_workspace_state(wm, ws_id);
    if (!ws)
    {
        GF_LOG_WARN("Workspace %d not found", ws_id);
        return;
    }

    GF_LOG_INFO("─── Workspace %d ───", ws_id);
    GF_LOG_INFO("  Locked: %s  Max-only: %s",
                ws->locked ? "yes" : "no",
                ws->maximized_only ? "yes" : "no");
    GF_LOG_INFO("  Windows: %u", ws->windows.count);

    for (uint32_t i = 0; i < ws->windows.count; i++)
    {
        gf_win_info_t *w = &ws->windows.items[i];
        GF_LOG_INFO("    [%u] handle=%p name=\"%s\" valid=%s",
                    i, w->id, w->name, w->is_valid ? "yes" : "no");
        gf_debug_print_rect("      geo", &w->geometry);
    }

    /* Dump grid cells */
    if (ws->layout.cells)
    {
        GF_LOG_INFO("  Grid: %ux%u", ws->layout.rows, ws->layout.cols);
        for (uint32_t r = 0; r < ws->layout.rows; r++)
        {
            char row_buf[512] = {0};
            char *p = row_buf;
            for (uint32_t c = 0; c < ws->layout.cols; c++)
            {
                gf_cell_t *cell = &ws->layout.cells[r * ws->layout.cols + c];
                if (cell->occupied)
                    p += sprintf(p, "[■ %p] ", cell->window);
                else
                    p += sprintf(p, "[  ·  ] ");
            }
            GF_LOG_INFO("    %s", row_buf);
        }
    }
}

void
gf_debug_print_rect(const char *label, const gf_rect_t *r)
{
    if (!r) return;
    GF_LOG_INFO("  %s: {x=%d y=%d w=%d h=%d}",
                label ? label : "rect", r->x, r->y, r->w, r->h);
}