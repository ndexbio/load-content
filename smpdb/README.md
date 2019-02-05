# Post-process SMPDB pathways

Script updates a set of SMPDB pathways networks in set on http://www.ndexbio.org/#/networkset/00289894-2025-11e9-bb6a-0ac135e8bacf (or other network set as specified by command line arguments).

Specifications are given here: https://ndexbio.atlassian.net/browse/NSU-78

## Running the script

```sh
python process_smpdb.py <username> <password> <ndex_server> <network_set_uuid> <smpdb_pathways_csv_file>
```


for example:

<pre>python process_smpdb.py ccc1 ccc2 dev.ndexbio.org 832e7ee6-24df-11e9-a05d-525400c25d22 smpdb_pathways.csv</pre>

After finishing, script gives a brief message with a number of network processed, for example:

<pre>Done. Processed 3 networks.</pre>

## Verification

For verification purpose, script creates 3 additional files in the folder where it runs:

```sh
1) original_networks.json - networks in json format that were received from NDEx server before processing;
2) processed_networks.json - networks in json format after processing by the script; these networks are then sent to the  server replacing original networks
3)  smpdb_pathways_processed.csv - data from smpdb_pathways.csv that was used for transforming the networks.
```
