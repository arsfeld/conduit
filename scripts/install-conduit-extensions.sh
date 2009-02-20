#!/bin/sh

APP="conduit/conduit"
if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    exit 1
fi

CONDUIT_DIR=`pwd`
EOG_PLUGIN_DIR=~/.gnome2/eog/plugins/
TOTEM_PLUGIN_DIR=~/.config/totem/plugins/conduit
NAUTILUS_PLUGIN_DIR=~/.nautilus/python-extensions

echo "Installing EOG Plugin"
mkdir -p $EOG_PLUGIN_DIR
ln -f --symbolic $CONDUIT_DIR/conduit/libconduit.py $CONDUIT_DIR/tools/eog-plugin/conduit.{eog-plugin,py} $EOG_PLUGIN_DIR/

echo "Installing Totem Plugin"
mkdir -p $TOTEM_PLUGIN_DIR
ln -f --symbolic $CONDUIT_DIR/conduit/libconduit.py $CONDUIT_DIR/tools/totem-plugin/conduit.{totem-plugin,py} $TOTEM_PLUGIN_DIR/

echo "Installing Nautilus Extension"
mkdir -p $NAUTILUS_PLUGIN_DIR
ln -f --symbolic $CONDUIT_DIR/conduit/libconduit.py $CONDUIT_DIR/tools/nautilus-extension/conduit.py $NAUTILUS_PLUGIN_DIR/

