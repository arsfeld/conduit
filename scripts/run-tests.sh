#!/bin/bash
#define a whole heap of directories
BASEDIR=`pwd`"/test"
LOGDIR="$BASEDIR/results"
PY_TEST_DIR="$BASEDIR/python-tests"
TEST_DATA_DIR="$BASEDIR/test-data"

#coverage  definitions
COVERAGE_APP="scripts/coverage.py"
COVERAGE_RESULTS="$BASEDIR/results/coverage"

USAGE="\
Usage:\n\
./scripts/run-tests.sh [OPTIONS]\n\n\
Options:\n\
    -a      Run the automatically generated (SLOW) tests\n\
    -c      Code coverage analysis\n\
    -u      Upload results\n\
    -p      Prepare some files on remote servers\n\
    -s NAME Perform only the test called NAME\n\
    -o      Offline. Skip tests that require a net connection\n\
    -d      Debug. also print test ouput to console\n\
The operation of the script is affected by two environment\n\
variables. TEST_USERNAME and TEST_PASSWORD are used as\n\
login information in the relevant dataproviders\n\
"

if [ ! -f "conduit/start_conduit.py" ] ; then
    echo "ERROR: Must be run from top directory\n$USAGE"
    exit 1
fi

#Parse command line arguments
do_coverage=0
do_upload=0
do_prepare=0
do_single_test="Test*.py"
do_online="TRUE"
do_auto=0
do_debug=0
while getopts "acups:od" options
do
    case $options in
        a )     do_auto=1;;
        c )     do_coverage=1;;
        u )     do_upload=1;;
        p )     do_prepare=1;;
        s )     do_single_test=$OPTARG;;
        o )     do_online="FALSE";;
        d )     do_debug=1;;
        \? )    echo -e $USAGE
                exit 1;;
        * )     echo -e $USAGE
                exit 1;;
    esac
done

#prepare output folders, etc
rm -r $LOGDIR 2> /dev/null
rm -r $TEST_DATA_DIR 2> /dev/null
#Prepare some folders
mkdir -p $LOGDIR
mkdir -p $COVERAGE_RESULTS
mkdir -p $TEST_DATA_DIR

#Disable save on exit (the test sets are read only)
gconftool-2 --type bool --set /apps/conduit/save_on_exit false

#prepare stuff for the folder and file tests
if [ $do_prepare -ne 0 ] ; then
    echo "PREPARING"
    mkdir -p $TEST_DATA_DIR/old
    mkdir -p $TEST_DATA_DIR/new
    echo "oldest" > $TEST_DATA_DIR/old/oldest
    sleep 2
    echo "older" > $TEST_DATA_DIR/old/older
    sleep 2
    echo "newer" > $TEST_DATA_DIR/new/newer
    sleep 2
    echo "newest" > $TEST_DATA_DIR/new/newest
    #put them on a remote server (with same mtimes)
    scp -rpq $TEST_DATA_DIR root@www.greenbirdsystems.com:/root/sync/
fi

rm $PY_TEST_DIR/TestAuto*.py 2> /dev/null
if [ $do_auto -ne 0 ] ; then
    python $PY_TEST_DIR/AutoGenerate.py
fi

#-------------------------------------------------------------------------------
HEADER="<html><head><title>Conduit Test Results</title></head><body>"
FOOTER="</body></html>"
#test results go to index.html
indexfile=$LOGDIR/index.html

echo $HEADER > $indexfile

for t in `ls $PY_TEST_DIR/$do_single_test`
do
    fname=`basename $t`
    #if [ $do_single_test == "x" -o $fname == $do_single_test ] ; then
        echo "RUNNING UNIT TEST: $fname"

        #html
        echo "<p><h1>RUNNING UNIT TEST: <a href=$fname.txt>$fname</a></h1><pre>" >> $indexfile

        #conduit debug output goes to individual log files
        logfile=$LOGDIR/$fname.txt

        #code coverage analysis?
        if [ $do_coverage -ne 0 ] ; then
            EXEC="$COVERAGE_APP -x $t"
        else
            EXEC="$t"
        fi

        #code coverage analysis?
        if [ $do_debug -eq 1 ] ; then
            #run the test
            TEST_DIRECTORY=$TEST_DATA_DIR \
            COVERAGE_FILE="$LOGDIR/.coverage" \
            CONDUIT_LOGFILE=$logfile \
            CONDUIT_ONLINE=$do_online \
            python $EXEC
        else
            #run the test
            TEST_DIRECTORY=$TEST_DATA_DIR \
            COVERAGE_FILE="$LOGDIR/.coverage" \
            CONDUIT_LOGFILE=$logfile \
            CONDUIT_ONLINE=$do_online \
            python $EXEC 2> /dev/null | \
            tee --append $indexfile
        fi

        #html
        echo "</pre></p>" >> $indexfile
    #fi
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
