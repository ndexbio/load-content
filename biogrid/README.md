# Description of run_dev.sh script

Script that modifies biogrid networks on Dev account takes three arguments: biogrid version (i.e., <strong>3.5.170</strong>), username, and password. 
To run the script:
```
./run_dev.sh <version> <user> <password>
```
1) using <strong>version</strong> argument, <strong>run_dev.sh</strong> constructs a link and downloads <strong>BIOGRID-ORGANISM-version.tab2.zip</strong> file from 
  <italic>https://downloads.thebiogrid.org/Download/BioGRID/Release-Archive</italic>. Then it starts <strong>load_biogrid_orgainism.py</strong> python script.

2) For every network listed in <strong>dev_organism_list.txt</strong>, <strong>load_biogrid_orgainism.py</strong> constructs a corresponding file name found in the downloaded archive (i.e., <strong>BIOGRID-ORGANISM-Zea_mays-3.5.170.tab2.txt</strong>), extracts this file from the downloaded archive, parses it, and creates a new <strong>tsv</strong> file.

3) After tsv file is created, <strong>load_biogrid_orgainism.py</strong> converts it to network in Nice CX, updates some of the networks properties (description, references, version, etc), applies template (if specified), and updates the network on the server if it already exists (or creates a new one if it doesn’t exist).

4) Then <strong>load_biogrid_orgainism.py</strong> takes the next network entry from in <strong>dev_organism_list.txt</strong> (step 2).

Once <strong>load_biogrid_orgainism.py</strong> processed all networks listed in <strong>dev_organism_list.txt</strong>, <strong>run_dev.sh</strong> downloads <strong>BIOGRID-CHEMICALS-<version>.chemtab.zip</strong> (i.e *BIOGRID-CHEMICALS‌-3.5.170.chemtab.zip*), extracts the only text file in this archive, and starts <strong>load_biogrid.py</strong> script.

load_biogrid.py parses the unzipped BIOGRID-CHEMICALS-<version>.chemtab.txt file, and creates a new tsv file. Then load_biogrid.py processes this tsv file the same way load_biogrid_orgainism.py does (described above), and uploads it to the server replacing the original network (if it exists), or creating a new one (if it doesn’t exist).

Script that modifies biogrid networks on Prod ./run_prod.sh is similar to

./run_dev.sh. ./run_prod.sh uses the production server.
