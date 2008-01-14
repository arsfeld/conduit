#!/bin/bash
APP="conduit/conduit"
ME=`basename $0`
USAGE="\
Usage:\n\
$ME [OPTIONS]\n\
Builds conduit docs using epydoc\n\n\
Options:\n\
\t-h, --help\t\tThis message\n\
\t-q, --quiet\t\tNo console output"

if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    echo -e $USAGE
    exit 1
fi

VERBOSITY='--verbose'
#Check the arguments.
for option in "$@"; do
  case "$option" in
    -h | --help)
      echo -e $USAGE
      exit 0 ;;
    -q | --quiet)
      VERBOSITY='-qqq' ;;
    -*)
      echo "Unrecognized option: $option\n\n$USAGE"
      exit 1 ;;
  esac
done

epydoc  -o doc --name conduit --css white \
        --url http://www.conduit-project.org \
        --inheritance listed \
        --no-frames \
        --parse-only \
        --graph all \
        $VERBOSITY \
        conduit \
        conduit/dataproviders \
        conduit/datatypes \
        doc/ExampleModule.py
