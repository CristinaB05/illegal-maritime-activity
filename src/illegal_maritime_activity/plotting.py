"""Maps and charts for the dark-period analysis.

All maps use ETRS89 / UTM zone 32N (EPSG:25832), the standard projection for
Denmark. A land outline for the North Sea and Baltic (Natural Earth, public
domain) ships with the repository. Danish waters (``dk.json``) and submarine
cables (``cable-geo.json``) are optional layers: see ``data/README.md``.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from shapely.geometry import LineString, Point

from .preprocessing import TIMESTAMP, valid_position

# Resolved from this file so the paths work from any working directory.
EXTERNAL_DIR = Path(__file__).resolve().parents[2] / "data" / "external"

CRS_WGS84 = "EPSG:4326"   # latitude / longitude, as reported by AIS
CRS_DK = "EPSG:25832"     # ETRS89 / UTM 32N, metres

# Colours are fixed per meaning so they stay the same across all figures.
COLORS = {
    "off": "#2a78d6", "on": "#eb6834", "path": "#8a8984",
    "sea": "#eef4fb", "land": "#e4e3df", "coast": "#c3c2b7",
    "water": "#cfe0f3", "cable": "#52514e", "grid": "#e4e3df",
}
FLAG_COLORS = {"Danish": "#2a78d6", "Russian": "#eb6834",
               "FoC": "#1baf7a", "Other": "#eda100"}


# --------------------------------------------------------------------------
# Base layers
# --------------------------------------------------------------------------

def load_land(external_dir: str | Path = EXTERNAL_DIR) -> gpd.GeoDataFrame | None:
    """Load the bundled land outline, or return None if it is missing."""
    path = Path(external_dir) / "land_north_sea_baltic.geojson"
    return gpd.read_file(path).to_crs(CRS_DK) if path.exists() else None


def load_basemaps(external_dir: str | Path = EXTERNAL_DIR):
    """Load the optional Danish waters and submarine cable layers.

    Returns
    -------
    tuple
        ``(waters, cables)``, each a GeoDataFrame or None when the file is
        not present. When both exist, only cables that cross Danish waters
        are kept.
    """
    external_dir = Path(external_dir)
    waters = cables = None
    if (external_dir / "dk.json").exists():
        waters = gpd.read_file(external_dir / "dk.json").to_crs(CRS_DK)
    if (external_dir / "cable-geo.json").exists():
        cables = gpd.read_file(external_dir / "cable-geo.json").to_crs(CRS_DK)
        cables = cables[cables.geometry.is_valid]
        if waters is not None:
            cables = gpd.sjoin(cables, waters, how="inner", predicate="intersects")
    return waters, cables


def to_points(df: pd.DataFrame, lat: str = "Latitude",
              lon: str = "Longitude") -> gpd.GeoDataFrame:
    """Turn a frame with latitude/longitude columns into projected points."""
    geometry = [Point(xy) for xy in zip(df[lon], df[lat])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs=CRS_WGS84).to_crs(CRS_DK)


def _map_axes(bounds, waters=None, cables=None, figsize=(10, 7), pad=0.05):
    """Create a map with land, optional layers, zoomed to ``bounds``.

    ``bounds`` is ``(minx, miny, maxx, maxy)`` in the projected CRS; a small
    margin (``pad``, as a share of the extent) is added on every side.
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_facecolor(COLORS["sea"])

    land = load_land()
    if land is not None:
        land.plot(ax=ax, color=COLORS["land"], edgecolor=COLORS["coast"],
                  linewidth=0.4)
    if waters is not None:
        waters.plot(ax=ax, color=COLORS["water"], edgecolor="none", alpha=0.6)
    if cables is not None:
        cables.plot(ax=ax, color=COLORS["cable"], linewidth=0.6, alpha=0.6)

    minx, miny, maxx, maxy = bounds
    dx, dy = (maxx - minx) * pad, (maxy - miny) * pad
    ax.set(xlim=(minx - dx, maxx + dx), ylim=(miny - dy, maxy + dy))
    ax.set_aspect("equal")
    ax.set_xticks([]), ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color(COLORS["coast"])
    return fig, ax


def _finish_map(ax, title):
    """Shared final touches: clear the CRS axis labels geopandas adds."""
    ax.set_xlabel(""), ax.set_ylabel("")
    ax.set_title(title, loc="left")
    ax.get_figure().tight_layout()


# --------------------------------------------------------------------------
# Dark-period figures
# --------------------------------------------------------------------------

def plot_dark_events(events: pd.DataFrame, waters=None, cables=None,
                     title: str | None = None):
    """Map where vessels switched AIS off (circles) and back on (triangles).

    A thin grey line joins the two positions of each dark period. Periods
    with an unavailable position at either end are left out.

    Parameters
    ----------
    events : pandas.DataFrame
        Output of :func:`illegal_maritime_activity.gaps.detect_dark_periods`.
    waters, cables : geopandas.GeoDataFrame, optional
        Extra layers from :func:`load_basemaps`.
    """
    off = events.rename(columns={"off_lat": "Latitude", "off_lon": "Longitude"})
    on = events.rename(columns={"on_lat": "Latitude", "on_lon": "Longitude"})
    keep = valid_position(off) & valid_position(on)
    off_pts, on_pts = to_points(off[keep]), to_points(on[keep])

    paths = gpd.GeoSeries(
        [LineString([a, b]) for a, b in zip(off_pts.geometry, on_pts.geometry)],
        crs=CRS_DK,
    )

    fig, ax = _map_axes(paths.total_bounds, waters, cables)
    paths.plot(ax=ax, color=COLORS["path"], linewidth=0.6, alpha=0.7)
    off_pts.plot(ax=ax, color=COLORS["off"], marker="o", markersize=18,
                 edgecolor="white", linewidth=0.5, zorder=3)
    on_pts.plot(ax=ax, color=COLORS["on"], marker="^", markersize=22,
                edgecolor="white", linewidth=0.5, zorder=3)

    handles = [
        Line2D([], [], marker="o", ls="", color=COLORS["off"], label="AIS switched off"),
        Line2D([], [], marker="^", ls="", color=COLORS["on"], label="AIS switched on"),
        Line2D([], [], color=COLORS["path"], label="Straight line between positions"),
    ]
    if cables is not None:
        handles.append(Line2D([], [], color=COLORS["cable"], label="Submarine cable"))
    ax.legend(handles=handles, loc="lower right", framealpha=0.9, edgecolor="none")
    _finish_map(ax, title or f"AIS dark periods ({int(keep.sum())} with known positions)")
    return fig, ax


def plot_gap_durations(events: pd.DataFrame, title: str | None = None):
    """Histogram of dark-period lengths, in one-hour bins."""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(events["gap_hours"], bins=range(2, 25), color=COLORS["off"],
            edgecolor="white", linewidth=2)
    ax.set_xlabel("Length of AIS gap (hours)")
    ax.set_ylabel("Number of dark periods")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title or "How long vessels stayed dark", loc="left")
    fig.tight_layout()
    return fig, ax


# --------------------------------------------------------------------------
# Sprint maps: infrastructure and fishing activity in Danish waters
# --------------------------------------------------------------------------

# Map extent used during the sprint, covering Danish waters (EPSG:25832).
DK_BOUNDS = (2.6e5, 6.0e6, 11.0e5, 6.45e6)


def plot_cables_in_danish_waters(waters: gpd.GeoDataFrame,
                                 cables: gpd.GeoDataFrame,
                                 title: str | None = None):
    """Map the submarine cables that cross Danish waters.

    Each cable gets its own colour so that individual cables can be told
    apart where they run close together. Requires both optional layers
    (see :func:`load_basemaps`).
    """
    fig, ax = _map_axes(DK_BOUNDS, waters)
    cables.plot(ax=ax, column="id_left", cmap="tab20", linewidth=0.8)
    _finish_map(ax, title or f"Submarine cables in Danish waters ({len(cables)})")
    return fig, ax


def plot_positions_by_flag(df: pd.DataFrame, waters=None, cables=None,
                           month: int | None = None, title: str | None = None):
    """Map fishing-vessel positions coloured by flag group.

    Parameters
    ----------
    df : pandas.DataFrame
        AIS messages with a ``country`` column from
        :func:`illegal_maritime_activity.preprocessing.classify_mmsi`.
    waters, cables : geopandas.GeoDataFrame, optional
        Extra layers from :func:`load_basemaps`.
    month : int, optional
        Restrict the map to one calendar month (1-12), as in the sprint's
        monthly maps.
    """
    if month is not None:
        df = df[df[TIMESTAMP].dt.month == month]
    points = to_points(df[valid_position(df)])

    fig, ax = _map_axes(DK_BOUNDS, waters, cables)
    handles = []
    for flag, color in FLAG_COLORS.items():   # fixed order and colour per flag
        subset = points[points["country"] == flag]
        if subset.empty:
            continue
        subset.plot(ax=ax, color=color, markersize=1)
        handles.append(Line2D([], [], marker="o", ls="", color=color,
                              label=f"{flag} ({subset['MMSI'].nunique()} vessels)"))
    ax.legend(handles=handles, title="Flag", loc="lower right",
              framealpha=0.9, edgecolor="none")

    period = pd.Timestamp(2024, month, 1).strftime("%B") if month else "2024"
    _finish_map(ax, title or f"Fishing vessel positions by flag, {period}")
    return fig, ax
