import math
import sys
from pathlib import Path

import numpy as np
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "terrain"))
from build_terrain import aspect_sector, slope_aspect, tile_name  # noqa: E402

LAT = 41.0
RES = 1 / 3600  # 1 arc-second, like the 30 m DEM


def plane(rise_east_per_m: float, rise_north_per_m: float, n: int = 20) -> tuple[np.ndarray, object]:
    transform = from_origin(22.0, LAT + n * RES, RES, RES)
    dx = RES * 111_320 * math.cos(math.radians(LAT))
    dy = RES * 111_320
    cols = np.arange(n) * dx
    rows_north = (n - 1 - np.arange(n)) * dy  # row 0 is the northern edge
    dem = rise_east_per_m * cols[None, :] + rise_north_per_m * rows_north[:, None]
    return dem, transform


def test_slope_of_known_plane():
    dem, t = plane(math.tan(math.radians(35)), 0.0)
    slope, _ = slope_aspect(dem, t, LAT)
    assert np.allclose(slope, 35.0, atol=0.01)


def test_terrain_rising_to_the_east_faces_west():
    dem, t = plane(0.5, 0.0)
    _, aspect = slope_aspect(dem, t, LAT)
    assert np.allclose(aspect, 270.0, atol=0.01)


def test_terrain_rising_to_the_south_faces_north():
    dem, t = plane(0.0, -0.5)
    _, aspect = slope_aspect(dem, t, LAT)
    assert np.allclose(aspect % 360, 0.0, atol=0.01) or np.allclose(aspect, 360.0, atol=0.01)


def test_aspect_sectors():
    angles = np.array([0, 22, 23, 90, 180, 270, 337, 338, 359])
    assert aspect_sector(angles).tolist() == [0, 0, 1, 2, 4, 6, 7, 0, 0]


def test_tile_name():
    assert tile_name(41, 22) == "N41_00_E022_00"


def test_tile_pixels_fall_inside_their_tile_range():
    from build_terrain import tile_pixel_lonlat, tile_range

    bounds = (22.05, 41.08, 22.35, 41.26)
    xs, ys = tile_range(bounds, 13)
    lon_w, lat_n = tile_pixel_lonlat(13, xs[0], ys[0])
    lon_e, lat_s = tile_pixel_lonlat(13, xs[-1], ys[-1])
    # The covering tiles extend past the bounds on every side, by less than one tile.
    assert lon_w[0] <= bounds[0] <= lon_w[-1] + 360 / 2**13
    assert lon_e[-1] >= bounds[2] and lat_n[0] >= bounds[3] and lat_s[-1] <= bounds[1]


def test_slope_index_classes():
    from build_terrain import slope_index

    assert slope_index(np.array([10, 28, 32, 37, 42, 50])).tolist() == [0, 1, 2, 3, 4, 5]


def test_tile_bounds_match_pixel_centres():
    from build_terrain import tile_bounds, tile_pixel_lonlat

    w, s, e, n = tile_bounds(12, 2299, 1534)
    lon, lat = tile_pixel_lonlat(12, 2299, 1534)
    assert w < lon[0] < lon[-1] < e and s < lat[-1] < lat[0] < n


def test_intersects():
    from build_terrain import intersects

    assert intersects((0, 0, 2, 2), (1, 1, 3, 3))
    assert not intersects((0, 0, 1, 1), (2, 2, 3, 3))


def test_mosaic_bounds_snap_to_dem_pixel_edges():
    from build_terrain import snap_to_dem_grid

    w, s, e, n = snap_to_dem_grid((20.4, 40.8, 23.1, 42.4))
    for v in (w, s, e, n):
        # Pixel edges sit half a pixel off whole arc-seconds.
        assert abs((v * 3600 + 0.5) - round(v * 3600 + 0.5)) < 1e-6
    assert w <= 20.4 and s <= 40.8 and e >= 23.1 and n >= 42.4


def test_flat_ground_has_no_shadow():
    from build_terrain import hillshade, shadow_alpha

    flat = hillshade(np.zeros((3, 3)), np.zeros((3, 3)))
    assert shadow_alpha(flat).max() == 0


def test_contours_on_a_slope():
    from build_terrain import contour_index

    # Elevation rising 10 m per pixel to the east: a minor (20 m) line every 2 px, a major (100 m) every 10 px.
    elev = np.tile(np.arange(0, 400, 10, dtype=float), (5, 1))
    idx = contour_index(elev, 20, 100)
    row = idx[2]
    assert (row == 2).sum() >= 3 and (row == 1).sum() >= 10
    assert contour_index(np.full((4, 4), 1234.0), 20, 100).max() == 0  # flat: no lines
    nan = np.full((4, 4), np.nan)
    assert contour_index(nan, 20, 100).max() == 0
