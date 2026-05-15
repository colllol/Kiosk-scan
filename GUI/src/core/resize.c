#include "resize.h"
#include "layout.h"
#include "wm_internal.h"
#include "../platform/platform.h"
#include "../utils/logger.h"
#include "../utils/math_utils.h"
#include <math.h>

/* ── Resize state (tracked between begin and end) ──────────── */

typedef struct {
    gf_handle_t       window;
    gf_rect_t         original_geo;
    gf_point_t        drag_start;
    gf_cell_t         original_cell;
    bool              active;
} gf_resize_state_t;

static gf_resize_state_t resize_state = {0};

/* ── Public API ─────────────────────────────────────────────── */

gf_err_t
gf_resize_begin(gf_wm_t *wm, gf_handle_t window)
{
    if (!wm || !window)
        return GF_ERROR_INVALID_PARAMETER;

    resize_state.window = window;
    resize_state.active = true;
    resize_state.original_cell = (gf_cell_t){0};
    resize_state.original_geo = (gf_rect_t){0, 0, 0, 0};
    resize_state.drag_start = (gf_point_t){0, 0};

    /* Capture original geometry */
    if (wm->platform->window_get_geometry)
        wm->platform->window_get_geometry(wm->display, window,
                                          &resize_state.original_geo);

    /* Capture original cursor position */
    if (wm->platform->get_cursor_pos)
        wm->platform->get_cursor_pos(wm->display, &resize_state.drag_start);

    /* Find the cell this window occupies */
    for (uint32_t ws = 0; ws < wm->workspace_count; ws++)
    {
        gf_layout_t *layout = &wm->workspaces[ws].layout;
        for (uint32_t i = 0; i < layout->rows * layout->cols; i++)
        {
            if (layout->cells[i].occupied && layout->cells[i].window == window)
            {
                resize_state.original_cell = layout->cells[i];
                break;
            }
        }
    }

    wm->resize_active = true;
    GF_LOG_DEBUG("Resize began for window %p", window);
    return GF_SUCCESS;
}

gf_err_t
gf_resize_update(gf_wm_t *wm, const gf_resize_event_t *ev)
{
    if (!wm || !ev || !resize_state.active)
        return GF_ERROR_INVALID_PARAMETER;

    /* Calculate delta from drag start */
    int dx = ev->current_rect.x - resize_state.drag_start.x;
    int dy = ev->current_rect.y - resize_state.drag_start.y;

    /* Compute new geometry from original + delta */
    gf_rect_t new_geo = resize_state.original_geo;
    new_geo.w += dx;
    new_geo.h += dy;

    /* Apply minimum size constraints */
    if (new_geo.w < 100) new_geo.w = 100;
    if (new_geo.h < 60)  new_geo.h = 60;

    /* Clamp to screen bounds */
    gf_rect_t screen_bounds;
    if (wm->platform->screen_get_bounds(wm->display, &screen_bounds) == GF_SUCCESS)
    {
        if (new_geo.x + new_geo.w > screen_bounds.x + screen_bounds.w)
            new_geo.w = (screen_bounds.x + screen_bounds.w) - new_geo.x;
        if (new_geo.y + new_geo.h > screen_bounds.y + screen_bounds.h)
            new_geo.h = (screen_bounds.y + screen_bounds.h) - new_geo.y;
    }

    wm->platform->window_set_geometry(wm->display, resize_state.window,
                                       &new_geo, GF_GEOMETRY_RESIZE_IMMEDIATE,
                                       wm->config);

    return GF_SUCCESS;
}

gf_err_t
gf_resize_end(gf_wm_t *wm, const gf_resize_event_t *ev)
{
    if (!wm || !resize_state.active)
        return GF_ERROR_INVALID_PARAMETER;

    /* Snap the final size back to the nearest grid cell */
    gf_rect_t final_geo;
    wm->platform->window_get_geometry(wm->display, resize_state.window,
                                      &final_geo);

    /* Find the cell this window should snap to based on its center */
    gf_point_t center = {
        final_geo.x + final_geo.w / 2,
        final_geo.y + final_geo.h / 2
    };

    for (uint32_t ws = 0; ws < wm->workspace_count; ws++)
    {
        gf_layout_t *layout = &wm->workspaces[ws].layout;
        for (uint32_t r = 0; r < layout->rows; r++)
        {
            for (uint32_t c = 0; c < layout->cols; c++)
            {
                gf_cell_t *cell = &layout->cells[r * layout->cols + c];
                if (gf_point_in_rect(&center, &cell->rect))
                {
                    /* Re-assign window to this cell */
                    gf_layout_clear(layout);
                    gf_layout_assign(layout, r, c, resize_state.window);
                    wm->platform->window_set_geometry(
                        wm->display, resize_state.window,
                        &cell->rect, GF_GEOMETRY_APPLY_PADDING,
                        wm->config);
                    break;
                }
            }
        }
    }

    /* Reset resize state */
    resize_state.active = false;
    resize_state.window = 0;
    wm->resize_active = false;

    /* Re-tile active workspace to fix any layout inconsistencies */
    gf_wm_tile_workspace(wm, wm->active_workspace);

    GF_LOG_DEBUG("Resize ended, snapped to grid");
    return GF_SUCCESS;
}
