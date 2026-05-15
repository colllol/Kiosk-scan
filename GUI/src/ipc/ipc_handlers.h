/*
   ____        _             _
  |  _ \ _   _| | ___  _   _| | __ _| |_ ___
  | | | | | | | |/ _ \| | | | |/ _` | __/ _ \
  | |_| | |_| | | (_) | |_| | | (_| | ||  __/
  |____/ \__,_|_|\___/ \__,_|_|\__,_|\__\___|

  IPC command handlers — parses incoming commands and
  dispatches to the appropriate WM function.
*/

#ifndef GRIDFLUX_IPC_HANDLERS_H
#define GRIDFLUX_IPC_HANDLERS_H

#include "ipc.h"

/* Forward-declare WM type to avoid circular dependency */
typedef struct gf_wm_t gf_wm_t;

/* Main IPC dispatch — parses a command string and calls the
 * appropriate handler. Returns a response struct. */
gf_ipc_response_t gf_ipc_dispatch(gf_wm_t *wm, const char *command);

#endif /* GRIDFLUX_IPC_HANDLERS_H */