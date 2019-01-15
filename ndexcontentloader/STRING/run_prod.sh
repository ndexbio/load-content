#!/bin/bash

# You need to run this script in the current directory.


if [ "$#" -ne 3 ]; then
    echo "This program needs 3 pramameters <STRING_version> <ndex_username> <ndex_password>"
    echo "For example:"
    echo "./run_prod.sh 10.5 ndexuser1 ndexuser1password"
    exit 1
fi

#the version you want to update
VERSION=$1

#connect parameters for uploading networks
USER=$2
PASSWD=$3
SERVER=public.ndexbio.org

#Protein-chemical style template network on the server
LINK_TEMPLATE=829b6370-39dc-11e8-8695-0ac135e8bacf
HC_LINK_TEMPLATE=e729e193-39dc-11e8-8695-0ac135e8bacf

echo "Updating networks."

PROTFILE_NAME=9606.protein.links.v$VERSION.txt

curl https://stringdb-static.org/download/protein.links.v$VERSION/PROTFILE_NAME.gz -o $PROTFILE_NAME.gz

if [ $? -gt 0 ]
then
   echo "failed to download protein-link gz file."
   exit 2
fi

gzip -d $PROTFILE_NAME.gz

python3 load_links.py $VERSION $USER $PASSWD -s $SERVER -t $LINK_TEMPLATE -t2 $HC_LINK_TEMPLATE

if [ $? -gt 0 ]
then
   echo "failed to update protein-links network"
   exit 2
fi

rm $$PROTFILE_NAME
