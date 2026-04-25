# Docker Runtime Context Preparation

- Host architecture: `arm64`
- Source Docker root: `sticks-docker/docker`
- Prepared runtime root: `docker-context`
- Prepared curated API root: `curated-api`
- Repaired shell scripts: `29`
- Reset state directories: `2`
- Generated runtime config files: `2`
- Host architecture patches: `2`
- Curated API overlay patches: `6`

## Reset Directories

- `kali-data`
- `.docker/db/dbdata`

## Repaired Shell Scripts

- `.docker/caldera/plugins/access/data/payloads/scanner.sh`
- `.docker/caldera/plugins/builder/install.sh`
- `.docker/caldera/plugins/emu/download_payloads.sh`
- `.docker/caldera/plugins/manx/update-shells.sh`
- `.docker/caldera/plugins/sandcat/payloads/sandcat-inmem.sh`
- `.docker/caldera/plugins/sandcat/update-agents.sh`
- `.docker/caldera/plugins/stockpile/payloads/file_search.sh`
- `.docker/caldera/plugins/stockpile/payloads/transfer_suid.sh`
- `.docker/caldera/plugins/stockpile/payloads/wifi.sh`
- `.docker/db/apt41_dust_sutb.sh`
- `.docker/db/c0010_sutb.sh`
- `.docker/db/c0026_sutb.sh`
- `.docker/db/costaricto_sutb.sh`
- `.docker/db/entrypoint.sh`
- `.docker/db/operation_midnighteclipse_sutb.sh`
- `.docker/db/outer_space_sutb.sh`
- `.docker/db/salesforce_data_exfiltration_sutb.sh`
- `.docker/db/shadowray_sutb.sh`
- `.docker/nginx/apt41_dust_suta.sh`
- `.docker/nginx/c0010_suta.sh`
- `.docker/nginx/c0026_suta.sh`
- `.docker/nginx/costaricto_suta.sh`
- `.docker/nginx/entrypoint.sh`
- `.docker/nginx/operation_midnighteclipse_suta.sh`
- `.docker/nginx/outer_space_suta.sh`
- `.docker/nginx/salesforce_data_exfiltration_suta.sh`
- `.docker/nginx/shadowray_suta.sh`
- `.docker/nginx/var/www/html/backdor.sh`
- `.docker/nginx/var/www/html/maliciousfile.sh`

## Generated Runtime Config Files

- `.docker/caldera/conf/agents.yml`
- `.docker/caldera/conf/payloads.yml`

## Host Architecture Patches

- `.docker/caldera/Dockerfile`
- `.docker/kali/Dockerfile`

## Curated API Overlay Patches

- `apt41_dust_dag-ability.json`
- `operation_midnighteclipse_dag-ability.json`
- `outer_space_dag-adversary.json`
- `salesforce_data_exfiltration_dag-ability.json`
- `shadowray_dag-ability.json`
- `shadowray_dag-adversary.json`
