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

#make script globally invoked
echo "export PATH=\"\$PATH:/home/adaq/IIHE/mkMeasure/bin\"" >> ~/.bashrc

echo "Installation complete."
