from datetime import datetime, timedelta
import math
import os
import re
import sys
import time

import numpy as np

import matplotlib
import matplotlib.dates as mdates
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# for dealing with commas in quoted fields
reValue = re.compile(r'"(.*?)"')

from download_mpx_owid import download_data

def list_nations(strDataFile):
    
    # download if required
    try:
        nHeaderSize, nCountryIndex, nDateIndex, nStatusIndex, nUnconfirmedDateIndex = download_data(strDataFile)
    except Exception as e:
        print(e)
        print("PROBABLY DUE TO DATA FILE FORMAT CHANGE")
        print("Expect columns: Status, Country, Date_confirmation, Date_entry to exist")
        print("Check downloaded file: ", strDataFile," and see if header has changed")
        sys.exit(0)
    
    mapISO3 = {}
    with open('iso3.csv') as inFile:
        for strLine in inFile:
            lstLine = strLine.strip().split(':')
            if len(lstLine) == 2:
                mapISO3[lstLine[1]]  = lstLine[0]
            else:
                print("Ignored: ", strLine.strip())
    
    # find nations
    mapNations = {}
    with open(strDataFile) as inFile:
        for strLine in inFile:
            lstMatches = reValue.findall(strLine)
            for strMatch in lstMatches:
                strLine = strLine.replace(strMatch, strMatch.replace(",", "DNUSID"))
            lstLine = strLine.split(",")
            if len(lstLine) != nHeaderSize: continue
            if lstLine[nStatusIndex].lower() == "confirmed": 
                strCountry = lstLine[nCountryIndex]
                if strCountry not in mapNations:
                    mapNations[strCountry] = 0
                mapNations[strCountry] += 1
                
    lstNations = list(mapNations)
    lstNations.sort()
    for strCountry in lstNations:
        if strCountry in mapISO3:
            print(strCountry, mapISO3[strCountry], mapNations[strCountry])
        else:
            print(strCountry, "-----", mapNations[strCountry])
        
###
strDataFile = "owid_monkeypox.csv"

strNation = "World"
nNationIndex = 1
bUC = False
strUC = ""
if len(sys.argv) > 1:
    if "help" in sys.argv[1] or "-h" == sys.argv[1]:
        print("")
        print("python3 mpx_pandemic.py [-n --nations] [-c] <<ISO3>>")
        print("")
        print("ISO3 is three-letter ISO code")
        print("Taiwan is not part of China")
        print("")
        print("-n or --nations lists all nations (including name and ISO code) and their total case numbers")
        print("")
        print("-c drops the confirmed case requirement (adds _uc to output filenames")
        print("")
        print("3 weeks with > 200 confirmed cases is required for analysis, otherwise")
        print(" just the summary file is generated")
        print("")
        print("ISO3 argument generates YYYY-DD-MM_owid_ISO3.csv and")
        print(" YYYY-DD-MM_fit_nation_name.png")
        print("")
        print("If no ISO3 given World is used")
        print("")
        print("Data is downloaded from https://ourworldindata.org/monkeypox via")
        print(" https://raw.githubusercontent.com/globaldothealth/monkeypox/main/latest.csv")
        print(" to "+strDataFile)
        sys.exit(0)
    elif "-n" == sys.argv[1] or "--nations" == sys.argv[1]:
        list_nations(strDataFile)
        sys.exit(0)
    elif "-c" == sys.argv[1]:
        bUC = True
        strUC = "_uc"
        nNationIndex = 2
    elif sys.argv[1].startswith("-"):
        print("Unrecognized option: ", sys.argv[1])
        print("Try -h for help")
        sys.exit(0)
        
    if len(sys.argv) > nNationIndex:
        strNation = sys.argv[nNationIndex]

print("Processing: ", strNation)

# setup date info
pToday = datetime.today()
strDate = str(pToday.date())

# download if required
try:
    nHeaderSize, nCountryIndex, nDateIndex, nStatusIndex, nUnconfirmedDateIndex = download_data(strDataFile)
except Exception as e:
    print(e)
    print("PROBABLY DUE TO DATA FILE FORMAT CHANGE")
    print("Expect columns: Status, Country, Date_confirmation, Date_entry to exist")
    print("Check downloaded file: ", strDataFile," and see if header has changed")
    sys.exit(0)
    
# import the data
pBaseDate = datetime(2022, 4, 20)
mapDate = {}
nMaxDay = 0
strNationLower = strNation.lower().replace(" ","_")
pLastDate = pBaseDate
with open(strDataFile) as inFile:
    lstHeader = inFile.readline().split(",")
    
    for strLine in inFile:
        lstMatches = reValue.findall(strLine)
        for strMatch in lstMatches:
            strLine = strLine.replace(strMatch, strMatch.replace(",", " "))
        lstLine = strLine.split(",")
        if len(lstLine) != nHeaderSize: continue
        if lstLine[nStatusIndex].lower() == "confirmed" or (bUC and lstLine[nStatusIndex] != "discarded"): 
            if strNation == "World" or lstLine[nCountryIndex] == strNation:
                if bUC:
                    nYear, nMonth, nDay = map(int, lstLine[nUnconfirmedDateIndex].split("-"))
                else:
                    nYear, nMonth, nDay = map(int, lstLine[nDateIndex].split("-"))
                pDate = datetime(nYear, nMonth, nDay)
#                print(nYear, nMonth, nDay)
                nDay = (pDate-pBaseDate).days
                if nDay not in mapDate:
                    mapDate[nDay] = 0
                mapDate[nDay] += 1
                if nDay > nMaxDay: nMaxDay = nDay
                if pDate > pLastDate: pLastDate = pDate

# look at most recent data in file
print("Last updated: ", pLastDate," which was ", (pToday-pLastDate).days," days ago")

# skip the last few days as they are generally not up to date
nMaxDay -= 3

# accumulate weekly data, working backward to ensure full week at end
lstWeek = []
lstDays = []
lstCount = []
lstDayCount = []
nFitStart = -1
with open(strDate+"_owid_"+strNationLower+strUC+".csv", "w") as outFile:
    for nI in range(nMaxDay, -1, -1):
        if nI in mapDate:
            lstWeek.append(mapDate[nI])
            lstDayCount.insert(0, mapDate[nI]) # keep track of daily
        else:
            lstWeek.append(0)
            lstDayCount.insert(0, 0) # keep track of daily

        if len(lstWeek) == 7:
            nCount = sum(lstWeek)
            outFile.write(str(nI+3)+" "+str(nCount)+"\n")
#            print(nI+3, nCount)
            lstWeek = []

            lstDays.insert(0, nI+3)
            lstCount.insert(0, nCount)

# dump day count for debugging/inspections
with open("monkeypox_"+strNationLower+"_daily.csv", "w") as outFile:
    nTotal = 0
    outFile.write("# Start day: "+str(pBaseDate.date())+"\n")
    for nI, nCount in enumerate(lstDayCount):
        nTotal += nCount
        outFile.write(str(nI)+" "+str(nCount)+" "+str(nTotal)+"\n")

# only fit for days > 200
for nI, nCount in enumerate(lstCount):
    if nCount > 200:
        nFitStart = nI
        break
            
# bail if not enough data
if nFitStart < 0 or len(lstDays) - nFitStart < 3:
    print("Insufficient data for fitting. Must have three weeks > 200 new cases per week")
    sys.exit(0)

# fit the data
lstCoeffs = np.polyfit(lstDays[nFitStart:], np.log(lstCount[nFitStart:]), deg=1)
fEfoldingTime = 1/lstCoeffs[0]
fBase = math.exp(lstCoeffs[1])
fDoublingTime = math.log(2)*fEfoldingTime
fit = np.poly1d(lstCoeffs)
fLogRMS = 0.0
nCount = 0
with open(strDate+"_fit_"+strNationLower+strUC+".csv", "w") as outFile:
    outFile.write("# Doubling: "+str(fDoublingTime)+"\n")
    outFile.write("# "+str(fBase)+"+exp(nDay/"+str(fEfoldingTime)+")\n")
    for nI, nDay in enumerate(lstDays):
        if nFitStart > 0 and nI >= nFitStart:
            print(nDay, lstCount[nI], int(math.exp(fit(nDay))))
            fLogRMS += (math.log(lstCount[nI])-fit(nDay))**2
            nCount += 1
            outFile.write(" ".join(map(str, (nDay, lstCount[nI], math.exp(fit(nDay)))))+"\n")

if nCount > 0:
    print("Doubling time (days): %4.2f"%fDoublingTime)
    print("RMS of Log Fit: %5.3F"%math.sqrt(fLogRMS/nCount))

# correct last point for incomplete data
lstCount[-1] = 1.15*lstCount[-1]

# plot with dates
lstDates = [pBaseDate+timedelta(days=x) for x in lstDays]
pLocator = mdates.AutoDateLocator()
pFormatter = mdates.AutoDateFormatter(pLocator)
pFigure, pPlot = plt.subplots()
pPlot.xaxis.set_major_locator(pLocator)
pPlot.xaxis.set_major_formatter(pFormatter)
pPlot.set_yscale("log")
if bUC:
    pPlot.set_title("Monkeypox "+strNation+" Weekly New Cases (incl. unconfirmed)")
else:
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
pPlot.annotate('Fit: '+str(fBase)[0:5]+"*exp(nDay/"+str(fEfoldingTime)[0:5]+")",
            xy=(.14, .77), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)            
pPlot.annotate('Start day: '+str(pBaseDate.date()),
            xy=(.14, .74), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)            
pPlot.annotate('x',
            xy=(.14, .715), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=10, color="r")            
pPlot.annotate('= partial data, corrected',
            xy=(.16, .71), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)            
pPlot.annotate('Generated: '+strDate+" from https://ourworldindata.org/monkeypox",
            xy=(.3, .25), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)
pPlot.plot(lstDates[nFitStart:-1], lstCount[nFitStart:-1], "bx")
pPlot.plot(lstDates[-1:], lstCount[-1:], "rx")
pPlot.plot(lstDates[nFitStart:], [math.exp(fit(x)) for x in lstDays[nFitStart:]])
pFigure.autofmt_xdate()
pFigure.savefig(strDate+"_owid_"+strNationLower+strUC+".png")

# plot linear with dates
lstDates = [pBaseDate+timedelta(days=x) for x in lstDays]
pLocator = mdates.AutoDateLocator()
pFormatter = mdates.AutoDateFormatter(pLocator)
pFigure, pPlot = plt.subplots()
pPlot.xaxis.set_major_locator(pLocator)
pPlot.xaxis.set_major_formatter(pFormatter)
#pPlot.set_yscale("log")
if bUC:
    pPlot.set_title("Monkeypox "+strNation+" Weekly New Cases (incl. unconfirmed)")
else:
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
pPlot.annotate('Fit: '+str(fBase)[0:5]+"*exp(nDay/"+str(fEfoldingTime)[0:5]+")",
            xy=(.14, .77), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)            
pPlot.annotate('Start day: '+str(pBaseDate.date()),
            xy=(.14, .74), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)            
pPlot.annotate('x',
            xy=(.14, .715), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=10, color="r")            
pPlot.annotate('= partial data, corrected',
            xy=(.16, .71), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)            
pPlot.annotate('Generated: '+strDate+" from https://ourworldindata.org/monkeypox",
            xy=(.3, .25), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)
pPlot.plot(lstDates[nFitStart:-1], lstCount[nFitStart:-1], "bx")
pPlot.plot(lstDates[-1:], lstCount[-1:], "rx")
pPlot.plot(lstDates[nFitStart:], [math.exp(fit(x)) for x in lstDays[nFitStart:]])
pFigure.autofmt_xdate()
strUC += "_linear"
pFigure.savefig(strDate+"_owid_"+strNationLower+strUC+".png")
