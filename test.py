#test.py
import requests
import sys
try:
    file_name = sys.argv[1]
    fopen = open(file_name, 'r')
    for x in fopen.readlines():
        url = x.strip('\n')
        req = requests.get(url)
        print url
        print req.status_code
    fopen.close()
except Exception as e:
    print e
