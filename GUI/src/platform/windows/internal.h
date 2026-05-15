#ifndef GRIDFLUX_WINDOWS_INTERNAL_H
#define GRIDFLUX_WINDOWS_INTERNAL_H

#include "../../platform/platform.h"
#include "../../core/types.h"
#include <windows.h>

/* Per-monitor border window */
typedef struct {
    HWND    hwnd;
    gf_rect_t last_rect;
    bool    visible;
} gf_win_border_t;

/* Per-workspace border set */
typedef struct {
    gf_win_border_t borders[4];  /* top, bottom, left, right */
} gf_workspace_borders_t;

typedef struct {
    HWND target;
    gf_win_border_t borders[4];  /* top, bottom, left, right */
    bool in_use;
} gf_task_borders_t;

/* Internal Win32 platform state */
typedef struct {
    HINSTANCE h_instance;

    /* Window class for border/deco windows */
    ATOM border_class_atom;
    ATOM msg_window_class_atom;

    /* Active display */
    HMONITOR active_monitor;
    MONITORINFO active_monitor_info;

    /* Border windows per workspace */
    gf_workspace_borders_t ws_borders[GF_MAX_WORKSPACES];
    gf_task_borders_t task_borders[GF_MAX_WORKSPACES * GF_MAX_WINDOWS_PER_WORKSPACE];

    /* Keymap hooks */
    HHOOK keyboard_hook;
    HHOOK mouse_hook;

    /* Resize drag tracking */
    HWND  resize_hwnd;
    POINT resize_start_pos;
    bool  resize_active;
    DWORD resize_edge;  /* which edge/corner is being dragged */

    /* Dock hiding */
    bool  dock_hidden;
    RECT  dock_auto_hide_rect;  /* APPBAR data */
    HWND  taskbar_hwnd;

    /* IPC named pipe */
    HANDLE ipc_pipe;
    char   pipe_name[128];
    bool   ipc_server;

    /* Enumerated windows cache */
    HWND  *enum_cache;
    uint32_t enum_cache_count;
    uint32_t enum_cache_capacity;

    /* Message-only window for IPC and hotkeys */
    HWND msg_hwnd;
} gf_win32_state_t;

#endif /* GRIDFLUX_WINDOWS_INTERNAL_H */
