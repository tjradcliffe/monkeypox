from datetime import datetime, timedelta
import math
import os
import re
import requests
import sys
import time

import numpy as np

import matplotlib
import matplotlib.dates as mdates
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# for dealing with commas in quoted fields
reValue = re.compile(r'"(.*?)"')

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

def list_nations(strDataFile):
    
    # download if required
    download_data(strDataFile)
    
    # find nations
    mapNations = {}
    with open(strDataFile) as inFile:
        for strLine in inFile:
            lstMatches = reValue.findall(strLine)
            for strMatch in lstMatches:
                strLine = strLine.replace(strMatch, strMatch.replace(",", "DNUSID"))
            lstLine = strLine.split(",")
            if len(lstLine) != 32: continue
            if lstLine[1].lower() == "confirmed": 
                strCountry = lstLine[4]
                if strCountry not in mapNations:
                    mapNations[strCountry] = 0
                mapNations[strCountry] += 1
                
    lstNations = list(mapNations)
    lstNations.sort()
    for strCountry in lstNations:
        print(strCountry, mapNations[strCountry])
        
###
strDataFile = "owid_monkeypox.csv"

strNation = "World"
if len(sys.argv) > 1:
    if "help" in sys.argv[1] or "-h" == sys.argv[1]:
        print("")
        print("python3 mpx_pandemic.py [-n --nations] <<Nation Name>>")
        print("")
        print("Nation Name should be capitalized with spaces")
        print("United States for the US")
        print("UK nations reported separately")
        print("Taiwan is not part of China")
        print("")
        print("-n or --nations lists all nations and their total case numbers")
        print("")
        print("3 weeks with > 100 confirmed cases is required for analysis, otherwise")
        print(" just the summary file is generated")
        print("")
        print("Nation Name generates YYYY-DD-MM_owid_nation_name.csv and")
        print(" YYYY-DD-MM_fit_nation_name.png")
        print("")
        print("If no Nation Name given World is used")
        print("")
        print("Data is downloaded from https://ourworldindata.org/monkeypox via")
        print(" https://raw.githubusercontent.com/globaldothealth/monkeypox/main/latest.csv")
        print(" to "+strDataFile)
        sys.exit(0)
    elif "-n" == sys.argv[1] or "--nations" == sys.argv[1]:
        list_nations(strDataFile)
        sys.exit(0)
    elif sys.argv[1].startswith("-"):
        print("Unrecognized option: ", sys.argv[1])
        print("Try -h for help")
        sys.exit(0)
        
    strNation = sys.argv[1]

# setup date info
pToday = datetime.today()
strDate = str(pToday.date())

# download if required
download_data(strDataFile)

# import the data
pBaseDate = datetime(2022, 4, 20)
mapDate = {}
nMaxDay = 0
strNationLower = strNation.lower().replace(" ","_")
with open(strDataFile) as inFile:
    lstHeader = inFile.readline().split(",")
#    print(lstHeader)
    for strLine in inFile:
        lstMatches = reValue.findall(strLine)
        for strMatch in lstMatches:
            strLine = strLine.replace(strMatch, strMatch.replace(",", " "))
        lstLine = strLine.split(",")
        if len(lstLine) != 32: continue
        if lstLine[1].lower() == "confirmed": 
            if strNation == "World" or lstLine[4] == strNation:
                nYear, nMonth, nDay = map(int, lstLine[8].split("-"))
                pDate = datetime(nYear, nMonth, nDay)
                nDay = (pDate-pBaseDate).days
                if nDay not in mapDate:
                    mapDate[nDay] = 0
                mapDate[nDay] += 1
                if nDay > nMaxDay: nMaxDay = nDay

# accumulate weekly data, working backward to ensure full week at end
lstWeek = []
lstDays = []
lstCount = []
nFitStart = -1
with open(strDate+"_owid_"+strNationLower+".csv", "w") as outFile:
    for nI in range(nMaxDay, -1, -1):
        if nI in mapDate:
            lstWeek.append(mapDate[nI])
        else:
            lstWeek.append(0)

        if len(lstWeek) == 7:
            nCount = sum(lstWeek)
            outFile.write(str(nI+3)+" "+str(nCount)+"\n")
            print(nI+3, nCount)
            lstWeek = []

            lstDays.insert(0, nI+3)
            lstCount.insert(0, nCount)

# only fit for days > 100
for nI, nCount in enumerate(lstCount):
    if nCount > 100:
        nFitStart = nI
        break
            
# bail if not enough data
if nFitStart < 0 or len(lstDays) - nFitStart < 3:
    print("Insufficient data for fitting. Must have three weeks > 100 new cases per week")
    sys.exit(0)

# fit the data
lstCoeffs = np.polyfit(lstDays[nFitStart:], np.log(lstCount[nFitStart:]), deg=1)
fEfoldingTime = 1/lstCoeffs[0]
fBase = math.exp(lstCoeffs[1])
fDoublingTime = math.log(2)*fEfoldingTime
print("Doubling time (days):", fDoublingTime)
fit = np.poly1d(lstCoeffs)
fLogRMS = 0.0
nCount = 0
with open(strDate+"_fit_"+strNationLower+".csv", "w") as outFile:
    outFile.write("# Doubling: "+str(fDoublingTime)+"\n")
    outFile.write("# "+str(fBase)+"+exp(nDay/"+str(fEfoldingTime)+")\n")
    for nI, nDay in enumerate(lstDays):
        if nFitStart > 0 and nI >= nFitStart:
            print(nDay, lstCount[nI], math.exp(fit(nDay)))
            fLogRMS += (math.log(lstCount[nI])-fit(nDay))**2
            nCount += 1
            outFile.write(" ".join(map(str, (nDay, lstCount[nI], math.exp(fit(nDay)))))+"\n")

print("")
if nCount > 0:
    print("Log RMS: ", str(math.sqrt(fLogRMS/nCount))[0:5])

# plot with dates
lstDates = [pBaseDate+timedelta(days=x) for x in lstDays]
pLocator = mdates.AutoDateLocator()
pFormatter = mdates.AutoDateFormatter(pLocator)
pFigure, pPlot = plt.subplots()
pPlot.xaxis.set_major_locator(pLocator)
pPlot.xaxis.set_major_formatter(pFormatter)
pPlot.set_yscale("log")
pPlot.set_title("Monkeypox "+strNation+" Weekly New Confirmed Cases")
pPlot.set_xlabel("Date")
pPlot.set_ylabel("Count")
pPlot.annotate('Doubling Time: '+str(fDoublingTime)[0:5]+" days",
            xy=(.14, .85), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=12)
pPlot.annotate("(Comparison: Dec/Jan Omicron Doubling Time was 10.3 days)",
            xy=(.14, .8), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=6)            
pPlot.annotate('Fit: '+str(fBase)[0:5]+"+exp(nDay/"+str(fEfoldingTime)[0:5]+")",
            xy=(.14, .77), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)            
pPlot.annotate('Start day: '+str(pBaseDate.date()),
            xy=(.14, .74), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)            
pPlot.annotate('Generated: '+strDate+" from https://ourworldindata.org/monkeypox",
            xy=(.3, .25), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)
pPlot.plot(lstDates[nFitStart:], lstCount[nFitStart:], "bx")
pPlot.plot(lstDates[nFitStart:], [math.exp(fit(x)) for x in lstDays[nFitStart:]])
pFigure.autofmt_xdate()
pFigure.savefig(strDate+"_owid_"+strNationLower+".png")
