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
#include <windows.h>

static volatile bool g_running = true;

static void
signal_handler(int sig)
{
    (void)sig;
    g_running = false;
}

int
server_main(int argc, char *argv[])
{
    (void)argc; (void)argv;

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
        return 1;
    }

    /* Initialize WM */
    if (gf_wm_init(wm, platform, cfg) != GF_SUCCESS)
    {
        fprintf(stderr, "Fatal: WM init failed\n");
        gf_wm_destroy(wm);
        gf_config_free(cfg);
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

        /* Idle sleep to avoid busy-wait */
        Sleep(16);
    }

    /* Cleanup */
    GF_LOG_INFO("Shutting down GridFlux server");
    if (wm) gf_wm_destroy(wm);
    if (ipc) gf_ipc_close(ipc);
    gf_config_free(cfg);
    gf_manager_destroy();

    printf("GridFlux WM Server stopped.\n");
    return 0;
}

int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;
    return server_main(argc, argv);
}
