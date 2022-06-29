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

strNation = "World"
if len(sys.argv) > 1:
    strNation = sys.argv[1]

# setup date info
pToday = datetime.today()
nYear = pToday.year
nMonth = pToday.month
nDay = pToday.day
strDate = "-".join(map(str, (nYear, nMonth, nDay)))
nWeekday = pToday.weekday()
#print(nWeekday)

# download the data if required
bDownload = True
strDataFile = "owid_monkeypox.csv"
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
        print("Get failed")
        sys.exit(-1)

    with open(strDataFile, "w") as outFile:
        outFile.write(pResponse.text+"\n")

reValue = re.compile(r'"(.*?)"')

# import the data
pBaseDate = datetime(2022, 4, 18+nWeekday)
mapDate = {}
nMaxDay = 0
strNationLower = strNation.lower().replace(" ","_")
with open(strDataFile) as inFile:
    lstHeader = inFile.readline().split(",")
#    print(lstHeader)
    for strLine in inFile:
        lstMatches = reValue.findall(strLine)
        for strMatch in lstMatches:
            strLine = strLine.replace(strMatch, strMatch.replace(",", "DNUSID"))
        lstLine = strLine.split(",")
        if len(lstLine) != 32: continue
        if lstLine[1].lower() == "confirmed": 
            if strNationLower == "world" or lstLine[4].lower() == strNationLower:
                nYear, nMonth, nDay = map(int, lstLine[8].split("-"))
                pDate = datetime(nYear, nMonth, nDay)
                nDay = (pDate-pBaseDate).days
                if nDay not in mapDate:
                    mapDate[nDay] = 0
                mapDate[nDay] += 1
                if nDay > nMaxDay: nMaxDay = nDay

# accumulate weekly data            
lstWeek = []
lstDays = []
lstCount = []
nFitStart = -1
with open(strDate+"_owid_"+strNationLower+".csv", "w") as outFile:
    for nI in range(nMaxDay+1):
        if nI in mapDate:
            lstWeek.append(mapDate[nI])
    #        print(nI)
        else:
            lstWeek.append(0)

        if len(lstWeek) == 7:
            nCount = sum(lstWeek)
            outFile.write(str(nI-3)+" "+str(nCount)+"\n")
#            print(nI-3, nCount)
            lstWeek = []
            if nCount > 100 and nFitStart < 0:
                nFitStart = len(lstDays)

            lstDays.append(nI-3)
            lstCount.append(nCount)
            
print("Residual (should be 0):",len(lstWeek))

# bail if not enough data
if len(lstDays) - nFitStart < 3:
    print("Insufficient data for fitting. Must have three weeks > 100 new cases per week")
    sys.exit(0)

# fit the data
lstCoeffs = np.polyfit(lstDays[nFitStart:], np.log(lstCount[nFitStart:]), deg=1)
fEfoldingTime = 1/lstCoeffs[0]
fBase = math.exp(lstCoeffs[1])
fDoublingTime = math.log(2)*fEfoldingTime
print("Doubling time (days):", fDoublingTime)
fit = np.poly1d(lstCoeffs)
with open(strDate+"_fit_"+strNationLower+".csv", "w") as outFile:
    for nI, nDay in enumerate(lstDays):
        if nI >= nFitStart:
            print(nDay, lstCount[nI], math.exp(fit(nDay)))
            outFile.write(" ".join(map(str, (nDay, lstCount[nI], math.exp(fit(nDay)))))+"\n")

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
pPlot.annotate('Doubling time: '+str(fDoublingTime)[0:5]+" days",
            xy=(.14, .85), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=12)
pPlot.annotate('Fit: '+str(fBase)[0:5]+"+exp(nDay/"+str(fEfoldingTime)[0:5]+")",
            xy=(.14, .8), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)            
pPlot.annotate('Start day: '+str(pBaseDate.date()),
            xy=(.14, .77), xycoords='figure fraction',
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
