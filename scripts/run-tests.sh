#!/bin/bash
#define a whole heap of directories
BASEDIR="test"
LOGDIR="$BASEDIR/results"
PY_TEST_DIR="$BASEDIR/python-tests"
FILE_TEST_DIR="$PY_TEST_DIR/tests"

#coverage  definitions
COVERAGE_APP="scripts/coverage.py"
COVERAGE_RESULTS="$BASEDIR/results/coverage"

USAGE="\
Usage:\n\
./scripts/run-tests.sh [OPTIONS]\n\n\
Options:\n\
    -c      Code coverage analysis\n\
    -u      Upload results\n\
    -p      Prepare some files on remote servers\n\
"

if [ ! -f "conduit/start_conduit.py" ] ; then
    echo "ERROR: Must be run from top directory\n$USAGE"
    exit 1
fi

#Parse command line arguments
do_coverage=0
do_upload=0
do_prepare=0
while getopts "cup" options
do
    case $options in
        c )     do_coverage=1;;
        u )     do_upload=1;;
        p )     do_prepare=1;;
        \? )    echo -e $USAGE
                exit 1;;
        * )     echo -e $USAGE
                exit 1;;
    esac
done

#prepare output folders, etc
rm -r $LOGDIR 2> /dev/null
rm -r $FILE_TEST_DIR 2> /dev/null
#Prepare some folders
mkdir -p $LOGDIR
mkdir -p $COVERAGE_RESULTS

#Disable save on exit (the test sets are read only)
gconftool-2 --type bool --set /apps/conduit/save_on_exit false

#prepare stuff for the folder and file tests
if [ $do_prepare -ne 0 ] ; then
    echo "PREPARING"
    mkdir -p $FILE_TEST_DIR/old
    mkdir -p $FILE_TEST_DIR/new
    echo "oldest" > $FILE_TEST_DIR/old/oldest
    sleep 2
    echo "older" > $FILE_TEST_DIR/old/older
    sleep 2
    echo "newer" > $FILE_TEST_DIR/new/newer
    sleep 2
    echo "newest" > $FILE_TEST_DIR/new/newest
    #put them on a remote server (with same mtimes)
    scp -rpq $FILE_TEST_DIR root@www.greenbirdsystems.com:/root/sync/
fi

#-------------------------------------------------------------------------------
HEADER="<html><head><title>Conduit Test Results</title></head><body>"
FOOTER="</body></html>"
#test results go to index.html
indexfile=$LOGDIR/index.html

echo $HEADER > $indexfile

for t in `ls $PY_TEST_DIR/Test*.py`
do
    fname=`basename $t`
    echo "RUNNING UNIT TEST: $fname"

    #html
    echo "<p><h1>RUNNING UNIT TEST: <a href=$fname.log>$fname</a></h1><pre>" >> $indexfile

    #conduit debug output goes to individual log files
    logfile=$LOGDIR/$fname.log

    #code coverage analysis?
    if [ $do_coverage -ne 0 ] ; then
        EXEC="$COVERAGE_APP -x $t"
    else
        EXEC="$t"
    fi

    #run the test
    COVERAGE_FILE="$LOGDIR/.coverage" \
    CONDUIT_LOGFILE=$logfile \
    python $EXEC 2> /dev/null | \
    tee --append $indexfile

    #html
    echo "</pre></p>" >> $indexfile
done

#include code coverage results in output
if [ $do_coverage -ne 0 ] ; then
    echo "<p><h1><a href=coverage/>Code Coverage Analysis</a></h1><pre>" >> $indexfile

    #put in the index.html file
    COVERAGE_FILE="$LOGDIR/.coverage" \
    python $COVERAGE_APP -r -a -d $COVERAGE_RESULTS \
    conduit/*.py \
    conduit/datatypes/*.py \
    conduit/dataproviders/*.py \
    conduit/dataproviders/BackpackModule/BackpackModule.py \
    conduit/dataproviders/FileModule/FileModule.py \
    conduit/dataproviders/FlickrModule/FlickrModule.py \
    conduit/dataproviders/GmailModule/GmailModule.py | \
    tee --append $indexfile

    echo "</pre></p>" >> $indexfile
fi

echo $FOOTER >> $indexfile

#upload results
if [ $do_upload -ne 0 ] ; then
    echo "UPLOADING"
    rsync -tzr $LOGDIR/ root@greenbirdsystems.com:/var/www/conduit-project.org/tests
fi

echo "FINISHED"
