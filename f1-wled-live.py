#!/usr/bin/env python3

import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import time
import socket
import atexit
import os

## Configure Influx DB
INFLUX_TOKEN = os.environ["INFLUX_TOKEN"]
INFLUX_ORG = "Call a Nerd"
INFLUX_URL = "http://influxdb.local:8086"

WLED_IP = "wled-tv.local"
WLED_PORT = 21324
WLED_LED_COUNT = 110

## The global counter for the animation 
current_frame = 0

## The global variable for the WLED socket to be able to close it
sock = None


## Colors are no all the official team colors since they don't work on a LED, especially Haas 
driver_colors = {
    "ALB": "37BEDD",
    "ALO": "0E784A",
    "BOT": "00E701",
    "DEV": "7598AA",
    "GAS": "2293D1",
    "HAM": "6CD3BF",
    "HUL": "FFFFFF",
    "LEC": "FF0000",
    "MAG": "FFFFFF",
    "NOR": "F58020",
    "OCO": "2293D1",
    "PER": "0000FF",
    "PIA": "F58020",
    "RIC": "7598AA",
    "RUS": "6CD3BF",
    "SAI": "FF0000",
    "SAR": "37BEDD",
    "STR": "0E784A",
    "TSU": "7598AA",
    "VER": "0000FF",
    "ZHO": "00E701"
}


def getDataFromDB():
    collected_data = {}
    query_client = influxdb_client.InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = query_client.query_api()
    ## Query taken from the Grafana dashboard's table, this could be easier?
    query = """gapDataHumanReadable = from(bucket: "data")
        |> range(start: 0)
        |> filter(fn: (r) => r["_measurement"] == "gapToLeader")
        |> filter(fn: (r) => r["_field"] == "GapToLeaderHumanReadable")
        |> last()
        |> group()
        |> keep(columns: ["driver", "_value"])
        gapData = from(bucket: "data")
        |> range(start: 0)
        |> filter(fn: (r) => r["_measurement"] == "gapToLeader")
        |> filter(fn: (r) => r["_field"] == "GapToLeader")
        |> last()
        |> group()
        |> keep(columns: ["driver", "_value"])
        intervalData = from(bucket: "data")
        |> range(start: 0)
        |> filter(fn: (r) => r["_measurement"] == "intervalToPositionAhead")
        |> filter(fn: (r) => r["_field"] == "IntervalToPositionAhead")
        |> last()
        |> group()
        |> keep(columns: ["driver", "_value"])
        lastLapData = from(bucket: "data")
        |> range(start: 0)
        |> filter(fn: (r) => r["_measurement"] == "lastLapTime")
        |> filter(fn: (r) => r["_field"] == "LastLapTime")
        |> last()
        |> group()
        |> keep(columns: ["driver", "_value"])
        numberLapsData = from(bucket: "data")
        |> range(start: 0)
        |> filter(fn: (r) => r["_measurement"] == "numberOfLaps")
        |> filter(fn: (r) => r["_field"] == "NumberOfLaps")
        |> last()
        |> group()
        |> keep(columns: ["driver", "_value", "_time"]) 
        intermediateJoinData1 = join(tables: {gapHumanReadable:gapDataHumanReadable, interval:intervalData},on: ["driver"],)
        intermediateJoinData2 = join(tables: {intermediateJoin1:intermediateJoinData1, numberLaps:numberLapsData},on: ["driver"],)
        intermediateJoinData3 = join(tables: {intermediateJoin1:intermediateJoinData2, gap:gapData},on: ["driver"],)
        join(
            tables: {intermediateJoin:intermediateJoinData3, lastLap:lastLapData},
            on: ["driver"],)
        |> sort(columns: ["_time"], desc: false)  
        |> sort(columns: ["_value_gap"], desc: false)
        |> sort(columns: ["_value_intermediateJoin1"], desc: true)
        |> fill(column: "position", value: 1.0)
        |> cumulativeSum(columns: ["position"])
        |> map(fn: (r) => ({ r with interval: r._value_interval * 1000.0 }))
        |> map(fn: (r) => ({ r with lastLap: r._value * 1000.0 }))"""
    tables = query_api.query(query, org="Call a Nerd")
    
    table = tables[0]
    for idx, record in enumerate(table.records):
        driver = record["driver"]
        gapToLeader = record["_value_gap"]
        lastLapTime = record["_value"]
        collected_data[driver] = {"gapToLeader":gapToLeader,"position":idx,"color":driver_colors[driver],"lastLapTime":lastLapTime}
        
    leader = list(collected_data.keys())[0]
    leaderData = collected_data[leader]
    lastLeaderRound = leaderData["lastLapTime"]
    
    ## If there is no lap yet just make it some lap time
    if lastLeaderRound < 1:
        lastLeaderRound = 100
    
    ## Defines how fast the cars go around the strip, currently the lap should roughly fit into one round
    secondsPerSegment = lastLeaderRound / WLED_LED_COUNT
    
    ## Keep all LEDs with no car off
    black_color = "000000"
    led_segments = []
    
    ## This whole block of code for calculating which driver is where on the strip works but is not very pretty, should be fixed
    led_segments.append(leaderData["color"])
    nextDriver = 1
    for i in range(WLED_LED_COUNT-1):
        color = black_color
        nextDriverName = list(collected_data.keys())[nextDriver]
        gapSeconds = (i+1)*secondsPerSegment
        nextDriverData = collected_data[nextDriverName]
        nextDriverGap = nextDriverData["gapToLeader"]
        if(gapSeconds >= nextDriverGap and nextDriver < len(collected_data)-1):
            color = nextDriverData["color"]
            nextDriver = nextDriver + 1
        elif(nextDriver >= len(collected_data)-1):
            nextDriver = len(collected_data)-1
            color = black_color
        led_segments.append(color)
    return led_segments, secondsPerSegment


## Use the UDP API to send the data as fast as possible to the strip
def sendFrameToLeds(next_frame):
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    protocol = 1
    timeout = 1
    
    colors = []
    for color in next_frame:
        rgb_color = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        colors.append(rgb_color)

    data = bytearray([protocol, timeout])
    for i in range(WLED_LED_COUNT):
        data += bytearray([i, colors[i][0], colors[i][1], colors[i][2]])
    data[1] = 255
    sock.sendto(data, (WLED_IP, WLED_PORT))

## Trying to be a good citizen when the strip is stopped 
def closeSock():
    print("Closing socket")
    sock.close()

## The animation that makes the cars go around the strip. Works but could be cleaner
def shiftFrame(frame):
    global current_frame
    secondHalf = frame[current_frame:]
    firstHalf = frame[:current_frame]
    secondHalf.extend(firstHalf)
    current_frame = current_frame + 1
    if(current_frame == WLED_LED_COUNT):
        current_frame = 0
    return secondHalf

def main():
    atexit.register(closeSock)
    while True:
        frame, seconds_per_segment = getDataFromDB()
        shiftedFrame = shiftFrame(frame)
        sendFrameToLeds(shiftedFrame)
        time.sleep(seconds_per_segment)
        
if __name__ == "__main__":
    main()