# Changelog

## 1.0.0 (2026-10-28)

First public release. The analysis from the February 2025 data sprint,
rewritten from exploratory notebooks into a documented, tested package.
The detection method is unchanged and reproduces the sprint output exactly
(211 dark periods across 48 vessels).

### Added
- `illegal_maritime_activity` package with preprocessing, gap detection
  and plotting modules.
- Command-line scripts to rebuild the data, run the analysis and draw the
  maps, with configurable gap thresholds and flag groups.
- One row per dark period with distance travelled and implied speed, plus
  a per-vessel summary.
- Monthly maps of fishing-vessel positions by flag and a map of submarine
  cables in Danish waters, ported from the sprint.
- Land outline so maps are readable without the optional layers.
- Unit tests and a GitHub Actions workflow.
- Walkthrough notebook and documentation of the data.

### Fixed
- Messages that end one dark period and start the next were labelled only
  `off`; they are now `on/off` (17 messages).
- Distances and speeds were computed from the AIS "position not
  available" value (latitude 91), giving values up to ~4,000 km; they are
  now left empty for the 47 periods concerned.
- Maps dropped invalid positions by removing the minimum latitude; they
  now check coordinates explicitly.

### Changed
- The per-vessel loop is replaced by a vectorised group-by, which also
  removes the pandas `SettingWithCopyWarning` raised for every vessel.
- Map extents follow the data, since most events lie east of Denmark.

### Removed
- Unused imports and the single-vessel trial run from the notebooks.
- Wind-turbine map: it failed in the sprint because turbine coordinates
  were never converted to point geometries.
