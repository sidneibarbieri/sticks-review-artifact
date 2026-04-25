# Study Robustness Provenance

- Bundle: `sticks/data/stix/enterprise-attack.json`

## Alternative Binary-Distance Clustering

- `hamming` average-linkage agglomerative clustering: `k=7` silhouette `0.2386` with cluster sizes `[45, 1, 1, 1, 1, 1, 1]`; `k=2..10` silhouettes `{'2': 0.563, '3': 0.5355, '4': 0.469, '5': 0.2968, '6': 0.2668, '7': 0.2386, '8': 0.2219, '9': 0.226, '10': 0.2193}`.
- `jaccard` average-linkage agglomerative clustering: `k=7` silhouette `0.0296` with cluster sizes `[28, 12, 5, 2, 2, 1, 1]`; `k=2..10` silhouettes `{'2': 0.0488, '3': 0.0363, '4': 0.0297, '5': 0.0366, '6': 0.0311, '7': 0.0296, '8': 0.0366, '9': 0.0406, '10': 0.049}`.

## Randomized Tactic-Assignment LCS Sensitivity

- Mean LCS across 200 trials: average `2.739`, range `2.728`--`2.754`.
- Median LCS across 200 trials: average `2.0`, range `2.0`--`2.0`.
- Max LCS across 200 trials: average `25.86`, range `24`--`28`.

## Campaign ↔ Intrusion-Set Overlap

- Attributed campaign/intrusion-set pairs with techniques on both sides: `22`.
- Intrusion-set techniques observed in the linked campaign (`|C∩I|/|I|`): median `11.6`%, mean `14.4`%, min `0.0`%, max `42.9`%.
- Campaign techniques shared with the linked intrusion set (`|C∩I|/|C|`): median `50.0`%, mean `45.2`%, min `0.0`%, max `76.5`%.
- Jaccard overlap: median `10.0`%, mean `11.8`%, min `0.0`%, max `37.5`%.
- Pairs below thresholds: `|C∩I|/|I| < 50%` in `22/22` pairs; Jaccard `< 50%` in `22/22` pairs.

### Lowest-Overlap Examples

- `3CX Supply Chain Attack` ↔ `AppleJeus`: `|C∩I|/|I|=0.0`%, `|C∩I|/|C|=0.0`%, `J=0.0`% (`|C∩I|=0`, `|C|=22`, `|I|=2`).
- `Operation Ghost` ↔ `APT29`: `|C∩I|/|I|=3.0`%, `|C∩I|/|C|=25.0`%, `J=2.8`% (`|C∩I|=2`, `|C|=8`, `|I|=66`).
- `SPACEHOP Activity` ↔ `APT5`: `|C∩I|/|I|=3.4`%, `|C∩I|/|C|=25.0`%, `J=3.1`% (`|C∩I|=1`, `|C|=4`, `|I|=29`).
- `Versa Director Zero Day Exploitation` ↔ `Volt Typhoon`: `|C∩I|/|I|=3.7`%, `|C∩I|/|C|=37.5`%, `J=3.5`% (`|C∩I|=3`, `|C|=8`, `|I|=81`).
- `SPACEHOP Activity` ↔ `Ke3chang`: `|C∩I|/|I|=4.3`%, `|C∩I|/|C|=50.0`%, `J=4.2`% (`|C∩I|=2`, `|C|=4`, `|I|=46`).
- `2022 Ukraine Electric Power Attack` ↔ `Sandworm Team`: `|C∩I|/|I|=6.3`%, `|C∩I|/|C|=50.0`%, `J=6.0`% (`|C∩I|=5`, `|C|=10`, `|I|=79`).
- `Outer Space` ↔ `OilRig`: `|C∩I|/|I|=6.6`%, `|C∩I|/|C|=62.5`%, `J=6.3`% (`|C∩I|=5`, `|C|=8`, `|I|=76`).
- `KV Botnet Activity` ↔ `Volt Typhoon`: `|C∩I|/|I|=8.6`%, `|C∩I|/|C|=35.0`%, `J=7.4`% (`|C∩I|=7`, `|C|=20`, `|I|=81`).
- `APT28 Nearest Neighbor Campaign` ↔ `APT28`: `|C∩I|/|I|=11.0`%, `|C∩I|/|C|=55.6`%, `J=10.1`% (`|C∩I|=10`, `|C|=18`, `|I|=91`).
- `HomeLand Justice` ↔ `HEXANE`: `|C∩I|/|I|=11.1`%, `|C∩I|/|C|=16.0`%, `J=7.0`% (`|C∩I|=4`, `|C|=25`, `|I|=36`).
