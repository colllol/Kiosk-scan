/*
   ____  _ _            ____
  / ___|| | | __ _  ___| __ ) _ __  _ __ ___
  \___ \| | |/ _` |/ __|  _ \| '_ \| '__/ __|
   ___) | | | (_| | (__| |_) | |_) | |  \__ \
  |____/|_|_|\__,_|\___|____/| .__/|_|  |___/
                              |_|

  Core window manager — tiling logic, workspace management,
  event loop, resize handling, and debugging.
*/

#ifndef GRIDFLUX_WM_H
#define GRIDFLUX_WM_H

#include "types.h"

/* Opaque WM handle */
typedef struct gf_wm_t gf_wm_t;

/* ── Lifecycle ──────────────────────────────────────────────── */
gf_err_t  gf_wm_create   (gf_wm_t **out_wm);
gf_err_t  gf_wm_init     (gf_wm_t *wm, gf_platform_t *platform, gf_config_t *cfg);
void      gf_wm_destroy  (gf_wm_t *wm);

/* ── Main loop ──────────────────────────────────────────────── */
gf_err_t  gf_wm_run      (gf_wm_t *wm);
void      gf_wm_stop     (gf_wm_t *wm);

/* ── Window operations ──────────────────────────────────────── */
gf_err_t  gf_wm_add_window         (gf_wm_t *wm, gf_handle_t window, gf_ws_id_t ws_id);
gf_err_t  gf_wm_remove_window      (gf_wm_t *wm, gf_handle_t window);
gf_err_t  gf_wm_move_window        (gf_wm_t *wm, gf_handle_t window, gf_ws_id_t target_ws);
gf_err_t  gf_wm_tile_all           (gf_wm_t *wm);
gf_err_t  gf_wm_tile_workspace     (gf_wm_t *wm, gf_ws_id_t ws_id);
gf_err_t  gf_wm_refresh_workspace  (gf_wm_t *wm, gf_ws_id_t ws_id);

/* ── Focus ──────────────────────────────────────────────────── */
gf_err_t  gf_wm_focus_window       (gf_wm_t *wm, gf_handle_t window);
gf_handle_t gf_wm_get_focused     (gf_wm_t *wm);
gf_err_t  gf_wm_cycle_focus        (gf_wm_t *wm, int direction);

/* ── Workspace ──────────────────────────────────────────────── */
gf_ws_id_t gf_wm_get_active_workspace(gf_wm_t *wm);
gf_err_t  gf_wm_switch_workspace   (gf_wm_t *wm, gf_ws_id_t ws_id);
gf_err_t  gf_wm_workspace_lock     (gf_wm_t *wm, gf_ws_id_t ws_id);
gf_err_t  gf_wm_workspace_unlock   (gf_wm_t *wm, gf_ws_id_t ws_id);

/* ── Window info helpers ────────────────────────────────────── */
gf_err_t  gf_wm_window_class       (gf_wm_t *wm, gf_handle_t window,
                                     char *buf, size_t bufsize);
gf_win_list_t *gf_wm_windows       (gf_wm_t *wm);
gf_ws_list_t  *gf_wm_workspaces    (gf_wm_t *wm);
gf_platform_t *gf_wm_platform      (gf_wm_t *wm);
gf_display_t *gf_wm_display        (gf_wm_t *wm);

/* ── Border management ──────────────────────────────────────── */
gf_err_t  gf_wm_toggle_borders     (gf_wm_t *wm);
gf_err_t  gf_wm_update_borders     (gf_wm_t *wm);

#endif /* GRIDFLUX_WM_H */