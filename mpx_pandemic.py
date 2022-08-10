import argparse
from datetime import datetime, timedelta
import math
import os
import re
import sys
import time

import numpy as np

import matplotlib
import matplotlib.dates as mdates
matplotlib.use("Agg") # have to do this before pyplot import
import matplotlib.pyplot as plt

from download_mpx_owid import download_data

# for dealing with commas in quoted fields
reValue = re.compile(r'"(.*?)"')

def getColumns(strDataFile):
    """Find columns in data file"""
    with open(strDataFile) as inFile:
        lstHeader = inFile.readline().split(",")
        for nI, strWord in enumerate(lstHeader):
            if strWord == "Country_ISO3":
                nCountryIndex = nI
            elif strWord == "Date_confirmation":
                nDateIndex = nI
            elif strWord == "Status":
                nStatusIndex = nI
            elif strWord == "Date_entry":
                nUnconfirmedDateIndex = nI

    return nCountryIndex, nDateIndex, nStatusIndex, nUnconfirmedDateIndex
    
def listNations(strDataFile):
    """List nations and their ISO3 codes"""
    
    # download if required
    try:
        download_data(strDataFile)
    except Exception as e:
        print(e)
        sys.exit(0)

    # import ISO3 data
    mapISO3 = {}
    with open('iso3.csv') as inFile:
        for strLine in inFile:
            lstLine = strLine.strip().split(':')
            if len(lstLine) == 2:
                mapISO3[lstLine[1]]  = lstLine[0]
            else:
                print("Ignored: ", strLine.strip())

    # find country column
    nCountryIndex, nDateIndex, nStatusIndex, nUnconfirmedDateIndex = getColumns(strDataFile)
    
    # find nations
    mapNations = {}
    with open(strDataFile) as inFile:
        nHeaderSize = len(inFile.readline().strip().split(","))
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
bUC = False
strUC = ""
    
pParser = argparse.ArgumentParser(prog="python3 mpx_pandemic.py", description="Download and plot monkeypox data from OWID")
pParser.add_argument("nation", help="ISO3 code for target nation, generates YYYY-DD-MM_owid_ISO3.csv, \
YYYY-DD-MM_fit_ISO3.png, YYYY-DD-MM_fit_ISO3_linear.png \
If no nation given 'world' is used. Taiwan is not part of China. \
Data is downloaded from https://ourworldindata.org/monkeypox via \
 https://raw.githubusercontent.com/globaldothealth/monkeypox/main/latest.csv \
 to "+strDataFile, nargs="?", default="")
pParser.add_argument("--nations", "-n", action="store_true", help="List nations by ISO3 code")
pParser.add_argument("-c", action="store_true", help="drops the confirmed case requirement (adds _uc to output filenames")

pArgs = pParser.parse_args(sys.argv[1:])
    
if pArgs.nations:
    listNations(strDataFile)
    sys.exit(0)
elif pArgs.c:
    bUC = True
    strUC = "_uc"
    
if len(pArgs.nation):
    strNation = pArgs.nation

print("Processing: ", strNation)

# setup date info
pToday = datetime.today()
strDate = str(pToday.date())

# download if required
try:
    download_data(strDataFile)
except Exception as e:
    print(e)
    sys.exit(0)

# get columns
nCountryIndex, nDateIndex, nStatusIndex, nUnconfirmedDateIndex = getColumns(strDataFile)
    
# import the data
pBaseDate = datetime(2022, 4, 20)
mapDate = {}
nMaxDay = 0
strNationLower = strNation.lower().replace(" ","_")
pLastDate = pBaseDate
with open(strDataFile) as inFile:
    nHeaderSize = len(inFile.readline().strip().split(","))    
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
for nI in range(nMaxDay, -1, -1):
    if nI in mapDate:
        lstWeek.append(mapDate[nI])
        lstDayCount.insert(0, mapDate[nI]) # keep track of daily
    else:
        lstWeek.append(0)
        lstDayCount.insert(0, 0) # keep track of daily

    if len(lstWeek) == 7:
        nCount = sum(lstWeek)
        lstWeek = []

        lstDays.insert(0, nI+3)
        lstCount.insert(0, nCount)

# dump to file
with open(strDate+"_owid_"+strNationLower+strUC+".csv", "w") as outFile:
    for nI, nDay in enumerate(lstDays):
        outFile.write(str(nDay)+" "+str(lstCount[nI])+"\n")

# dump day count for debugging/inspections
with open("monkeypox_"+strNationLower+"_daily.csv", "w") as outFile:
    nTotal = 0
    outFile.write("# Start day: "+str(pBaseDate.date())+"\n")
    for nI, nCount in enumerate(lstDayCount):
        nTotal += nCount
        outFile.write(str(nI)+" "+str(nCount)+" "+str(nTotal)+"\n")

# only fit for weeks with > 200 new cases
for nI, nCount in enumerate(lstCount):
    if nCount > 200:
        nFitStart = nI
        break
            
# bail if not enough data
if nFitStart < 0 or len(lstDays) - nFitStart < 3:
    print("Insufficient data for fitting. Must have three weeks > 200 new cases per week")
    sys.exit(0)

# fit the data using linear fit to logs (=> log weighting of error)
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

# correct last point for incomplete data (after fitting: visual correction only)
lstCount[-1] = 1.15*lstCount[-1]

# log plot with dates
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
pPlot.annotate('Code: https://github.com/tjradcliffe/monkeypox',
            xy=(.48, .28), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)            
pPlot.annotate('Generated: '+strDate+" from https://ourworldindata.org/monkeypox",
            xy=(.3, .25), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)
pPlot.plot(lstDates[nFitStart:-1], lstCount[nFitStart:-1], "bx")
pPlot.plot(lstDates[-1:], lstCount[-1:], "rx")
pPlot.plot(lstDates[nFitStart:], [math.exp(fit(x)) for x in lstDays[nFitStart:]])
pPlot.grid(True, linewidth=0.2)
pFigure.autofmt_xdate()
pFigure.savefig(strDate+"_owid_"+strNationLower+strUC+".png")

# linear plot with dates and log inset
lstDates = [pBaseDate+timedelta(days=x) for x in lstDays]
pLocator = mdates.AutoDateLocator()
pFormatter = mdates.AutoDateFormatter(pLocator)
pFigure, pPlot = plt.subplots()
pPlot.xaxis.set_major_locator(pLocator)
pPlot.xaxis.set_major_formatter(pFormatter)
if bUC:
    pPlot.set_title("Monkeypox "+strNation+" Weekly New Cases (incl. unconfirmed)")
else:
    pPlot.set_title("Monkeypox "+strNation+" Weekly New Confirmed Cases")
    
pPlot.set_xlabel("Date")
pPlot.set_ylabel("Count")
pPlot.annotate('Fit: '+str(fBase)[0:5]+"*exp(nDay/"+str(fEfoldingTime)[0:5]+")",
            xy=(.64, .27), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)            
pPlot.annotate('Start day: '+str(pBaseDate.date()),
            xy=(.64, .24), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)            
pPlot.annotate('x',
            xy=(.64, .215), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=10, color="r")            
pPlot.annotate('= partial data, corrected',
            xy=(.66, .21), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)
pPlot.annotate('Code: https://github.com/tjradcliffe/monkeypox',
            xy=(.48, .18), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)            

pPlot.annotate('Generated: '+strDate+" from https://ourworldindata.org/monkeypox",
            xy=(.3, .15), xycoords='figure fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=8)
pPlot.plot(lstDates[nFitStart:-1], lstCount[nFitStart:-1], "bx")
pPlot.plot(lstDates[-1:], lstCount[-1:], "rx")
pPlot.plot(lstDates[nFitStart:], [math.exp(fit(x)) for x in lstDays[nFitStart:]])
pPlot.grid(True, linewidth=0.2)

left, bottom, width, height = [0.19, 0.45, 0.4, 0.4] # log-plot inset
pLogPlot = pFigure.add_axes([left, bottom, width, height])
pLogPlot.set_yscale("log")
pLogPlot.plot(lstDates[nFitStart:-1], lstCount[nFitStart:-1], "bx")
pLogPlot.plot(lstDates[-1:], lstCount[-1:], "rx")
pLogPlot.plot(lstDates[nFitStart:], [math.exp(fit(x)) for x in lstDays[nFitStart:]])
pLogPlot.annotate("Log Scale", xy=(0.1, 0.9), xycoords='axes fraction', 
            horizontalalignment='left', verticalalignment='top',
            fontsize=12)
pLogPlot.annotate('Doubling Time: '+str(fDoublingTime)[0:5]+" days",
            xy=(.1, .11), xycoords='axes fraction',
            horizontalalignment='left', verticalalignment='top',
            fontsize=12, color="crimson")
pLogPlot.set_facecolor('lightgrey')
pLogPlot.grid(True, linewidth=0.2)
for n, label in enumerate(pLogPlot.xaxis.get_ticklabels()):
    label.set_fontsize(8) # sparse, small, date tics
    if not n%2:
        label.set_visible(False)

#pFigure.autofmt_xdate() # doing this creates angled dates that use more real estate
strUC += "_linear"
pFigure.savefig(strDate+"_owid_"+strNationLower+strUC+".png")
