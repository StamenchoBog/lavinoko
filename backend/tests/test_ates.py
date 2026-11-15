import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ates"))
from prepare_inputs import CELL_M, block_mean_percent, utm_grid, worldcover_tiles  # noqa: E402


def test_canopy_is_the_share_of_tree_cells_per_block():
    trees = np.zeros((6, 6), dtype="uint8")
    trees[:3, :3] = 1  # one full block of trees
    trees[3, 3] = 1  # one tree cell in the last block
    np.testing.assert_allclose(block_mean_percent(trees), [[100, 0], [0, 100 / 9]], rtol=1e-6)


def test_worldcover_tiles_cover_a_tile_boundary():
    assert worldcover_tiles((22.12, 41.12, 22.28, 41.22)) == ["N39E021"]  # Kožuf
    assert worldcover_tiles((20.77, 41.96, 20.92, 42.04)) == ["N39E018", "N42E018"]  # Popova Šapka


def test_utm_grid_has_whole_cells_and_includes_the_margin():
    t, w, h = utm_grid((22.12, 41.12, 22.28, 41.22))
    assert t.a == CELL_M and -t.e == CELL_M
    assert t.c % CELL_M == 0 and t.f % CELL_M == 0
    # ~13.4 km x 11.1 km detail area plus 2 km on each side
    assert 17_000 < w * CELL_M < 18_500 and 15_000 < h * CELL_M < 16_000
