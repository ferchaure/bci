#!/usr/bin/python
#Configurations for process communications
import config



TIMEOUT_GET=int(config.PAQ_USB/config.FS)
TIMEOUT_PUT=int(config.PAQ_USB/config.FS)/10

#--------
GRAPH_DATA_BUFFER=15
DATA_BUFFER=15
WARNIGNS_BUFFER =50

#--------
EXIT_SIGNAL=0
STOP_SIGNAL=1
START_SIGNAL=2

SLOW_PROCESS_SIGNAL=3
SLOW_GRAPHICS_SIGNAL=4
SLOW_CAPTURE_DATA=5
DATA_NONSYNCHRONIZED=6
DATA_CORRUPTION=7
COUNTER_ERROR=8
DATA_NONSYNCHRONIZED=9
CANT_SYNCHRONIZE=10

#--------
Errors_Messages = {SLOW_PROCESS_SIGNAL: "Loss data in processing", 
SLOW_GRAPHICS_SIGNAL: 'Loss data in graphics',
COUNTER_ERROR: 'Counter, data loss',
CANT_SYNCHRONIZE: 'Cant synchronize',
DATA_NONSYNCHRONIZED: 'data non-synchronized',
DATA_CORRUPTION: 'the data corrupted'}

