/*
   ____  _____     _           _
  / ___|| ____|_ _| | ___  ___| |_
  \___ \|  _| | || |/ _ \/ __| __|
   ___) | |___| || |  __/\__ \ |_
  |____/|_____|_| |\___||___/\__|
               |__/

  Resize interaction — smooth resize during user drag,
  final snap to grid on release.
*/

#ifndef GRIDFLUX_RESIZE_H
#define GRIDFLUX_RESIZE_H

#include "../core/types.h"
#include "wm.h"

/* Begin tracking a resize on the given window. */
gf_err_t gf_resize_begin(gf_wm_t *wm, gf_handle_t window);

/* Update tracked resize state (called during drag). */
gf_err_t gf_resize_update(gf_wm_t *wm, const gf_resize_event_t *ev);

/* Finalize resize — snap to grid cell. */
gf_err_t gf_resize_end(gf_wm_t *wm, const gf_resize_event_t *ev);

#endif /* GRIDFLUX_RESIZE_H */