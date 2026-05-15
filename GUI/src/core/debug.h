/*
   ____  _ _            ____
  / ___|| | | __ _  ___|  _ \ _   _ _ __
  \___ \| | |/ _` |/ __| | | | | | | '_ \
   ___) | | | (_| | (__| |_| | |_| | |_) |
  |____/|_|_|\__,_|\___|____/ \__,_| .__/
                                   |_|

  Debug helpers — dumps WM state, layout, and window info.
*/

#ifndef GRIDFLUX_DEBUG_H
#define GRIDFLUX_DEBUG_H

#include "wm.h"

/* Dump full WM state to log. */
void gf_debug_dump_wm(const gf_wm_t *wm);

/* Dump a single workspace layout. */
void gf_debug_dump_workspace(const gf_wm_t *wm, gf_ws_id_t ws_id);

/* Print a human-readable rect. */
void gf_debug_print_rect(const char *label, const gf_rect_t *r);

#endif /* GRIDFLUX_DEBUG_H */