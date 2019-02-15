# Normalize Humanet v2 data

Script takes as an argument raw tsv file that has three columns: the first two columns have IDs of genes and the third column 
is a float value.

Specifications are given here: https://ndexbio.atlassian.net/browse/NSU-82

## Running the script

```sh
python normalize_humanet_net.py <humanet_csv_file>
```


for example:

<pre>python normalize_humanet_net.py HumanNet-XN.tsv</pre>
