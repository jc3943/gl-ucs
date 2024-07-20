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
    vmAllList = []
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
        vmmHostJson = requests.get(vmmHostApiTargert, verify=False).json()
        for i in range(len(vmmHostJson['vmwareHosts'])):
            hostMoid = vmmHostJson['vmwareHosts'][i]['Moid']
            vmUrl = apiTarget + f'?host_moid={hostMoid}'
            print(vmUrl)
            vmInvJson = requests.get(vmUrl, verify=False).json()
            for k in range(len(vmInvJson["virtualMachines"])):
                #print(hostMoid)
                vmHostDict = vmInvJson["virtualMachines"][k]
                vmHostDict['hostMoid'] = vmmHostJson['vmwareHosts'][i]['Moid']
                vmHostDict['hostName'] = vmmHostJson['vmwareHosts'][i]['Name']
                vmAllList.append(vmHostDict)
            
            #print(vmInvJson)
            keys = vmAllList[0].keys()
        with open(outFileName, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(vmAllList)
        print(vmAllList)



if __name__ == "__main__":
    getUcsInventory()