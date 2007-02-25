#!/bin/bash
BASEDIR="test"
SETTINGSDIR="$BASEDIR/settings"
LOGDIR="$BASEDIR/results"
PY_TEST_DIR="$BASEDIR/python-tests"
FILE_TEST_DIR="$PY_TEST_DIR/tests"
APP="conduit/start_conduit.py"

if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    exit 1
fi

echo "PREPARING"
rm -r $LOGDIR/* 2> /dev/null
rm -r $FILE_TEST_DIR 2> /dev/null
#Prepare some folders
mkdir -p $LOGDIR
#Disable save on exit (the test sets are read only)
gconftool-2 --type bool --set /apps/conduit/save_on_exit false

#prepare stuff for the folder and file tests
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
    CONDUIT_LOGFILE=$logfile python "$t" 2> /dev/null | tee --append $indexfile

    #html
    echo "</pre></p>" >> $indexfile
done

echo $FOOTER >> $indexfile

echo "UPLOADING"
rsync -tz $LOGDIR/*.{html,log} root@greenbirdsystems.com:/var/www/conduit-project.org/tests

echo "FINISHED"
