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

The script opens the original tsv file, creates list of all gene ids from both columns of that file, then opens dictionary.json file from local folder (if it is there) and checks what ids are in the dictionary.  Ids that are not in the dictionary are retrieved from the server 200 ids at a time, and are saved to disk for future use. 
After all ids are retrieved from the server, we create the output file.

When running, script provides info on what it is doing.  If there are any unresolved gene ids, they will be printed in the end.  Below is example of running the script with HumanNet-XN.tsv:
```sh
python normalize_humanet_net.py  HumanNet-XN.tsv 
Found 17929 unique Gene Ids in HumanNet-XN.tsv
Dictionary is empty, need to populate it with 17929 symbols
Updating dictionary ...
New symbols added: 200;  dictionary size: 200 symbols
New symbols added: 400;  dictionary size: 400 symbols
New symbols added: 600;  dictionary size: 600 symbols
New symbols added: 800;  dictionary size: 800 symbols
. . . 
New symbols added: 17800;  dictionary size: 17800 symbols
New symbols added: 17929;  dictionary size: 17929 symbols

Total new symbols added to dictionary: 17929

Generating normalized tsv file normalized_HumanNet-XN.tsv ...

Normalized 10000 rows
Normalized 20000 rows
Normalized 30000 rows
. . .
Normalized 490000 rows
Normalized 500000 rows
Normalized 510000 rows
Normalized 520000 rows

normalized_HumanNet-XN.tsv is ready; normalized 525537 rows

the following 4 gene id(s) unresolved: 
729574 117153 26148 100506627
```
