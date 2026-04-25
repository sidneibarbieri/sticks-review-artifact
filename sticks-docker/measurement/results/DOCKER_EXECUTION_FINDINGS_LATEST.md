# Docker Execution Findings

- Shared substrate model: `True`
- Networks: `local-network, caldera-kali-network, kali-nginx-network, nginx-db-network`
- Runtime script repairs: `29`
- Generated runtime config files: `.docker/caldera/conf/agents.yml, .docker/caldera/conf/payloads.yml`
- Host architecture patches: `.docker/caldera/Dockerfile, .docker/kali/Dockerfile`
- Operations with progress: `8/8`
- Total successful links: `109`
- Total failed links: `0`
- Total pending links: `0`
- Poll timeout reached: `False`
- Quiescent plateau reached: `True`

## Architecture Findings

- Nginx bootstrap scripts: `8`
- DB bootstrap scripts: `8`
- Both target-side entrypoints load every campaign bootstrap script during container startup, which yields one shared multi-campaign substrate.

## Execution Findings

### OP001 — APT41 DUST
- State: `running`
- Links observed: `24`
- Successful links: `24`
- Failed links: `0`
- Pending links: `0`
- Blocking technique: `T1529` END OF APT 41 DUST

### OP002 — C0010
- State: `running`
- Links observed: `10`
- Successful links: `10`
- Failed links: `0`
- Pending links: `0`
- Blocking technique: `T1529` END OF C0010

### OP003 — C0026
- State: `running`
- Links observed: `7`
- Successful links: `7`
- Failed links: `0`
- Pending links: `0`
- Blocking technique: `T1529` END OF C0026

### OP004 — CostaRicto
- State: `running`
- Links observed: `11`
- Successful links: `11`
- Failed links: `0`
- Pending links: `0`
- Blocking technique: `T1529` END OF COSTARICTO

### OP005 — Operation MidnightEclipse
- State: `running`
- Links observed: `18`
- Successful links: `18`
- Failed links: `0`
- Pending links: `0`
- Blocking technique: `T1529` END OF OPERATION MIDNIGHT ECLIPSE

### OP006 — Outer Space
- State: `running`
- Links observed: `9`
- Successful links: `9`
- Failed links: `0`
- Pending links: `0`
- Blocking technique: `T1529` END OF OUTER SPACE

### OP007 — Salesforce Data Exfiltration
- State: `running`
- Links observed: `19`
- Successful links: `19`
- Failed links: `0`
- Pending links: `0`
- Blocking technique: `T1529` END OF SALESFORCE DATA EXFILTRATION

### OP008 — ShadowRay
- State: `running`
- Links observed: `11`
- Successful links: `11`
- Failed links: `0`
- Pending links: `0`
- Blocking technique: `T1529` END OF SHADOWRAY

## Reproducibility Takeaways

- The Docker artifact executes all curated campaigns inside one shared pre-composed substrate, not one isolated SUT per campaign.
- For this legacy Caldera path, executed work is visible in operation.chain even when operation.steps remains empty.
- Reproducibility depends on runtime repair outside the frozen artifact: missing executable bits, missing Caldera conf files, and host-aware bootstrap adjustments are required for clean replay on a fresh ARM64 host.
- All curated campaigns progressed. 0 record at least one non-zero link status, 0 still have a pending tail under the observed window, and 8 reach explicit end markers.
- The legacy artifact demonstrates partial procedural enactment on a shared laboratory environment, not independent push-button replay of fully isolated campaigns.
