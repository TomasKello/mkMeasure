#!/bin/bash

#compile
cd ../source
/usr/bin/python3 -m PyInstaller --clean mkMeasure.spec

#kill running binaries
runningMacros=`pgrep SensBoxEnvSer`
macrosArray=($(echo $runningMacros | tr ' ' "\n"))
for macro in "${macrosArray[@]}"
do
    kill $macro
done

#create bin arch
if [ ! -d "../bin/" ]
then
    mkdir ../bin/
fi

#copy build executable
cp -R dist/mkMeasure/* ../bin/

echo "Update Done."
