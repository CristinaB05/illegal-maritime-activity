# Data

## Source

AIS (Automatic Identification System) messages for 2024 published by the
[Danish Maritime Authority](https://www.dma.dk/safety-at-sea/navigational-information/ais-data),
resampled to one message per vessel every 30 minutes (`aisdk-2024-30m.parquet`).
The raw file is several GB and is not tracked. Place it in `data/raw/` to
rebuild the processed files with `scripts/prepare_data.py`.

## `processed/`

| File | Rows | Description |
|---|---|---|
| `russian_fishing_vessels_2024.csv` | 9,669 | All AIS messages from Russian-flagged fishing vessels (MMSI prefix `273`), 83 vessels. Sprint name: `russian.csv`. |
| `russian_dark_events_2024.csv` | 422 | Sprint output: the message before and after each dark period (211 periods). Sprint name: `sus_russian.csv`. |

Both files keep the row index of the raw parquet file as their first column,
so every message can be traced back to the source. They also carry the
`Status` column produced during the sprint (`Regular` / `off` / `on`); the
analysis recomputes it.

Main columns: `MMSI` (vessel identifier), `# Timestamp`, `Latitude`,
`Longitude`, `Navigational status`, `SOG` (speed over ground, knots), `COG`
(course over ground), `IMO`, `Name`, `Ship type`, `Destination`.

## `external/`

| File | Tracked | Source |
|---|---|---|
| `land_north_sea_baltic.geojson` | yes | [Natural Earth](https://www.naturalearthdata.com/) 1:10m land polygons (public domain), clipped to 1–23°E, 52.5–62°N |
| `dk.json` | no | Danish waters polygon used during the sprint |
| `cable-geo.json` | no | Submarine cables from [submarinecablemap.com](https://www.submarinecablemap.com/api/v3/cable/cable-geo.json) |

Drop `dk.json` and `cable-geo.json` into `external/` and the maps will
include them automatically.
