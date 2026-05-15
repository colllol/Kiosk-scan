#ifndef GRIDFLUX_MANAGER_H
#define GRIDFLUX_MANAGER_H

#include "../core/wm.h"
#include <stdbool.h>

bool gf_manager_create(gf_wm_t *wm);
void gf_manager_show(void);
bool gf_manager_is_running(void);
void gf_manager_launch_configured_tasks(gf_wm_t *wm);
void gf_manager_destroy(void);

#endif /* GRIDFLUX_MANAGER_H */
