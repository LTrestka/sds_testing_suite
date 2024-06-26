#!/bin/sh -x

cd /srv4/moibenko/stuff/test_files_for_enstore
dat=$(date | sed -e 's/ //g')
export PNFS_DIR=/pnfs/fs/usr/data/moibenko/LTO8/ACCT/enstore-$dat
mkdir -p $PNFS_DIR
export LOCAL_DIR=`pwd`
/opt/enstore/tools/encp_test_script_no_dcache
