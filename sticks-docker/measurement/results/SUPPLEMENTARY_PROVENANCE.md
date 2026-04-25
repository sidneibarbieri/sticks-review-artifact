# Supplementary Measurement Provenance

- Bundle: `sticks/data/stix/enterprise-attack.json`
- Docker execution report: `sticks-docker/measurement/results/docker_caldera_execution_latest.json`
- Docker findings report: `sticks-docker/measurement/results/docker_execution_findings_latest.json`
- Active Enterprise attack-patterns: `691`

## Automation-Relevant Field Population

- `kill_chain_phases`: present `691`, non-empty `691`
- `x_mitre_platforms`: present `691`, non-empty `691`
- `x_mitre_system_requirements`: present `0`, non-empty `0`
- `x_mitre_detection`: present `691`, non-empty `0`
- `x_mitre_data_sources`: present `0`, non-empty `0`
- `x_mitre_permissions_required`: present `0`, non-empty `0`

## Non-Sequential Campaign Itemset Support

- Size `1`: max support `28` (54.9%), example `T1105`
- Size `2`: max support `17` (33.3%), example `T1105, T1588.002`
- Size `3`: max support `10` (19.6%), example `T1105, T1190, T1588.002`
- Size `4`: max support `7` (13.7%), example `T1005, T1053.005, T1059.003, T1071.001`
- Size `5`: max support `6` (11.8%), example `T1005, T1033, T1059.003, T1071.001, T1588.002`

## Docker Audit Breakdown

- `APT41 DUST`: successful links `24`, end marker `True`, residual non-zero `0`
- `C0010`: successful links `10`, end marker `True`, residual non-zero `0`
- `C0026`: successful links `7`, end marker `True`, residual non-zero `0`
- `CostaRicto`: successful links `11`, end marker `True`, residual non-zero `0`
- `Operation MidnightEclipse`: successful links `18`, end marker `True`, residual non-zero `0`
- `Outer Space`: successful links `9`, end marker `True`, residual non-zero `0`
- `Salesforce Data Exfiltration`: successful links `19`, end marker `True`, residual non-zero `0`
- `ShadowRay`: successful links `11`, end marker `True`, residual non-zero `0`
