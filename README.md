# F1-WLED-Live

The goal of this code is to use live F1 timing data to visualise the current gaps between drivers on a WLED strip, for me that strip is behind my TV

## Current setup

Currently I am using [f1stuff's setup](https://github.com/f1stuff/f1-live-data) to ingest the live (or recorded) data into a InfluxDB2 database. While that is running the provided script is executed, takes the data from the InfluxDB, creates a frame for the LEDs and sends it to [WLED](https://github.com/Aircoookie/WLED) using the UDP interface. The current roundtrip is around 250ms, fast enough to have the strip do a lap close to realtime.

## Limitations

Currently this setup has some limitations:

* The script uses timing data and not position data and the reference frame is the last lap of the leader, lapped drivers will not be visualized.
* The data is close to realtime, however the animation going around the strip is not.
* Two scripts need to run at the same time, talking to InfluxDB, this is not ideal for the DB and the script should probably keep the data in RAM an directly lisren to the F1 timing server.
* To support the next (2024) season the driver data in f1stuff's code needs to be updated to reflect driver changes (RIC for DEV). Run ```pip install .``` after you made the change.

## Usage

In order for this to work you need to do a couple of things:

* Configure your hosts (InfluxDB and WLED), the strip length etc. before the race
* Start the data ingestion from f1-live-data
* Start the script (ideally on another computer)

## Long-term ideas

* Skip the data base and keep timing data in RAM to speed up the process
* Make the logic for the LEDs more robust, potentially including lapped cars
* Move from a script on a laptop to a HomeAssistant Add-on or integration

## Demo


https://github.com/plaetzchen/F1-WLED-Live/assets/365135/43a54522-2f14-484f-90b2-ea250cebc6b2


Note that the race shown is not the data used for the WLED
