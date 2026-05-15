/*
   ____  _           _                 ____
  / ___|| |_ __ _   _| | ___  _   _   / ___|  ___ _ ____   _____ _ __
  \___ \| __/ _` | | | |/ _ \| | | | | |  _  / _ \ '__\ \ / / _ \ '__|
   ___) | || (_| | |_| | (_) | |_| | | |_| |  __/ |   \ V /  __/ |
  |____/ \__\__,_|\__, |\___/ \__, |  \____|\___|_|    \_/ \___|_|
                   |___/     |___/

  GridFlux CLI — send commands to the running WM server.
*/

#include "../ipc/ipc.h"
#include "../config/config.h"
#include "../utils/logger.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void
print_usage(const char *prog)
{
    printf("GridFlux CLI - send commands to GridFlux WM server\n\n");
    printf("Usage: %s <command> [args...]\n\n", prog);
    printf("Commands:\n");
    printf("  ping                    Check if server is running\n");
    printf("  status                  Show current WM state\n");
    printf("  tile                    Re-tile all workspaces\n");
    printf("  cycle [+|−]             Cycle focus forward/backward\n");
    printf("  switch <ws>             Switch to workspace <ws>\n");
    printf("  toggle-borders          Toggle border visibility\n");
    printf("  set-grid <rows> <cols>  Set grid dimensions\n");
    printf("  lock-grids <on|off>     Lock or unlock all grids\n");
    printf("  dump                    Dump full WM state to log\n");
    printf("  reload                  Reload config from disk\n");
    printf("\n");
}

int
main(int argc, char *argv[])
{
    if (argc < 2)
    {
        print_usage(argv[0]);
        return 1;
    }

    /* Handle --help */
    if (strcmp(argv[1], "--help") == 0 || strcmp(argv[1], "-h") == 0)
    {
        print_usage(argv[0]);
        return 0;
    }

    /* Build command string from all arguments */
    char command[GF_IPC_MSG_SIZE] = {0};
    for (int i = 1; i < argc; i++)
    {
        strncat(command, argv[i], sizeof(command) - strlen(command) - 1);
        if (i + 1 < argc)
            strncat(command, " ", sizeof(command) - strlen(command) - 1);
    }

    GF_LOG_INFO("Sending command: %s", command);

    /* Send to IPC server */
    gf_ipc_response_t resp = gf_ipc_send_command("GridFluxPipe", command);

    /* Print response */
    switch (resp.status)
    {
    case GF_IPC_SUCCESS:
        printf("OK: %s\n", resp.message[0] ? resp.message : "OK");
        return 0;

    case GF_IPC_ERROR_CONNECTION:
        fprintf(stderr, "ERROR: Could not connect to GridFlux server.\n");
        fprintf(stderr, "       Is gridflux-server running?\n");
        return 1;

    case GF_IPC_ERROR_TIMEOUT:
        fprintf(stderr, "ERROR: Connection timed out.\n");
        return 1;

    case GF_IPC_ERROR_INVALID_COMMAND:
        fprintf(stderr, "ERROR: %s\n", resp.message);
        return 1;

    default:
        fprintf(stderr, "ERROR: Unknown IPC error.\n");
        return 1;
    }
}
