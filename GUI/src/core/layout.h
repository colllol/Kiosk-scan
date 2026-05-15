#ifndef GRIDFLUX_LAYOUT_H
#define GRIDFLUX_LAYOUT_H

#include "types.h"

/*
 * Layout engine — divides a screen rectangle into a rows×cols grid
 * and assigns windows to cells with configurable gaps.
 */

/* Initialize a grid layout within the given screen bounds */
gf_err_t  gf_layout_init   (gf_layout_grid_t *grid, uint32_t rows, uint32_t cols,
                             const gf_rect_t *bounds, uint32_t gap);

void      gf_layout_set_weights(gf_layout_grid_t *grid,
                                const uint32_t *row_weights,
                                const uint32_t *col_weights);

/* Recalculate cell rectangles (call after bounds change) */
gf_err_t  gf_layout_update  (gf_layout_grid_t *grid, const gf_rect_t *bounds);

/* Get cell rectangle for (row, col). Returns GF_SUCCESS if valid. */
gf_err_t  gf_layout_cell_at (const gf_layout_grid_t *grid, uint32_t row, uint32_t col,
                             gf_rect_t *out);

/* Assign a window handle to a cell */
gf_err_t  gf_layout_assign  (gf_layout_grid_t *grid, uint32_t row, uint32_t col,
                             gf_handle_t window);

/* Clear all assignments without changing geometry */
void      gf_layout_clear   (gf_layout_grid_t *grid);

/* Free grid memory */
void      gf_layout_destroy (gf_layout_grid_t *grid);

/* Compute next layout position for auto-placement (row-major order) */
gf_err_t  gf_layout_next_pos(const gf_layout_grid_t *grid, uint32_t *row, uint32_t *col);

#endif /* GRIDFLUX_LAYOUT_H */
