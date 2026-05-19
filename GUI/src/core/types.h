/*
   ____  _ _            ____  _ _            ____
  / ___|| | | __ _  ___| __ )(_) |_ ___     / ___|  ___ _ ____   _____ _ __
  \___ \| | |/ _` |/ __|  _ \| | __/ _ \   | |  _  / _ \ '__\ \ / / _ \ '__|
   ___) | | | (_| | (__| |_) | | ||  __/   | |_| |  __/ |   \ V /  __/ |
  |____/|_|_|\__,_|\___|____/|_|\__\___|    \____|\___|_|    \_/ \___|_|

  GridFlux — tiling window manager for Windows
  Core type definitions. No external dependencies.
*/

#ifndef GRIDFLUX_TYPES_H
#define GRIDFLUX_TYPES_H

#include <stdbool.h>
#include <stdint.h>
#include <time.h>

/* ══════════════════════════════════════════════════════════════
   Basic Types
   ══════════════════════════════════════════════════════════════ */

typedef int32_t  gf_dimension_t;
typedef uint32_t gf_ws_id_t;
typedef void*    gf_handle_t;
typedef int      gf_err_t;

#define GF_MAX_MONITORS              16
#define GF_MAX_WINDOWS_PER_WORKSPACE 64
#define GF_MAX_WORKSPACES            10
#define GF_MAX_RULES                 128
#define GF_MAX_GRID_TRACKS           16
#define GF_MAX_GRID_CELLS            (GF_MAX_GRID_TRACKS * GF_MAX_GRID_TRACKS)
#define GF_MAX_TASK_COMMAND          512
#define GF_FIRST_WORKSPACE_ID        0
#define GF_DEFAULT_PADDING           8
#define GF_DEFAULT_ROWS              2
#define GF_DEFAULT_COLS              2
#define GF_DEFAULT_GAP               8

#define GF_IPC_SUCCESS               0
#define GF_IPC_ERROR_GENERIC         1
#define GF_IPC_ERROR_CONNECTION      2
#define GF_IPC_ERROR_INVALID_COMMAND 3
#define GF_IPC_ERROR_TIMEOUT         4

/* ══════════════════════════════════════════════════════════════
   Rectangle / Point / Size
   ══════════════════════════════════════════════════════════════ */

typedef struct gf_layout_grid_t {
    gf_dimension_t x;
    gf_dimension_t y;
    gf_dimension_t w;
    gf_dimension_t h;
} gf_rect_t;

typedef struct { gf_dimension_t x; gf_dimension_t y; } gf_point_t;
typedef struct { gf_dimension_t w; gf_dimension_t h; } gf_size_t;

/* ══════════════════════════════════════════════════════════════
   Monitor
   ══════════════════════════════════════════════════════════════ */

typedef struct {
    uint32_t     id;
    gf_rect_t    bounds;       /* work area (excluding taskbar) */
    gf_rect_t    full_bounds;  /* full physical bounds */
    bool         is_primary;
} gf_monitor_t;

/* ══════════════════════════════════════════════════════════════
   Window Info
   ══════════════════════════════════════════════════════════════ */

typedef struct {
    gf_handle_t  id;
    gf_ws_id_t   workspace_id;
    gf_rect_t    geometry;
    char         name[256];
    bool         is_maximized;
    bool         is_valid;
    time_t       last_modified;
    uint32_t     monitor_id;
} gf_win_info_t;

/* ══════════════════════════════════════════════════════════════
   Color
   ══════════════════════════════════════════════════════════════ */

typedef uint32_t gf_color_t;  /* 0xAARRGGBB */

/* ══════════════════════════════════════════════════════════════
   Layout Cell
   ══════════════════════════════════════════════════════════════ */

typedef struct gf_cell_t {
    gf_rect_t         rect;
    gf_handle_t       window;     /* 0 = empty */
    bool               occupied;
    struct gf_cell_t  *next;
} gf_cell_t;

/* ══════════════════════════════════════════════════════════════
   Layout Grid
   ══════════════════════════════════════════════════════════════ */

typedef struct {
    uint32_t     rows;
    uint32_t     cols;
    gf_cell_t   *cells;         /* rows × cols, row-major order */
    gf_rect_t    bounds;
    uint32_t     gap;
    uint32_t     row_weights[GF_MAX_GRID_TRACKS];
    uint32_t     col_weights[GF_MAX_GRID_TRACKS];
} gf_layout_grid_t;

/* ══════════════════════════════════════════════════════════════
   Workspace Info
   ══════════════════════════════════════════════════════════════ */

typedef struct {
    gf_ws_id_t   id;
    char         name[64];
    uint32_t     window_count;
    uint32_t     capacity;
    bool         has_maximized_state;
    int32_t      available_space;
} gf_ws_info_t;

/* ══════════════════════════════════════════════════════════════
   Resize
   ══════════════════════════════════════════════════════════════ */

typedef enum {
    GF_RESIZE_NONE    = 0,
    GF_RESIZE_LEFT    = 1 << 0,
    GF_RESIZE_RIGHT   = 1 << 1,
    GF_RESIZE_TOP     = 1 << 2,
    GF_RESIZE_BOTTOM  = 1 << 3,
} gf_resize_dir_t;

typedef enum {
    GF_RESIZE_IDLE,
    GF_RESIZE_ACTIVE,
    GF_RESIZE_COMPLETE,
} gf_resize_phase_t;

typedef struct {
    gf_handle_t        window;
    gf_resize_phase_t  phase;
    gf_resize_dir_t    direction;
    gf_rect_t          initial_rect;
    gf_rect_t          current_rect;
    int32_t            dx, dy, dw, dh;
} gf_resize_event_t;

/* ══════════════════════════════════════════════════════════════
   Geometry Flags
   ══════════════════════════════════════════════════════════════ */

typedef enum {
    GF_GEOMETRY_APPLY_PADDING   = 1 << 0,
    GF_GEOMETRY_IGNORE_MINMAX   = 1 << 1,
    GF_GEOMETRY_BORDER_UPDATE   = 1 << 2,
    GF_GEOMETRY_RESIZE_IMMEDIATE = 1 << 3,
    GF_GEOMETRY_LOCK_CAPTION_BUTTONS = 1 << 4,
} gf_geom_flags_t;

/* ══════════════════════════════════════════════════════════════
   Key Callback
   ══════════════════════════════════════════════════════════════ */

typedef void (*gf_key_callback)(void *user_data, uint32_t key,
                                 uint32_t modifiers, bool pressed);

/* ══════════════════════════════════════════════════════════════
   Events
   ══════════════════════════════════════════════════════════════ */

typedef enum {
    GF_EVENT_QUIT,
    GF_EVENT_WINDOW_CLOSE,
    GF_EVENT_WINDOW_FOCUS,
    GF_EVENT_WINDOW_NEW,
    GF_EVENT_RESIZE_BEGIN,
    GF_EVENT_RESIZE_UPDATE,
    GF_EVENT_RESIZE_END,
    GF_EVENT_KEY,
    GF_EVENT_DISPLAY_CHANGE,
} gf_event_type_t;

/* Modifier keys */
typedef enum {
    GF_MODIFIER_NONE    = 0,
    GF_MODIFIER_SHIFT   = 1 << 0,
    GF_MODIFIER_CONTROL = 1 << 1,
    GF_MODIFIER_ALT     = 1 << 2,
    GF_MODIFIER_SUPER   = 1 << 3,
} gf_modifier_t;

/* Virtual key symbols used by GridFlux */
#define GF_KEY_TAB 0x09
#define GF_KEY_F1  0x70
#define GF_KEY_F2  0x71

typedef struct {
    gf_handle_t handle;
} gf_event_window_t;

typedef struct {
    gf_handle_t         window;
    gf_resize_phase_t   phase;
    gf_resize_dir_t     direction;
    gf_rect_t           rect;
} gf_event_resize_t;

typedef struct {
    uint32_t    sym;
    uint32_t    modifiers;
    bool        pressed;
} gf_event_key_t;

typedef union {
    gf_event_window_t   window_close;
    gf_event_window_t   window_focus;
    gf_event_window_t   window_new;
    gf_resize_event_t   resize_begin;
    gf_resize_event_t   resize_update;
    gf_resize_event_t   resize_end;
    gf_event_key_t      key;
} gf_event_data_t;

typedef struct {
    gf_event_type_t  type;
    gf_event_data_t  data;
} gf_event_t;

/* ══════════════════════════════════════════════════════════════
   Border
   ══════════════════════════════════════════════════════════════ */

typedef struct gf_border_t {
    gf_handle_t         target;
    void*               overlay;      /* platform-specific */
    gf_color_t          color;
    int                 thickness;
    struct gf_border_t *next;
    /* platform scratch */
    void*               plat_rects;
    int                 plat_rect_count;
} gf_border_t;

/* ══════════════════════════════════════════════════════════════
   Window Rules
   ══════════════════════════════════════════════════════════════ */

typedef struct {
    char    wm_class[128];
    int     workspace_id;
} gf_window_rule_t;

/* ══════════════════════════════════════════════════════════════
   Config
   ══════════════════════════════════════════════════════════════ */

typedef struct gf_config_t {
    uint32_t     rows;
    uint32_t     cols;
    uint32_t     gap;
    uint32_t     border_width;
    uint32_t     row_weights[GF_MAX_GRID_TRACKS];
    uint32_t     col_weights[GF_MAX_GRID_TRACKS];

    bool         enable_borders;
    bool         auto_tile;
    bool         follow_focus;
    bool         lock_grids;
    bool         auto_launch_tasks;

    uint32_t     window_rules_count;
    gf_window_rule_t window_rules[GF_MAX_RULES];

    uint32_t     workspace_count;
    char         workspace_names[GF_MAX_WORKSPACES][64];

    char         startup_tasks[GF_MAX_GRID_CELLS][GF_MAX_TASK_COMMAND];
    bool         startup_task_f11[GF_MAX_GRID_CELLS];
    bool         startup_task_lock_buttons[GF_MAX_GRID_CELLS];
} gf_config_t;

/* ══════════════════════════════════════════════════════════════
   Key Actions
   ══════════════════════════════════════════════════════════════ */

typedef enum {
    GF_KEY_NONE            = 0,
    GF_KEY_WORKSPACE_PREV  = 1,
    GF_KEY_WORKSPACE_NEXT  = 2,
    GF_KEY_TOGGLE_MAXIMIZE = 3,
    GF_KEY_CLOSE_WINDOW    = 4,
} gf_key_action_t;

/* ══════════════════════════════════════════════════════════════
   Platform Interface (opaque forward declarations)
   ══════════════════════════════════════════════════════════════ */

typedef struct gf_platform_t   gf_platform_t;   /* defined in platform.h */

/* Display handle — wraps an HMONITOR or platform-specific display ref */
typedef struct {
    uintptr_t id;    /* HMONITOR cast to uintptr_t on Win32 */
} gf_display_t;

/* ══════════════════════════════════════════════════════════════
   IPC Types (moved up to avoid circular dependency)
   ══════════════════════════════════════════════════════════════ */

#define GF_IPC_MSG_SIZE 8192

/* ══════════════════════════════════════════════════════════════
   Limits
   ══════════════════════════════════════════════════════════════ */

/* Opaque handle — full struct defined here so it can be used by
   function pointer typedefs below and stored in gf_wm_t. */
typedef struct gf_ipc_handle_t {
    uintptr_t _priv;  /* opaque pointer to gf_ipc_handle_int_t */
} gf_ipc_handle_t;

typedef struct {
    int status;
    char message[GF_IPC_MSG_SIZE];
} gf_ipc_response_t;

/* Function pointer types for the platform vtable */
typedef gf_err_t   (*fn_init_t)(gf_platform_t*, gf_display_t*);
typedef void       (*fn_cleanup_t)(gf_display_t, gf_platform_t*);

typedef gf_err_t   (*fn_enum_windows_t)(gf_display_t, gf_handle_t**, uint32_t*);
typedef gf_handle_t (*fn_get_focused_t)(gf_display_t);
typedef gf_err_t   (*fn_get_geom_t)(gf_display_t, gf_handle_t, gf_rect_t*);
typedef gf_err_t   (*fn_set_geom_t)(gf_display_t, gf_handle_t, const gf_rect_t*,
                                     gf_geom_flags_t, const gf_config_t*);
typedef gf_err_t   (*fn_unmaximize_t)(gf_display_t, gf_handle_t);
typedef bool       (*fn_is_valid_t)(gf_display_t, gf_handle_t);
typedef bool       (*fn_is_excl_t)(gf_display_t, gf_handle_t);
typedef bool       (*fn_is_fs_t)(gf_display_t, gf_handle_t);
typedef bool       (*fn_is_max_t)(gf_display_t, gf_handle_t);
typedef bool       (*fn_is_min_t)(gf_display_t, gf_handle_t);
typedef bool       (*fn_is_hidden_t)(gf_display_t, gf_handle_t);
typedef gf_err_t   (*fn_minimize_t)(gf_display_t, gf_handle_t);
typedef gf_err_t   (*fn_unminimize_t)(gf_display_t, gf_handle_t);
typedef gf_err_t   (*fn_ws_count_t)(gf_display_t);
typedef gf_err_t   (*fn_screen_bounds_t)(gf_display_t, gf_rect_t*);
typedef void       (*fn_border_add_t)(gf_platform_t*, gf_handle_t,
                                       gf_color_t, int);
typedef void       (*fn_border_update_t)(gf_platform_t*, const gf_config_t*);
typedef void       (*fn_border_cleanup_t)(gf_platform_t*);
typedef void       (*fn_border_remove_t)(gf_platform_t*, gf_handle_t);
typedef void       (*fn_dock_hide_t)(gf_platform_t*);
typedef void       (*fn_dock_restore_t)(gf_platform_t*);
typedef gf_err_t   (*fn_keymap_init_t)(gf_platform_t*, gf_display_t);
typedef void       (*fn_keymap_cleanup_t)(gf_platform_t*);
typedef gf_key_action_t (*fn_keymap_poll_t)(gf_platform_t*, gf_display_t);
typedef gf_err_t   (*fn_resize_install_t)(gf_platform_t*);
typedef void       (*fn_resize_uninstall_t)(gf_platform_t*);
typedef bool       (*fn_resize_poll_t)(gf_platform_t*, gf_resize_event_t*);
typedef gf_err_t   (*fn_ipc_init_t)(gf_platform_t*, const char*, gf_ipc_handle_t*);

/* Provide 'gf_layout_t' as alias for layout engine */
typedef gf_layout_grid_t gf_layout_t;

struct gf_platform_t;

/* ══════════════════════════════════════════════════════════════
   Window / Workspace Lists
   ══════════════════════════════════════════════════════════════ */

typedef struct {
    gf_win_info_t *items;
    uint32_t       count;
    uint32_t       capacity;
} gf_win_list_t;

typedef struct {
    gf_ws_info_t *items;
    uint32_t      count;
    uint32_t      capacity;
    gf_ws_id_t    active_workspace;
} gf_ws_list_t;

/* ══════════════════════════════════════════════════════════════
   Grid Dimensions
   ══════════════════════════════════════════════════════════════ */

typedef struct {
    uint32_t rows;
    uint32_t cols;
} gf_grid_dims_t;

/* ══════════════════════════════════════════════════════════════
   Error Codes
   ══════════════════════════════════════════════════════════════ */

#define GF_SUCCESS                     0
#define GF_ERROR_GENERIC              -1
#define GF_ERROR_INVALID_PARAMETER    -2
#define GF_ERROR_MEMORY_ALLOCATION    -3
#define GF_ERROR_PLATFORM_ERROR       -4
#define GF_ERROR_DISPLAY_CONNECTION   -5
#define GF_ERROR_WORKSPACE_LOCKED     -6
#define GF_ERROR_WORKSPACE_FULL       -7
#define GF_ERROR_WORKSPACE_MAXIMIZED  -8
#define GF_ERROR_ALREADY_LOCKED       -9
#define GF_ERROR_ALREADY_UNLOCKED    -10
#define GF_ERROR_TIMEOUT             -11
#define GF_ERROR_CONNECTION          -12

#define GRIDFLUX_VERSION "0.1.0"

#endif /* GRIDFLUX_TYPES_H */
