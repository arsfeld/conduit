#!/bin/bash
USAGE="\
Usage:\n\
.$0 [OPTIONS]\n\n\
Options:\n\
    -d      Delete invalid tickets\n
"

#Parse command line arguments
do_delete=0
while getopts "d" options
do
    case $options in
        d )     do_delete=1;;
        \? )    echo -e $USAGE
                exit 1;;
        * )     echo -e $USAGE
                exit 1;;
    esac
done

echo "Invalid Bugs"
wget -q -O - "http://www.conduit-project.org/query?format=csv&status=closed&resolution=invalid&order=priority" | sed 1d | awk -F, '{print $1,$2}'

if [ $do_delete -eq 1 ] ; then
    BUGS=`wget -q -O - "http://www.conduit-project.org/query?format=csv&status=closed&resolution=invalid&order=priority" | sed 1d | awk -F, '{print $1}'`
    for b in $BUGS
    do
        echo "Deleting $b"
    done
fi

