#include "layout.h"
#include "../utils/memory.h"
#include <string.h>

gf_err_t
gf_layout_init (gf_layout_grid_t *grid, uint32_t rows, uint32_t cols,
                const gf_rect_t *bounds, uint32_t gap)
{
    if (!grid || !bounds || rows == 0 || cols == 0)
        return GF_ERROR_INVALID_PARAMETER;

    grid->rows = rows;
    grid->cols = cols;
    grid->gap  = gap;
    grid->bounds = *bounds;
    for (uint32_t i = 0; i < GF_MAX_GRID_TRACKS; i++)
    {
        grid->row_weights[i] = 1;
        grid->col_weights[i] = 1;
    }

    size_t ncells = (size_t)rows * cols;
    grid->cells = gf_calloc (ncells, sizeof (gf_cell_t));
    if (!grid->cells)
        return GF_ERROR_MEMORY_ALLOCATION;

    gf_layout_update (grid, bounds);
    return GF_SUCCESS;
}

void
gf_layout_set_weights(gf_layout_grid_t *grid,
                      const uint32_t *row_weights,
                      const uint32_t *col_weights)
{
    if (!grid)
        return;

    for (uint32_t i = 0; i < GF_MAX_GRID_TRACKS; i++)
    {
        grid->row_weights[i] = row_weights ? row_weights[i] : 1;
        grid->col_weights[i] = col_weights ? col_weights[i] : 1;
        if (grid->row_weights[i] == 0) grid->row_weights[i] = 1;
        if (grid->col_weights[i] == 0) grid->col_weights[i] = 1;
    }

    gf_layout_update(grid, &grid->bounds);
}

gf_err_t
gf_layout_update (gf_layout_grid_t *grid, const gf_rect_t *bounds)
{
    if (!grid || !bounds)
        return GF_ERROR_INVALID_PARAMETER;

    grid->bounds = *bounds;

    uint32_t rows = grid->rows;
    uint32_t cols = grid->cols;
    for (uint32_t r = 0; r < rows; r++)
    {
        for (uint32_t c = 0; c < cols; c++)
        {
            uint32_t row_total = 0, col_total = 0;
            uint32_t row_before = 0, col_before = 0;

            for (uint32_t i = 0; i < rows; i++)
                row_total += grid->row_weights[i] ? grid->row_weights[i] : 1;
            for (uint32_t i = 0; i < cols; i++)
                col_total += grid->col_weights[i] ? grid->col_weights[i] : 1;
            for (uint32_t i = 0; i < r; i++)
                row_before += grid->row_weights[i] ? grid->row_weights[i] : 1;
            for (uint32_t i = 0; i < c; i++)
                col_before += grid->col_weights[i] ? grid->col_weights[i] : 1;

            if (row_total == 0) row_total = rows;
            if (col_total == 0) col_total = cols;

            gf_dimension_t x1 = bounds->x + (gf_dimension_t)((int64_t)col_before * bounds->w / col_total);
            gf_dimension_t x2 = bounds->x + (gf_dimension_t)((int64_t)(col_before + (grid->col_weights[c] ? grid->col_weights[c] : 1)) * bounds->w / col_total);
            gf_dimension_t y1 = bounds->y + (gf_dimension_t)((int64_t)row_before * bounds->h / row_total);
            gf_dimension_t y2 = bounds->y + (gf_dimension_t)((int64_t)(row_before + (grid->row_weights[r] ? grid->row_weights[r] : 1)) * bounds->h / row_total);
            gf_cell_t *cell = &grid->cells[r * cols + c];
            cell->rect.x = x1;
            cell->rect.y = y1;
            cell->rect.w = x2 - x1;
            cell->rect.h = y2 - y1;
            /* keep occupied flag / window pointer untouched */
        }
    }
    return GF_SUCCESS;
}

gf_err_t
gf_layout_cell_at (const gf_layout_grid_t *grid, uint32_t row, uint32_t col,
                   gf_rect_t *out)
{
    if (!grid || !out || row >= grid->rows || col >= grid->cols)
        return GF_ERROR_INVALID_PARAMETER;

    *out = grid->cells[row * grid->cols + col].rect;
    return GF_SUCCESS;
}

gf_err_t
gf_layout_assign (gf_layout_grid_t *grid, uint32_t row, uint32_t col,
                  gf_handle_t window)
{
    if (!grid || row >= grid->rows || col >= grid->cols)
        return GF_ERROR_INVALID_PARAMETER;

    gf_cell_t *cell = &grid->cells[row * grid->cols + col];
    cell->window    = window;
    cell->occupied  = (window != NULL);
    return GF_SUCCESS;
}

void
gf_layout_clear (gf_layout_grid_t *grid)
{
    if (!grid || !grid->cells)
        return;

    size_t ncells = (size_t)grid->rows * grid->cols;
    for (size_t i = 0; i < ncells; i++)
    {
        grid->cells[i].window   = NULL;
        grid->cells[i].occupied = false;
    }
}

void
gf_layout_destroy (gf_layout_grid_t *grid)
{
    if (!grid)
        return;
    gf_free (grid->cells);
    grid->cells = NULL;
    grid->rows  = 0;
    grid->cols  = 0;
}

gf_err_t
gf_layout_next_pos (const gf_layout_grid_t *grid, uint32_t *row, uint32_t *col)
{
    if (!grid || !row || !col)
        return GF_ERROR_INVALID_PARAMETER;

    for (uint32_t r = 0; r < grid->rows; r++)
    {
        for (uint32_t c = 0; c < grid->cols; c++)
        {
            if (!grid->cells[r * grid->cols + c].occupied)
            {
                *row = r;
                *col = c;
                return GF_SUCCESS;
            }
        }
    }
    return GF_ERROR_GENERIC; /* grid full */
}
