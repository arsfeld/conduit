#!/bin/bash
USAGE="\
Usage:\n\
./get-closed-bugs.sh -v VERSION_NUMBER[OPTIONS]"

#Parse command line arguments
version="x"
while getopts "hv:" options
do
    case $options in
        v )     version=$OPTARG;;
        h )     echo -e $USAGE
                exit 0;;
        \? )    echo -e $USAGE
                exit 1;;
        * )     echo -e $USAGE
                exit 1;;
    esac
done

if [ $version == "x" ] ; then
    echo -e $USAGE
    exit 1
fi

wget -q -O - "http://www.conduit-project.org/query?status=closed&format=csv&milestone=$version&order=priority" | sed 1d | awk -F, '{print $2}'
