#!/usr/bin/python
# coding=utf-8
#
# This script loads a web page that indexes qlog files, and then downloads the individual qlogs

import sys
import requests
import traceback


# To test, choose a web site that provides qlog files

if len(sys.argv) == 3:
    qlog_index_url = sys.argv[1]
    qlog_list_file = sys.argv[2]
else:
    print("Usage: " + sys.argv[0] + " qlog-server-url list_file")
    exit(-1)

# URL of the index  to be downloaded 
r = requests.get(qlog_index_url) # create HTTP response object 
tx = r.content.decode('utf-8')
tx = tx.casefold()

with open("qlog_index.txt",'w') as f1: 
  
    # Saving received content in text format 
    
    # write the contents of the response (r.content) 
    # to a new file in binary mode. 

    f1.write(tx)

href_parts = tx.split('href=\"')
print("Found " + str(len(href_parts)) + " href parts")
nb_qlog_url = 0

with open(qlog_list_file,'w') as f2:
    for href_part in href_parts:
        url_parts = href_part.split('\">')
        url_dots = url_parts[0].split('.')
        if len(url_dots) > 0 and url_dots[len(url_dots) - 1] == 'qlog' and not "qvis" in url_parts[0] :
            qlog_url = url_parts[0]
            if not qlog_url.startswith("http"):
                qlog_url = qlog_index_url + qlog_url
            f2.write(qlog_url+"\n")
            nb_qlog_url += 1

print("Parsed " + str(nb_qlog_url) + " URLs.")
