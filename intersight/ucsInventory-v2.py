# Jeff Comer
# click app to parse args, interact with intersightApiFront.py flask app, and parse response

import click
import requests
import urllib3
import urllib.parse
import os
import csv

API_BASE_URL = "http://localhost:5002"


@click.command()
@click.option("--name", type=str, help='Hostname of server')
@click.option("--type", type=click.Choice(['svrSummary', 'diskInventory', 'vmmHost', 'vmmInventory']), help='[default: svrSummary]', show_default=True, required=True)
def getUcsInventory(name, type):
    diskList = []
    outFilePath = os.environ['dataPath']
    outFileName = outFilePath + "/" + type + ".csv"
    svrApiEndpoint = "/intersight/serverSummary"
    vmmHostApiEndpoint = "/intersight/vmmHosts"
    if type == "svrSummary":
        apiEndpoint = "/intersight/serverSummary"
    elif type == "diskInventory":
        apiEndpoint = "/intersight/physicalDisks"
    elif type == "vmmHost":
        apiEndpoint = "/intersight/vmmHosts"
    elif type == "vmmInventory":
        apiEndpoint = "/intersight/virtMachines"
    svrApiTarget = API_BASE_URL + svrApiEndpoint
    vmmHostApiTargert = API_BASE_URL + vmmHostApiEndpoint
    apiTarget = API_BASE_URL + apiEndpoint
    #responseJson = requests.get(apiTarget, verify=False).json()
    if type == "svrSummary":
        responseJson = requests.get(svrApiTarget, verify=False).json()
        print(responseJson)
        keys = responseJson['servers'][0].keys()
        with open(outFileName, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(responseJson['servers'])
    elif type == "diskInventory":
        for i in range(len(responseJson['diskInventory'])):
            diskDict = responseJson['diskInventory'][i]
            for k in range(len(responseJson['servers'])):
                if responseJson['servers'][k]['DeviceMoId'] == responseJson['diskInventory'][i]['DeviceMoId']:
                    for svrKey, svrItems in responseJson['servers'][k].items():
                        if svrKey == "Name":
                            diskDict[svrKey] = svrItems
                    diskList.append(diskDict)
        print(diskList)
        keys = diskList[0].keys()
        with open(outFileName, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(diskList)
    #print(responseJson)
    elif type == "vmmHost":
        responseJson = requests.get(vmmHostApiTargert, verify=False).json()
        print(responseJson)
        keys = responseJson['vmwareHosts'][0].keys()
        with open(outFileName, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(responseJson['vmwareHosts'])
    elif type == "vmmInventory":
        svrSummaryJson = requests.get(svrApiTarget, verify=False).json()
        for i in range(len(svrSummaryJson['servers'])):
            deviceMoid = svrSummaryJson['servers'][i]['DeviceMoId']
            vmUrl = apiTarget + f'?host_moid={deviceMoid}'
            vmInvJson = requests.get(vmUrl, verify=False).json()
            print(deviceMoid)
            print(vmInvJson)
        #print(svrSummaryJson)



if __name__ == "__main__":
    getUcsInventory()