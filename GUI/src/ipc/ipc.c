/*
   ____  _ _            ____
  / ___|| | | __ _  ___|  _ \ ___  __ _ _ __
  \___ \| | |/ _` |/ __| | | / __|/ _` | '__|
   ___) | | | (_| | (__| |_| \__ \ (_| | |
  |____/|_|_|\__,_|\___|____/|___/\__,_|_|

  IPC implementation — named pipe server for GridFlux
  on Windows, handling commands from CLI and editors.
*/

#include "ipc.h"
#include "../core/types.h"
#include "../utils/logger.h"
#include "../utils/memory.h"
#include <windows.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

/* ── Handle cast helpers ─────────────────────────────────────── */

static gf_ipc_handle_int_t *
ipc_upcast(gf_ipc_handle_t *handle)
{
    return (gf_ipc_handle_int_t *)(uintptr_t)handle->_priv;
}

static gf_ipc_handle_t
ipc_make_handle(gf_ipc_handle_int_t *ci)
{
    gf_ipc_handle_t h = { 0 };
    h._priv = (uintptr_t)ci;
    return h;
}

/* ── Server ─────────────────────────────────────────────────── */

gf_err_t
gf_ipc_server_create(const char *pipe_name, gf_ipc_handle_t **out_handle)
{
    if (!pipe_name || !out_handle)
        return GF_ERROR_INVALID_PARAMETER;

    char unc_path[256];
    snprintf(unc_path, sizeof(unc_path), "\\\\.\\pipe\\%s", pipe_name);

    HANDLE pipe = CreateNamedPipeA(
        unc_path,
        PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED,
        PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
        1,
        GF_IPC_MSG_SIZE,
        GF_IPC_MSG_SIZE,
        0,
        NULL
    );

    if (pipe == INVALID_HANDLE_VALUE)
    {
        GF_LOG_ERROR("CreateNamedPipe failed: %lu", GetLastError());
        return GF_ERROR_PLATFORM_ERROR;
    }

    /* Connect to client (wait up to 5 seconds) */
    OVERLAPPED ovlp = { 0 };
    ovlp.hEvent = CreateEventA(NULL, TRUE, FALSE, NULL);

    BOOL connected = ConnectNamedPipe(pipe, &ovlp);
    if (!connected && GetLastError() == ERROR_IO_PENDING)
    {
            DWORD wait = WaitForSingleObject(ovlp.hEvent, 100);
        if (wait != WAIT_OBJECT_0)
        {
            DisconnectNamedPipe(pipe);
            CloseHandle(pipe);
            if (ovlp.hEvent) CloseHandle(ovlp.hEvent);
            return GF_ERROR_TIMEOUT;
        }
    }

    if (ovlp.hEvent) CloseHandle(ovlp.hEvent);

    gf_ipc_handle_int_t *ci = gf_calloc(1, sizeof(gf_ipc_handle_int_t));
    if (!ci)
    {
        DisconnectNamedPipe(pipe);
        CloseHandle(pipe);
        return GF_ERROR_MEMORY_ALLOCATION;
    }

    ci->pipe = pipe;
    ci->is_server = true;
    strncpy(ci->name, pipe_name, sizeof(ci->name) - 1);

    *out_handle = gf_calloc(1, sizeof(gf_ipc_handle_t));
    if (!*out_handle)
    {
        gf_free(ci);
        DisconnectNamedPipe(pipe);
        CloseHandle(pipe);
        return GF_ERROR_MEMORY_ALLOCATION;
    }

    **out_handle = ipc_make_handle(ci);
    GF_LOG_INFO("IPC server started: %s", pipe_name);
    return GF_SUCCESS;
}

/* ── Client ─────────────────────────────────────────────────── */

gf_err_t
gf_ipc_client_connect(const char *pipe_name, gf_ipc_handle_t **out_handle)
{
    if (!pipe_name || !out_handle)
        return GF_ERROR_INVALID_PARAMETER;

    char unc_path[256];
    snprintf(unc_path, sizeof(unc_path), "\\\\.\\pipe\\%s", pipe_name);

    /* Retry loop — pipe may not be ready yet */
    HANDLE pipe = INVALID_HANDLE_VALUE;
    for (int attempt = 0; attempt < 10; attempt++)
    {
        pipe = CreateFileA(unc_path,
                           GENERIC_READ | GENERIC_WRITE,
                           0, NULL, OPEN_EXISTING,
                           FILE_FLAG_OVERLAPPED, NULL);

        if (pipe != INVALID_HANDLE_VALUE)
            break;

        if (GetLastError() != ERROR_PIPE_BUSY)
        {
            GF_LOG_ERROR("Cannot open pipe %s: %lu", pipe_name, GetLastError());
            return GF_ERROR_CONNECTION;
        }

        if (!WaitNamedPipeA(unc_path, 1000))
        {
            GF_LOG_ERROR("WaitNamedPipe timeout");
            return GF_ERROR_TIMEOUT;
        }
    }

    if (pipe == INVALID_HANDLE_VALUE)
        return GF_ERROR_CONNECTION;

    /* Set message mode */
    DWORD mode = PIPE_READMODE_MESSAGE;
    SetNamedPipeHandleState(pipe, &mode, NULL, NULL);

    gf_ipc_handle_int_t *ci = gf_calloc(1, sizeof(gf_ipc_handle_int_t));
    if (!ci)
    {
        CloseHandle(pipe);
        return GF_ERROR_MEMORY_ALLOCATION;
    }

    ci->pipe = pipe;
    ci->is_server = false;
    strncpy(ci->name, pipe_name, sizeof(ci->name) - 1);

    *out_handle = gf_calloc(1, sizeof(gf_ipc_handle_t));
    if (!*out_handle)
    {
        gf_free(ci);
        CloseHandle(pipe);
        return GF_ERROR_MEMORY_ALLOCATION;
    }

    **out_handle = ipc_make_handle(ci);
    GF_LOG_INFO("IPC client connected: %s", pipe_name);
    return GF_SUCCESS;
}

/* ── Read / Write ───────────────────────────────────────────── */

gf_ipc_response_t
gf_ipc_read(gf_ipc_handle_t *handle)
{
    gf_ipc_response_t resp = { GF_IPC_ERROR_CONNECTION, { 0 } };

    if (!handle)
        return resp;

    gf_ipc_handle_int_t *ci = ipc_upcast(handle);
    if (!ci || ci->pipe == INVALID_HANDLE_VALUE)
        return resp;

    char buf[GF_IPC_MSG_SIZE] = { 0 };
    DWORD read = 0;

    OVERLAPPED ovlp = { 0 };
    ovlp.hEvent = CreateEventA(NULL, TRUE, FALSE, NULL);

    if (!ReadFile(ci->pipe, buf, sizeof(buf) - 1, &read, &ovlp))
    {
        if (GetLastError() == ERROR_IO_PENDING)
        {
            WaitForSingleObject(ovlp.hEvent, 5000);
            GetOverlappedResult(ci->pipe, &ovlp, &read, FALSE);
        }
        else
        {
            resp.status = GF_IPC_ERROR_CONNECTION;
            if (ovlp.hEvent) CloseHandle(ovlp.hEvent);
            return resp;
        }
    }

    if (ovlp.hEvent) CloseHandle(ovlp.hEvent);

    if (read > 0)
    {
        buf[read] = '\0';
        resp.status = GF_IPC_SUCCESS;
        strncpy(resp.message, buf, sizeof(resp.message) - 1);
        GF_LOG_DEBUG("IPC read %lu bytes: %s", read, buf);
    }

    return resp;
}

gf_err_t
gf_ipc_write(gf_ipc_handle_t *handle, const char *message)
{
    if (!handle || !message)
        return GF_ERROR_INVALID_PARAMETER;

    gf_ipc_handle_int_t *ci = ipc_upcast(handle);
    if (!ci || ci->pipe == INVALID_HANDLE_VALUE)
        return GF_ERROR_INVALID_PARAMETER;

    DWORD written = 0;
    size_t len = strlen(message);
    if (len >= GF_IPC_MSG_SIZE)
        len = GF_IPC_MSG_SIZE - 1;

    OVERLAPPED ovlp = { 0 };
    ovlp.hEvent = CreateEventA(NULL, TRUE, FALSE, NULL);

    if (!WriteFile(ci->pipe, message, (DWORD)len, &written, &ovlp))
    {
        if (GetLastError() == ERROR_IO_PENDING)
        {
            WaitForSingleObject(ovlp.hEvent, 3000);
            GetOverlappedResult(ci->pipe, &ovlp, &written, FALSE);
        }
        else
        {
            if (ovlp.hEvent) CloseHandle(ovlp.hEvent);
            return GF_ERROR_PLATFORM_ERROR;
        }
    }

    if (ovlp.hEvent) CloseHandle(ovlp.hEvent);
    GF_LOG_DEBUG("IPC wrote %lu bytes: %s", written, message);
    return GF_SUCCESS;
}

/* ── IPC response helpers ───────────────────────────────────── */

gf_ipc_response_t
gf_ipc_ok(const char *detail)
{
    gf_ipc_response_t resp = { GF_IPC_SUCCESS, { 0 } };
    if (detail)
        strncpy(resp.message, detail, sizeof(resp.message) - 1);
    else
        strncpy(resp.message, "OK", sizeof(resp.message) - 1);
    return resp;
}

gf_ipc_response_t
gf_ipc_error(const char *detail)
{
    gf_ipc_response_t resp = { GF_IPC_ERROR_GENERIC, { 0 } };
    if (detail)
        strncpy(resp.message, detail, sizeof(resp.message) - 1);
    else
        strncpy(resp.message, "ERROR", sizeof(resp.message) - 1);
    return resp;
}

/* ── Send command (client utility) ──────────────────────────── */

gf_ipc_response_t
gf_ipc_send_command(const char *pipe_name, const char *command)
{
    gf_ipc_response_t resp;
    gf_ipc_handle_t *handle = NULL;

    gf_err_t rc = gf_ipc_client_connect(pipe_name, &handle);
    if (rc != GF_SUCCESS)
    {
        resp = gf_ipc_error("Connection failed");
        return resp;
    }

    rc = gf_ipc_write(handle, command);
    if (rc != GF_SUCCESS)
    {
        resp = gf_ipc_error("Write failed");
        gf_ipc_close(handle);
        return resp;
    }

    resp = gf_ipc_read(handle);
    gf_ipc_close(handle);
    return resp;
}

/* ── Close ──────────────────────────────────────────────────── */

void
gf_ipc_close(gf_ipc_handle_t *handle)
{
    if (!handle) return;

    gf_ipc_handle_int_t *ci = ipc_upcast(handle);
    if (ci)
    {
        if (ci->pipe != INVALID_HANDLE_VALUE)
        {
            if (ci->is_server)
                DisconnectNamedPipe(ci->pipe);
            CloseHandle(ci->pipe);
        }
        gf_free(ci);
    }
    gf_free(handle);
}
