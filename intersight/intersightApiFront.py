# Jeff Comer
# Flask app to provide api front end for inventory collection from Intersight

from flask import Flask
from flask_restx import Resource, Api, reqparse
from intersight_auth import IntersightAuth
import requests

app = Flask(__name__)
api = Api(app)

AUTH = IntersightAuth(
    secret_key_filename='creds/dev-isight-SecretKey.txt',
    api_key_id='6457bfa47564612d300f0917/6457cbbd7564612d30cb32ab/64595f8c7564612d30cb47cc'
    )
intersightUrl = "https://dev-intersight.thor.iws.navy.mil"

@api.route("/intersight/serverSummary")
class getServerSummary(Resource):
    def get(self):
        svrPhysList = []
        serverSummaryURL = intersightUrl + "/api/v1/compute/PhysicalSummaries?$inlinecount=allpages"
        response = requests.get(serverSummaryURL, verify=False, auth=AUTH)
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
        vmmHostUrl = intersightUrl + "/api/v1/virtualization/Hosts"
        response = requests.get(vmmHostUrl, verify=False, auth=AUTH)
        vmmHostJson = response.json()
        return(vmmHostJson)

if __name__ == "__main__":
    app.run(debug=True, port=5002)