# Jeff Comer
# Flask app to provide api front end for inventory collection from Intersight

from flask import Flask
from flask_restx import Resource, Api, reqparse
from intersight_auth import IntersightAuth, repair_pem
import requests
import hvac

app = Flask(__name__)
api = Api(app)

# AUTH = IntersightAuth(
#     secret_key_filename='path_to_the_secrete_key',
#     api_key_id='contents of the key id'
#     )

#export VAULT_ADDR='ip address for vault'
#export VAULT_TOKEN='vault access token'

#get credentials from vault for Intersight API access
client = hvac.Client(verify=False)
key_id = client.secrets.kv.v2.read_secret_version(mount_point='intersight', path="intersight_api").get("data").get("data").get("api_key_id")
key_string = client.secrets.kv.v2.read_secret_version(mount_point='intersight', path="intersight_api").get("data").get("data").get("secret_key_string")
intersightUrl = client.secrets.kv.v2.read_secret_version(mount_point='intersight', path="intersight_api").get("data").get("data").get("target-url")

#get cimc credentials from vault for redfish access
cimc_user = client.secrets.kv.v2.read_secret_version(mount_point='cimc', path="cimc-admin").get("data").get("data").get("username")
cimc_pw = client.secrets.kv.v2.read_secret_version(mount_point='cimc', path="cimc-admin").get("data").get("data").get("password")

AUTH = IntersightAuth(
    secret_key_string=key_string,
    api_key_id=key_id
    )

#intersightUrl = "https://dev-intersight.thor.iws.navy.mil"

@api.route("/intersight/serverSummary")
class getServerSummary(Resource):
    def get(self):
        svrPhysList = []
        serverSummaryURL = intersightUrl + "/api/v1/compute/PhysicalSummaries?$inlinecount=allpages"
        response = requests.get(serverSummaryURL, verify=False, auth=AUTH)
        print(response)
        serverSummaryJson = response.json()
        for i in range(len(serverSummaryJson["Results"])):
            svrPhysDict = {}
            for respKey, respItem in serverSummaryJson["Results"][i].items():
                if respKey == "Name":
                    svrPhysDict[respKey] = respItem
                elif respKey == "Model":
                    svrPhysDict[respKey] = respItem
                elif respKey == "MgmtIpAddress":
                    svrPhysDict[respKey] = respItem
                elif respKey == "Serial":
                    svrPhysDict[respKey] = respItem
                elif respKey == "DeviceMoId":
                    svrPhysDict[respKey] = respItem
                elif respKey == "Firmware":
                    svrPhysDict[respKey] = respItem
                elif respKey == "MemorySpeed":
                    svrPhysDict[respKey] = respItem
                elif respKey == "NumCpuCores":
                    svrPhysDict[respKey] = respItem
                elif respKey == "NumCpus":
                    svrPhysDict[respKey] = respItem
                elif respKey == "PlatformType":
                    svrPhysDict[respKey] = respItem
            svrPhysList.append(svrPhysDict)
            responseData = {'servers':svrPhysList} 
        return(responseData)
        #return(serverSummaryJson)

@api.route("/intersight/physicalDisks")
class getPhysicalDisks(Resource):
    def get(self):
        svrPhysList = []
        svrDiskList = []
        serverSummaryURL = "http://localhost:5002/intersight/serverSummary"
        response = requests.get(serverSummaryURL, verify=False)
        serverSummaryJson = response.json()

        physicalDiskUrl = intersightUrl + "/api/v1/storage/PhysicalDisks"
        response = requests.get(physicalDiskUrl, verify=False, auth=AUTH)
        physicalDiskJson = response.json()
        for i in range(len(physicalDiskJson["Results"])):
            svrDiskDict = {}
            for respKey, respItem in physicalDiskJson["Results"][i].items():
                if respKey == "DeviceMoId":
                    svrDiskDict[respKey] = respItem
                elif respKey == "DiskId":
                    svrDiskDict[respKey] = respItem
                elif respKey == "DiskState":
                    svrDiskDict[respKey] = respItem
                elif respKey == "DriveFirmware":
                    svrDiskDict[respKey] = respItem
                elif respKey == "DriveState":
                    svrDiskDict[respKey] = respItem
                elif respKey == "LinkSpeed":
                    svrDiskDict[respKey] = respItem
                elif respKey == "Model":
                    svrDiskDict[respKey] = respItem
                elif respKey == "Pid":
                    svrDiskDict[respKey] = respItem
                elif respKey == "Protocol":
                    svrDiskDict[respKey] = respItem
                elif respKey == "Serial":
                    svrDiskDict[respKey] = respItem
                elif respKey == "Size":
                    svrDiskDict[respKey] = respItem
            svrDiskList.append(svrDiskDict)
            responseData = {'servers':serverSummaryJson["servers"], 'diskInventory':svrDiskList}
        return(responseData)
        #return(physicalDiskJson)

@api.route("/intersight/vmmHosts")
class getVmmHosts(Resource):
    def get(self):
        vmmHostList = []
        
        vmmHostUrl = intersightUrl + "/api/v1/virtualization/VmwareHosts"
        response = requests.get(vmmHostUrl, verify=False, auth=AUTH)
        vmmHostJson = response.json()
        for i in range(len(vmmHostJson["Results"])):
            vmmHostDict = {}
            for respKey, respItem in vmmHostJson["Results"][i].items():
                if respKey == "ConnectionState":
                    vmmHostDict[respKey] = respItem
                elif respKey == "CpuInfo":
                    for cpuKey, cpuItem in vmmHostJson["Results"][i]["CpuInfo"].items():
                        if cpuKey == "Cores":
                            vmmHostDict[cpuKey] = cpuItem
                        elif cpuKey == "Sockets":
                            vmmHostDict[cpuKey] = cpuItem
                        elif cpuKey == "Speed":
                            vmmHostDict[cpuKey] = cpuItem
                        elif cpuKey == "Vendor":
                            vmmHostDict[cpuKey] = cpuItem
                elif respKey == "DnsServers":
                    vmmHostDict[respKey] = respItem
                elif respKey == "HwPowerSTate":
                    vmmHostDict[respKey] = respItem
                elif respKey == "MemoryCapacity":
                    for memKey, memItem in vmmHostJson["Results"][i]["MemoryCapacity"].items():
                        if memKey == "Capacity":
                            reKey = "MemCapacity"
                            vmmHostDict[reKey] = memItem
                        elif memKey == "Used":
                            reKey = "MemUsed"
                            vmmHostDict[reKey] = memItem
                elif respKey == "Model":
                    vmmHostDict[respKey] = respItem
                elif respKey == "Moid":
                    vmmHostDict[respKey] = respItem
                elif respKey == "Name":
                    vmmHostDict[respKey] = respItem
                elif respKey == "NtpServers":
                    vmmHostDict[respKey] = respItem
                elif respKey == "ProcessorCapacity":
                    for procCapKey, procCapItem in vmmHostJson["Results"][i]["ProcessorCapacity"].items():
                        if procCapKey == "Capacity":
                            reKey = "ProcCapacity"
                            vmmHostDict[reKey] = procCapItem
                        elif procCapKey == "Used":
                            reKey = "ProcUsed"
                            vmmHostDict[reKey] = procCapItem
                elif respKey == "ProductInfo":
                    for prodKey, prodItem in vmmHostJson["Results"][i]["ProductInfo"].items():
                        if prodKey == "Build":
                            vmmHostDict[prodKey] = prodItem
                        elif prodKey == "Version":
                            vmmHostDict[prodKey] = prodItem
            vmmHostList.append(vmmHostDict)
        responseData = {"vmwareHosts":vmmHostList}
        return(responseData)
        #return(vmmHostJson)

hostMoidParser = reqparse.RequestParser()
hostMoidParser.add_argument("host_moid", type=str)
@api.route("/intersight/virtMachines")
class getVirtMachines(Resource):
    @api.expect(hostMoidParser)
    def get(self):
        vmList = []
        args = hostMoidParser.parse_args()
        virtMachinestUrl = intersightUrl + f'/api/v1/search/SearchItems?$filter=(Host.Moid eq \'{args.host_moid}\')'
        #virtMachinestUrl = "https://dev-intersight.thor.iws.navy.mil/api/v1/search/SearchItems?$filter=(Host.Moid%20eq%20%2764a81cb2736c6f2d30dc35b6%27)"
        response = requests.get(virtMachinestUrl, verify=False, auth=AUTH)
        virtMachinesJson = response.json()
        for i in range(len(virtMachinesJson["Results"])):
            vmDict = {}
            for respKey, respItem in virtMachinesJson["Results"][i].items():
                if respKey == "ConnectionState":
                    vmDict[respKey] = respItem
                elif respKey == "CpuUtilization":
                    vmDict[respKey] = respItem
                elif respKey == "DnsServerList":
                    vmDict[respKey] = respItem
                elif respKey == "GuestInfo":
                    for guestInfoKey, guestInfoItem in virtMachinesJson["Results"][i]["GuestInfo"].items():
                        if guestInfoKey == "Hostname":
                            vmDict[guestInfoKey] = guestInfoItem
                        elif guestInfoKey == "IpAddress":
                            vmDict[guestInfoKey] = guestInfoItem
                        elif guestInfoKey == "OperatingSystem":
                            vmDict[guestInfoKey] = guestInfoItem
                elif respKey == "GuestState":
                    vmDict[respKey] = respItem
                elif respKey == "MemoryCapacity":
                    for memKey, memItem in virtMachinesJson["Results"][i]["MemoryCapacity"].items():
                        if memKey == "Capacity":
                            reKey = "MemCapacity"
                            vmDict[reKey] = memItem
                        elif memKey == "Used":
                            reKey = "MemUsed"
                            vmDict[reKey] = memItem
                elif respKey == "MemoryUtilization":
                    vmDict[respKey] = respItem
                elif respKey == "Moid":
                    reKey = "vmMoid"
                    vmDict[reKey] = respItem
                elif respKey == "Name":
                    vmDict[respKey] = respItem
                elif respKey == "ObjectType":
                    vmDict[respKey] = respItem
                elif respKey == "PowerState":
                    vmDict[respKey] = respItem
                elif respKey == "ProcessorCapacity":
                    for procCapKey, procCapItem in virtMachinesJson["Results"][i]["ProcessorCapacity"].items():
                        if procCapKey == "Capacity":
                            reKey = "vCPU_Capacity"
                            vmDict[reKey] = procCapItem
                        elif procCapKey == "Used":
                            reKey = "vCPU_Used"
                            vmDict[reKey] = procCapItem
            vmList.append(vmDict)
        responseData = {"virtualMachines":vmList}
        #return(virtMachinesJson)
        return(responseData)

cimcIpParser = reqparse.RequestParser()
cimcIpParser.add_argument("cimc_ip", type=str)
@api.route("/imc/pwrStats")
class getUcsPwrStats(Resource):
    @api.expect(cimcIpParser)
    def get(self):
        args = cimcIpParser.parse_args()
        svrList = []
        pwrStats = {}
        if args.get("cimc_ip"):
            pwrStats = getHostPwrStats(args.cimc_ip)
        else:
            serverSummaryURL = "http://localhost:5002/intersight/serverSummary"
            serverSummaryJson = requests.get(serverSummaryURL, verify=False).json()
            print(serverSummaryJson["servers"])
            for i in range(len(serverSummaryJson["servers"])):
                perHostPwrStats = getHostPwrStats(serverSummaryJson["servers"][i]["MgmtIpAddress"])
                pwrStats.update(perHostPwrStats)
        return(pwrStats)
        #return(response)

def getHostPwrStats(cimc):
    hostPwrStats = {}
    hostPwrStats = {}
    pwrDict = {}
    pwrStatsUrl = f'https://{cimc}/redfish/v1/Chassis/1/Power'
    response = requests.get(pwrStatsUrl, auth=(cimc_user, cimc_pw), verify=False).json()
    for respKey, respItem in response.items():
        if respKey == "PowerControl":
            pwrDict["sysAvgWatts"] = response["PowerControl"][0]["PowerMetrics"]["AverageConsumedWatts"]
            pwrDict["sysMaxWatts"] = response["PowerControl"][0]["PowerMetrics"]["MaxConsumedWatts"]
            pwrDict["sysMinWatts"] = response["PowerControl"][0]["PowerMetrics"]["MinConsumedWatts"]
            pwrDict["sysConsumedWatts"] = response["PowerControl"][0]["PowerConsumedWatts"]
    hostPwrStats = {cimc:pwrDict}
    return hostPwrStats


if __name__ == "__main__":
    app.run(debug=True, port=5002, host='0.0.0.0')