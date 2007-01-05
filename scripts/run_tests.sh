#!/bin/sh
BASEDIR="test"
SETTINGSDIR="$BASEDIR/settings"
RESULTSDIR="$BASEDIR/results"
LOGDIR="$RESULTSDIR/logs"
PY_TEST_DIR="$BASEDIR/python-tests"
FILE_TEST_DIR="$PY_TEST_DIR/tests"
APP="conduit/start_conduit.py"

if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    exit 1
fi

echo "PREPARING"
rm -r $RESULTSDIR/* 2> /dev/null
rm -r $FILE_TEST_DIR 2> /dev/null
#Prepare some folders
mkdir -p $LOGDIR
mkdir -p $RESULTSDIR
#Disable save on exit (the test sets are read only)
gconftool-2 --type bool --set /apps/conduit/save_on_exit false

#prepare stuff for the folder and file tests
mkdir -p $FILE_TEST_DIR/old
mkdir -p $FILE_TEST_DIR/new
echo "oldest" > $FILE_TEST_DIR/old/file1
sleep 2
echo "older" > $FILE_TEST_DIR/old/file2
sleep 2
echo "newer" > $FILE_TEST_DIR/new/file1
sleep 2
echo "newest" > $FILE_TEST_DIR/new/file2
#put them on a remote server (with same mtimes)
scp -rpq tests root@www.greenbirdsystems.com:/root/sync/

for t in `ls $PY_TEST_DIR/Test*.py`
do
    fname=`basename $t`
    echo "RUNNING UNIT TEST: $fname"
    python "$t" | tee --append $LOGDIR/$fname.log
done

#for t in `ls $SETTINGSDIR`
#do
#    echo "RUNNING TEST: $t"
#    python $APP "--settings=$SETTINGSDIR/$t" &> $LOGDIR/$t.log
#done

echo "FINISHED"
