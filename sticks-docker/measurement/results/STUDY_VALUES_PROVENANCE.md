# Study Values Provenance

- Bundle: `sticks/data/stix/enterprise-attack.json`

## Counts

- Active campaigns: `52`
- Active campaigns with techniques: `51`
- Active intrusion sets: `172`
- Intrusion sets with techniques: `168`
- Intrusion sets without techniques: `4`
- Active attack-pattern objects: `691`
- `uses` relationships: `17270`
- Total objects in analyzed bundle: `24772`

## Platform-Agnostic Classifier

- Definition: Active top-level ATT&CK techniques without a concrete host platform (Containers, ESXi, Linux, Network Devices, Windows, macOS).
- Count: `32`

### Included Techniques

- `T1526` Cloud Service Discovery (IaaS, Identity Provider, Office Suite, SaaS)
- `T1530` Data from Cloud Storage (IaaS, Office Suite, SaaS)
- `T1535` Unused/Unsupported Cloud Regions (IaaS)
- `T1537` Transfer Data to Cloud Account (IaaS, Office Suite, SaaS)
- `T1538` Cloud Service Dashboard (IaaS, Identity Provider, Office Suite, SaaS)
- `T1578` Modify Cloud Compute Infrastructure (IaaS)
- `T1580` Cloud Infrastructure Discovery (IaaS)
- `T1583` Acquire Infrastructure (PRE)
- `T1584` Compromise Infrastructure (PRE)
- `T1585` Establish Accounts (PRE)
- `T1586` Compromise Accounts (PRE)
- `T1587` Develop Capabilities (PRE)
- `T1588` Obtain Capabilities (PRE)
- `T1589` Gather Victim Identity Information (PRE)
- `T1590` Gather Victim Network Information (PRE)
- `T1591` Gather Victim Org Information (PRE)
- `T1592` Gather Victim Host Information (PRE)
- `T1593` Search Open Websites/Domains (PRE)
- `T1594` Search Victim-Owned Websites (PRE)
- `T1595` Active Scanning (PRE)
- `T1596` Search Open Technical Databases (PRE)
- `T1597` Search Closed Sources (PRE)
- `T1598` Phishing for Information (PRE)
- `T1608` Stage Capabilities (PRE)
- `T1619` Cloud Storage Object Discovery (IaaS)
- `T1648` Serverless Execution (IaaS, Office Suite, SaaS)
- `T1650` Acquire Access (PRE)
- `T1651` Cloud Administration Command (IaaS)
- `T1666` Modify Cloud Resource Hierarchy (IaaS)
- `T1671` Cloud Application Integration (Office Suite, SaaS)
- `T1677` Poisoned Pipeline Execution (SaaS)
- `T1681` Search Threat Vendor Data (PRE)

## Case Studies

- `ShadowRay` -> `ShadowRay` (campaign, runs=10, local_campaign_id=0.shadowray, description_mentions_display_name=True)
- `Soft Cell` -> `GALLIUM` (intrusion-set, runs=10, local_campaign_id=n/a, description_mentions_display_name=True)
