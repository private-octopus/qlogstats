#!/usr/bin/python
# coding=utf-8
#
# This script loads a qlog file and computes statistics

import sys
import json
import traceback
import os
from os.path import isfile, join

class qlogstats:
    def __init__(self):
        self.packet_received = 0
        self.packets_sent = 0
        self.packets_lost = 0
        self.next_lost_packet_number = -1
        self.consecutive_losses = 0
        self.pre_hs_losses = 0
        self.congestion_losses = 0
        self.congestion_consecutive = 0
        self.other_losses = 0
        self.min_rtt = 999999999
        self.max_rtt = 0
        self.threshold_rtt = 0
        self.content_length = 0
        self.nb_events = 0

    def csv_header():
        header = "packets sent, lost, consec_losses, pre_hs_losses, cc_losses, consec_cc_losses, other_losses, min_rtt, max_rtt, threshold_rtt,"
        return header

    def csv_line(self):
        csv_line = str(self.packets_sent) + "," + str(self.packets_lost) + "," + \
            str(self.consecutive_losses) + "," + str(self. pre_hs_losses) + "," + \
            str(self.congestion_losses) + "," + str(self.congestion_consecutive) + "," + \
            str(self.other_losses) + "," + \
            str(self.min_rtt) + "," + str(self.max_rtt) + "," + str(self.threshold_rtt) + ","
        return csv_line

    def load(self, file_name):
        ret = True
        try:
            with open(file_name) as json_file:
                data = json.load(json_file)
                self.content_length = str(len(data))
                # for key in data:
                #    print(key + ": " + str(len(data[key])))
                if 'traces' in data:
                    traces = data['traces']
                    for trace in traces:
                        time_rank = -1
                        group_id_rank = -1
                        category_rank = -1
                        event_rank = -1
                        data_rank = -1
                        event_len_min = -1

                        if 'event_fields' in trace:
                            event_field_error = False
                            event_fields = trace['event_fields']
                            field_rank = 0
                            while field_rank < len(event_fields):
                                event_name = event_fields[field_rank].casefold()
                                if event_name == "category":
                                    if category_rank == -1:
                                        category_rank = field_rank
                                        event_len_min = field_rank+1
                                    else:
                                        print ("error : category listed twice in event field.");
                                        event_field_error = True
                                elif event_name == "event" or event_name == "event_type":
                                    if event_rank == -1:
                                        event_rank = field_rank
                                        event_len_min = field_rank+1
                                    else:
                                        print ("error : event listed twice in event field.");
                                        event_field_error = True
                                elif event_name == "data":
                                    if data_rank == -1:
                                        data_rank = field_rank
                                        event_len_min = field_rank+1
                                    else:
                                        print ("error : data listed twice in event field.");
                                        event_field_error = True
                                field_rank += 1
                
                        if 'events' in trace: 
                            if category_rank == -1 or event_rank == -1 or data_rank == -1:
                                print("error : no rank defined for one of category, event and data.")
                                event_field_error = True
                            if event_field_error:
                                print("cannot process events due to event field error.")
                                break
                            self.nb_events = str(len(trace['events']))
                            rtt_found = False
                            for event in trace['events']:
                                # compute RTT min/max as seen on traces
                                if len(event) >= event_len_min and event[category_rank].casefold() == 'recovery'.casefold() and event[event_rank].casefold() == 'metrics_updated'.casefold():
                                    metric_data = event[data_rank]
                                    if 'latest_rtt' in metric_data:
                                        rtt_found = True
                                        rtt = int(metric_data['latest_rtt'])
                                        if rtt < self.min_rtt:
                                            self.min_rtt = rtt
                                        if rtt > self.max_rtt:
                                            self.max_rtt = rtt
                            if rtt_found:
                                self.threshold_rtt = int ((self.min_rtt + 31*self.max_rtt)/32)
                                if self.threshold_rtt > 2*self.min_rtt:
                                    self.threshold_rtt = 2*self.min_rtt
                            latest_rtt = self.min_rtt
                            
                            received_1rtt = False
                            sent_1rtt = False
                            post_handshake = False

                            for event in trace['events']:
                                # TODO: tracking of packets sent in both directions, packets acked, and MTU. (MTU statistics.)
                                category = event[category_rank].casefold()
                                event_type = event[event_rank].casefold()
                                if len(event) >= event_len_min and category == 'recovery' and event_type == 'metrics_updated':
                                    metric_data = event[data_rank]
                                    if 'latest_rtt' in metric_data:
                                        latest_rtt = int(metric_data['latest_rtt'])
                                elif len(event) >= event_len_min and category == 'transport' and event_type == 'packet_received':
                                    self.packet_received += 1
                                    packet = event[data_rank]
                                    if 'packet_type' in packet:
                                        packet_type = packet['packet_type'].casefold()
                                        if not received_1rtt and (packet_type == '1rtt' or packet_type == 'onertt'):
                                            received_1rtt = True
                                            post_handshake = sent_1rtt
                                elif len(event) >= event_len_min and category == 'transport' and event_type == 'packet_sent':
                                    self.packets_sent += 1
                                    packet = event[data_rank]
                                    if 'packet_type' in packet:
                                        packet_type = packet['packet_type'].casefold()
                                        if not sent_1rtt and (packet_type == '1rtt' or packet_type == 'onertt'):
                                            sent_1rtt = True
                                            post_handshake = received_1rtt
                                elif len(event) >= event_len_min and category == 'recovery' and event_type == 'packet_lost':
                                    self.packets_lost += 1
                                    loss_data = event[data_rank]
                                    if not post_handshake:
                                        self.pre_hs_losses += 1
                                        is_congestion_loss = False
                                    else:
                                        is_congestion_loss = rtt_found and latest_rtt > self.threshold_rtt
                                    if is_congestion_loss:
                                        self.congestion_losses += 1
                                    if 'packet_number' in loss_data and 'packet_type' in loss_data and loss_data['packet_type'].casefold() == "1rtt":
                                        pn = int(loss_data['packet_number'])
                                        if pn == self.next_lost_packet_number:
                                            self.consecutive_losses += 1
                                            if is_congestion_loss:
                                                self.congestion_consecutive += 1
                                        self.next_lost_packet_number = pn + 1
        except Exception as e:
            traceback.print_exc()
            print("Cannot load <" + file_name + ">, error: " + str(e));
            ret = False
        self.other_losses = self.packets_lost - self.congestion_losses - self.pre_hs_losses
        return ret

# To test, use file sample/small.qlog or sample/big.qlog

if len(sys.argv) == 3:
    folder = sys.argv[1]
    csv_file = sys.argv[2]
else:
    print("Usage: " + sys.argv[0] + " folder csv_file")
    exit(-1)

print(folder)

if not isfile(csv_file):
    f = open(csv_file, "w")
    f.write("file," + qlogstats.csv_header() + "\n")
    f.close()

for x in os.listdir(folder):
    file_name = join(folder, x)
    if isfile(file_name):
        print(file_name)
        if file_name.endswith('.qlog'):
            qs = qlogstats()
            if (qs.load(file_name)):
                f = open(csv_file, "a")
                f.write(x + "," + qs.csv_line() + "\n")

