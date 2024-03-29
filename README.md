# F1-WLED-Live

The goal of this code is to use live F1 timing data to visualise the current gaps between drivers on a WLED strip, for me that strip is behind my TV

## Current setup

Currently I am using [f1stuff's setup](https://github.com/f1stuff/f1-live-data) to ingest the live (or recorded) data into a InfluxDB2 database. While that is running the provided script is executed, takes the data from the InfluxDB, creates a frame for the LEDs and sends it to [WLED](https://github.com/Aircoookie/WLED) using the UDP interface. The current roundtrip is around 250ms, fast enough to have the strip do a lap close to realtime.

## Limitations

Currently this setup has some limitations:

* The script uses timing data and not position data and the reference frame is the last lap of the leader, lapped drivers will not be visualized.
* The data is close to realtime, however the animation going around the strip is not.
* Two scripts need to run at the same time, talking to InfluxDD. This is not ideal for the DB and the script should probably keep the data in RAM and directly listen to the F1 timing server.
* To support the 2024 season the driver data in f1stuff's code needs to be updated. I did so in my fork and opened a pull request.

## Usage

In order for this to work you need to do a couple of things:

* Configure your hosts (InfluxDB and WLED), the strip length etc. before the race
  - If you use the f1stuff Docker setup use the following:
    - ```INFLUX_TOKEN = "wwPE9MycN2RzYX2ngYuap-Ri5pt5YOrxcVqN_u46SOs6CBj8SGKzxBHJpLnLfPrXLJZFLpEtzwoJR3Ik_8M2NQ=="```
    - ```INFLUX_ORG = "c6d6c0228d6fd3ea"```
    - ```INFLUX_URL = "http://localhost:8086"```
* Start the data ingestion from f1-live-data
  - See the Readme of F1stuff on how to do that
* Start the script (ideally on another computer)
  - ```python f1-wled-live.py```

## Long-term ideas

* Skip the database and keep timing data in RAM to speed up the process
* Make the logic for the LEDs more robust, potentially including lapped cars
* Move from a script on a laptop to a HomeAssistant Add-on or integration

## Demo


https://github.com/plaetzchen/F1-WLED-Live/assets/365135/43a54522-2f14-484f-90b2-ea250cebc6b2


Note that the race shown is not the data used for the WLED
