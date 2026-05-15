#ifndef GRIDFLUX_WM_INTERNAL_H
#define GRIDFLUX_WM_INTERNAL_H

#include "../config/config.h"
#include "../core/types.h"
#include "../utils/list.h"

/*
 * Internal WM state — not exposed outside the core.
 */

/* Per-workspace state */
typedef struct {
    gf_ws_id_t   id;
    gf_layout_grid_t layout;
    gf_win_list_t    windows;    /* windows assigned to this workspace */
    bool             locked;
    bool             maximized_only;
} gf_workspace_state_t;

/* Global WM state */
struct gf_wm_t {
    gf_platform_t    *platform;
    gf_display_t      display;
    gf_config_t      *config;

    /* Workspace array */
    gf_workspace_state_t workspaces[GF_MAX_WORKSPACES];
    uint32_t             workspace_count;
    gf_ws_id_t           active_workspace;

    /* Global window list (all workspaces) */
    gf_win_list_t all_windows;

    /* Focused window */
    gf_handle_t focused_window;

    /* Border state */
    bool borders_enabled;

    /* Resize tracking */
    gf_resize_event_t last_resize;
    bool resize_active;

    /* IPC */
    gf_ipc_handle_t ipc_handle;
    bool ipc_running;
};

/* Internal helpers */
gf_workspace_state_t *gf_wm_get_workspace_state(gf_wm_t *wm, gf_ws_id_t ws_id);
gf_err_t              gf_wm_tile_workspace(gf_wm_t *wm, gf_ws_id_t ws_id);
void                  gf_wm_apply_layout_cell(gf_wm_t *wm, gf_workspace_state_t *ws,
                                               uint32_t row, uint32_t col);
gf_err_t              gf_wm_ensure_workspace_state(gf_wm_t *wm, gf_ws_id_t ws_id);

#endif /* GRIDFLUX_WM_INTERNAL_H */