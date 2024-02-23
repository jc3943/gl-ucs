import click
import requests
import urllib3
import urllib.parse
import os
import csv

API_BASE_URL = "http://localhost:5002"


@click.command()
@click.option("--name", type=str, help='Hostname of server')
@click.option("--type", type=click.Choice(['svrSummary', 'diskInventory']), help='[default: svrSummary]', show_default=True, required=True)
def getUcsInventory(name, type):
    diskList = []
    outFilePath = os.environ['dataPath']
    outFileName = outFilePath + "/" + type + ".csv"
    if type == "svrSummary":
        apiEndpoint = "/intersight/serverSummary"
    elif type == "diskInventory":
        apiEndpoint = "/intersight/physicalDisks"
    apiTarget = API_BASE_URL + apiEndpoint
    responseJson = requests.get(apiTarget, verify=False).json()
    if type == "svrSummary":
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


if __name__ == "__main__":
    getUcsInventory()