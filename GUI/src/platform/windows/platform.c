/*
   ____  _                            ____  _           _
  / ___|| |_ _ __ _   _  ___ _ __    |  _ \(_)_ __   __| | ___ _ __
  \___ \| __| '__| | | |/ _ \ '_ \   | | | | | '_ \ / _` |/ _ \ '__|
   ___) | |_| |  | |_| |  __/ | | |  | |_| | | | | | (_| |  __/ |
  |____/ \__|_|   \__, |\___|_| |_|  |____/|_|_| |_|\__,_|\___|_|
                   |___/

  Windows (Win32) platform implementation — every function pointer
  declared in gf_platform_t lives here.
*/

#include "../platform.h"
#include "internal.h"
#include "../../core/types.h"
#include "../../utils/logger.h"
#include "../../utils/memory.h"
#include "../../ipc/ipc.h"
#include <windows.h>
#include <shlobj.h>
#include <dwmapi.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

/* ── Globals ────────────────────────────────────────────────── */
static gf_win32_state_t g_win32 = {0};

/* ── Forward declarations ───────────────────────────────────── */
static LRESULT CALLBACK border_wnd_proc(HWND hwnd, UINT msg,
                                         WPARAM wParam, LPARAM lParam);
static LRESULT CALLBACK msg_wnd_proc(HWND hwnd, UINT msg,
                                      WPARAM wParam, LPARAM lParam);
static void register_border_class(void);
static void register_msg_class(void);
static void win32_border_update(struct gf_platform_t *self, const gf_config_t *cfg);
static void win32_task_border_update(HWND target, const gf_config_t *cfg);
extern struct gf_platform_t gf_platform_win32;

/* ── Helpers ────────────────────────────────────────────────── */

static inline HWND
gf_handle_to_hwnd(gf_handle_t handle)
{
    return (HWND)(uintptr_t)handle;
}

static inline gf_handle_t
gf_hwnd_to_handle(HWND hwnd)
{
    return (gf_handle_t)(uintptr_t)hwnd;
}

static bool
win32_get_visible_frame(HWND hwnd, RECT *out)
{
    if (!hwnd || !out)
        return false;

    HRESULT hr = DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS,
                                       out, sizeof(*out));
    if (SUCCEEDED(hr))
        return true;

    return GetWindowRect(hwnd, out) != 0;
}

/* Refresh the active monitor cache */
static void
gf_win32_update_monitor_info(void)
{
    POINT cursor = {0};
    GetCursorPos(&cursor);
    g_win32.active_monitor = MonitorFromPoint(cursor, MONITOR_DEFAULTTONEAREST);
    g_win32.active_monitor_info.cbSize = sizeof(MONITORINFO);
    GetMonitorInfo(g_win32.active_monitor, &g_win32.active_monitor_info);
}

/* ── Platform init / cleanup ────────────────────────────────── */

static gf_err_t
win32_init(struct gf_platform_t *self, gf_display_t *out_display)
{
    g_win32.h_instance = GetModuleHandle(NULL);
    g_win32.keyboard_hook = NULL;
    g_win32.mouse_hook = NULL;
    g_win32.resize_active = false;
    g_win32.dock_hidden = false;
    g_win32.ipc_pipe = INVALID_HANDLE_VALUE;
    g_win32.ipc_server = false;
    g_win32.enum_cache = NULL;
    g_win32.enum_cache_count = 0;
    g_win32.enum_cache_capacity = 0;
    g_win32.msg_hwnd = NULL;

    memset(g_win32.ws_borders, 0, sizeof(g_win32.ws_borders));

    register_border_class();
    register_msg_class();

    /* Create message-only window for IPC hotkey dispatch */
    g_win32.msg_hwnd = CreateWindowEx(0,
        (LPCSTR)g_win32.msg_window_class_atom, "GridFluxMsg",
        0, 0, 0, 0, 0,
        HWND_MESSAGE, NULL, g_win32.h_instance, NULL);

    gf_win32_update_monitor_info();

    *out_display = (gf_display_t){(uintptr_t)g_win32.active_monitor};

    /* Hide the dock by default */
    self->dock_hide(self);

    GF_LOG_INFO("Win32 platform initialized (monitor=%p)",
                g_win32.active_monitor);
    return GF_SUCCESS;
}

static void
win32_cleanup(gf_display_t display, struct gf_platform_t *self)
{
    /* Restore dock */
    self->dock_restore(self);

    /* Clean up keyboard hook */
    if (g_win32.keyboard_hook)
    {
        UnhookWindowsHookEx(g_win32.keyboard_hook);
        g_win32.keyboard_hook = NULL;
    }

    /* Clean up mouse hook */
    if (g_win32.mouse_hook)
    {
        UnhookWindowsHookEx(g_win32.mouse_hook);
        g_win32.mouse_hook = NULL;
    }

    /* Destroy border windows */
    self->border_cleanup(self);

    /* Free enum cache */
    if (g_win32.enum_cache)
    {
        gf_free(g_win32.enum_cache);
        g_win32.enum_cache = NULL;
    }

    /* Destroy message window */
    if (g_win32.msg_hwnd)
    {
        DestroyWindow(g_win32.msg_hwnd);
        g_win32.msg_hwnd = NULL;
    }

    /* Close IPC pipe if open — close the raw handle directly */
    if (g_win32.ipc_pipe != INVALID_HANDLE_VALUE)
    {
        if (g_win32.ipc_server)
            DisconnectNamedPipe(g_win32.ipc_pipe);
        CloseHandle(g_win32.ipc_pipe);
        g_win32.ipc_pipe = INVALID_HANDLE_VALUE;
    }

    GF_LOG_INFO("Win32 platform cleaned up");
}

static void
win32_platform_destroy(struct gf_platform_t *self)
{
    /* Final unregister window classes */
    UnregisterClassA((LPCSTR)g_win32.border_class_atom, g_win32.h_instance);
    UnregisterClassA((LPCSTR)g_win32.msg_window_class_atom, g_win32.h_instance);

    /* Destroy IPC pipe name */
    g_win32.pipe_name[0] = '\0';
    memset(&g_win32, 0, sizeof(g_win32));
}

/* ── Display ────────────────────────────────────────────────── */

static gf_err_t
win32_screen_get_bounds(gf_display_t display, gf_rect_t *out_bounds)
{
    HMONITOR mon = (HMONITOR)(uintptr_t)display.id;
    if (!mon)
    {
        gf_win32_update_monitor_info();
        mon = g_win32.active_monitor;
    }

    MONITORINFO mi = {sizeof(MONITORINFO)};
    if (!GetMonitorInfo(mon, &mi))
        return GF_ERROR_PLATFORM_ERROR;

    out_bounds->x = mi.rcMonitor.left;
    out_bounds->y = mi.rcMonitor.top;
    out_bounds->w = mi.rcMonitor.right - mi.rcMonitor.left;
    out_bounds->h = mi.rcMonitor.bottom - mi.rcMonitor.top;

    return GF_SUCCESS;
}

/* ── Window geometry ────────────────────────────────────────── */

static gf_err_t
win32_window_set_geometry(gf_display_t display, gf_handle_t window,
                          const gf_rect_t *geom, uint32_t flags,
                          const gf_config_t *cfg)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    if (!IsWindow(hwnd))
        return GF_ERROR_PLATFORM_ERROR;

    int x = geom->x;
    int y = geom->y;
    int w = geom->w;
    int h = geom->h;

    RECT win_rect;
    RECT frame_rect;
    if (GetWindowRect(hwnd, &win_rect) && win32_get_visible_frame(hwnd, &frame_rect))
    {
        int left_pad = frame_rect.left - win_rect.left;
        int top_pad = frame_rect.top - win_rect.top;
        int right_pad = win_rect.right - frame_rect.right;
        int bottom_pad = win_rect.bottom - frame_rect.bottom;

        x -= left_pad;
        y -= top_pad;
        w += left_pad + right_pad;
        h += top_pad + bottom_pad;
    }

    if (w < 1) w = 1;
    if (h < 1) h = 1;

    UINT swp_flags = SWP_NOACTIVATE;

    /* If immediate resize (during drag), skip animation */
    if (flags & GF_GEOMETRY_RESIZE_IMMEDIATE)
        swp_flags |= SWP_NOCOPYBITS;

    /* Remove maximized state before moving */
    if (IsZoomed(hwnd))
        ShowWindow(hwnd, SW_RESTORE);

    BOOL ok = SetWindowPos(hwnd, HWND_NOTOPMOST, x, y, w, h, swp_flags);
    win32_task_border_update(hwnd, cfg);

    if (flags & GF_GEOMETRY_BORDER_UPDATE)
    {
        /* Redraw border overlays */
        win32_border_update(&gf_platform_win32, cfg);
    }

    return ok ? GF_SUCCESS : GF_ERROR_PLATFORM_ERROR;
}

static gf_err_t
win32_window_get_geometry(gf_display_t display, gf_handle_t window,
                          gf_rect_t *out_geom)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    if (!IsWindow(hwnd))
        return GF_ERROR_PLATFORM_ERROR;

    RECT r;
    if (!GetWindowRect(hwnd, &r))
        return GF_ERROR_PLATFORM_ERROR;

    out_geom->x = r.left;
    out_geom->y = r.top;
    out_geom->w = r.right - r.left;
    out_geom->h = r.bottom - r.top;

    return GF_SUCCESS;
}

/* ── Window visibility ──────────────────────────────────────── */

static void
win32_window_show(gf_display_t display, gf_handle_t window)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    if (IsWindow(hwnd))
        ShowWindow(hwnd, SW_SHOWNOACTIVATE);
}

static void
win32_window_hide(gf_display_t display, gf_handle_t window)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    if (IsWindow(hwnd))
        ShowWindow(hwnd, SW_HIDE);
}

static void
win32_window_bring_to_top(gf_display_t display, gf_handle_t window)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    if (IsWindow(hwnd))
    {
        SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0,
                     SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    }
}

/* ── Window state queries ───────────────────────────────────── */

static bool
win32_window_is_valid(gf_display_t display, gf_handle_t window)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    return hwnd != NULL && IsWindow(hwnd) == TRUE;
}

static bool
win32_window_is_maximized(gf_display_t display, gf_handle_t window)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    return IsWindow(hwnd) && IsZoomed(hwnd);
}

static bool
win32_window_is_minimized(gf_display_t display, gf_handle_t window)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    return IsWindow(hwnd) && IsIconic(hwnd);
}

/* ── Window class / title ───────────────────────────────────── */

static void
win32_window_get_class(gf_display_t display, gf_handle_t window,
                       char *buf, size_t bufsize)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    if (IsWindow(hwnd))
        GetClassNameA(hwnd, buf, (int)bufsize);
    else
        buf[0] = '\0';
}

static void
win32_window_get_title(gf_display_t display, gf_handle_t window,
                       char *buf, size_t bufsize)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    if (IsWindow(hwnd))
        GetWindowTextA(hwnd, buf, (int)bufsize);
    else
        buf[0] = '\0';
}

static void
win32_window_set_title(gf_display_t display, gf_handle_t window,
                       const char *title)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    if (IsWindow(hwnd))
        SetWindowTextA(hwnd, title);
}

static void
win32_window_redraw(gf_display_t display, gf_handle_t window)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    if (IsWindow(hwnd))
        RedrawWindow(hwnd, NULL, NULL,
                     RDW_INVALIDATE | RDW_UPDATENOW | RDW_ERASE);
}

/* ── Window enumeration ─────────────────────────────────────── */

static BOOL CALLBACK
enum_windows_proc(HWND hwnd, LPARAM lParam)
{
    gf_win32_state_t *state = (gf_win32_state_t *)lParam;

    /* Skip invisible, disabled, or cloaked windows */
    if (!IsWindowVisible(hwnd))
        return TRUE;

    LONG style = GetWindowLongA(hwnd, GWL_STYLE);
    if (style & WS_DISABLED)
        return TRUE;

    /* Skip Windows 10/11 UWP cloaked windows */
    BOOL cloaked = FALSE;
    DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, &cloaked, sizeof(cloaked));
    if (cloaked)
        return TRUE;

    /* Skip the message window itself */
    if (hwnd == state->msg_hwnd)
        return TRUE;

    /* Skip child windows */
    if (GetWindow(hwnd, GW_OWNER) != NULL)
        return TRUE;

    /* Ensure capacity */
    if (state->enum_cache_count >= state->enum_cache_capacity)
    {
        uint32_t new_cap = state->enum_cache_capacity == 0
                           ? 64 : state->enum_cache_capacity * 2;
        HWND *new_cache = gf_realloc(state->enum_cache,
                                      new_cap * sizeof(HWND));
        if (!new_cache)
            return FALSE;
        state->enum_cache = new_cache;
        state->enum_cache_capacity = new_cap;
    }

    state->enum_cache[state->enum_cache_count++] = hwnd;
    return TRUE;
}

static gf_err_t
win32_enum_windows(gf_display_t display,
                   gf_handle_t **out_handles, uint32_t *out_count)
{
    g_win32.enum_cache_count = 0;
    EnumWindows(enum_windows_proc, (LPARAM)&g_win32);

    if (g_win32.enum_cache_count == 0)
    {
        *out_handles = NULL;
        *out_count = 0;
        return GF_SUCCESS;
    }

    size_t alloc_size = g_win32.enum_cache_count * sizeof(gf_handle_t);
    *out_handles = gf_malloc(alloc_size);
    if (!*out_handles)
        return GF_ERROR_MEMORY_ALLOCATION;

    for (uint32_t i = 0; i < g_win32.enum_cache_count; i++)
        ((gf_handle_t *)*out_handles)[i] = gf_hwnd_to_handle(g_win32.enum_cache[i]);

    *out_count = g_win32.enum_cache_count;
    return GF_SUCCESS;
}

/* ── Mouse / cursor ─────────────────────────────────────────── */

static gf_err_t
win32_get_cursor_pos(gf_display_t display, gf_point_t *out_pos)
{
    POINT p;
    if (!GetCursorPos(&p))
        return GF_ERROR_PLATFORM_ERROR;

    /* Convert to virtual-desktop coordinates */
    out_pos->x = p.x;
    out_pos->y = p.y;
    return GF_SUCCESS;
}

static void
win32_set_cursor_pos(gf_display_t display, int x, int y)
{
    SetCursorPos(x, y);
}

static void
win32_capture_mouse(gf_display_t display, gf_handle_t window)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    if (IsWindow(hwnd))
        SetCapture(hwnd);
}

static void
win32_release_mouse(gf_display_t display)
{
    ReleaseCapture();
}

/* ── Keyboard hook ──────────────────────────────────────────── */

static LRESULT CALLBACK
win32_keyboard_hook(int nCode, WPARAM wParam, LPARAM lParam)
{
    if (nCode >= 0)
    {
        KBDLLHOOKSTRUCT *kb = (KBDLLHOOKSTRUCT *)lParam;
        /* Forward to the message window for hotkey dispatch */
        PostMessageA(g_win32.msg_hwnd, WM_USER + 1,
                     (WPARAM)kb->vkCode,
                     (LPARAM)(wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN));
    }
    return CallNextHookEx(g_win32.keyboard_hook, nCode, wParam, lParam);
}

static gf_err_t
win32_keymap_init(struct gf_platform_t *self, gf_display_t display)
{
    g_win32.keyboard_hook = SetWindowsHookExA(
        WH_KEYBOARD_LL, win32_keyboard_hook, g_win32.h_instance, 0);

    if (!g_win32.keyboard_hook)
    {
        GF_LOG_ERROR("Failed to install keyboard hook: %lu", GetLastError());
        return GF_ERROR_PLATFORM_ERROR;
    }

    return GF_SUCCESS;
}

static void
win32_keymap_cleanup(struct gf_platform_t *self)
{
    if (g_win32.keyboard_hook)
    {
        UnhookWindowsHookEx(g_win32.keyboard_hook);
        g_win32.keyboard_hook = NULL;
    }
}

/* Keymap registration is handled via hotkey registration on the message window */
static gf_err_t
win32_keymap_register(struct gf_platform_t *self,
                      uint32_t key, uint32_t modifiers,
                      gf_key_callback callback, void *user_data)
{
    /* Convert GF key/modifier to VK code and modifiers */
    UINT vk = 0;
    UINT fsModifiers = 0;

    if (modifiers & GF_MODIFIER_SUPER)
        fsModifiers |= MOD_WIN;
    if (modifiers & GF_MODIFIER_SHIFT)
        fsModifiers |= MOD_SHIFT;
    if (modifiers & GF_MODIFIER_CONTROL)
        fsModifiers |= MOD_CONTROL;
    if (modifiers & GF_MODIFIER_ALT)
        fsModifiers |= MOD_ALT;

    if (key >= 'A' && key <= 'Z')
        vk = (UINT)key;
    else if (key >= '0' && key <= '9')
        vk = (UINT)key;
    else
    {
        switch (key)
        {
        case GF_KEY_TAB:    vk = VK_TAB; break;
        case GF_KEY_F1:     vk = VK_F1; break;
        case GF_KEY_F2:     vk = VK_F2; break;
        default:
            GF_LOG_WARN("Unmapped key: 0x%X", key);
            return GF_ERROR_INVALID_PARAMETER;
        }
    }

    /* We store the callback for dispatch in msg_wnd_proc */
    (void)callback;
    (void)user_data;

    /* Register system-wide hotkey via message window */
    static UINT hotkey_id = 0x4000;
    ATOM atom = GlobalAddAtomA("GridFluxHotkey");
    if (!RegisterHotKey(g_win32.msg_hwnd, hotkey_id++, fsModifiers, vk))
    {
        GlobalDeleteAtom(atom);
        GF_LOG_WARN("Failed to register hotkey (vk=0x%X mod=0x%X): %lu",
                    vk, fsModifiers, GetLastError());
        return GF_ERROR_PLATFORM_ERROR;
    }

    return GF_SUCCESS;
}

/* ── Border windows ─────────────────────────────────────────── */

static void
register_border_class(void)
{
    WNDCLASSA wc = {0};
    wc.lpfnWndProc   = border_wnd_proc;
    wc.hInstance      = g_win32.h_instance;
    wc.lpszClassName  = "GridFluxBorder";
    wc.hCursor        = LoadCursor(NULL, IDC_ARROW);
    wc.style          = CS_HREDRAW | CS_VREDRAW;
    g_win32.border_class_atom = RegisterClassA(&wc);
}

static LRESULT CALLBACK
border_wnd_proc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    switch (msg)
    {
    case WM_PAINT:
    {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);

        /* Get associated workspace index from window user data */
        int ws_id = (int)(uintptr_t)GetWindowLongPtrA(hwnd, GWLP_USERDATA);
        RECT r;
        GetClientRect(hwnd, &r);

        /* Draw colored border rectangle */
        HBRUSH brush = CreateSolidBrush(RGB(80, 120, 200));
        FrameRect(hdc, &r, brush);
        DeleteObject(brush);

        EndPaint(hwnd, &ps);
        return 0;
    }
    case WM_NCHITTEST:
    {
        /* Make borders click-through but visible */
        return HTTRANSPARENT;
    }
    default:
        return DefWindowProcA(hwnd, msg, wParam, lParam);
    }
}

static void
win32_border_init(struct gf_platform_t *self)
{
    /* Already registered in init */
    (void)self;
}

static gf_task_borders_t *
win32_get_task_borders(HWND target)
{
    gf_task_borders_t *free_slot = NULL;

    for (uint32_t i = 0; i < GF_MAX_WORKSPACES * GF_MAX_WINDOWS_PER_WORKSPACE; i++)
    {
        gf_task_borders_t *slot = &g_win32.task_borders[i];
        if (slot->in_use && slot->target == target)
            return slot;
        if (!slot->in_use && !free_slot)
            free_slot = slot;
    }

    if (!free_slot)
        return NULL;

    memset(free_slot, 0, sizeof(*free_slot));
    free_slot->target = target;
    free_slot->in_use = true;
    return free_slot;
}

static void
win32_hide_task_borders(gf_task_borders_t *slot)
{
    if (!slot) return;

    for (int i = 0; i < 4; i++)
    {
        if (slot->borders[i].hwnd)
        {
            ShowWindow(slot->borders[i].hwnd, SW_HIDE);
            slot->borders[i].visible = false;
        }
    }
}

static HWND
win32_ensure_task_border(HWND target, gf_task_borders_t *slot, int index)
{
    if (slot->borders[index].hwnd)
        return slot->borders[index].hwnd;

    HWND hwnd = CreateWindowExA(
        WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
        "GridFluxBorder", NULL, WS_POPUP,
        0, 0, 1, 1, NULL, NULL, g_win32.h_instance, NULL);
    if (!hwnd)
        return NULL;

    SetWindowLongPtrA(hwnd, GWLP_USERDATA, (LONG_PTR)(uintptr_t)target);
    SetLayeredWindowAttributes(hwnd, 0, 220, LWA_ALPHA);
    slot->borders[index].hwnd = hwnd;
    return hwnd;
}

static void
win32_task_border_update(HWND target, const gf_config_t *cfg)
{
    if (!cfg)
        return;

    gf_task_borders_t *slot = win32_get_task_borders(target);
    if (!slot)
        return;

    if (!cfg->enable_borders || cfg->border_width == 0 || !IsWindow(target))
    {
        win32_hide_task_borders(slot);
        return;
    }

    RECT r;
    if (!win32_get_visible_frame(target, &r))
    {
        win32_hide_task_borders(slot);
        return;
    }

    int bw = (int)cfg->border_width;
    int x = r.left;
    int y = r.top;
    int w = r.right - r.left;
    int h = r.bottom - r.top;

    HWND top = win32_ensure_task_border(target, slot, 0);
    HWND bottom = win32_ensure_task_border(target, slot, 1);
    HWND left = win32_ensure_task_border(target, slot, 2);
    HWND right = win32_ensure_task_border(target, slot, 3);

    if (top)
        SetWindowPos(top, HWND_TOPMOST, x, y, w, bw, SWP_NOACTIVATE | SWP_SHOWWINDOW);
    if (bottom)
        SetWindowPos(bottom, HWND_TOPMOST, x, y + h - bw, w, bw, SWP_NOACTIVATE | SWP_SHOWWINDOW);
    if (left)
        SetWindowPos(left, HWND_TOPMOST, x, y, bw, h, SWP_NOACTIVATE | SWP_SHOWWINDOW);
    if (right)
        SetWindowPos(right, HWND_TOPMOST, x + w - bw, y, bw, h, SWP_NOACTIVATE | SWP_SHOWWINDOW);

    for (int i = 0; i < 4; i++)
        slot->borders[i].visible = slot->borders[i].hwnd != NULL;
}

static void
win32_border_update(struct gf_platform_t *self, const gf_config_t *cfg)
{
    (void)self;
    if (!cfg) return;

    for (uint32_t ws = 0; ws < GF_MAX_WORKSPACES; ws++)
    {
        gf_workspace_borders_t *wsb = &g_win32.ws_borders[ws];
        for (int i = 0; i < 4; i++)
        {
            if (wsb->borders[i].hwnd)
            {
                ShowWindow(wsb->borders[i].hwnd, SW_HIDE);
                wsb->borders[i].visible = false;
            }
        }
    }

    for (uint32_t i = 0; i < GF_MAX_WORKSPACES * GF_MAX_WINDOWS_PER_WORKSPACE; i++)
    {
        gf_task_borders_t *slot = &g_win32.task_borders[i];
        if (!slot->in_use)
            continue;

        if (!IsWindow(slot->target))
        {
            for (int j = 0; j < 4; j++)
            {
                if (slot->borders[j].hwnd)
                {
                    DestroyWindow(slot->borders[j].hwnd);
                    slot->borders[j].hwnd = NULL;
                }
            }
            slot->in_use = false;
            slot->target = NULL;
            continue;
        }

        win32_task_border_update(slot->target, cfg);
    }
}

static void
win32_border_cleanup(struct gf_platform_t *self)
{
    (void)self;
    for (uint32_t ws = 0; ws < GF_MAX_WORKSPACES; ws++)
    {
        for (int i = 0; i < 4; i++)
        {
            if (g_win32.ws_borders[ws].borders[i].hwnd)
            {
                DestroyWindow(g_win32.ws_borders[ws].borders[i].hwnd);
                g_win32.ws_borders[ws].borders[i].hwnd = NULL;
                g_win32.ws_borders[ws].borders[i].visible = false;
            }
        }
    }

    for (uint32_t slot = 0; slot < GF_MAX_WORKSPACES * GF_MAX_WINDOWS_PER_WORKSPACE; slot++)
    {
        for (int i = 0; i < 4; i++)
        {
            if (g_win32.task_borders[slot].borders[i].hwnd)
            {
                DestroyWindow(g_win32.task_borders[slot].borders[i].hwnd);
                g_win32.task_borders[slot].borders[i].hwnd = NULL;
            }
        }
        g_win32.task_borders[slot].target = NULL;
        g_win32.task_borders[slot].in_use = false;
    }
}

/* ── Dock / taskbar hiding ──────────────────────────────────── */

static void
win32_dock_hide(struct gf_platform_t *self)
{
    if (g_win32.dock_hidden) return;

    /* Find the taskbar window */
    HWND taskbar = FindWindowA("Shell_TrayWnd", NULL);
    if (!taskbar) return;

    /* Find the start button (Windows 7 and earlier) */
    HWND start = FindWindowExA(NULL, NULL, "Button", NULL);

    /* Use APPBARDATA to auto-hide */
    APPBARDATA abd = {0};
    abd.cbSize = sizeof(APPBARDATA);
    abd.hWnd = taskbar;

    /* Set auto-hide */
    SHAppBarMessage(ABM_SETSTATE, &abd);

    /* Alternative: hide by removing WS_VISIBLE and adding to tray */
    SetWindowLongPtrA(taskbar, GWL_EXSTYLE,
                      GetWindowLongPtrA(taskbar, GWL_EXSTYLE) | WS_EX_TOOLWINDOW);
    ShowWindow(taskbar, SW_HIDE);

    if (start)
        ShowWindow(start, SW_HIDE);

    g_win32.taskbar_hwnd = taskbar;
    g_win32.dock_hidden = true;

    GF_LOG_INFO("Taskbar/dock hidden");
}

static void
win32_dock_restore(struct gf_platform_t *self)
{
    if (!g_win32.dock_hidden) return;

    if (g_win32.taskbar_hwnd)
    {
        SetWindowLongPtrA(g_win32.taskbar_hwnd, GWL_EXSTYLE,
                          GetWindowLongPtrA(g_win32.taskbar_hwnd, GWL_EXSTYLE) &
                          ~WS_EX_TOOLWINDOW);
        ShowWindow(g_win32.taskbar_hwnd, SW_SHOW);
    }

    /* Restore start button */
    HWND start = FindWindowExA(NULL, NULL, "Button", NULL);
    if (start)
        ShowWindow(start, SW_SHOW);

    g_win32.dock_hidden = false;
    GF_LOG_INFO("Taskbar/dock restored");
}

/* ── Workspace / virtual desktop ────────────────────────────── */

static gf_err_t
win32_workspace_switch(struct gf_platform_t *self,
                       gf_display_t display, uint32_t index)
{
    /* On Windows 10/11, use IVirtualDesktopManager COM interface */
    (void)self;
    (void)display;
    (void)index;

    /* Fallback: Ctrl+Win+Left/Right simulation for virtual desktops */
    /* This is a placeholder — full IVirtualDesktopManager integration
       would require COM initialization and is deferred to a later phase */

    INPUT inputs[4] = {0};
    int i = 0;

    /* Hold Ctrl */
    inputs[i].type = INPUT_KEYBOARD;
    inputs[i].ki.wVk = VK_CONTROL;
    i++;

    /* Hold Win */
    inputs[i].type = INPUT_KEYBOARD;
    inputs[i].ki.wVk = VK_LWIN;
    i++;

    /* Press Left or Right */
    inputs[i].type = INPUT_KEYBOARD;
    inputs[i].ki.wVk = (index % 2 == 0) ? VK_LEFT : VK_RIGHT;
    i++;

    /* Release keys (zero-init remaining slots act as releases) */
    /* ... simplified: send key up events */
    inputs[i].type = INPUT_KEYBOARD;
    inputs[i].ki.wVk = VK_CONTROL;
    inputs[i].ki.dwFlags = KEYEVENTF_KEYUP;
    i++;

    SendInput((UINT)i, inputs, sizeof(INPUT));

    return GF_SUCCESS;
}

static gf_err_t
win32_workspace_count(struct gf_platform_t *self,
                      gf_display_t display, uint32_t *out_count)
{
    /* Windows doesn't have a straightforward API for virtual desktop count.
     * We default to 4 and let it be overridden by config. */
    *out_count = 4;
    return GF_SUCCESS;
}

/* ── IPC (named pipe server/client) ────────────────────────── */

static gf_err_t
win32_ipc_init(struct gf_platform_t *self,
               const char *pipe_name,
               gf_ipc_handle_t *out_handle)
{
    if (!pipe_name || !out_handle)
        return GF_ERROR_INVALID_PARAMETER;

    strncpy(g_win32.pipe_name, pipe_name, sizeof(g_win32.pipe_name) - 1);

    /* Convert pipe name to UNC format */
    char unc_path[256];
    snprintf(unc_path, sizeof(unc_path), "\\\\.\\pipe\\%s", pipe_name);

    /* Create named pipe (overlapped for async) */
    HANDLE pipe = CreateNamedPipeA(
        unc_path,
        PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED,
        PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
        1,  /* max instances */
        GF_IPC_MSG_SIZE,
        GF_IPC_MSG_SIZE,
        0,   /* default timeout */
        NULL /* default security */
    );

    if (pipe == INVALID_HANDLE_VALUE)
    {
        GF_LOG_ERROR("CreateNamedPipe failed: %lu", GetLastError());
        return GF_ERROR_PLATFORM_ERROR;
    }

    /* Store original handle in platform state */
    g_win32.ipc_pipe = pipe;
    g_win32.ipc_server = true;

    /* Start async connect */
    OVERLAPPED ovlp = {0};
    ovlp.hEvent = CreateEventA(NULL, TRUE, FALSE, NULL);
    if (!ConnectNamedPipe(pipe, &ovlp))
    {
        if (GetLastError() != ERROR_IO_PENDING &&
            GetLastError() != ERROR_PIPE_CONNECTED)
        {
            CloseHandle(pipe);
            g_win32.ipc_pipe = INVALID_HANDLE_VALUE;
            return GF_ERROR_PLATFORM_ERROR;
        }
    }

    if (ovlp.hEvent)
        CloseHandle(ovlp.hEvent);

    /* Wrap in gf_ipc_handle_t */
    gf_ipc_handle_int_t *ci = gf_calloc(1, sizeof(gf_ipc_handle_int_t));
    if (!ci)
    {
        CloseHandle(pipe);
        g_win32.ipc_pipe = INVALID_HANDLE_VALUE;
        return GF_ERROR_PLATFORM_ERROR;
    }
    ci->pipe = pipe;
    ci->handle = (uintptr_t)pipe;
    ci->is_server = true;
    strncpy(ci->name, pipe_name, sizeof(ci->name) - 1);

    out_handle->_priv = (uintptr_t)ci;

    GF_LOG_INFO("IPC pipe created: %s", unc_path);
    return GF_SUCCESS;
}

static gf_err_t
win32_ipc_read(gf_ipc_handle_t handle, void *buf, size_t bufsize,
               size_t *out_read)
{
    gf_ipc_handle_int_t *ci = (gf_ipc_handle_int_t *)(uintptr_t)handle._priv;
    if (!ci || ci->pipe == INVALID_HANDLE_VALUE)
        return GF_ERROR_PLATFORM_ERROR;

    DWORD read = 0;
    OVERLAPPED ovlp = {0};
    ovlp.hEvent = CreateEventA(NULL, TRUE, FALSE, NULL);

    if (!ReadFile(ci->pipe, buf, (DWORD)bufsize, &read, &ovlp))
    {
        if (GetLastError() != ERROR_IO_PENDING)
        {
            if (ovlp.hEvent) CloseHandle(ovlp.hEvent);
            return GF_ERROR_PLATFORM_ERROR;
        }

        /* Wait for pending read */
        WaitForSingleObject(ovlp.hEvent, 5000);
        GetOverlappedResult(ci->pipe, &ovlp, &read, FALSE);
    }

    if (ovlp.hEvent) CloseHandle(ovlp.hEvent);
    *out_read = (size_t)read;
    return GF_SUCCESS;
}

static gf_err_t
win32_ipc_write(gf_ipc_handle_t handle, const void *buf, size_t len,
                size_t *out_written)
{
    gf_ipc_handle_int_t *ci = (gf_ipc_handle_int_t *)(uintptr_t)handle._priv;
    if (!ci || ci->pipe == INVALID_HANDLE_VALUE)
        return GF_ERROR_PLATFORM_ERROR;

    DWORD written = 0;
    OVERLAPPED ovlp = {0};
    ovlp.hEvent = CreateEventA(NULL, TRUE, FALSE, NULL);

    if (!WriteFile(ci->pipe, buf, (DWORD)len, &written, &ovlp))
    {
        if (GetLastError() != ERROR_IO_PENDING)
        {
            if (ovlp.hEvent) CloseHandle(ovlp.hEvent);
            return GF_ERROR_PLATFORM_ERROR;
        }

        WaitForSingleObject(ovlp.hEvent, 3000);
        GetOverlappedResult(ci->pipe, &ovlp, &written, FALSE);
    }

    if (ovlp.hEvent) CloseHandle(ovlp.hEvent);
    *out_written = (size_t)written;
    return GF_SUCCESS;
}

static void
win32_ipc_close(gf_ipc_handle_t handle)
{
    gf_ipc_handle_int_t *ci = (gf_ipc_handle_int_t *)(uintptr_t)handle._priv;
    if (ci && ci->pipe != INVALID_HANDLE_VALUE)
    {
        if (ci->is_server)
            DisconnectNamedPipe(ci->pipe);
        CloseHandle(ci->pipe);
        g_win32.ipc_pipe = INVALID_HANDLE_VALUE;
    }
}

/* ── Messaging ──────────────────────────────────────────────── */

static void
win32_send_message(gf_display_t display, gf_handle_t window,
                   uint32_t msg, uintptr_t wParam, uintptr_t lParam)
{
    HWND hwnd = gf_handle_to_hwnd(window);
    if (IsWindow(hwnd))
        SendMessageA(hwnd, (UINT)msg, (WPARAM)wParam, (LPARAM)lParam);
}

/* ── Message window for IPC dispatch ────────────────────────── */

static LRESULT CALLBACK
msg_wnd_proc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    switch (msg)
    {
    case WM_USER + 1:
        /* Keyboard hook forwarded event */
        /* wParam = VK code, lParam = pressed (1) / released (0) */
        /* TODO: Dispatch to registered hotkey callbacks */
        break;

    case WM_HOTKEY:
    {
        /* System hotkey triggered — forward to IPC or WM */
        ATOM atom = (ATOM)wParam;
        UINT vk = (UINT)(lParam & 0xFFFF);
        UINT fsModifiers = (UINT)((lParam >> 16) & 0xFFFF);
        GF_LOG_DEBUG("Hotkey triggered: atom=%u vk=0x%X mod=0x%X",
                     atom, vk, fsModifiers);
        break;
    }
    }

    return DefWindowProcA(hwnd, msg, wParam, lParam);
}

static void
register_msg_class(void)
{
    WNDCLASSA wc = {0};
    wc.lpfnWndProc   = msg_wnd_proc;
    wc.hInstance      = g_win32.h_instance;
    wc.lpszClassName  = "GridFluxMsg";
    g_win32.msg_window_class_atom = RegisterClassA(&wc);
}

/* No queued events — all input handled via hooks and hotkeys.
   Returns false (no event) to let the WM idle-sleep. */
static bool
win32_poll_event(gf_display_t display, gf_event_t *out_event)
{
    MSG msg;
    while (PeekMessageA(&msg, NULL, 0, 0, PM_REMOVE))
    {
        TranslateMessage(&msg);
        DispatchMessageA(&msg);
    }

    /* No discrete event to report — events arrive via hooks */
    (void)display;
    (void)out_event;
    return false;
}

/* ── Platform struct instance ───────────────────────────────── */

struct gf_platform_t gf_platform_win32 = {
    .init                = win32_init,
    .cleanup             = win32_cleanup,
    .platform_destroy    = win32_platform_destroy,
    .screen_get_bounds   = win32_screen_get_bounds,
    .window_set_geometry = win32_window_set_geometry,
    .window_get_geometry = win32_window_get_geometry,
    .window_show         = win32_window_show,
    .window_hide         = win32_window_hide,
    .window_bring_to_top = win32_window_bring_to_top,
    .window_is_valid     = win32_window_is_valid,
    .window_is_maximized = win32_window_is_maximized,
    .window_is_minimized = win32_window_is_minimized,
    .window_get_class    = win32_window_get_class,
    .window_get_title    = win32_window_get_title,
    .window_set_title    = win32_window_set_title,
    .window_redraw       = win32_window_redraw,
    .enum_windows        = win32_enum_windows,
    .poll_event          = win32_poll_event,
    .get_cursor_pos      = win32_get_cursor_pos,
    .set_cursor_pos      = win32_set_cursor_pos,
    .capture_mouse       = win32_capture_mouse,
    .release_mouse       = win32_release_mouse,
    .keymap_init         = win32_keymap_init,
    .keymap_cleanup      = win32_keymap_cleanup,
    .keymap_register     = win32_keymap_register,
    .border_init         = win32_border_init,
    .border_update       = win32_border_update,
    .border_cleanup      = win32_border_cleanup,
    .dock_hide           = win32_dock_hide,
    .dock_restore        = win32_dock_restore,
    .workspace_switch    = win32_workspace_switch,
    .workspace_count     = win32_workspace_count,
    .send_message        = win32_send_message,
    .ipc_init            = win32_ipc_init,
    .ipc_read            = win32_ipc_read,
    .ipc_write           = win32_ipc_write,
    .ipc_close           = win32_ipc_close,
};
