# Jeff Comer
# Collection of Intersight functions

import sys, getopt, csv, time
import requests, json
import urllib3
from intersight_auth import IntersightAuth
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create an AUTH object
AUTH = IntersightAuth(
    secret_key_filename='creds/dev-isight-SecretKey.txt',
    api_key_id='6457bfa47564612d300f0917/6457cbbd7564612d30cb32ab/64595f8c7564612d30cb47cc'
    )

def getDevTargetStatus(specDict):
    i = 0
    j = 0
    k = 0
    claimCheck = 0
    statusCheck = 0
    cimcList = []
    claimList = []

    with open(specDict['infile'], 'r') as csv_file:
        csvread = csv.DictReader(csv_file)
        csvDict = list(csvread)
    
    targetURL = specDict['url'] + "/api/v1/asset/Targets"
    #print(targetClaimStatus.text)
    
    for k in range(len(csvDict)):
        cimcList.append(csvDict[k]['cimc'])
    print(cimcList)
    for claimCheck in range(0, 900):
        j = 0
        claimList = []
        targetClaimStatus = requests.get(targetURL, verify=False, auth=AUTH)
        targetClaimStatusJson = targetClaimStatus.json()
        #print(targetClaimStatusJson)
        #if ("IntersightAssist" not in targetClaimStatusJson["Results"][i]["TargetType"]):
        for j in range(len(targetClaimStatusJson["Results"])):
            if (targetClaimStatusJson["Results"][j]["IpAddress"] != []):
                claimList.append(targetClaimStatusJson["Results"][j]["IpAddress"][0])
        print(claimList)
        cimcsClaimed = all(elem in claimList for elem in cimcList)
        print(cimcsClaimed)
        if cimcsClaimed:
            print("Targets from terraform device claims are claimed in Intersight")
            break
        else:
            claimCheck += 1
            time.sleep(60)

    for statusCheck in range(0, 900):
        statusList = []
        for i in range(len(targetClaimStatusJson["Results"])):
            if ("IMC" in targetClaimStatusJson["Results"][i]["TargetType"]):
                statusList.append(targetClaimStatusJson["Results"][i]["Status"])
        #print(statusList)
        if "NotConnected" in statusList:
            statusCheck += 1
            time.sleep(60)
        else:
            print("Targets from terraform device claims are conected in Intersight")
            break

def getServerSummaries(specDict):
    serverSummaryURL = specDict['url'] + "/api/v1/compute/PhysicalSummaries?$inlinecount=allpages"
    response = requests.get(serverSummaryURL, verify=False, auth=AUTH)
    serverSummaryJson = response.json()
    

def deployHXProfiles(specDict):
    hxProfile = os.environ['BRANCH_NAME']
    profileURL = specDict['url'] + "/api/v1/hyperflex/ClusterProfiles"
    response = requests.get(profileURL, verify=False, auth=AUTH)
    hxProfileJson = response.json()
    for i in range(len(hxProfileJson['Results'])):
        profileName =  hxProfileJson["Results"][i]["Name"]
        if (profileName == hxProfile):
            profileMoid =  hxProfileJson["Results"][i]["Moid"]
            profileDeployURL = profileURL + "/" + profileMoid
            profileDeployPayload = {"Action":"Deploy"}
            profileDeployResponse = requests.post(profileDeployURL, json=profileDeployPayload, verify=False, auth=AUTH)
            time.sleep(60)
            print(profileDeployResponse.text)
            print("*********************************")
            profileDeployStatus = requests.get(profileDeployURL, json=profileDeployPayload, verify=False, auth=AUTH)
    return profileMoid

def statusHXDeploy(specDict, profileMoid):
    profileURL = specDict['url'] + "/api/v1/hyperflex/ClusterProfiles"
    #response = requests.get(profileURL, verify=False, auth=AUTH)
    #hxProfileJson = response.json()
    #profileMoid =  hxProfileJson["Results"][0]["Moid"]
    profileDeployURL = profileURL + "/" + profileMoid
    for i in range(0, 18):
        print("*********************************")
        profileDeployStatus = requests.get(profileDeployURL, verify=False, auth=AUTH)
        profileDeployStatusJson = profileDeployStatus.json()
        if (profileDeployStatusJson["ConfigContext"]["OperState"] == "Configuring"):
            i += 1
            print(profileDeployStatusJson["ConfigContext"]["OperState"])
            time.sleep(600)
        elif (profileDeployStatusJson["ConfigContext"]["ConfigState"] == "Failed"):
            print("HX Profile Deployment Failed")
            exit(1)
        elif (profileDeployStatusJson["ConfigContext"]["ConfigState"] == "Associated"):
            print("HX Profile Deployment Complete")
            exit(0)
    
        print(profileDeployStatus.text)
