import os
import requests
import time

def download_data(strDataFile):
    # download the data if required
    bDownload = True
    if os.path.exists(strDataFile):
        pStat = os.stat(strDataFile)
        nTime = int(time.time())
    #    print(nTime, pStat.st_mtime)
        if (nTime-pStat.st_mtime)/3600 < 12:
            bDownload = False

    if bDownload:
        print("****DOWNLOADING****")
        pResponse = requests.get("https://raw.githubusercontent.com/globaldothealth/monkeypox/main/latest.csv")
        if pResponse.status_code != 200:
            print("Failed to download: https://raw.githubusercontent.com/globaldothealth/monkeypox/main/latest.csv")
            print("Error code:", pResponse.status_code)
            sys.exit(-1)

        with open(strDataFile, "w") as outFile:
            outFile.write(pResponse.text+"\n")

    with open(strDataFile) as inFile:
        lstHeader = inFile.readline().split(",")
        nHeaderSize = len(lstHeader)
        for nI, strWord in enumerate(lstHeader):
            if strWord == "Country_ISO3":
                nCountryIndex = nI
            elif strWord == "Date_confirmation":
                nDateIndex = nI
            elif strWord == "Status":
                nStatusIndex = nI
            elif strWord == "Date_entry":
                nUnconfirmedDateIndex = nI
#            print(nI, strWord)

    return nHeaderSize, nCountryIndex, nDateIndex, nStatusIndex, nUnconfirmedDateIndex
    