# Post-process SMPDB pathways

Script that updates a set of SMPDB pathways networks in networks set on http://www.ndexbio.org/#/networkset/00289894-2025-11e9-bb6a-0ac135e8bacf (or other network set as specified by command line arguments).

Specifications are given here: https://ndexbio.atlassian.net/browse/NSU-78

## Running the script

python process_smpdb.py <username> <password> <ndex server> <network set uuid> <smpdb_pathways.csv file>

for example:

python process_smpdb.py ccc1 ccc2 dev.ndexbio.org 832e7ee6-24df-11e9-a05d-525400c25d22 smpdb_pathways.csv

After finishing, script gives a brief message with a number of network processed, for example:

Done. Processed 3 networks.

## Checking server response

Sc

## Prerequisites

What things you need to install the software and how to install them

```
Give examples
```
