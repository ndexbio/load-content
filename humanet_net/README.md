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

The output is another TSV file that has 5 columns: <header 1 from original tsv> <symbol 1> <header 2 from original tsv> <symbol 2> <header 3 from original tsv>. In other words, columns 1, 3 and 5 contain data from the original file; columns 2 and 4 are gene symbols for columns 1 and 3, respectively.
