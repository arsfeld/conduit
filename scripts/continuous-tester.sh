#!/bin/sh
#Continuously builds and tests conduit from GNOME svn
TEST_DIR='/tmp/conduittestdir'
LOGFILE='/home/john/Desktop/conduit-test.log'
SVN_REPO='http://svn.gnome.org/svn/conduit/trunk'
TEST_OPTIONS='cu'
SLEEP_TIME='1h'

ME=`basename $0`
USAGE="\
Usage:\n\
$ME [OPTIONS]\n\
Runs the conduit test suite and uploads the results. Defaults to only running\n\
if the remote repository has changed\n\n\
Options:\n\
\t-f, --force\t\tRun the tests even if the repository has not changed\n\
\t-d, --disable-docs\tDisable buliding of documentation\n\
\t-l, --loop\t\tRuns in a never ending loop"

FORCE=no
DOCS=yes
CNT=-1
LOOP=no
#Check the arguments.
for option in "$@"; do
  case "$option" in
    -h | --help)
      echo $USAGE
      exit 0 ;;
    -f | --force)
      FORCE=yes ;;
    -d | --disable-docs)
      DOCS=no ;;
    -l | --loop)
      CNT=1
      LOOP=yes ;;
    -*)
      echo "Unrecognized option: $option\n\n$USAGE"
      exit 1 ;;
  esac
done

if [ ! -d $TEST_DIR ]; then
    mkdir -p $TEST_DIR
    svn co $SVN_REPO $TEST_DIR
    FORCE=yes
fi
touch $LOGFILE
cd $TEST_DIR

#Emulate a do-while loop
while [ $CNT -ne 0 ]; do

    #Calculate local and remote repository revisions
    LVERSION=`svnversion $TEST_DIR`
    RVERSION=`svn info http://svn.gnome.org/svn/conduit/trunk | sed -n 's/^Revision: \([0-9][0-9]*\).*/\1/p'`

    if [ "$LVERSION" != "$RVERSION" -o "$FORCE" = "yes" ]; then
        #Run tests (dbus-launch sets a private session bus incase we are
        #being run from a VT
        svn up . 
        echo "`date` Running Test (Revision $RVERSION)" | tee -a $LOGFILE
        dbus-launch $TEST_DIR/scripts/run-tests.sh -$TEST_OPTIONS 
        
        #Build packages
        #./autogen.sh && make && make dist &>/dev/null
        #Build debs
        #./build-svn-packages.sh &>/dev/null

        #Build API docs
        if [ $DOCS = "yes" ]; then
            echo "`date` Building API Docs" | tee -a $LOGFILE
            $TEST_DIR/scripts/make-doc.sh --quiet
            $TEST_DIR/scripts/upload-doc.sh
        fi
    fi
    
    #Dont sleep if not run in loop
    if [ $LOOP = "yes" ]; then
        echo "`date` Sleeping" | tee -a $LOGFILE
        sleep $SLEEP_TIME
    fi

    CNT=`expr $CNT + 1`
done

echo "`date` Finished" | tee -a $LOGFILE
cd - &>/dev/null



