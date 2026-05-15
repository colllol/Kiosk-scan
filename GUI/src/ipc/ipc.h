#ifndef GRIDFLUX_IPC_H
#define GRIDFLUX_IPC_H

#include "../core/types.h"

/* ── IPC Handle (concrete, internal to this translation unit) ── */
struct gf_ipc_handle_int_t {
    uintptr_t handle;       /* platform handle (HANDLE on Win32) */
    void     *pipe;         /* named-pipe handle used by Win32 code */
    bool      is_server;
    char      name[128];
};
typedef struct gf_ipc_handle_int_t gf_ipc_handle_int_t;

/* Public opaque type — defined in types.h.
   Concrete internals below are private to this TU. */

/* ── Server API ─────────────────────────────────────────────── */
gf_err_t   gf_ipc_server_create(const char *pipe_name,
                                 gf_ipc_handle_t **out_handle);

/* ── Client API ─────────────────────────────────────────────── */
gf_err_t   gf_ipc_client_connect(const char *pipe_name,
                                  gf_ipc_handle_t **out_handle);
gf_ipc_response_t gf_ipc_read(gf_ipc_handle_t *handle);
gf_err_t   gf_ipc_write(gf_ipc_handle_t *handle, const char *message);

/* ── Response helpers ───────────────────────────────────────── */
gf_ipc_response_t gf_ipc_ok(const char *detail);
gf_ipc_response_t gf_ipc_error(const char *detail);
gf_ipc_response_t gf_ipc_send_command(const char *pipe_name,
                                        const char *command);

/* ── Close ──────────────────────────────────────────────────── */
void       gf_ipc_close(gf_ipc_handle_t *handle);

#endif /* GRIDFLUX_IPC_H */
