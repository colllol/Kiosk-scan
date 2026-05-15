/*
   ____  _ _     _
  / ___|| | | __| | ___  ___
  \___ \| | |/ _` |/ _ \/ __|
   ___) | | | (_| |  __/\__ \
  |____/|_|_|\__,_|\___||___/

  GridFlux configuration — persisted to JSON, loaded at startup.
*/

#ifndef GRIDFLUX_CONFIG_H
#define GRIDFLUX_CONFIG_H

#include "core/types.h"

/* ── Config file location (stored in %APPDATA%/GridFlux/config.json) ── */

const char *gf_config_get_path(void);

/* ── Config access ──────────────────────────────────────────── */

gf_err_t  gf_config_load   (const char *path, gf_config_t **out_cfg);
gf_err_t  gf_config_save   (const char *path, const gf_config_t *cfg);
gf_err_t  gf_config_default(gf_config_t **out_cfg);
void      gf_config_free   (gf_config_t *cfg);

#endif /* GRIDFLUX_CONFIG_H */