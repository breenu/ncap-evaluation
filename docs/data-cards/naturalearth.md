# Data card: Natural Earth 1:10m coastline

**Role:** distance from each urban centre to the sea, to define the "coastal" region (`config/regions.yaml`, DEC-065). Not used for maps; maps use DataMeet boundaries (DEC-018).

| | |
|---|---|
| Publisher | Natural Earth (naturalearthdata.com) |
| What we download | `ne_10m_coastline.zip` (version 5.x shapefile) from the naciscdn.org mirror |
| Licence | Public domain |
| Version | File dated 2021-12-08 (Last-Modified); pinned by ETag and sha256 in the manifest |
| Size | 3.1 MB |

## Known issues

- At 1:10m scale the line is generalised to roughly 1 km, far finer than the distance threshold used.
- Natural Earth draws disputed boundaries its own way, but only the coastline is used here, so boundary depiction does not arise.
