#!/bin/bash
#Automatically creates a deb file of the specified version
#
#If the version is a major verson 0.X.0 then the changelog data from
#the trac bug tracker is folded in and added as entries to the debian changelog
#
#If its a minor release then no changelog entries are added


#Check command line args
NO_ARGS=0
if [ $# -eq "$NO_ARGS" ]  # Script invoked with no command-line args?
then
    echo "Usage: `basename $0` version"
    exit 1
fi 
VERSION=$1

#Compute if this is a major or minor version
MINOR=`echo $VERSION | awk -F . '{print $3}'`

if [ $MINOR -eq 0 ]
then #Major Release
    echo "New v$VERSION Release"
    echo "Adding entry to debian changelog"
    dch -v $VERSION "New version with the following improvements:"
    #Only add changelog entries if we havent already done so 
    #i.e. the version doesnt yet exist
    if [ $? -eq 0 ]
    then
        echo "Fetching closed bugs from website"
        #Script-foo. Write this to a temp file and replace spaces with
        #underscores otherwise....
        wget -q -O \
            - "http://www.conduit-project.org/query?status=closed&format=csv&milestone=$VERSION&order=priority" | \
            sed 1d | \
            awk -F , '{print $2}' | \
            sed -e "s/\ /_stupid_spaces_/g"\
            > changes
        echo "Adding changelog entries for bugs"
        #...This loop tokenizes on spaces
        for i in `cat changes`
        do
            #Now replace the underscores with spaces again
            dch -a `echo $i | sed -e 's/_stupid_spaces_/\ /g'`
        done
        #Remove temp file and exit
        rm changes
    else
        echo "v$VERSION allready added. Not adding changelog entries"
    fi
else #Minor Release
    echo "Minor v$VERSION Release"
    echo "Adding entry to debian changelog"
    dch -v $VERSION "Bugfix Release"
fi 

#Binary??? unsigned package
debuild -i -uc -us -b
debuild clean

exit 0
