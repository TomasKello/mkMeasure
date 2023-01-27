# mkMeasure
Multi-device control console application. Plug-n-Play design for serial RS232 and I2C connection. Considered device types:  
- multimeters
- HV sources 
- motion controller 
- environmental readings

# Get repository: 
git clone https://github.com/TomasKello/mkMeasure.git

# Install:  
cd mkMeasure/install  
(Install pre-requisites in requirements.txt)  
chmod u+rwx setup.sh  
./setup.sh  

# Re-compile if needed:  
cd mkMeasure/install  
chmod u+rwx update.sh  
./update.sh  

# Quick start:
`mkMeasure  --addPort zstation,probeFast -vvv --txt --json --csv --png --expOhm 1e7 -d FMX -o FMX_Sandwich_Bottom_Number --cfg IV_5-800step20.py`
- `--cfg` defines path to configuration file (default search dir is `configuration/IV_5-800step20.py`)
- options `-d` and `-o` define path to output directory and nametag: `results/FMX/FMX_Sandwich_Bottom_Number_YYYYMMDD.<format>`
- options `--txt/json/csv/png` define output <format>
- `--addPort` enlists device types communicating through RS232 protocol needed per measurement defined in config (zstation, probeFast, probe, source)
- `--expOhm` defines ballpark of operational "resistance" (in Ohms) to set correct resolution. Option is used instead of `--autoRange` to speed up
measurement.
- `-vvv` defines 3rd level of verbosity (debug)
  
`mkMeasure --addPort probe -vvv -e all`
- read enviro input only
  
`mkMeasure --term`
`mkMeasure --abort`
- mkMeasure has autonomous abort system
- these options serve only to manually terminate (soft) or abort (hard) all devices after unresolved emergency or unpredicted program crash

# All options:
```
usage: mkMeasure [-h] [--testPort | --testMeas | --testStatus] [--selectPort]
                 [--extVSource] [--addPort ADDPORT] [--addSocket ADDSOCKET]
                 [--expOhm expected_resistance] [--autoSensing] [--autoRange]
                 [-v] [-o OUTPUTFILE] [-d OUTPUTDIR] [--txt] [--json] [--csv]
                 [--xml] [--root] [--png] [--pdf] [--db]
                 [--cfg CONFIGFILE | -s <bias> | -m <bias_range> | -c <bias_range> | -e <enviro> | -g <cont_enviro> | -w <stand_by_mode>]
                 [-r <repeat>] [--sampleTime <sample_time>]
                 [--nSamples <n_samples>] [--debug] [--term | --abort]

optional arguments:
  -h, --help            show this help message and exit
  --testPort            Find available ports and exit measurement.
  --testMeas            Try single IV measurement with +-10V.
  --testStatus          Show device status.
  --selectPort          Disable automatic port selection.
  --extVSource          Use the secondary device as a VSource.
  --addPort ADDPORT     Enable additional port to be used as RS232.
  --addSocket ADDSOCKET
                        Enable additional port to be used as Client.
  --expOhm expected_resistance
                        Expected resistance order.
  --autoSensing         Enable automatic current sensing when placing probe.
  --autoRange           Enable automatic autorange for measured function.
  -v, --verbosity       Increase output verbosity
  -o OUTPUTFILE, --outputFile OUTPUTFILE
                        Output file name.
  -d OUTPUTDIR, --outputDir OUTPUTDIR
                        Output directory.
  --txt                 Produce output in txt format.
  --json                Produce output in json format.
  --csv                 Produce output in csv format.
  --xml                 Produce output in xml format.
  --root                Produce output in root format.
  --png                 Produce output in png format.
  --pdf                 Produce output in pdf format.
  --db                  Input/Outpur are taken/saved in DB.
  --cfg CONFIGFILE      Define measurement inside of config file.
  -s <bias>, --single <bias>
                        Single IV measurement. USAGE: -s 60.5
  -m <bias_range>, --multi <bias_range>
                        Multiple point IV measurement. USAGE: -m start end
                        incr OR -c [1,2,3,4]
  -c <bias_range>, --continuous <bias_range>
                        Continuous IV measurement. USAGE: -c start end incr OR
                        -c [1,2,3,4]
  -e <enviro>, --enviro <enviro>
                        Enviro readings: all, temp, humi or lumi.
  -g <cont_enviro>, --contenv <cont_enviro>
                        Continuous Enviro measurement. USAGE: -g <type>
                        [<timeStep> <nSteps>]
  -w <stand_by_mode>, --standBy <stand_by_mode>
                        Stanby mode with motion controller in position.
                        Possible to measure enviro readings.
  -r <repeat>, --repeat <repeat>
                        Repeat selected measurement for R=1..N. Do nothing for
                        R=0,-1. Repeat endlessly for R=-2. Value ignored if
                        cfg provided.
  --sampleTime <sample_time>
                        Sample time for each range point.
  --nSamples <n_samples>
                        Number of samples for each range point.
  --debug               Bypass several options.
  --term                Immediately terminate all devices.
  --abort               Immediately abort all devices.
```
