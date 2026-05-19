/*
   ____  _                ____  _           _
  / ___|| |_ _ __ _   _  |  _ \(_)_ __   __| | ___ _ __
  \___ \| __| '__| | | | | | | | | '_ \ / _` |/ _ \ '__|
   ___) | |_| |  | |_| | | |_| | | | | | (_| |  __/ |
  |____/ \__|_|   \__, | |____/|_|_| |_|\__,_|\___|_|
                   |___/

  GridFlux WM server — entry point, main loop, IPC server.
*/

#include "../core/wm.h"
#include "../core/wm_internal.h"
#include "../core/events.h"
#include "../ipc/ipc.h"
#include "../ipc/ipc_handlers.h"
#include "../config/config.h"
#include "../utils/logger.h"
#include "../platform/platform.h"
#include "../manager/manager.h"
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <string.h>
#include <windows.h>

static volatile bool g_running = true;

static void
signal_handler(int sig)
{
    (void)sig;
    g_running = false;
}

static bool file_exists(const char *path)
{
    DWORD attr = GetFileAttributesA(path);
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY);
}

static bool dir_exists(const char *path)
{
    DWORD attr = GetFileAttributesA(path);
    return attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY);
}

static void dirname_in_place(char *path)
{
    char *last = strrchr(path, '\\');
    if (!last)
        last = strrchr(path, '/');
    if (last)
        *last = '\0';
}

static bool find_app_root(char *out_dir, size_t out_size)
{
    char dir[MAX_PATH] = {0};
    char backend_main[MAX_PATH] = {0};
    char frontend_index[MAX_PATH] = {0};

    if (!GetModuleFileNameA(NULL, dir, sizeof(dir)))
        return false;
    dirname_in_place(dir);

    for (int i = 0; i < 8; i++)
    {
        snprintf(backend_main, sizeof(backend_main), "%s\\backend\\main.py", dir);
        snprintf(frontend_index, sizeof(frontend_index), "%s\\frontend\\index.html", dir);
        if (file_exists(backend_main) && file_exists(frontend_index))
        {
            strncpy(out_dir, dir, out_size - 1);
            out_dir[out_size - 1] = '\0';
            return true;
        }
        dirname_in_place(dir);
        if (!dir[0])
            return false;
    }

    return false;
}

static void start_python_script_hidden(const char *working_dir, const char *script_path)
{
    char exe[MAX_PATH] = {0};
    char params[MAX_PATH * 2] = {0};
    SHELLEXECUTEINFOA sei = {0};

    snprintf(exe, sizeof(exe), "%s\\venv\\Scripts\\pythonw.exe", working_dir);
    if (!file_exists(exe))
        strncpy(exe, "pythonw.exe", sizeof(exe) - 1);

    snprintf(params, sizeof(params), "\"%s\"", script_path);

    sei.cbSize = sizeof(sei);
    sei.lpVerb = "open";
    sei.lpFile = exe;
    sei.lpParameters = params;
    sei.lpDirectory = working_dir;
    sei.nShow = SW_HIDE;

    if (!ShellExecuteExA(&sei))
    {
        sei.lpFile = "python.exe";
        ShellExecuteExA(&sei);
    }
}

static void start_backend_hidden(const char *app_root)
{
    char backend_dir[MAX_PATH] = {0};
    char main_py[MAX_PATH] = {0};

    snprintf(backend_dir, sizeof(backend_dir), "%s\\backend", app_root);
    snprintf(main_py, sizeof(main_py), "%s\\main.py", backend_dir);
    if (!dir_exists(backend_dir) || !file_exists(main_py))
        return;

    start_python_script_hidden(backend_dir, main_py);
}

static void start_frontend_hidden(const char *app_root)
{
    char frontend_dir[MAX_PATH] = {0};
    SHELLEXECUTEINFOA sei = {0};

    snprintf(frontend_dir, sizeof(frontend_dir), "%s\\frontend", app_root);
    if (!dir_exists(frontend_dir))
        return;

    sei.cbSize = sizeof(sei);
    sei.lpVerb = "open";
    sei.lpFile = "python.exe";
    sei.lpParameters = "-m http.server 3000 --bind 127.0.0.1";
    sei.lpDirectory = frontend_dir;
    sei.nShow = SW_HIDE;

    if (!ShellExecuteExA(&sei))
    {
        sei.lpFile = "py.exe";
        ShellExecuteExA(&sei);
    }
}

static void start_kiosk_services_hidden(void)
{
    char app_root[MAX_PATH] = {0};

    if (!find_app_root(app_root, sizeof(app_root)))
        return;

    start_backend_hidden(app_root);
    start_frontend_hidden(app_root);
    Sleep(1500);
}

int
server_main(int argc, char *argv[])
{
    (void)argc; (void)argv;

    HANDLE instance_mutex = CreateMutexA(NULL, TRUE, "Local\\GridFluxSingleton");
    if (!instance_mutex)
        return 0;
    if (GetLastError() == ERROR_ALREADY_EXISTS)
    {
        CloseHandle(instance_mutex);
        return 0;
    }

    ShowWindow(GetConsoleWindow(), SW_HIDE);
    start_kiosk_services_hidden();
    printf("GridFlux WM Server starting...\n");

    /* Setup logging */
    gf_log_set_level(GF_LOG_INFO);

    /* Setup signal handlers */
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    /* Load config */
    const char *path = gf_config_get_path();

    gf_config_t *cfg = NULL;
    if (gf_config_load(path, &cfg) != GF_SUCCESS)
    {
        GF_LOG_WARN("No existing config, using defaults");
        if (gf_config_default(&cfg) != GF_SUCCESS)
        {
            fprintf(stderr, "Fatal: failed to create default config\n");
            ReleaseMutex(instance_mutex);
            CloseHandle(instance_mutex);
            return 1;
        }
        gf_config_save(path, cfg);
    }

    /* Create platform */
    gf_platform_t *platform = &gf_platform_win32;

    /* Create WM */
    gf_wm_t *wm = NULL;
    if (gf_wm_create(&wm) != GF_SUCCESS)
    {
        fprintf(stderr, "Fatal: failed to create WM\n");
        gf_config_free(cfg);
        ReleaseMutex(instance_mutex);
        CloseHandle(instance_mutex);
        return 1;
    }

    /* Initialize WM */
    if (gf_wm_init(wm, platform, cfg) != GF_SUCCESS)
    {
        fprintf(stderr, "Fatal: WM init failed\n");
        gf_wm_destroy(wm);
        gf_config_free(cfg);
        ReleaseMutex(instance_mutex);
        CloseHandle(instance_mutex);
        return 1;
    }

    /* Start IPC server */
    gf_ipc_handle_t *ipc = NULL;
    if (gf_ipc_server_create("GridFluxPipe", &ipc) == GF_SUCCESS)
    {
        wm->ipc_running = true;
        wm->ipc_handle = *ipc;
        GF_LOG_INFO("IPC server ready");
    }
    else
    {
        GF_LOG_WARN("IPC server failed to start (continuing without IPC)");
    }

    /* Scan for existing windows */
    gf_wm_rescan_windows(wm);

    /* Initial tile */
    gf_wm_tile_all(wm);

    /* Open the desktop manager when gridflux.exe is started. */
    if (!gf_manager_create(wm))
    {
        GF_LOG_WARN("Manager window failed to open; server will continue");
    }

    if (wm->config->auto_launch_tasks)
    {
        gf_manager_launch_configured_tasks(wm);
    }

    /* Main loop */
    DWORD last_auto_tile = GetTickCount();
    DWORD last_task_check = GetTickCount();
    while (g_running && gf_manager_is_running())
    {
        /* Pump platform events */
        if (!gf_wm_pump_events(wm))
        {
            g_running = false;
            break;
        }

        /* Handle IPC commands */
        if (wm->ipc_running)
        {
            gf_ipc_response_t resp = gf_ipc_read(&wm->ipc_handle);
            if (resp.status == GF_IPC_SUCCESS && resp.message[0] != '\0')
            {
                gf_ipc_response_t result = gf_ipc_dispatch(wm, resp.message);
                if (result.message[0] != '\0')
                {
                    /* Write response back through pipe (simplified) */
                    gf_ipc_write(&wm->ipc_handle, result.message);
                }
            }
        }

        if (wm->config->auto_tile && !wm->config->lock_grids)
        {
            DWORD now = GetTickCount();
            if (now - last_auto_tile >= 500)
            {
                gf_wm_tile_all(wm);
                last_auto_tile = now;
            }
        }

        {
            DWORD now = GetTickCount();
            if (now - last_task_check >= 1000)
            {
                gf_manager_relaunch_missing_tasks(wm);
                last_task_check = now;
            }
        }

        /* Idle sleep to avoid busy-wait */
        Sleep(16);
    }

    /* Cleanup */
    GF_LOG_INFO("Shutting down GridFlux server");
    if (wm) gf_wm_destroy(wm);
    if (ipc) gf_ipc_close(ipc);
    gf_config_free(cfg);
    gf_manager_destroy();
    ReleaseMutex(instance_mutex);
    CloseHandle(instance_mutex);

    printf("GridFlux WM Server stopped.\n");
    return 0;
}

int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;
    return server_main(argc, argv);
}
