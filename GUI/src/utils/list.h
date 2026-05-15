#ifndef GRIDFLUX_LIST_H
#define GRIDFLUX_LIST_H

#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>

/* Generic singly-linked list node */
typedef struct gf_list_node {
    void                *data;
    struct gf_list_node *next;
} gf_list_node_t;

/* Generic singly-linked list */
typedef struct {
    gf_list_node_t *head;
    gf_list_node_t *tail;
    size_t          length;
} gf_list_t;

gf_list_t *gf_list_create       (void);
void       gf_list_destroy      (gf_list_t *list, void (*free_fn)(void *));
void       gf_list_push         (gf_list_t *list, void *data);
void      *gf_list_pop          (gf_list_t *list);
void      *gf_list_peek         (const gf_list_t *list);
size_t     gf_list_length       (const gf_list_t *list);
bool       gf_list_is_empty     (const gf_list_t *list);
void       gf_list_clear        (gf_list_t *list, void (*free_fn)(void *));

/* Iterator macros */
#define gf_list_for_each(list, node) \
    for (node = (list)->head; node != NULL; node = node->next)

#define gf_list_for_each_safe(list, node, tmp) \
    for (node = (list)->head; node != NULL && (tmp = node->next, true); node = tmp)

#endif /* GRIDFLUX_LIST_H */