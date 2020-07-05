#!/usr/bin/python
# coding=utf-8
#
# This script loads a qlog file and computes statistics

import sys
import json
import traceback

# To test, use file sample/small.qlog or sample/big.qlog

if len(sys.argv) == 2:
    file_name = sys.argv[1]
else:
    print("Usage: " + sys.argv[0] + " filename.qlog")
    exit(-1)

try:
    packets_sent = 0
    packets_lost = 0
    next_lost_packet_number = -1
    consecutive_losses = 0
    congestion_losses = 0
    congestion_consecutive = 0
    min_rtt = 999999999
    max_rtt = 0
    with open(file_name) as json_file:
        data = json.load(json_file)
        print("Data has length: " + str(len(data)))
        for key in data:
            print(key + ": " + str(len(data[key])))
        if 'traces' in data:
            traces = data['traces']
            for trace in traces:
                if 'events' in trace: 
                    print("events: " + str(len(trace['events'])))
                    for event in trace['events']:
                        # TODO: compute RTT min/max as seen on traces
                        if len(event) >= 4 and event[1].casefold() == 'recovery'.casefold() and event[2].casefold() == 'metrics_updated'.casefold():
                            metric_data = event[3]
                            if 'latest_rtt' in metric_data:
                                rtt = int(metric_data['latest_rtt'])
                                if rtt < min_rtt:
                                    min_rtt = rtt
                                if rtt > max_rtt:
                                    max_rtt = rtt
                    print("min_rtt: " + str(min_rtt))
                    print("max_rtt: " + str(max_rtt))
                    threshold_rtt = int ((min_rtt + 15*max_rtt)/16)
                    print("threshold_rtt: " + str(threshold_rtt))
                    latest_rtt = min_rtt

                    for event in trace['events']:
                        # TODO: tracking of packets sent in both directions, packets acked, and MTU. (MTU statistics.)
                        if len(event) >= 4 and event[1].casefold() == 'recovery'.casefold() and event[2].casefold() == 'metrics_updated'.casefold():
                            metric_data = event[3]
                            if 'latest_rtt' in metric_data:
                                latest_rtt = int(metric_data['latest_rtt'])
                        if event[1].casefold() == 'transport'.casefold() and event[2].casefold() == 'packet_sent'.casefold():
                            packets_sent += 1
                        if len(event) >= 4 and event[1].casefold() == 'recovery'.casefold() and event[2].casefold() == 'packet_lost'.casefold():
                            packets_lost += 1
                            loss_data = event[3]
                            if latest_rtt > threshold_rtt:
                                congestion_losses += 1
                            if 'packet_number' in loss_data and 'packet_type' in loss_data and loss_data['packet_type'].casefold() == "1rtt".casefold() :
                                pn = int(loss_data['packet_number'])
                                if pn == next_lost_packet_number:
                                    consecutive_losses += 1
                                    if latest_rtt > threshold_rtt:
                                        congestion_consecutive += 1
                                next_lost_packet_number = pn + 1

                    print("packets_sent: " + str(packets_sent))
                    print("packets_lost: " + str(packets_lost))
                    print("consecutive_losses: " + str(consecutive_losses))
                    print("congestion_losses: " + str(congestion_losses))
                    print("congestion_consecutive: " + str(congestion_consecutive))

except Exception as e:
    traceback.print_exc()
    print("Cannot load <" + file_name + ">, error: " + str(e));
