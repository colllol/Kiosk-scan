/*
   ____  _       _ _                ____  _           _
  / ___|| |_ _ __(_) |_ _ __ _   _  |  _ \(_)___ _ __ | |_ ___
  \___ \| __| '__| | __| '__| | | | | | | | / __| '_ \| __/ __|
   ___) | |_| |  | | |_| |  | |_| | | |_| \__ \ |_) | |_\__ \
  |____/ \__|_|  |_|\__|_|   \__, | |____/|___/ .__/ \__|___/
                              |___/          |_|

  Platform abstraction — public interface and Windows implementation.
*/

#ifndef GRIDFLUX_PLATFORM_H
#define GRIDFLUX_PLATFORM_H

#include <stdbool.h>
#include "core/types.h"

/* ── Public platform interface ──────────────────────────────── */

struct gf_platform_t {
    void               *platform_data;

    /* Init / cleanup */
    gf_err_t (*init)            (struct gf_platform_t *self, gf_display_t *out_display);
    void     (*cleanup)         (gf_display_t display, struct gf_platform_t *self);
    void     (*platform_destroy)(struct gf_platform_t *self);

    /* Display */
    gf_err_t (*screen_get_bounds)(gf_display_t display, gf_rect_t *out_bounds);

    /* Windows */
    gf_err_t (*window_set_geometry)(gf_display_t display, gf_handle_t window,
                                     const gf_rect_t *geom, uint32_t flags,
                                     const gf_config_t *cfg);
    gf_err_t (*window_get_geometry)(gf_display_t display, gf_handle_t window,
                                     gf_rect_t *out_geom);
    void     (*window_show)(gf_display_t display, gf_handle_t window);
    void     (*window_hide)(gf_display_t display, gf_handle_t window);
    void     (*window_bring_to_top)(gf_display_t display, gf_handle_t window);
    bool     (*window_is_valid)(gf_display_t display, gf_handle_t window);
    bool     (*window_is_maximized)(gf_display_t display, gf_handle_t window);
    bool     (*window_is_minimized)(gf_display_t display, gf_handle_t window);
    void     (*window_get_class)(gf_display_t display, gf_handle_t window,
                                 char *buf, size_t bufsize);
    void     (*window_get_title)(gf_display_t display, gf_handle_t window,
                                 char *buf, size_t bufsize);
    void     (*window_set_title)(gf_display_t display, gf_handle_t window,
                                 const char *title);
    void     (*window_redraw)(gf_display_t display, gf_handle_t window);

    /* Window enumeration — fills an allocated array of handles */
    gf_err_t (*enum_windows)(gf_display_t display,
                             gf_handle_t **out_handles, uint32_t *out_count);

    /* Event polling — returns true if an event was retrieved.
     * Used by gf_wm_pump_events() in the WM core. */
    bool     (*poll_event)(gf_display_t display, gf_event_t *out_event);

    /* Mouse / cursor */
    gf_err_t (*get_cursor_pos)(gf_display_t display, gf_point_t *out_pos);
    void     (*set_cursor_pos)(gf_display_t display, int x, int y);
    void     (*capture_mouse)(gf_display_t display, gf_handle_t window);
    void     (*release_mouse)(gf_display_t display);

    /* Keyboard / keymap */
    gf_err_t (*keymap_init)(struct gf_platform_t *self, gf_display_t display);
    void     (*keymap_cleanup)(struct gf_platform_t *self);
    gf_err_t (*keymap_register)(struct gf_platform_t *self,
                                uint32_t key, uint32_t modifiers,
                                gf_key_callback callback, void *user_data);

    /* Borders */
    void     (*border_init)(struct gf_platform_t *self);
    void     (*border_update)(struct gf_platform_t *self,
                              const gf_config_t *cfg);
    void     (*border_cleanup)(struct gf_platform_t *self);

    /* Dock / taskbar */
    void     (*dock_hide)(struct gf_platform_t *self);
    void     (*dock_restore)(struct gf_platform_t *self);

    /* Workspace / virtual desktop */
    gf_err_t (*workspace_switch)(struct gf_platform_t *self,
                                 gf_display_t display, uint32_t index);
    gf_err_t (*workspace_count)(struct gf_platform_t *self,
                                gf_display_t display, uint32_t *out_count);

    /* Messaging */
    void     (*send_message)(gf_display_t display, gf_handle_t window,
                             uint32_t msg, uintptr_t wParam, uintptr_t lParam);

    /* IPC — named pipe integration */
    gf_err_t (*ipc_init)(struct gf_platform_t *self, const char *pipe_name,
                         gf_ipc_handle_t *out_handle);
    gf_err_t (*ipc_read)(gf_ipc_handle_t handle, void *buf, size_t bufsize,
                         size_t *out_read);
    gf_err_t (*ipc_write)(gf_ipc_handle_t handle, const void *buf, size_t len,
                          size_t *out_written);
    void     (*ipc_close)(gf_ipc_handle_t handle);

    /* Internal state (Win32: pointer to gf_win32_state_t) */
    void *internal;
};

extern struct gf_platform_t gf_platform_win32;

#endif /* GRIDFLUX_PLATFORM_H */
