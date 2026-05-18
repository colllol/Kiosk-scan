#include "manager.h"
#include "../core/wm_internal.h"
#include "../core/layout.h"
#include "../core/events.h"
#include "../platform/platform.h"
#include "../config/config.h"
#include "../utils/logger.h"
#include <windows.h>
#include <dwmapi.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define GF_MANAGER_CLASS "GridFluxManagerWindow"
#define ID_ROWS          1001
#define ID_COLS          1002
#define ID_GAP           1003
#define ID_WORKSPACES    1004
#define ID_AUTO_START    1005
#define ID_LOCK_GRIDS    1006
#define ID_BORDERS       1007
#define ID_AUTO_TILE     1008
#define ID_APPLY         1009
#define ID_TILE_NOW      1010
#define ID_HIDE          1011
#define ID_EXIT          1012
#define ID_STATUS        1013
#define ID_ROW_WEIGHTS   1014
#define ID_COL_WEIGHTS   1015
#define ID_AUTO_LAUNCH   1017
#define ID_LAUNCH_TASKS  1018
#define ID_TASK_BASE      1100
#define GF_MANAGER_MAX_TASK_CONTROLS 16

typedef struct gf_manager_t {
    HWND hwnd;
    HWND rows;
    HWND cols;
    HWND gap;
    HWND row_weights;
    HWND col_weights;
    HWND workspaces;
    HWND auto_start;
    HWND auto_launch;
    HWND task_labels[GF_MANAGER_MAX_TASK_CONTROLS];
    HWND task_edits[GF_MANAGER_MAX_TASK_CONTROLS];
    HWND task_f11[GF_MANAGER_MAX_TASK_CONTROLS];
    HWND managed_task_windows[GF_MANAGER_MAX_TASK_CONTROLS];
    bool managed_task_f11[GF_MANAGER_MAX_TASK_CONTROLS];
    HWND lock_grids;
    HWND borders;
    HWND auto_tile;
    HWND status;
    gf_wm_t *wm;
    bool running;
} gf_manager_t;

static gf_manager_t g_manager = {0};

static void set_text_uint(HWND hwnd, uint32_t value)
{
    char buf[32];
    snprintf(buf, sizeof(buf), "%u", value);
    SetWindowTextA(hwnd, buf);
}

static uint32_t get_text_uint(HWND hwnd, uint32_t fallback, uint32_t minv, uint32_t maxv)
{
    char buf[32] = {0};
    char *end = NULL;
    GetWindowTextA(hwnd, buf, sizeof(buf));
    long value = strtol(buf, &end, 10);
    if (end == buf || value < (long)minv || value > (long)maxv)
        return fallback;
    return (uint32_t)value;
}

static void set_weights_text(HWND hwnd, const uint32_t *weights, uint32_t count)
{
    char buf[256] = {0};
    size_t pos = 0;

    if (count == 0)
        count = 1;

    for (uint32_t i = 0; i < count && i < GF_MAX_GRID_TRACKS; i++)
    {
        pos += snprintf(buf + pos, sizeof(buf) - pos, "%u%s",
                        weights[i] ? weights[i] : 1,
                        (i + 1 < count) ? "," : "");
        if (pos >= sizeof(buf))
            break;
    }

    SetWindowTextA(hwnd, buf);
}

static void get_weights_text(HWND hwnd, uint32_t *weights, uint32_t count)
{
    char buf[256] = {0};
    char *p = buf;

    for (uint32_t i = 0; i < GF_MAX_GRID_TRACKS; i++)
        weights[i] = 1;

    GetWindowTextA(hwnd, buf, sizeof(buf));

    for (uint32_t i = 0; i < count && i < GF_MAX_GRID_TRACKS; i++)
    {
        char *end = NULL;
        long value = strtol(p, &end, 10);
        weights[i] = value > 0 ? (uint32_t)value : 1;
        if (end == p)
            break;
        p = end;
        while (*p == ' ' || *p == '\t' || *p == ',' || *p == ';')
            p++;
        if (!*p)
            break;
    }
}

static uint32_t manager_visible_task_count_from_config(const gf_config_t *cfg)
{
    uint32_t count = cfg->rows * cfg->cols;
    if (count > GF_MANAGER_MAX_TASK_CONTROLS)
        count = GF_MANAGER_MAX_TASK_CONTROLS;
    return count;
}

static uint32_t manager_visible_task_count_from_inputs(void)
{
    uint32_t rows = get_text_uint(g_manager.rows, 1, 1, 16);
    uint32_t cols = get_text_uint(g_manager.cols, 1, 1, 16);
    uint32_t count = rows * cols;
    if (count > GF_MANAGER_MAX_TASK_CONTROLS)
        count = GF_MANAGER_MAX_TASK_CONTROLS;
    return count;
}

static void manager_update_task_visibility(uint32_t count)
{
    for (uint32_t i = 0; i < GF_MANAGER_MAX_TASK_CONTROLS; i++)
    {
        int show = i < count ? SW_SHOW : SW_HIDE;
        ShowWindow(g_manager.task_labels[i], show);
        ShowWindow(g_manager.task_edits[i], show);
        ShowWindow(g_manager.task_f11[i], show);
    }
}

static void set_task_controls(gf_config_t *cfg)
{
    uint32_t count = manager_visible_task_count_from_config(cfg);

    for (uint32_t i = 0; i < GF_MANAGER_MAX_TASK_CONTROLS; i++)
    {
        SetWindowTextA(g_manager.task_edits[i],
                       i < count ? cfg->startup_tasks[i] : "");
        SendMessageA(g_manager.task_f11[i], BM_SETCHECK,
                     (i < count && cfg->startup_task_f11[i]) ? BST_CHECKED : BST_UNCHECKED,
                     0);
    }

    manager_update_task_visibility(count);
}

static void get_task_controls(gf_config_t *cfg)
{
    uint32_t count = cfg->rows * cfg->cols;
    if (count > GF_MANAGER_MAX_TASK_CONTROLS)
        count = GF_MANAGER_MAX_TASK_CONTROLS;

    for (uint32_t i = 0; i < GF_MAX_GRID_CELLS; i++)
        cfg->startup_tasks[i][0] = '\0';

    for (uint32_t i = 0; i < count; i++)
    {
        GetWindowTextA(g_manager.task_edits[i],
                       cfg->startup_tasks[i],
                       GF_MAX_TASK_COMMAND);
        cfg->startup_task_f11[i] =
            SendMessageA(g_manager.task_f11[i], BM_GETCHECK, 0, 0) == BST_CHECKED;
    }
}

static void manager_split_command(const char *command,
                                  char *exe, size_t exe_size,
                                  char *args, size_t args_size)
{
    const char *p = command;
    while (*p == ' ' || *p == '\t')
        p++;

    exe[0] = '\0';
    args[0] = '\0';

    if (*p == '"')
    {
        p++;
        const char *end = strchr(p, '"');
        if (!end)
            end = p + strlen(p);
        size_t len = (size_t)(end - p);
        if (len >= exe_size)
            len = exe_size - 1;
        memcpy(exe, p, len);
        exe[len] = '\0';
        p = (*end == '"') ? end + 1 : end;
    }
    else
    {
        const char *end = p;
        while (*end && *end != ' ' && *end != '\t')
            end++;
        size_t len = (size_t)(end - p);
        if (len >= exe_size)
            len = exe_size - 1;
        memcpy(exe, p, len);
        exe[len] = '\0';
        p = end;
    }

    while (*p == ' ' || *p == '\t')
        p++;
    strncpy(args, p, args_size - 1);
    args[args_size - 1] = '\0';

    if (strcmp(exe, "chrome") == 0)
        strncpy(exe, "chrome.exe", exe_size - 1);
    else if (strcmp(exe, "edge") == 0 || strcmp(exe, "msedge") == 0)
        strncpy(exe, "msedge.exe", exe_size - 1);
    else if (strcmp(exe, "explorer") == 0)
        strncpy(exe, "explorer.exe", exe_size - 1);
}

static bool manager_is_browser(const char *exe)
{
    const char *base = exe;
    if (!exe || !*exe)
        return false;

    for (const char *p = exe; *p; p++)
    {
        if (*p == '\\' || *p == '/')
            base = p + 1;
    }

    return lstrcmpiA(base, "chrome.exe") == 0 ||
           lstrcmpiA(base, "msedge.exe") == 0;
}

static bool manager_looks_like_url(const char *text)
{
    return strncmp(text, "http://", 7) == 0 ||
           strncmp(text, "https://", 8) == 0 ||
           strchr(text, '.') != NULL;
}

static bool manager_is_single_token(const char *text)
{
    if (!text || !*text)
        return false;
    for (const char *p = text; *p; p++)
    {
        if (*p == ' ' || *p == '\t')
            return false;
    }
    return true;
}

static void manager_normalize_url(const char *input, char *out, size_t out_size)
{
    if (strncmp(input, "http://", 7) == 0 ||
        strncmp(input, "https://", 8) == 0)
    {
        snprintf(out, out_size, "%s", input);
    }
    else
    {
        snprintf(out, out_size, "https://%s", input);
    }
}

static void manager_profile_arg(const char *exe, uint32_t index,
                                char *out, size_t out_size)
{
    char appdata[MAX_PATH] = {0};
    char root[MAX_PATH] = {0};
    char profiles[MAX_PATH] = {0};
    char profile[MAX_PATH] = {0};
    const char *name = "chrome";
    if (manager_is_browser(exe))
    {
        const char *base = exe;
        for (const char *p = exe; *p; p++)
        {
            if (*p == '\\' || *p == '/')
                base = p + 1;
        }
        if (lstrcmpiA(base, "msedge.exe") == 0)
            name = "edge";
    }

    DWORD len = GetEnvironmentVariableA("APPDATA", appdata, sizeof(appdata));
    if (len == 0 || len >= sizeof(appdata))
    {
        out[0] = '\0';
        return;
    }

    snprintf(root, sizeof(root), "%s\\GridFlux", appdata);
    snprintf(profiles, sizeof(profiles), "%s\\profiles", root);
    snprintf(profile, sizeof(profile), "%s\\%s-grid-%u", profiles, name, index + 1);
    CreateDirectoryA(root, NULL);
    CreateDirectoryA(profiles, NULL);
    CreateDirectoryA(profile, NULL);

    snprintf(out, out_size, "--user-data-dir=\"%s\"", profile);
}

static bool manager_file_exists(const char *path)
{
    DWORD attr;
    if (!path || !*path)
        return false;
    attr = GetFileAttributesA(path);
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY);
}

static bool manager_read_app_path(HKEY root, const char *subkey,
                                  char *out, size_t out_size)
{
    HKEY key;
    DWORD type = 0;
    DWORD size = (DWORD)out_size;

    if (RegOpenKeyExA(root, subkey, 0, KEY_READ, &key) != ERROR_SUCCESS)
        return false;

    LONG rc = RegQueryValueExA(key, NULL, NULL, &type, (LPBYTE)out, &size);
    RegCloseKey(key);
    if (rc != ERROR_SUCCESS || type != REG_SZ || !manager_file_exists(out))
        return false;

    out[out_size - 1] = '\0';
    return true;
}

static bool manager_try_browser_candidate(const char *dir, const char *rel,
                                          char *out, size_t out_size)
{
    char path[MAX_PATH] = {0};
    DWORD len;

    if (!dir || !*dir)
        return false;

    len = GetEnvironmentVariableA(dir, path, sizeof(path));
    if (len == 0 || len >= sizeof(path))
        return false;

    snprintf(out, out_size, "%s\\%s", path, rel);
    return manager_file_exists(out);
}

static bool manager_resolve_browser_exe(const char *exe,
                                        char *out, size_t out_size)
{
    const char *base = exe;
    const bool wants_edge = exe && manager_is_browser(exe) &&
        (lstrcmpiA((strrchr(exe, '\\') ? strrchr(exe, '\\') + 1 : exe), "msedge.exe") == 0);

    if (!exe || !*exe)
        return false;

    if ((strchr(exe, '\\') || strchr(exe, '/')) && manager_file_exists(exe))
    {
        snprintf(out, out_size, "%s", exe);
        return true;
    }

    for (const char *p = exe; *p; p++)
    {
        if (*p == '\\' || *p == '/')
            base = p + 1;
    }

    if (lstrcmpiA(base, "chrome.exe") != 0 && lstrcmpiA(base, "msedge.exe") != 0)
    {
        snprintf(out, out_size, "%s", exe);
        return true;
    }

    if (!wants_edge)
    {
        if (manager_read_app_path(HKEY_CURRENT_USER,
                "Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\chrome.exe",
                out, out_size) ||
            manager_read_app_path(HKEY_LOCAL_MACHINE,
                "Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\chrome.exe",
                out, out_size) ||
            manager_read_app_path(HKEY_LOCAL_MACHINE,
                "Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\App Paths\\chrome.exe",
                out, out_size) ||
            manager_try_browser_candidate("PROGRAMFILES",
                "Google\\Chrome\\Application\\chrome.exe", out, out_size) ||
            manager_try_browser_candidate("PROGRAMFILES(X86)",
                "Google\\Chrome\\Application\\chrome.exe", out, out_size) ||
            manager_try_browser_candidate("LOCALAPPDATA",
                "Google\\Chrome\\Application\\chrome.exe", out, out_size))
            return true;
    }

    if (manager_read_app_path(HKEY_CURRENT_USER,
            "Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\msedge.exe",
            out, out_size) ||
        manager_read_app_path(HKEY_LOCAL_MACHINE,
            "Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\msedge.exe",
            out, out_size) ||
        manager_read_app_path(HKEY_LOCAL_MACHINE,
            "Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\App Paths\\msedge.exe",
            out, out_size) ||
        manager_try_browser_candidate("PROGRAMFILES",
            "Microsoft\\Edge\\Application\\msedge.exe", out, out_size) ||
        manager_try_browser_candidate("PROGRAMFILES(X86)",
            "Microsoft\\Edge\\Application\\msedge.exe", out, out_size) ||
        manager_try_browser_candidate("LOCALAPPDATA",
            "Microsoft\\Edge\\Application\\msedge.exe", out, out_size))
        return true;

    if (wants_edge)
        return false;

    return manager_resolve_browser_exe("msedge.exe", out, out_size);
}

typedef struct manager_window_find_t {
    DWORD pid;
    HWND hwnd;
} manager_window_find_t;

typedef struct manager_window_snapshot_t {
    HWND items[256];
    uint32_t count;
} manager_window_snapshot_t;

static BOOL CALLBACK manager_find_window_proc(HWND hwnd, LPARAM lParam)
{
    manager_window_find_t *ctx = (manager_window_find_t *)lParam;
    DWORD pid = 0;

    if (!IsWindowVisible(hwnd))
        return TRUE;
    if (GetWindow(hwnd, GW_OWNER) != NULL)
        return TRUE;
    if (hwnd == g_manager.hwnd)
        return TRUE;

    GetWindowThreadProcessId(hwnd, &pid);
    if (pid != ctx->pid)
        return TRUE;

    ctx->hwnd = hwnd;
    return FALSE;
}

static HWND manager_wait_for_process_window(HANDLE process)
{
    DWORD pid;

    if (!process)
        return NULL;

    pid = GetProcessId(process);
    if (!pid)
        return NULL;

    WaitForInputIdle(process, 5000);

    for (int attempt = 0; attempt < 30; attempt++)
    {
        manager_window_find_t ctx = { pid, NULL };
        EnumWindows(manager_find_window_proc, (LPARAM)&ctx);
        if (ctx.hwnd)
            return ctx.hwnd;
        Sleep(200);
    }

    return NULL;
}

static bool manager_is_candidate_window(HWND hwnd)
{
    BOOL cloaked = FALSE;

    if (!hwnd || !IsWindowVisible(hwnd))
        return false;
    if (GetWindow(hwnd, GW_OWNER) != NULL)
        return false;
    if (hwnd == g_manager.hwnd)
        return false;
    DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, &cloaked, sizeof(cloaked));
    if (cloaked)
        return false;
    return true;
}

static BOOL CALLBACK manager_snapshot_proc(HWND hwnd, LPARAM lParam)
{
    manager_window_snapshot_t *snapshot = (manager_window_snapshot_t *)lParam;

    if (!manager_is_candidate_window(hwnd))
        return TRUE;
    if (snapshot->count >= (uint32_t)(sizeof(snapshot->items) / sizeof(snapshot->items[0])))
        return FALSE;

    snapshot->items[snapshot->count++] = hwnd;
    return TRUE;
}

static void manager_take_window_snapshot(manager_window_snapshot_t *snapshot)
{
    memset(snapshot, 0, sizeof(*snapshot));
    EnumWindows(manager_snapshot_proc, (LPARAM)snapshot);
}

static bool manager_snapshot_contains(const manager_window_snapshot_t *snapshot,
                                      HWND hwnd)
{
    for (uint32_t i = 0; i < snapshot->count; i++)
    {
        if (snapshot->items[i] == hwnd)
            return true;
    }
    return false;
}

static HWND manager_wait_for_new_window(const manager_window_snapshot_t *before)
{
    for (int attempt = 0; attempt < 50; attempt++)
    {
        manager_window_snapshot_t now;
        manager_take_window_snapshot(&now);
        for (uint32_t i = 0; i < now.count; i++)
        {
            if (!manager_snapshot_contains(before, now.items[i]))
                return now.items[i];
        }
        Sleep(200);
    }

    return NULL;
}

static HWND manager_launch_task_window(const char *exe, const char *args)
{
    SHELLEXECUTEINFOA sei;
    HWND hwnd = NULL;
    manager_window_snapshot_t before;

    manager_take_window_snapshot(&before);
    memset(&sei, 0, sizeof(sei));
    sei.cbSize = sizeof(sei);
    sei.fMask = SEE_MASK_NOCLOSEPROCESS;
    sei.lpVerb = "open";
    sei.lpFile = exe;
    sei.lpParameters = args && args[0] ? args : NULL;
    sei.nShow = SW_SHOWNORMAL;

    if (!ShellExecuteExA(&sei))
        return NULL;

    hwnd = manager_wait_for_process_window(sei.hProcess);
    if (!hwnd)
        hwnd = manager_wait_for_new_window(&before);
    if (sei.hProcess)
        CloseHandle(sei.hProcess);
    return hwnd;
}

static void manager_send_f11(HWND hwnd)
{
    if (!hwnd || !IsWindow(hwnd))
        return;

    ShowWindow(hwnd, SW_SHOWNORMAL);
    SetForegroundWindow(hwnd);
    Sleep(150);
    keybd_event(VK_F11, 0, 0, 0);
    keybd_event(VK_F11, 0, KEYEVENTF_KEYUP, 0);
    Sleep(300);
}

static HWND manager_launch_configured_task(gf_wm_t *wm, uint32_t index, bool *send_f11)
{
    char exe[MAX_PATH] = {0};
    char launch_exe[MAX_PATH] = {0};
    char args[2048] = {0};
    char launch_args[2048] = {0};
    const char *cmd;

    if (send_f11)
        *send_f11 = false;
    if (!wm || !wm->config || index >= GF_MANAGER_MAX_TASK_CONTROLS)
        return NULL;

    cmd = wm->config->startup_tasks[index];
    while (*cmd == ' ' || *cmd == '\t')
        cmd++;
    if (!*cmd)
        return NULL;

    manager_split_command(cmd, exe, sizeof(exe), args, sizeof(args));
    if (!exe[0])
        return NULL;

    if (!args[0] && manager_looks_like_url(exe))
    {
        char url[GF_MAX_TASK_COMMAND] = {0};
        manager_normalize_url(exe, url, sizeof(url));
        strncpy(exe, "chrome.exe", sizeof(exe) - 1);
        strncpy(args, url, sizeof(args) - 1);
    }

    if (manager_is_browser(exe))
    {
        char profile_arg[MAX_PATH + 64] = {0};
        manager_profile_arg(exe, index, profile_arg, sizeof(profile_arg));
        if (args[0] && manager_is_single_token(args) && manager_looks_like_url(args))
        {
            char app_url[GF_MAX_TASK_COMMAND] = {0};
            manager_normalize_url(args, app_url, sizeof(app_url));
            if (wm->config->startup_task_f11[index])
            {
                snprintf(launch_args, sizeof(launch_args),
                         "%s --no-first-run --disable-first-run-ui --app=\"%s\"",
                         profile_arg, app_url);
            }
            else
            {
                snprintf(launch_args, sizeof(launch_args),
                         "%s --no-first-run --disable-first-run-ui --new-window \"%s\"",
                         profile_arg, app_url);
            }
        }
        else
        {
            snprintf(launch_args, sizeof(launch_args),
                     "%s --no-first-run --disable-first-run-ui %s",
                     profile_arg, args);
        }
        if (!manager_resolve_browser_exe(exe, launch_exe, sizeof(launch_exe)))
        {
            GF_LOG_ERROR("Browser not found for task %u: %s", index + 1, exe);
            return NULL;
        }
    }
    else
    {
        strncpy(launch_args, args, sizeof(launch_args) - 1);
        strncpy(launch_exe, exe, sizeof(launch_exe) - 1);
        if (send_f11)
            *send_f11 = wm->config->startup_task_f11[index];
    }

    return manager_launch_task_window(launch_exe, launch_args[0] ? launch_args : NULL);
}

void gf_manager_launch_configured_tasks(gf_wm_t *wm)
{
    if (!wm || !wm->config)
        return;

    uint32_t count = wm->config->rows * wm->config->cols;
    HWND launched[GF_MAX_GRID_CELLS] = {0};
    bool launched_f11[GF_MAX_GRID_CELLS] = {0};
    uint32_t launched_count = 0;
    if (count > GF_MAX_GRID_CELLS)
        count = GF_MAX_GRID_CELLS;
    memset(g_manager.managed_task_windows, 0, sizeof(g_manager.managed_task_windows));
    memset(g_manager.managed_task_f11, 0, sizeof(g_manager.managed_task_f11));

    for (uint32_t i = 0; i < count; i++)
    {
        char exe[MAX_PATH] = {0};
        char launch_exe[MAX_PATH] = {0};
        char args[2048] = {0};
        char launch_args[2048] = {0};
        const char *cmd = wm->config->startup_tasks[i];
        while (*cmd == ' ' || *cmd == '\t')
            cmd++;
        if (!*cmd)
            continue;

        manager_split_command(cmd, exe, sizeof(exe), args, sizeof(args));
        if (!exe[0])
            continue;

        if (!args[0] && manager_looks_like_url(exe))
        {
            char url[GF_MAX_TASK_COMMAND] = {0};
            manager_normalize_url(exe, url, sizeof(url));
            strncpy(exe, "chrome.exe", sizeof(exe) - 1);
            strncpy(args, url, sizeof(args) - 1);
        }

        if (manager_is_browser(exe))
        {
            char profile_arg[MAX_PATH + 64] = {0};
            manager_profile_arg(exe, i, profile_arg, sizeof(profile_arg));
            if (args[0] && manager_is_single_token(args) && manager_looks_like_url(args))
            {
                char app_url[GF_MAX_TASK_COMMAND] = {0};
                manager_normalize_url(args, app_url, sizeof(app_url));
                if (wm->config->startup_task_f11[i])
                {
                    snprintf(launch_args, sizeof(launch_args),
                             "%s --no-first-run --disable-first-run-ui --app=\"%s\"",
                             profile_arg, app_url);
                }
                else
                {
                    snprintf(launch_args, sizeof(launch_args),
                             "%s --no-first-run --disable-first-run-ui --new-window \"%s\"",
                             profile_arg, app_url);
                }
            }
            else
            {
                snprintf(launch_args, sizeof(launch_args),
                         "%s --no-first-run --disable-first-run-ui %s",
                         profile_arg, args);
            }
            if (!manager_resolve_browser_exe(exe, launch_exe, sizeof(launch_exe)))
            {
                GF_LOG_ERROR("Browser not found for task %u: %s", i + 1, exe);
                continue;
            }
        }
        else
        {
            strncpy(launch_args, args, sizeof(launch_args) - 1);
            strncpy(launch_exe, exe, sizeof(launch_exe) - 1);
        }

        launched[launched_count] =
            manager_launch_task_window(launch_exe, launch_args[0] ? launch_args : NULL);
        if (launched[launched_count])
        {
            launched_f11[launched_count] =
                wm->config->startup_task_f11[i] && !manager_is_browser(exe);
            if (i < GF_MANAGER_MAX_TASK_CONTROLS)
            {
                g_manager.managed_task_windows[i] = launched[launched_count];
                g_manager.managed_task_f11[i] = launched_f11[launched_count];
            }
            launched_count++;
        }
        Sleep(manager_is_browser(exe) ? 300 : 150);
    }

    gf_ws_id_t ws_id = wm->active_workspace;
    gf_workspace_state_t *ws = gf_wm_get_workspace_state(wm, ws_id);
    if (ws)
    {
        ws->windows.count = 0;
        gf_layout_clear(&ws->layout);
    }

    for (uint32_t i = 0; i < launched_count; i++)
        gf_wm_add_window(wm, (gf_handle_t)(uintptr_t)launched[i], ws_id);

    gf_wm_tile_all(wm);

    for (uint32_t i = 0; i < launched_count; i++)
    {
        if (launched_f11[i])
            manager_send_f11(launched[i]);
    }

    for (int pass = 0; pass < 6; pass++)
    {
        Sleep(200);
        gf_wm_tile_all(wm);
    }
}

void gf_manager_relaunch_missing_tasks(gf_wm_t *wm)
{
    if (!wm || !wm->config || !wm->config->auto_launch_tasks)
        return;

    uint32_t count = wm->config->rows * wm->config->cols;
    if (count > GF_MANAGER_MAX_TASK_CONTROLS)
        count = GF_MANAGER_MAX_TASK_CONTROLS;

    for (uint32_t i = 0; i < count; i++)
    {
        const char *cmd = wm->config->startup_tasks[i];
        while (*cmd == ' ' || *cmd == '\t')
            cmd++;
        if (!*cmd)
            continue;

        if (g_manager.managed_task_windows[i] && IsWindow(g_manager.managed_task_windows[i]))
            continue;

        bool send_f11 = false;
        HWND hwnd = manager_launch_configured_task(wm, i, &send_f11);
        if (!hwnd)
            continue;

        g_manager.managed_task_windows[i] = hwnd;
        g_manager.managed_task_f11[i] = send_f11;
        gf_wm_add_window(wm, (gf_handle_t)(uintptr_t)hwnd, wm->active_workspace);
        gf_wm_tile_all(wm);
        if (send_f11)
            manager_send_f11(hwnd);
        for (int pass = 0; pass < 4; pass++)
        {
            Sleep(150);
            gf_wm_tile_all(wm);
        }
    }
}

static bool manager_get_exe_path(char *out, size_t out_size)
{
    DWORD len = GetModuleFileNameA(NULL, out, (DWORD)out_size);
    return len > 0 && len < out_size;
}

static bool manager_is_autostart_enabled(void)
{
    HKEY key;
    char actual[MAX_PATH] = {0};
    char expected[MAX_PATH] = {0};
    DWORD type = 0;
    DWORD size = sizeof(actual);

    if (!manager_get_exe_path(expected, sizeof(expected)))
        return false;

    if (RegOpenKeyExA(HKEY_CURRENT_USER,
        "Software\\Microsoft\\Windows\\CurrentVersion\\Run",
        0, KEY_READ, &key) != ERROR_SUCCESS)
        return false;

    LONG rc = RegQueryValueExA(key, "GridFlux", NULL, &type, (LPBYTE)actual, &size);
    RegCloseKey(key);

    return rc == ERROR_SUCCESS && type == REG_SZ && strcmp(actual, expected) == 0;
}

static bool manager_set_autostart(bool enabled)
{
    HKEY key;
    char exe[MAX_PATH] = {0};

    if (RegCreateKeyExA(HKEY_CURRENT_USER,
        "Software\\Microsoft\\Windows\\CurrentVersion\\Run",
        0, NULL, 0, KEY_SET_VALUE, NULL, &key, NULL) != ERROR_SUCCESS)
        return false;

    if (!enabled)
    {
        RegDeleteValueA(key, "GridFlux");
        RegCloseKey(key);
        return true;
    }

    if (!manager_get_exe_path(exe, sizeof(exe)))
    {
        RegCloseKey(key);
        return false;
    }

    LONG rc = RegSetValueExA(key, "GridFlux", 0, REG_SZ,
                             (const BYTE *)exe, (DWORD)strlen(exe) + 1);
    RegCloseKey(key);
    return rc == ERROR_SUCCESS;
}

static void manager_set_status(const char *text)
{
    if (g_manager.status)
        SetWindowTextA(g_manager.status, text);
}

static void manager_refresh_controls(void)
{
    gf_wm_t *wm = g_manager.wm;
    if (!wm || !wm->config)
        return;

    set_text_uint(g_manager.rows, wm->config->rows);
    set_text_uint(g_manager.cols, wm->config->cols);
    set_text_uint(g_manager.gap, wm->config->gap);
    set_text_uint(g_manager.workspaces, wm->config->workspace_count);
    set_weights_text(g_manager.row_weights, wm->config->row_weights, wm->config->rows);
    set_weights_text(g_manager.col_weights, wm->config->col_weights, wm->config->cols);
    set_task_controls(wm->config);

    SendMessageA(g_manager.auto_start, BM_SETCHECK,
                 manager_is_autostart_enabled() ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessageA(g_manager.auto_launch, BM_SETCHECK,
                 wm->config->auto_launch_tasks ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessageA(g_manager.lock_grids, BM_SETCHECK,
                 wm->config->lock_grids ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessageA(g_manager.borders, BM_SETCHECK,
                 wm->config->enable_borders ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessageA(g_manager.auto_tile, BM_SETCHECK,
                 wm->config->auto_tile ? BST_CHECKED : BST_UNCHECKED, 0);

    manager_set_status("Ready");
}

static void manager_apply_layout(gf_wm_t *wm)
{
    for (uint32_t i = 0; i < wm->workspace_count; i++)
    {
        gf_workspace_state_t *ws = &wm->workspaces[i];
        ws->id = (gf_ws_id_t)i;
        ws->locked = wm->config->lock_grids;

        gf_layout_destroy(&ws->layout);
        memset(&ws->layout, 0, sizeof(ws->layout));

        gf_rect_t bounds;
        if (wm->platform->screen_get_bounds(wm->display, &bounds) != GF_SUCCESS)
            bounds = (gf_rect_t){0, 0, 1920, 1080};

        gf_layout_init(&ws->layout, wm->config->rows, wm->config->cols,
                       &bounds, wm->config->gap);
        gf_layout_set_weights(&ws->layout,
                              wm->config->row_weights,
                              wm->config->col_weights);

        if (!ws->locked)
            gf_wm_tile_workspace(wm, (gf_ws_id_t)i);
    }

    wm->borders_enabled = wm->config->enable_borders;
    if (!wm->borders_enabled)
        wm->platform->border_cleanup(wm->platform);
    else
        gf_wm_update_borders(wm);
}

static void manager_apply_settings(void)
{
    gf_wm_t *wm = g_manager.wm;
    if (!wm || !wm->config)
        return;

    uint32_t old_count = wm->workspace_count;
    wm->config->rows = get_text_uint(g_manager.rows, wm->config->rows, 1, 16);
    wm->config->cols = get_text_uint(g_manager.cols, wm->config->cols, 1, 16);
    wm->config->gap = get_text_uint(g_manager.gap, wm->config->gap, 0, 100);
    wm->config->workspace_count = get_text_uint(g_manager.workspaces,
                                                wm->config->workspace_count,
                                                1, GF_MAX_WORKSPACES);
    get_weights_text(g_manager.row_weights,
                     wm->config->row_weights,
                     wm->config->rows);
    get_weights_text(g_manager.col_weights,
                     wm->config->col_weights,
                     wm->config->cols);
    wm->config->lock_grids =
        SendMessageA(g_manager.lock_grids, BM_GETCHECK, 0, 0) == BST_CHECKED;
    wm->config->enable_borders =
        SendMessageA(g_manager.borders, BM_GETCHECK, 0, 0) == BST_CHECKED;
    wm->config->auto_tile =
        SendMessageA(g_manager.auto_tile, BM_GETCHECK, 0, 0) == BST_CHECKED;
    wm->config->auto_launch_tasks =
        SendMessageA(g_manager.auto_launch, BM_GETCHECK, 0, 0) == BST_CHECKED;
    get_task_controls(wm->config);

    if (wm->config->workspace_count > old_count)
    {
        for (uint32_t i = old_count; i < wm->config->workspace_count; i++)
        {
            if (wm->config->workspace_names[i][0] == '\0')
                snprintf(wm->config->workspace_names[i],
                         sizeof(wm->config->workspace_names[i]),
                         "Grid %u", i + 1);
        }
    }

    wm->workspace_count = wm->config->workspace_count;
    if (wm->active_workspace >= wm->workspace_count)
        wm->active_workspace = wm->workspace_count - 1;

    bool auto_start =
        SendMessageA(g_manager.auto_start, BM_GETCHECK, 0, 0) == BST_CHECKED;
    bool auto_start_ok = manager_set_autostart(auto_start);

    manager_apply_layout(wm);
    gf_config_save(gf_config_get_path(), wm->config);
    manager_refresh_controls();
    manager_set_status(auto_start_ok ? "Settings saved" : "Settings saved, autostart failed");
}

static HWND add_label(HWND parent, const char *text, int x, int y, int w, int h)
{
    return CreateWindowExA(0, "STATIC", text, WS_CHILD | WS_VISIBLE,
                           x, y, w, h, parent, NULL, GetModuleHandleA(NULL), NULL);
}

static HWND add_edit(HWND parent, int id, int x, int y, int w, int h)
{
    return CreateWindowExA(WS_EX_CLIENTEDGE, "EDIT", "",
                           WS_CHILD | WS_VISIBLE | ES_NUMBER | ES_AUTOHSCROLL,
                           x, y, w, h, parent, (HMENU)(uintptr_t)id,
                           GetModuleHandleA(NULL), NULL);
}

static HWND add_text_edit(HWND parent, int id, int x, int y, int w, int h)
{
    return CreateWindowExA(WS_EX_CLIENTEDGE, "EDIT", "",
                           WS_CHILD | WS_VISIBLE | ES_AUTOHSCROLL,
                           x, y, w, h, parent, (HMENU)(uintptr_t)id,
                           GetModuleHandleA(NULL), NULL);
}

static HWND add_button(HWND parent, const char *text, int id, int x, int y, int w, int h)
{
    return CreateWindowExA(0, "BUTTON", text,
                           WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                           x, y, w, h, parent, (HMENU)(uintptr_t)id,
                           GetModuleHandleA(NULL), NULL);
}

static HWND add_check(HWND parent, const char *text, int id, int x, int y, int w, int h)
{
    return CreateWindowExA(0, "BUTTON", text,
                           WS_CHILD | WS_VISIBLE | BS_AUTOCHECKBOX,
                           x, y, w, h, parent, (HMENU)(uintptr_t)id,
                           GetModuleHandleA(NULL), NULL);
}

static void manager_create_controls(HWND hwnd)
{
    HFONT font = (HFONT)GetStockObject(DEFAULT_GUI_FONT);
    HWND controls[80];
    int n = 0;

    controls[n++] = add_label(hwnd, "GridFlux Manager", 18, 16, 220, 24);
    controls[n++] = add_label(hwnd, "Rows", 24, 58, 90, 20);
    g_manager.rows = controls[n++] = add_edit(hwnd, ID_ROWS, 124, 54, 70, 24);
    controls[n++] = add_label(hwnd, "Columns", 224, 58, 90, 20);
    g_manager.cols = controls[n++] = add_edit(hwnd, ID_COLS, 324, 54, 70, 24);

    controls[n++] = add_label(hwnd, "Gap", 24, 92, 90, 20);
    g_manager.gap = controls[n++] = add_edit(hwnd, ID_GAP, 124, 88, 70, 24);
    controls[n++] = add_label(hwnd, "Grid count", 224, 92, 90, 20);
    g_manager.workspaces = controls[n++] = add_edit(hwnd, ID_WORKSPACES, 324, 88, 70, 24);

    controls[n++] = add_label(hwnd, "Row heights %", 24, 126, 100, 20);
    g_manager.row_weights = controls[n++] = add_text_edit(hwnd, ID_ROW_WEIGHTS, 124, 122, 270, 24);
    controls[n++] = add_label(hwnd, "Col widths %", 24, 160, 100, 20);
    g_manager.col_weights = controls[n++] = add_text_edit(hwnd, ID_COL_WEIGHTS, 124, 156, 270, 24);

    controls[n++] = add_label(hwnd, "Startup tasks", 24, 194, 120, 20);
    for (uint32_t i = 0; i < GF_MANAGER_MAX_TASK_CONTROLS; i++)
    {
        char label[32];
        uint32_t col = i / 8;
        uint32_t row = i % 8;
        int label_x = col == 0 ? 24 : 230;
        int edit_x = col == 0 ? 74 : 280;
        int y = 220 + (int)row * 28;

        snprintf(label, sizeof(label), "Grid %u", i + 1);
        g_manager.task_labels[i] = controls[n++] =
            add_label(hwnd, label, label_x, y + 4, 46, 20);
        g_manager.task_edits[i] = controls[n++] =
            add_text_edit(hwnd, ID_TASK_BASE + (int)i, edit_x, y, 108, 24);
        g_manager.task_f11[i] = controls[n++] =
            add_check(hwnd, "F11", ID_TASK_BASE + 100 + (int)i, edit_x + 112, y, 50, 24);
    }

    g_manager.auto_start = controls[n++] =
        add_check(hwnd, "Tu dong chay voi Windows", ID_AUTO_START, 24, 462, 230, 24);
    g_manager.auto_launch = controls[n++] =
        add_check(hwnd, "Mo task khi khoi dong", ID_AUTO_LAUNCH, 24, 492, 230, 24);
    g_manager.lock_grids = controls[n++] =
        add_check(hwnd, "Khoa cac grid", ID_LOCK_GRIDS, 24, 522, 230, 24);
    g_manager.borders = controls[n++] =
        add_check(hwnd, "Hien border", ID_BORDERS, 270, 462, 150, 24);
    g_manager.auto_tile = controls[n++] =
        add_check(hwnd, "Tu dong sap xep", ID_AUTO_TILE, 270, 492, 150, 24);

    controls[n++] = add_button(hwnd, "Apply", ID_APPLY, 24, 574, 76, 30);
    controls[n++] = add_button(hwnd, "Tile now", ID_TILE_NOW, 108, 574, 76, 30);
    controls[n++] = add_button(hwnd, "Launch", ID_LAUNCH_TASKS, 192, 574, 76, 30);
    controls[n++] = add_button(hwnd, "Hide", ID_HIDE, 276, 574, 68, 30);
    controls[n++] = add_button(hwnd, "Exit", ID_EXIT, 352, 574, 68, 30);
    g_manager.status = controls[n++] =
        CreateWindowExA(0, "STATIC", "Ready", WS_CHILD | WS_VISIBLE,
                        24, 618, 398, 22, hwnd, (HMENU)(uintptr_t)ID_STATUS,
                        GetModuleHandleA(NULL), NULL);

    for (int i = 0; i < n; i++)
        SendMessageA(controls[i], WM_SETFONT, (WPARAM)font, TRUE);
}

static LRESULT CALLBACK manager_wnd_proc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    (void)lParam;

    switch (msg)
    {
    case WM_CREATE:
        manager_create_controls(hwnd);
        manager_refresh_controls();
        return 0;

    case WM_COMMAND:
        if ((LOWORD(wParam) == ID_ROWS || LOWORD(wParam) == ID_COLS) &&
            HIWORD(wParam) == EN_CHANGE)
        {
            manager_update_task_visibility(manager_visible_task_count_from_inputs());
            return 0;
        }

        switch (LOWORD(wParam))
        {
        case ID_APPLY:
            manager_apply_settings();
            return 0;
        case ID_TILE_NOW:
            if (g_manager.wm)
            {
                gf_wm_tile_all(g_manager.wm);
                manager_set_status("All grids tiled");
            }
            return 0;
        case ID_LAUNCH_TASKS:
            manager_apply_settings();
            gf_manager_launch_configured_tasks(g_manager.wm);
            manager_set_status("Startup tasks launched");
            return 0;
        case ID_HIDE:
            ShowWindow(hwnd, SW_HIDE);
            return 0;
        case ID_EXIT:
            g_manager.running = false;
            PostQuitMessage(0);
            return 0;
        }
        break;

    case WM_CLOSE:
        ShowWindow(hwnd, SW_HIDE);
        return 0;

    case WM_DESTROY:
        g_manager.hwnd = NULL;
        return 0;
    }

    return DefWindowProcA(hwnd, msg, wParam, lParam);
}

bool gf_manager_create(gf_wm_t *wm)
{
    HINSTANCE inst = GetModuleHandleA(NULL);
    WNDCLASSA wc = {0};

    g_manager.wm = wm;
    g_manager.running = true;

    wc.lpfnWndProc = manager_wnd_proc;
    wc.hInstance = inst;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.lpszClassName = GF_MANAGER_CLASS;
    RegisterClassA(&wc);

    g_manager.hwnd = CreateWindowExA(0, GF_MANAGER_CLASS, "GridFlux Manager",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        CW_USEDEFAULT, CW_USEDEFAULT, 460, 700,
        NULL, NULL, inst, NULL);

    if (!g_manager.hwnd)
    {
        GF_LOG_ERROR("Failed to create manager window: %lu", GetLastError());
        return false;
    }

    ShowWindow(g_manager.hwnd, SW_SHOW);
    UpdateWindow(g_manager.hwnd);
    return true;
}

void gf_manager_show(void)
{
    if (g_manager.hwnd)
    {
        ShowWindow(g_manager.hwnd, SW_SHOW);
        SetForegroundWindow(g_manager.hwnd);
    }
}

bool gf_manager_is_running(void)
{
    return g_manager.running;
}

void gf_manager_destroy(void)
{
    if (g_manager.hwnd)
    {
        DestroyWindow(g_manager.hwnd);
        g_manager.hwnd = NULL;
    }
    UnregisterClassA(GF_MANAGER_CLASS, GetModuleHandleA(NULL));
    memset(&g_manager, 0, sizeof(g_manager));
}
