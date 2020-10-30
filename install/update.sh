#!/bin/bash

#compile
cd ../source
/usr/bin/python3 -m PyInstaller --clean mkMeasure.spec

#kill running binaries
runningMacros=`pgrep SensBoxEnv`
if [ ! -z $runningMacros ]
then
    kill `echo $runningMacros`
fi

#create bin arch
if [ ! -d "../bin/" ]
then
    mkdir ../bin/
fi

#copy build executable
cp -R dist/mkMeasure/* ../bin/

echo "Update Done."