#include "rules.h"
#include "../utils/logger.h"
#include "../utils/memory.h"
#include <string.h>

gf_err_t
gf_rules_add(gf_config_t *cfg, const char *wm_class, int workspace_id)
{
    if (!cfg || !wm_class || wm_class[0] == '\0')
        return GF_ERROR_INVALID_PARAMETER;

    if ((uint32_t)workspace_id >= cfg->workspace_count)
        return GF_ERROR_INVALID_PARAMETER;

    /* Check existing */
    for (uint32_t i = 0; i < cfg->window_rules_count; i++) {
        if (strcmp(cfg->window_rules[i].wm_class, wm_class) == 0) {
            /* Update existing rule */
            if (cfg->window_rules[i].workspace_id == workspace_id)
                return GF_SUCCESS; /* Already same target */

            /* Check workspace not full */
            uint32_t count = 0;
            for (uint32_t j = 0; j < cfg->window_rules_count; j++) {
                if (cfg->window_rules[j].workspace_id == workspace_id)
                    count++;
            }
            if (count >= cfg->workspace_count)
                return GF_ERROR_WORKSPACE_FULL;

            cfg->window_rules[i].workspace_id = workspace_id;
            return GF_SUCCESS;
        }
    }

    if (cfg->window_rules_count >= GF_MAX_RULES)
        return GF_ERROR_GENERIC;

    /* Check workspace capacity */
    uint32_t count = 0;
    for (uint32_t j = 0; j < cfg->window_rules_count; j++) {
        if (cfg->window_rules[j].workspace_id == (gf_ws_id_t)workspace_id)
            count++;
    }

    strncpy(cfg->window_rules[cfg->window_rules_count].wm_class,
            wm_class, 127);
    cfg->window_rules[cfg->window_rules_count].wm_class[127] = '\0';
    cfg->window_rules[cfg->window_rules_count].workspace_id = workspace_id;
    cfg->window_rules_count++;

    GF_LOG_INFO("Rule added: %s -> workspace %d", wm_class, workspace_id);
    return GF_SUCCESS;
}

gf_err_t
gf_rules_remove(gf_config_t *cfg, const char *wm_class)
{
    if (!cfg || !wm_class)
        return GF_ERROR_INVALID_PARAMETER;

    for (uint32_t i = 0; i < cfg->window_rules_count; i++) {
        if (strcmp(cfg->window_rules[i].wm_class, wm_class) == 0) {
            /* Shift remaining */
            for (uint32_t j = i; j < cfg->window_rules_count - 1; j++)
                cfg->window_rules[j] = cfg->window_rules[j + 1];

            cfg->window_rules_count--;
            GF_LOG_INFO("Rule removed: %s", wm_class);
            return GF_SUCCESS;
        }
    }

    return GF_SUCCESS; /* Not found is not an error */
}

const gf_window_rule_t *
gf_rules_find(const gf_config_t *cfg, const char *wm_class)
{
    if (!cfg || !wm_class)
        return NULL;

    for (uint32_t i = 0; i < cfg->window_rules_count; i++) {
        if (strcmp(cfg->window_rules[i].wm_class, wm_class) == 0)
            return &cfg->window_rules[i];
    }
    return NULL;
}

uint32_t
gf_rules_count(const gf_config_t *cfg)
{
    return cfg ? cfg->window_rules_count : 0;
}

bool
gf_rules_match(const gf_config_t *cfg, const char *wm_class, gf_ws_id_t *ws)
{
    if (!cfg || !wm_class || !ws)
        return false;

    const gf_window_rule_t *rule = gf_rules_find(cfg, wm_class);
    if (rule) {
        *ws = (gf_ws_id_t)rule->workspace_id;
        return true;
    }
    return false;
}