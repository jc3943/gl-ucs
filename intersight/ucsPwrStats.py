# Jeff Comer
# click app to get ucs imc power stats via flask app

import click
import requests
import urllib3
import urllib.parse
import os
import csv
import sys
from time import localtime,strftime
import time
import datetime
# sys.path.append('/usr/lib64/python3.6/site-packages')
# sys.path.append('/usr/lib/python3.9/site-packages')
# sys.path.append('/usr/lib/python3.6/site-packages')

API_BASE_URL = "http://172.0.1.10:5002"
API_ENDPOINT = "/imc/pwrStats"

@click.command()
@click.option("--cimc_ip", type=str, help='CIMC Ip Address of host', required=False)
def getUcsPwrStats(cimc_ip):
    newDict = {}
    if not cimc_ip:
        pwrStatsTargetUrl = API_BASE_URL + API_ENDPOINT
    else:
        pwrStatsTargetUrl = API_BASE_URL + API_ENDPOINT + f'?cimc_ip={cimc_ip}'
    response = requests.get(pwrStatsTargetUrl, verify=False).json()
    for respKey, respItem in response.items():
        newDict['hostname'] = respKey
        newDict['timestamp'] = datetime.datetime.utcnow().isoformat() + "Z"
        newDict.update(respItem)
        #print(newDict)
        event_str = '\t'.join(f'{key}="{value}"' for key, value in newDict.items())
        print(event_str)
    #print(indexTime, response)

if __name__ == "__main__":
    getUcsPwrStats()
