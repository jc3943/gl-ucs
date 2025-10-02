# Jeff Comer
# click app to parse args, get moid, serial, hostname and build vars for bm deployment
import click
import requests
import urllib3
import urllib.parse
import os, yaml
import csv
import hvac
from intersight_auth import IntersightAuth, repair_pem

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#export VAULT_ADDR='ip address for vault'
#export VAULT_TOKEN='vault access token'

# get credentials from vault for Intersight API access
client = hvac.Client(verify=False, raise_on_deleted_version=True)
key_id = client.secrets.kv.v2.read_secret_version(mount_point='intersight', path="intersight_api").get("data").get("data").get("api_key_id")
key_string = client.secrets.kv.v2.read_secret_version(mount_point='intersight', path="intersight_api").get("data").get("data").get("secret_key_string")
intersightUrl = client.secrets.kv.v2.read_secret_version(mount_point='intersight', path="intersight_api").get("data").get("data").get("target-url")

# get cimc credentials from vault for redfish access
cimc_user = client.secrets.kv.v2.read_secret_version(mount_point='cimc', path="cimc-admin").get("data").get("data").get("username")
cimc_pw = client.secrets.kv.v2.read_secret_version(mount_point='cimc', path="cimc-admin").get("data").get("data").get("password")

AUTH = IntersightAuth(
    secret_key_string=key_string,
    api_key_id=key_id
    )

# AUTH = IntersightAuth(
#     secret_key_string='''
# -----BEGIN EC PRIVATE KEY-----
# MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg1kCol4dB/0svfhos
# F0FKgfYTwP9RA4ZERmoCTM7P+r2hRANCAATZrXTpYUcCcxBuPDjsJF+Al0gvNKyc
# 3Q8Zfa3TX2VWxcs4G6Dz15p4DnhvrRORTZn+sR8xuX9Sb0i9OvUTIKBh
# -----END EC PRIVATE KEY-----
# ''',
#     api_key_id='6457bfa47564612d300f0917/6457cbbd7564612d30cb32ab/682fa3bf756461301fd24382'
# )
# intersightUrl = "https://dev-intersight.thor.iws.navy.mil"
serverSummaryURL = intersightUrl + "/api/v1/compute/PhysicalSummaries?$inlinecount=allpages"

outFilePath = os.environ['dataPath']
outFile = outFilePath + "/os_install_servers.yml"

class yamlDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(yamlDumper, self).increase_indent(flow, False)

@click.command()
@click.option("--infile", type=str, help='BM Host Install Seed file csv', required=True)
@click.option("--pw", type=str, help='Password to be set during os install', required=True)
# @click.option("--cimc_pw", type=str, help='CIMC Password', required=True)
def getUcsIntersightData(infile, pw):
    with open(infile, 'r') as csv_file:
        csvread = csv.DictReader(csv_file)
        csvDict = list(csvread)
    svrSpecDict = {}
    svrSpecList = []
    serverSummaryURL = intersightUrl + "/api/v1/compute/PhysicalSummaries?$inlinecount=allpages"
    #print(serverSummaryURL)
    response = requests.get(serverSummaryURL, verify=False, auth=AUTH)
    serverSummaryJson = response.json()
    for i in range(len(serverSummaryJson["Results"])):
        svrSpecDict = {}
        for k in range(len(csvDict)):
            if (csvDict[k]['cimcIp'] == serverSummaryJson['Results'][i]['MgmtIpAddress']):
                svrSpecDict['obj_type'] = 'compute.RackUnit'
                svrSpecDict['os_ipv4_addr'] = csvDict[k]['hostIp']
                svrSpecDict['os_ipv4_netmask'] = csvDict[k]['hostNetmask']
                svrSpecDict['os_ipv4_gateway'] = csvDict[k]['hostGateway']
                svrSpecDict['os_ipv4_dns_ip'] = csvDict[k]['dns']
                svrSpecDict['os_root_password'] = pw
                svrSpecDict['os_answers_netDev'] = csvDict[k]['networkDevice']
                svrSpecDict['os_answers_vlanId'] = csvDict[k]['vlanId']
                for respKey, respItem in serverSummaryJson["Results"][i].items():
                    if respKey == "Name":
                        svrSpecDict['os_hostname'] = respItem
                    elif respKey == "Serial":
                        svrSpecDict['server_serial'] = respItem
                    elif respKey == "Moid":
                        svrSpecDict['server_moid'] = respItem
                svrSpecList.append(svrSpecDict)
    responseData = {'servers':svrSpecList}
    with open(outFile, 'w') as file:   
        yaml.dump(responseData, file, Dumper=yamlDumper, indent=2, default_flow_style=False, sort_keys=False)
    # print(responseData)
            # return(responseData)



if __name__ == "__main__":
    getUcsIntersightData()