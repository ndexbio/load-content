#!/bin/bash

# You need to run this script in the current directory.


if [ "$#" -ne 3 ]; then
    echo "This program needs 3 pramameters <biogrid_version> <ndex_username> <ndex_password>"
    echo "For example:"
    echo "./run_prod.sh 3.4.158 ndexuser1 ndexuser1password"
    exit 1
fi

#the version you want to update
VERSION=$1

#connect parameters for uploading networks
USER=$2
PASSWD=$3
SERVER=dev.ndexbio.org

#Protein-chemical style template network on the server
CHEM_TEMPLATE=63090182-1fef-11e9-a05d-525400c25d22
PROT_TEMPLATE=760403c5-1fef-11e9-a05d-525400c25d22
CHEM_TARGET_NETWORK=b192ccaa-2261-11e8-b939-0ac135e8bacf


echo "Updating protein-protein networks."

PROTFILE_NAME=BIOGRID-ORGANISM-$VERSION.tab2

curl https://downloads.thebiogrid.org/Download/BioGRID/Release-Archive/BIOGRID-$VERSION/$PROTFILE_NAME.zip -o $PROTFILE_NAME.zip

if [ $? -gt 0 ]
then
   echo "failed to download protein-protein zip file."
   exit 2
fi



python3 load_biogrid_organism.py $VERSION $USER $PASSWD -s $SERVER -t $PROT_TEMPLATE

if [ $? -gt 0 ]
then
   echo "failed to update protein-protien network"
   exit 2
fi

rm BIOGRID-ORGANISM-Homo_sapiens-$VERSION.tab2.txt
rm $PROTFILE_NAME.zip


echo "Updating protein-chemical networks"

CHEMFILE_NAME=BIOGRID-CHEMICALS-$VERSION.chemtab

curl https://downloads.thebiogrid.org/Download/BioGRID/Release-Archive/BIOGRID-$VERSION/$CHEMFILE_NAME.zip -o $CHEMFILE_NAME.zip

if [ $? -gt 0 ]
then
   echo "failed to download file"
   exit 2
fi

unzip -o $CHEMFILE_NAME.zip

## -t UUID for the template network -target UUID for update target
if [ -z ${CHEM_TARGET_NETWORK+x} ]
then
    python3 load_biogrid.py $VERSION $USER $PASSWD -s $SERVER -t $CHEM_TEMPLATE
else
    python3 load_biogrid.py $VERSION $USER $PASSWD -s $SERVER -t $CHEM_TEMPLATE -target $CHEM_TARGET_NETWORK
fi

if [ $? -gt 0 ]
then
   echo "failed to update chem-protien network"
   exit 2
fi

rm $CHEMFILE_NAME.zip
rm $CHEMFILE_NAME.txt

