/*
   ____  _ _            _
  / ___|| | | __ _  ___| | _____
  \___ \| | |/ _` |/ __| |/ / __|
   ___) | | | (_| | (__|   <\__ \
  |____/|_|_|\__,_|\___|_|\_\___/

  WM Event processing — polls platform events, dispatches to
  the appropriate WM subsystem (focus, resize, border, workspace).
*/

#ifndef GRIDFLUX_EVENTS_H
#define GRIDFLUX_EVENTS_H

#include "../core/types.h"
#include "wm.h"

/*
 * Main event pump. Returns true if the WM should keep running,
 * false if it should quit.
 */
bool gf_wm_pump_events(gf_wm_t *wm);

/* Process a single resize event (called from pump). */
void gf_wm_process_resize(gf_wm_t *wm, const gf_resize_event_t *ev);

/* Re-scan windows and add newly appeared ones to the active workspace. */
void gf_wm_rescan_windows(gf_wm_t *wm);

#endif /* GRIDFLUX_EVENTS_H */