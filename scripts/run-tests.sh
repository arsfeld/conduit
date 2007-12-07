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
    -s NAME Perform only the test called NAME\n\
    -o      Offline. Skip tests that require a net connection\n\
    -d      Debug. also print test ouput to console\n\
    -D      Perform dataprovider tests\n\
    -S      Perform sync tests\n\
The operation of the script is affected by two environment\n\
variables. TEST_USERNAME and TEST_PASSWORD are used as\n\
login information in the relevant dataproviders\n\
\n\
The default behaviour is to run all core (TestCore*.py) tests\n\
"

if [ ! -f "conduit/conduit" ] ; then
    echo "ERROR: Must be run from top directory\n$USAGE"
    exit 1
fi

#Parse command line arguments
do_coverage=0
do_upload=0
do_single_test=""
do_online="TRUE"
do_auto=0
do_debug=0
do_dataprovider_tests=0
do_sync_tests=0
while getopts "acus:odDS" options
do
    case $options in
        a )     do_auto=1;;
        c )     do_coverage=1;;
        u )     do_upload=1;;
        s )     do_single_test=$OPTARG;;
        o )     do_online="FALSE";;
        d )     do_debug=1;;
        D )     do_dataprovider_tests=1;;
        S )     do_sync_tests=1;;
        \? )    echo -e $USAGE
                exit 1;;
        * )     echo -e $USAGE
                exit 1;;
    esac
done

#prepare output folders, etc
rm -fr $LOGDIR 2> /dev/null
rm -fr $TEST_DATA_DIR 2> /dev/null
rm $PY_TEST_DIR/TestAuto*.py 2> /dev/null
#Prepare some folders
mkdir -p $LOGDIR
mkdir -p $COVERAGE_RESULTS
mkdir -p $TEST_DATA_DIR
#Prepare some test files with known mtimes
touch -t 198308160000 $TEST_DATA_DIR/oldest
touch -t 198308160001 $TEST_DATA_DIR/older
touch -t 198308160002 $TEST_DATA_DIR/newer
touch -t 198308160003 $TEST_DATA_DIR/newest

#Disable save on exit (the test sets are read only)
gconftool-2 --type bool --set /apps/conduit/save_on_exit false
#Without a gobject main loop the gtkmozembed browser hangs
gconftool-2 --type string --set /apps/conduit/web_login_browser system

#Work out which tests to run
if [ -n "$do_single_test" ] ; then
    tests="$PY_TEST_DIR/$do_single_test"
else
    tests="$PY_TEST_DIR/TestCore*.py"
    if [ $do_dataprovider_tests -ne 0 ] ; then
        tests="$tests $PY_TEST_DIR/TestDataProvider*.py"
    fi
    if [ $do_sync_tests -ne 0 ] ; then
        tests="$tests $PY_TEST_DIR/TestSync*.py"
    fi
    if [ $do_auto -ne 0 ] ; then
        python $PY_TEST_DIR/AutoGenerate.py
        tests="$tests $PY_TEST_DIR/TestAuto*.py"
    fi    
fi

#-------------------------------------------------------------------------------
HEADER="<html><head><title>Conduit Test Results</title></head><body>"
STYLE="<style type=\"text/css\"> pre.abort { background-color: #f99; } pre.fail { background-color: #fcc; } pre.normal { background-color: white; } pre.skip { color: #999; }</style>"
FOOTER="</body></html>"

#test results go to index.html
indexfile=$LOGDIR/index.html
tempfile=`tempfile`

echo $HEADER > $indexfile
echo $STYLE >> $indexfile

for t in `ls $tests`
do
    fname=`basename $t`
    echo "RUNNING UNIT TEST: $fname"

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
        tee $tempfile
    fi

    #html. Look for [SKIPPED], [FINISHED] or [FAIL]
    if grep -q "\[SKIPPED\]" $tempfile ; then 
        style="skip"
    else
        if ! grep -q "\[FINISHED\]" $tempfile ; then 
            style="abort"
        elif grep -q "\[FAIL\]" $tempfile ; then 
            style="fail"
        else
            style="normal"
        fi
    fi
    
    echo "<p><h1>RUNNING UNIT TEST: <a href=$fname.txt>$fname</a></h1><pre class=\"$style\">" >> $indexfile
    cat $tempfile >> $indexfile
    echo "</pre></p>" >> $indexfile
done

#include code coverage results in output
if [ $do_coverage -ne 0 ] ; then
    echo "<p><h1><a href=coverage/>Code Coverage Analysis</a></h1><pre>" >> $indexfile
    
    CORE_COVERAGE_FILES=`ls \
        conduit/*.py \
        conduit/datatypes/*.py \
        conduit/dataproviders/DataProvider.py \
        conduit/modules/TestModule.py \
        conduit/modules/ConverterModule.py`
        
    ALL_COVERAGE_FILES=`ls \
        conduit/*.py \
        conduit/datatypes/*.py \
        conduit/dataproviders/*.py \
        conduit/modules/*.py \
        conduit/modules/*/*.py`
    
    #only print coverage info on files we used    
    coveragefiles="$CORE_COVERAGE_FILES"
    if [ $do_dataprovider_tests -ne 0 ] ; then
        coveragefiles="$coveragefiles $ALL_COVERAGE_FILES"
    fi
    if [ $do_sync_tests -ne 0 ] ; then
        coveragefiles="$coveragefiles $ALL_COVERAGE_FILES"
    fi
        
    #put in the index.html file
    COVERAGE_FILE="$LOGDIR/.coverage" \
    python $COVERAGE_APP -r -a -d $COVERAGE_RESULTS \
    $coveragefiles \
    | tee --append $indexfile

    echo "</pre></p>" >> $indexfile
fi

echo $FOOTER >> $indexfile

#upload results
if [ $do_upload -ne 0 ] ; then
    echo "UPLOADING"
    rsync -tzr $LOGDIR/ root@greenbirdsystems.com:/var/www/conduit-project.org/tests
fi

