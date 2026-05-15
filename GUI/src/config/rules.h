/* ══════════════════════════════════════════════════════════════
   Rules
   ══════════════════════════════════════════════════════════════ */

#ifndef GRIDFLUX_RULES_H
#define GRIDFLUX_RULES_H

#include "core/types.h"

struct gf_config_t;

/* Add a rule: wm_class → workspace_id. */
gf_err_t gf_rules_add    (struct gf_config_t *cfg, const char *wm_class, int workspace_id);

/* Remove a rule by wm_class. Returns GF_SUCCESS even if not found. */
gf_err_t gf_rules_remove (struct gf_config_t *cfg, const char *wm_class);

/* Find rule for a wm_class. Returns NULL if not found. */
const gf_window_rule_t *gf_rules_find (const struct gf_config_t *cfg, const char *wm_class);

/* Count rules */
uint32_t gf_rules_count (const struct gf_config_t *cfg);

/* Check if a window class matches any rule, and return the workspace.
   Returns true and sets *ws if matched. */
bool     gf_rules_match  (const struct gf_config_t *cfg, const char *wm_class,
                          gf_ws_id_t *ws);

#endif /* GRIDFLUX_RULES_H */