# Description of run_dev.sh script

Script that modifies biogrid networks on Dev account takes three arguments: biogrid version (i.e., 3.5.170), username, and password. 
To run the script:
```
./run_dev.sh <version> <user> <password>
```
1) using <strong>version</strong> argument, run_dev.sh constructs a link and downloads BIOGRID-ORGANISM-<version>.tab2.zip file from 
https://downloads.thebiogrid.org/Download/BioGRID/Release-Archive. Then it starts load_biogrid_orgainism.py python script.

2) For every network listed in dev_organism_list.txt, load_biogrid_orgainism.py constructs a corresponding file name found in the downloaded archive (i.e., BIOGRID-ORGANISM-Zea_mays-3.5.170.tab2.txt), extracts this file from the downloaded archive, parses it, and creates a new tsv file.

3) after tsv file is created, load_biogrid_orgainism.py converts it to network in Nice CX, updates some of the networks properties (description, references, version, etc), applies template (if specified), and updates the network on the server if it already exists (or creates a new one if it doesn’t exist).

4) Then we take the next network entry from in dev_organism_list.txt (step 2)

Once load_biogrid_orgainism.py processed all networks listed in dev_organism_list.txt, run_dev.sh downloads BIOGRID-CHEMICALS-<version>.chemtab.zip (i.e *BIOGRID-CHEMICALS‌-3.5.170.chemtab.zip*), extracts the only text file in this archive, and starts load_biogrid.py script.

load_biogrid.py parses the unzipped BIOGRID-CHEMICALS-<version>.chemtab.txt file, and creates a new tsv file. Then load_biogrid.py processes this tsv file the same way load_biogrid_orgainism.py does (described above), and uploads it to the server replacing the original network (if it exists), or creating a new one (if it doesn’t exist).

Script that modifies biogrid networks on Prod ./run_prod.sh is similar to

./run_dev.sh. ./run_prod.sh uses the production server.
