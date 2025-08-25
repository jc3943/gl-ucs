# Jeff Comer
# Click app with threading for power operations on vm's in vcenter

import click
import requests
import urllib3
import urllib.parse
import os, threading, json, time
import csv
import hvac
import ssl
from requests.exceptions import HTTPError
from pyVim import connect
from pyVmomi import vim

inFilePath = os.environ['dataPath']
inFileName = inFilePath + "/vmware/" + "vmPoweredOn.json"
outFilePath = os.environ['dataPath']
outFileName = outFilePath + "/vmware/" + "vmPoweredOn.json"

#Flask front-end for Intersight
API_BASE_URL = "http://172.16.113.2:5002"
vmmHostApiEndpoint = "/intersight/vmmHosts"
virtMachineApiEngpoint = "/intersight/virtMachines"
vmmHostApiTargert = API_BASE_URL + vmmHostApiEndpoint
virtMachinesApiTarget = API_BASE_URL + virtMachineApiEngpoint

filterStringList = ["vcsa", "vapic", "stCtlVM", "vCLS", "git", "Git", "GIT", "intersight"]

def vcenterConnect(vcenterUrl, vcsa_user, vcsa_pw):
    endPointUrl = f"{vcenterUrl}/rest/com/vmware/cis/session"
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        response = requests.post(endPointUrl, auth=(vcsa_user, vcsa_pw), verify=False)
        response.raise_for_status()
        session_id = response.json().get('value')
        return session_id
    except requests.exceptions.RequestException as e:
        print(f"Error during authentication: {e}")
        return None

def vmPwrDown(session_id, oper, vmName, vcenterUrl):
    if (oper == "shutdown"):
        endPointUrl = f"{vcenterUrl}/api/vcenter/vm/{vmName}/guest/power?action={oper}"
        noToolsUrl = f"{vcenterUrl}/api/vcenter/vm/{vmName}/power?action=stop"
        header = {'vmware-api-session-id':session_id}
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        try:
            response = requests.post(endPointUrl, headers=header, verify=False)
            response.raise_for_status()
            print(response)
        except HTTPError as err:
            if (err.response.status_code == 503):
                response = requests.post(noToolsUrl, headers=header, verify=False)
                response.raise_for_status()
                print("No vmwaretools for: ", vmName, "Powering Off vm :", response)
        except requests.exceptions.RequestException as e:
            print(f"Error shutting down vm {vmName}: {e}")
            return None

def vmPwrOn(session_id, oper, vmName, vcenterUrl):
    endPointUrl = f"{vcenterUrl}/api/vcenter/vm/{vmName}/power?action=start"
    header = {'vmware-api-session-id':session_id}
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        response = requests.post(endPointUrl, headers=header, verify=False)
        response.raise_for_status()
        print(response)
    except requests.exceptions.RequestException as e:
        print(f"Error starting vm {vmName}: {e}")
        return None

def getOnVms(session_id, vcenterUrl):
    endPointUrl = f"{vcenterUrl}/api/vcenter/vm?power_states=POWERED_ON"
    header = {'vmware-api-session-id':session_id}
    try:
        response = requests.get(endPointUrl, headers=header, verify=False)
        response.raise_for_status()
        vmJson = response.json()
        return vmJson
    except requests.exceptions.RequestException as e:
        print(f"Effor getting vm's from vcenter: {e}")
        return None

def hostMaintenance(session_id, oper, hostName):
    endPointUrl = f"{vcenterUrl}/api/vcenter/vm/{vmName}/power?action={oper}"
    header = {'vmware-api-session-id':session_id}
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        response = requests.post(endPointUrl, headers=header, verify=False)
        response.raise_for_status()
        print(response)
    except requests.exceptions.RequestException as e:
        print(f"Error entering maintenance mode for {hostName}: {e}")
        return None


@click.command()
@click.option("--op", type=click.Choice(['start', 'shutdown']), help='[default: on]', show_default=True, required=True)
@click.option("--host", type=str, required=False)
@click.option("--user", type=str, help='vcsa usernamne', required=False)
@click.option("--pw", type=str, help='vcsa password', required=False)
@click.option("--vcsa_host", type=str, help='vcsa ip address', required=False)
def vmPwrOps(op, host, user, pw, vcsa_host):
    #get cimc credentials from vault for redfish access
    if (user):
        vcsa_user = user
        vcsa_pw = pw
        vcsa_ip = vcsa_host
    else:
        try:
            client = hvac.Client(verify=False)
            vcsa_user = client.secrets.kv.v2.read_secret_version(mount_point='vsphere', path="vcenter-creds").get("data").get("data").get("username")
            vcsa_pw = client.secrets.kv.v2.read_secret_version(mount_point='vsphere', path="vcenter-creds").get("data").get("data").get("password")
            vcsa_ip = client.secrets.kv.v2.read_secret_version(mount_point='vsphere', path="vcenter-creds").get("data").get("data").get("vcenter-ip")

        except:
            print("Unable to retrieve vault credentials")
            exit(1)
        vcenterUrl = f"https://{vcsa_ip}"
        vcsaConnect = vcenterConnect(vcenterUrl, vcsa_user, vcsa_pw)
    if (op == "shutdown" and not host):
        vmObj = getOnVms(vcsaConnect, vcenterUrl)
        with open(outFileName, 'w') as file:
            json.dump(vmObj, file)
        vmFilteredList = []
        threads = []
        for i in range(len(vmObj)):
            for k in range(len(filterStringList)):
                if filterStringList[k] in vmObj[i]['name']:
                    vmObj[i].clear()
                    break
        while {} in vmObj:
            vmObj.remove({})
        for i in range(len(vmObj)):
            vmFilteredList.append(vmObj[i]['vm'])

        for args in vmFilteredList:
            thread = threading.Thread(target=vmPwrDown, args=(vcsaConnect,op,args,vcenterUrl,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
        for pwrStat in range(0, 20):
            vmStillOn = []
            vmStat = getOnVms(vcsaConnect, vcenterUrl)
            for k in range(len(vmStat)):
                vmStillOn.append(vmStat[k]['vm'])
            vmAllOff = all((item not in vmFilteredList for item in vmStillOn))
            if not vmAllOff:
                print("Powering Down: ", vmStillOn)
                time.sleep(30)
                pwrStat += 1
            elif (pwrStat >= 20):
                print("Timed out waiting for vm's to power off: ", vmStillOn)
                exit(1)
            if vmAllOff:
                print("All phase 1 vm's have powered off: ", vmStillOn)
    #shutdown vm's only on specified host
    elif (op == "shutdown" and host):
        vmObj = getOnVms(vcsaConnect, vcenterUrl)
        try:
            vmHostJson = requests.get(vmmHostApiTargert, verify=False).json()
        except:
            print("Unable to retrieve data from flask api")
        vmNameListOnHost = []
        vmFilteredList = []
        vmPwrOnHostListDict = []
        threads = []
        for i in range(len(vmHostJson['vmwareHosts'])):
            if (vmHostJson['vmwareHosts'][i]['Name'] == host):
                hostMoid = vmHostJson['vmwareHosts'][i]['Moid']
                break
        specificHostUrl = virtMachinesApiTarget + f'?host_moid={hostMoid}'
        print(specificHostUrl)
        try:
            vmOnHostJson = requests.get(specificHostUrl, verify=False).json()
            print(vmOnHostJson)
        except:
            print("Error getting vm's on specified host")
        for k in range(len(vmOnHostJson['virtualMachines'])):
            if (vmOnHostJson['virtualMachines'][k]['ObjectType'] == "virtualization.VmwareVirtualMachine" and vmOnHostJson['virtualMachines'][k]['PowerState'] == "PoweredOn"):
                vmNameListOnHost.append(vmOnHostJson['virtualMachines'][k]['Name'])
        print("\n\n", vmNameListOnHost)
        #print(vmObj)
        for j in range(len(vmNameListOnHost)):
            for h in range(len(vmObj)):
                if (vmNameListOnHost[j] == vmObj[h]['name']):
                    vmFilteredList.append(vmObj[h]['vm'])
                    vmPwrOnHostListDict.append(vmObj[h])
        print(vmFilteredList)
        print(vmPwrOnHostListDict)
        with open(outFileName, 'w') as file:
            json.dump(vmPwrOnHostListDict, file)
        # for i in range(len(vmObj)):
        #     vmFilteredList.append(vmObj[i]['vm'])

        for args in vmFilteredList:
            thread = threading.Thread(target=vmPwrDown, args=(vcsaConnect,op,args,vcenterUrl,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
        for pwrStat in range(0, 20):
            vmStillOn = []
            vmStat = getOnVms(vcsaConnect, vcenterUrl)
            for k in range(len(vmStat)):
                vmStillOn.append(vmStat[k]['vm'])
            vmAllOff = all((item not in vmFilteredList for item in vmStillOn))
            if not vmAllOff:
                print("Powering Down: ", vmFilteredList)
                time.sleep(30)
                pwrStat += 1
            elif (pwrStat >= 20):
                print("Timed out waiting for vm's to power off: ", vmStillOn)
                exit(1)
            if vmAllOff:
                print(f'All vms have powered off for host: {host} ', vmFilteredList)

    elif (op == "start"):
        vmFilteredList = []
        threads = []
        with open(inFileName, 'r') as file:
            vmObj = json.load(file)
        # for i in range(len(vmObj)):
        #     for k in range(len(filterStringList)):
        #         if filterStringList[k] in vmObj[i]['name']:
        #             vmObj[i].clear()
        #             break
        # while {} in vmObj:
        #     vmObj.remove({})
        for i in range(len(vmObj)):
            vmFilteredList.append(vmObj[i]['vm'])

        for args in vmFilteredList:
            thread = threading.Thread(target=vmPwrOn, args=(vcsaConnect,op,args,vcenterUrl,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
        

if __name__ == "__main__":
    vmPwrOps()