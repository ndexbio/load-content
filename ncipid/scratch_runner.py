from os import path, listdir
import subprocess
import pandas as pd

current_directory = path.dirname(path.abspath(__file__))
biopax_path = path.join(current_directory, 'biopax')
sif_path = path.join(current_directory, 'biopax', 'sif')
biopax_files = listdir(biopax_path)
grp_file_path = path.join(current_directory, 'grp')
paxtools_file = path.join(current_directory, 'paxtools.jar')

#======================================
#======================================
# Process biopax files into ebs files
#======================================
#======================================
if False:
    for bpf in biopax_files:
        if path.isfile(path.join(biopax_path, bpf)) and bpf != '.DS_Store':
            print '------------- ' + bpf + ' -------------'
            subprocess.call(['java', '-jar', paxtools_file, 'toSIF', path.join(biopax_path, bpf),
                             path.join(sif_path, bpf.replace('.owl', '.sif')),
                             '"seqDb=hgnc,uniprot,refseq,ncbi,entrez,ensembl"',
                             '"chemDb=chebi,pubchem"', '-useNameIfNoId', '-extended'])



edge_table = []
node_table = []
id_list = []
ebs = {"edge_table": edge_table, "node_table": node_table}
#network_name = network_name_from_path(path)

#path_to_sif = path.join('sif', 'pid_EXTENDED_BINARY_SIF_2016-09-24T14:04:47.203937', file_name)
path_to_sif = path.join('simple_ebs.txt')
with open(path_to_sif, 'rU') as f:
    lines = f.readlines()
    mode = "edge"
    edge_lines = []
    edge_lines_tuples = []
    node_lines = []
    node_lines_tuples = []
    node_lines = []
    edge_fields = []
    node_fields = []
    for index in range(len(lines)):
        line = lines[index]
        if index is 0:
            edge_fields = [h.strip() for h in line.split('\t')]
        elif line == '\n':
            mode = "node_header"
        elif mode is "node_header":
            node_fields = [h.strip() for h in line.split('\t')]
            mode = "node"
        elif mode is "node":
            node_tuple = tuple(line.split('\t'))
            node_lines_tuples.append(node_tuple)
            node_lines.append(line)
        elif mode is "edge":
            edge_tuple = tuple(line.split('\t'))
            edge_lines_tuples.append(edge_tuple)
            edge_lines.append(line)

    df = pd.DataFrame.from_records(edge_lines_tuples, columns=edge_fields)
    df2 = pd.DataFrame.from_records(node_lines_tuples, columns=node_fields)

    df3 = df.join(df2.set_index('PART'), on='PARTA')

    df4 = df3.join(df2.set_index('PART'), on='PARTB', lsuffix='_A', rsuffix='_B')

    #df.loc[:, 'DEFAULT INTERACTION'] = pd.Series('interacts with', index=df.index)



    print(df3.head())
    print(df4.head())


