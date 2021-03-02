#!/usr/bin/env bash

# Obtain latest stable version
TEMP_FILE=/tmp/curl2.out
curl -s  https://chromedriver.storage.googleapis.com/LATEST_RELEASE -o $TEMP_FILE
LATEST_VERSION=`head -1 $TEMP_FILE`
echo latest version of driver is: $LATEST_VERSION
# now download it into given named driver folder (current only for windows, need to mod suffix for linux)
MAJOR_VERSION=`echo $LATEST_VERSION | cut -d'.' -f1`
DRIVER_DIR=./app/drivers/chromedriver${MAJOR_VERSION}_win32/
mkdir -p $DRIVER_DIR
TARGET_FILE=$DRIVER_DIR/chromedriver_win32.zip
curl https://chromedriver.storage.googleapis.com/$LATEST_VERSION/chromedriver_win32.zip -o $TARGET_FILE
unzip $TARGET_FILE -d $DRIVER_DIR

# cleanup
rm /tmp/curl2.out
