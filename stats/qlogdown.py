#!/usr/bin/python
# coding=utf-8
#
# This script loads a web page that indexes qlog files, and then downloads the individual qlogs

import sys
import requests
import traceback
import os.path

# To test, choose a file containing a list of download url, and a folder

if len(sys.argv) == 3:
    url_list = sys.argv[1]
    folder = sys.argv[2]
else:
    print("Usage: " + sys.argv[0] + " url-list folder")
    exit(-1)

downloaded = 0
try:
    # Using readlines() 
    url_file = open(url_list, 'r') 
    urls = url_file.readlines() 
  
    count = 0
    # Strips the newline character 
    for url in urls: 
        # analyze the URL, extract the doc name
        url = url.strip()
        url_file_parts = url.split("/")
        if len(url_file_parts) < 3:
            print("No file name in " + url)
        else:
            file_name = url_file_parts[len(url_file_parts)-1]
            file_path = folder + file_name
            if os.path.isfile(file_path):
                print("Skipping <" + url + "> as <" + file_path + "> exists.")
            else:
                try:
                    r = requests.get(url) # create HTTP response object 
                    qlog_text = r.content.decode('utf-8')
                    try:
                        file = open(file_path, 'w') 
                        file.write(qlog_text)
                        file.close()
                        print("downloaded " + url + " as " + file_path + ", " + str(len(qlog_text)) + " bytes." )
                        downloaded += 1
                    except Exception as e:
                        traceback.print_exc()
                        print("Cannot save <" + file_path + ">, error: " + str(e));
                        break
                except Exception as e:
                    traceback.print_exc()
                    print("Cannot load <" + url + ">, error: " + str(e));
                    break

except Exception as e:
    traceback.print_exc()
    print("Cannot load <" + file_name + ">, error: " + str(e));

print("Downloaded " + str(downloaded) + " qlog files.")