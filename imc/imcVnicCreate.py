# Jeff Comer
# script to add vnics to servers via cimc - manual reboot required
# Example input file is vars/<branch>/hx-cimc.csv

import sys, getopt, csv
import requests, json
import urllib3
from imcOps import createVnic, disablePC, powerCycle

def main(argv):
    """
    Main execution routine

    :return: None
    """

    username = ""
    password = ""
    userArg = ""
    pwArg = ""

    argDict = {"username":"","password":"","infile":""}
    try:
      opts, args = getopt.getopt(argv,"hu:p:i:",["username","password","infile="])
    except getopt.GetoptError:
      print('imcVnicCreate.py -u <username> -p <password> -i <inputcsv>')
      sys.exit(2)
    for opt, arg in opts:
      if opt == '-h':
         print('imcVnicCreate.py -u <username> -p <password> -i <inputcsv>')
         sys.exit()
      elif opt in ("-u", "--username"):
         userArg = arg
         argDict["username"] = userArg
      elif opt in ("-p", "--password"):
         pwArg = arg
         argDict["password"] = pwArg
      elif opt in ("-i", "--infile"):
         infileArg = arg
         argDict["infile"] = infileArg
    return argDict

if __name__ == '__main__':
    cimcData = main(sys.argv[1:])
    cimcResult = createVnic(cimcData)