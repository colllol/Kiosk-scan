#include "events.h"
#include "layout.h"
#include "wm_internal.h"
#include "resize.h"
#include "../platform/platform.h"
#include "../config/rules.h"
#include "../utils/memory.h"
#include "../utils/logger.h"
#include <string.h>

bool
gf_wm_pump_events(gf_wm_t *wm)
{
    if (!wm || !wm->platform)
        return false;

    gf_event_t ev;
    while (wm->platform->poll_event(wm->display, &ev))
    {
        switch (ev.type)
        {
        case GF_EVENT_QUIT:
            GF_LOG_INFO("Received quit event");
            return false;

        case GF_EVENT_WINDOW_CLOSE:
            GF_LOG_INFO("Window %p requested close", ev.data.window_close.handle);
            gf_wm_remove_window(wm, ev.data.window_close.handle);
            break;

        case GF_EVENT_WINDOW_FOCUS:
            GF_LOG_DEBUG("Window %p focused", ev.data.window_focus.handle);
            gf_wm_focus_window(wm, ev.data.window_focus.handle);

            /* Move window to active workspace if it belongs elsewhere */
            {
                bool found = false;
                for (uint32_t ws = 0; ws < wm->workspace_count; ws++)
                {
                    for (uint32_t i = 0; i < wm->workspaces[ws].windows.count; i++)
                    {
                        if (wm->workspaces[ws].windows.items[i].id == ev.data.window_focus.handle)
                        {
                            found = true;
                            if ((gf_ws_id_t)ws != wm->active_workspace)
                            {
                                GF_LOG_DEBUG("Auto-switching to workspace %d", ws);
                                gf_wm_switch_workspace(wm, ws);
                            }
                        }
                        if (found) break;
                    }
                    if (found) break;
                }
            }
            break;

        case GF_EVENT_WINDOW_NEW:
            GF_LOG_DEBUG("New window detected: %p", ev.data.window_new.handle);
            gf_wm_add_window(wm, ev.data.window_new.handle, wm->active_workspace);
            break;

        case GF_EVENT_RESIZE_BEGIN:
            GF_LOG_DEBUG("Resize begin on window %p", ev.data.resize_begin.window);
            gf_resize_begin(wm, ev.data.resize_begin.window);
            break;

        case GF_EVENT_RESIZE_UPDATE:
            gf_resize_update(wm, &ev.data.resize_update);
            break;

        case GF_EVENT_RESIZE_END:
            GF_LOG_DEBUG("Resize end on window %p", ev.data.resize_end.window);
            gf_resize_end(wm, &ev.data.resize_end);
            break;

        case GF_EVENT_KEY:
            /* Handled by platform keymap; fall through for logging */
            GF_LOG_TRACE("Key event: sym=0x%X mod=0x%X pressed=%d",
                         ev.data.key.sym, ev.data.key.modifiers, ev.data.key.pressed);

            /* Workspace switching via Mod+number */
            if (ev.data.key.pressed && ev.data.key.modifiers & GF_MODIFIER_SUPER)
            {
                if (ev.data.key.sym >= '1' && ev.data.key.sym <= '9')
                {
                    gf_ws_id_t target = (gf_ws_id_t)(ev.data.key.sym - '1');
                    if (target < wm->workspace_count)
                        gf_wm_switch_workspace(wm, target);
                }
            }
            /* Cycle focus with Super+Tab / Super+Shift+Tab */
            else if (ev.data.key.pressed && ev.data.key.sym == GF_KEY_TAB &&
                     ev.data.key.modifiers & GF_MODIFIER_SUPER)
            {
                int dir = (ev.data.key.modifiers & GF_MODIFIER_SHIFT) ? -1 : 1;
                gf_wm_cycle_focus(wm, dir);
            }
            /* Toggle borders with Super+B */
            else if (ev.data.key.pressed && ev.data.key.sym == 'B' &&
                     ev.data.key.modifiers & GF_MODIFIER_SUPER)
            {
                gf_wm_toggle_borders(wm);
                if (wm->borders_enabled)
                    gf_wm_update_borders(wm);
            }
            break;

        case GF_EVENT_DISPLAY_CHANGE:
            GF_LOG_INFO("Display change detected, re-tiling all");
            /* Re-init all workspace layouts with new screen bounds */
            for (uint32_t i = 0; i < wm->workspace_count; i++)
            {
                gf_rect_t bounds;
                if (wm->platform->screen_get_bounds(wm->display, &bounds) == GF_SUCCESS)
                {
                    gf_layout_destroy(&wm->workspaces[i].layout);
                    gf_layout_init(&wm->workspaces[i].layout,
                                   wm->config->rows, wm->config->cols,
                                   &bounds, wm->config->gap);
                    gf_layout_set_weights(&wm->workspaces[i].layout,
                                          wm->config->row_weights,
                                          wm->config->col_weights);
                }
                gf_wm_tile_workspace(wm, (gf_ws_id_t)i);
            }
            break;

        default:
            break;
        }
    }

    return true;
}

void
gf_wm_rescan_windows(gf_wm_t *wm)
{
    if (!wm || !wm->platform || !wm->platform->enum_windows)
        return;

    gf_handle_t *handles = NULL;
    uint32_t count = 0;

    if (wm->platform->enum_windows(wm->display, &handles, &count) != GF_SUCCESS)
        return;

    for (uint32_t i = 0; i < count; i++)
    {
        gf_handle_t h = handles[i];
        if (!wm->platform->window_is_valid(wm->display, h))
            continue;

        /* Skip desktop/taskbar windows */
        char cls[256] = {0};
        if (wm->platform->window_get_class)
            wm->platform->window_get_class(wm->display, h, cls, sizeof(cls));

        if (strcmp(cls, "WorkerW") == 0 || strcmp(cls, "Shell_TrayWnd") == 0)
            continue;

        /* Check if already tracked */
        bool tracked = false;
        for (uint32_t ws = 0; ws < wm->workspace_count && !tracked; ws++)
        {
            for (uint32_t j = 0; j < wm->workspaces[ws].windows.count; j++)
            {
                if (wm->workspaces[ws].windows.items[j].id == h)
                {
                    tracked = true;
                    break;
                }
            }
        }

        if (!tracked)
        {
            /* Apply window rules */
            gf_ws_id_t target = 0;
            if (cls[0] != '\0')
            {
                bool matched = gf_rules_match(wm->config, cls, &target);
                if (!matched)
                    target = wm->active_workspace;
            }

            gf_wm_add_window(wm, h, target);
        }
    }

    if (handles) gf_free(handles);
}

/* Stub: resize processing handled inline in pump_events */
void
gf_wm_process_resize(gf_wm_t *wm, const gf_resize_event_t *ev)
{
    if (!wm || !ev) return;
    gf_resize_update(wm, ev);
}
