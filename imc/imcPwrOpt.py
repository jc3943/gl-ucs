# Jeff Comer
# Click app with threading for power operations on UCS servers - Redfish API

import click
import requests
import urllib3
import urllib.parse
import os, threading
import csv
import hvac

#get cimc credentials from vault for redfish access
client = hvac.Client(verify=False)
cimc_user = client.secrets.kv.v2.read_secret_version(mount_point='cimc', path="cimc-admin").get("data").get("data").get("username")
cimc_pw = client.secrets.kv.v2.read_secret_version(mount_point='cimc', path="cimc-admin").get("data").get("data").get("password")

def hostPwrOpt(oper, cimcIp):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    baseUrl = "https://" + cimcIp + "/redfish/v1/Systems"
    systemsResponse = requests.get(baseUrl, verify=False, auth=(cimc_user, cimc_pw))
    systemsJson = systemsResponse.json()
    systemsUrl = systemsJson["Members"][0]["@odata.id"]
    pwrCycleUrl = "https://" + cimcIp + systemsUrl + "/Actions/ComputerSystem.Reset"
    pwrCyclePayload = {"ResetType":oper}
    pwrCycleResult = requests.post(pwrCycleUrl, json=pwrCyclePayload, verify=False, auth=(cimc_user, cimc_pw))
    print(pwrCycleResult)


@click.command()
@click.option("--file", type=str, help='seedfile name for cimmc addrs', required=True)
@click.option("--op", type=click.Choice(['On', 'GracefulShutdown', 'Off', 'PowerCycle']), help='[default: on]', show_default=True, required=True)
def imcPwrOps(file, op):
    inFilePath = os.environ['varPath']
    inFileName = inFilePath + "/imc/" + file
    hostIpList = []
    threads = []
    with open(inFileName, 'r') as csv_file:
        csvread = csv.DictReader(csv_file)
        csvDict = list(csvread)
    for i in range(len(csvDict)):
        hostIpList.append(csvDict[i]['cimc'])
    for args in hostIpList:
        thread = threading.Thread(target=hostPwrOpt, args=(op,args,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    imcPwrOps()
