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
        strURL = "https://raw.githubusercontent.com/owid/monkeypox/main/owid-monkeypox-data.csv"
        print("****DOWNLOADING****")
        pResponse = requests.get(strURL)
        if pResponse.status_code != 200:
            print("Failed to download: "+strURL)
            print("Error code:", pResponse.status_code)
            sys.exit(-1)

        with open(strDataFile, "w") as outFile:
            outFile.write(pResponse.text+"\n")

    # header length
    return len(open(strDataFile).readline().split(','))