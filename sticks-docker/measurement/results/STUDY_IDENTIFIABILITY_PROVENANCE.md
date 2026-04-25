# Study Identifiability Provenance

This report measures positive-evidence identifiability over ATT&CK profile technique sets.

Definitions:
- A profile is `distinguishable` when some subset of its techniques excludes every other profile in the same corpus.
- A profile is `impossible` when another profile subsumes it, so positive technique observations alone can never separate the two.
- `Minimum witness size` is the smallest distinguishing subset size under this model.

## Campaign

- Profiles analyzed: `51`
- Distinguishable: `51` (`100.0%`)
- Impossible under positive evidence alone: `0` (`0.0%`)
- Technique count min/mean/median/max: `4` / `19.98` / `17` / `71`
- Minimum witness min/mean/median/max: `1` / `1.25` / `1` / `3`
- Witness distribution: `{'1': 39, '2': 11, '3': 1}`

Hardest profiles:
- `SPACEHOP Activity`: witness `3`, profile size `4`, witness techniques `['T1190', 'T1583.003', 'T1588.002']`
- `2015 Ukraine Electric Power Attack`: witness `2`, profile size `17`, witness techniques `['T1218.011', 'T1136.002']`
- `Operation Dust Storm`: witness `2`, profile size `17`, witness techniques `['T1027.013', 'T1218.005']`
- `C0021`: witness `2`, profile size `15`, witness techniques `['T1218.011', 'T1027.009']`
- `FunnyDream`: witness `2`, profile size `14`, witness techniques `['T1583.001', 'T1049']`
- `CostaRicto`: witness `2`, profile size `10`, witness techniques `['T1583.001', 'T1090.003']`
- `C0011`: witness `2`, profile size `8`, witness techniques `['T1587.003', 'T1204.002']`
- `Versa Director Zero Day Exploitation`: witness `2`, profile size `8`, witness techniques `['T1584.008', 'T1587.001']`
- `C0026`: witness `2`, profile size `6`, witness techniques `['T1560.001', 'T1030']`
- `FLORAHOX Activity`: witness `2`, profile size `6`, witness techniques `['T1059', 'T1090.003']`

## Intrusion-Set

- Profiles analyzed: `168`
- Distinguishable: `145` (`86.3%`)
- Impossible under positive evidence alone: `23` (`13.7%`)
- Technique count min/mean/median/max: `1` / `25.96` / `17.0` / `109`
- Minimum witness min/mean/median/max: `1` / `1.77` / `2` / `4`
- Witness distribution: `{'1': 54, '2': 72, '3': 17, '4': 2}`

Hardest profiles:
- `Elderwood`: witness `4`, profile size `9`, witness techniques `['T1027.013', 'T1566.002', 'T1203', 'T1027.002']`
- `Suckfly`: witness `4`, profile size `5`, witness techniques `['T1003', 'T1553.002', 'T1078', 'T1059.003']`
- `Agrius`: witness `3`, profile size `22`, witness techniques `['T1560.001', 'T1583', 'T1003.002']`
- `Dark Caracal`: witness `3`, profile size `12`, witness techniques `['T1083', 'T1218.001', 'T1566.003']`
- `Moses Staff`: witness `3`, profile size `12`, witness techniques `['T1027.013', 'T1587.001', 'T1190']`
- `admin@338`: witness `3`, profile size `12`, witness techniques `['T1204.002', 'T1083', 'T1069.001']`
- `FIN10`: witness `3`, profile size `11`, witness techniques `['T1078', 'T1570', 'T1078.003']`
- `FIN5`: witness `3`, profile size `11`, witness techniques `['T1070.001', 'T1090.002', 'T1059']`
- `WIRTE`: witness `3`, profile size `11`, witness techniques `['T1140', 'T1571', 'T1218.010']`
- `APT-C-36`: witness `3`, profile size `9`, witness techniques `['T1036.004', 'T1571', 'T1027']`

Sample impossible profiles:
- `APT30`: blocked by `73` supersets, sample blockers `['APT-C-36', 'APT12', 'APT19']`
- `PittyTiger`: blocked by `33` supersets, sample blockers `['APT28', 'APT29', 'APT33']`
- `BlackOasis`: blocked by `17` supersets, sample blockers `['APT-C-36', 'APT3', 'APT37']`
- `TA459`: blocked by `14` supersets, sample blockers `['APT32', 'APT33', 'BRONZE BUTLER']`
- `Orangeworm`: blocked by `13` supersets, sample blockers `['APT28', 'APT32', 'APT39']`
- `APT16`: blocked by `9` supersets, sample blockers `['Daggerfly', 'Dragonfly', 'Earth Lusca']`
- `Moafee`: blocked by `7` supersets, sample blockers `['APT29', 'Akira', 'BRONZE BUTLER']`
- `Group5`: blocked by `4` supersets, sample blockers `['APT28', 'APT39', 'Magic Hound']`
- `Scarlet Mimic`: blocked by `4` supersets, sample blockers `['BRONZE BUTLER', 'BlackTech', 'Ferocious Kitten']`
- `IndigoZebra`: blocked by `3` supersets, sample blockers `['APT28', 'Kimsuky', 'Mustang Panda']`

