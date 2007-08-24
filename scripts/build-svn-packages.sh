#!/bin/sh

# Generates automated Debian packages for Conduit <http://conduit-project.org>
# Author: Jonny Lamb <jonnylamb@jonnylamb.com>
#
# Things to note:
#  * svn.greenbirdsystems.com's certificate has expired, and needs accepting permanently.
#    To do this, simply do "svn co https://svn.greenbirdsystems.com/conduit/trunk conduit"
#    yourself somewhere and press "p" when prompted.
#
# Requirements:
#  For this script to work:
#   * devscripts, dpkg-dev, subversion, gnome-common
#  And all the Build-dependencies for Conduit (some of these are unnecessary thanks to
#  recent commits, but are required until they're removed from debian/control):
#   * debhelper, python-support, python-all-dev, dpatch, python-vobject, libdbus-1-dev
#     python-pygoocanvas, python-gtk2-dev, intltool

# Directory to build the packages. This is a temporary directory and will be deleted
# at the end of the process
TMPDIR=/tmp/conduit/build

# Directory to keep the changelog file. There will be a single file inside this directory
# named changelog.
CHANGELOGDIR=/tmp/conduit/changelog

# Directory to publish the packages. I.e. where to put the packages and the sources.
# Ideally this'll be the actual webspace of e.g. debian.conduit-project.org, as
# dpkg-scan{sources,packages} is run inside that directory.
PUBLISHDIR=/tmp/conduit/packages

# Magic continues below.

mkdir $TMPDIR
cd $TMPDIR

# First checkout trunk so that the SVN version can be determined.
# This could be done a nicer way like using pysvn perhaps?
svn co --non-interactive https://svn.greenbirdsystems.com/conduit/trunk conduit
cd conduit

SVNREV=`svnversion .`

# Now get rid of all the horrible ".svn" directories.
# They rot the mind.
find -name "\.svn" | xargs rm -rf

# Hack out the version number from configure.ac. A VERSION file would be nice :)
VERSION=`perl -ne 'print $1 if /^AC_INIT\([^,]*, *\[([\d.]+)/' configure.ac`

# Run all the -ize tools.
NOCONFIGURE=1 sh ./autogen.sh

# Create the orig.tar.gz.
cd ..
tar -czf "conduit_$VERSION+svn$SVNREV.orig.tar.gz" conduit

# Clean up the directory name. Not necessary.
mv conduit "conduit-$VERSION+svn$SVNREV"

cd "conduit-$VERSION+svn$SVNREV"

# Now get Jose Carlos Garcia Sogo's packaging.
# No point in duplicating work.
svn export svn://svn.tribulaciones.org/srv/svn/conduit/trunk/debian

# This will return true on every run apart from the initial run.
# Only use jsogo's changelog if our running one doesn't already exist.
if [ -e "$CHANGELOGDIR/changelog" ]; then
  rm debian/changelog
  cp "$CHANGELOGDIR/changelog" debian/
fi

# Add a new changelog entry.
DEBEMAIL="debian@conduit-project.org" DEBFULLNAME="Conduit Packages" dch -v "$VERSION+svn$SVNREV-1" "New upstream SVN version."

# Build the package. Do not sign any files.
dpkg-buildpackage -rfakeroot -uc -us

# Copy all the nice generated files to the publishing directory
cp ../*.deb $PUBLISHDIR
cp ../*.diff.gz $PUBLISHDIR
cp ../*.orig.tar.gz $PUBLISHDIR
cp ../*.dsc $PUBLISHDIR

# Put the updated changelog file in its stored place.
cp debian/changelog $CHANGELOGDIR

# Get out of the temporary directory.
cd $PUBLISHDIR

# Get rid of the temporary directory.
rm -rf $TMPDIR

# Generate Packages and Packages.gz files for using as an APT package source.
dpkg-scanpackages . /dev/null | tee Packages | gzip -9 > Packages.gz

# Generate Sources and Sources.gz files for using as an APT package source, source.
dpkg-scansources . /dev/null | tee Sources | gzip -9 > Sources.gz
