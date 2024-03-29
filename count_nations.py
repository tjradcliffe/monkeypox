from datetime import datetime, timedelta
import re

import numpy as np

import matplotlib
import matplotlib.dates as mdates
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from download_mpx_owid import download_data

# for dealing with commas in quoted fields
reValue = re.compile(r'"(.*?)"')

def getColumns(strDataFile):
    """Find columns in data file"""
    with open(strDataFile) as inFile:
        lstHeader = inFile.readline().split(",")
        for nI, strWord in enumerate(lstHeader):
            if strWord == "iso_code":
                nCountryIndex = nI
            elif strWord == "date":
                nDateIndex = nI
            elif strWord == "new_cases":
                nCasesIndex = nI

    return nCountryIndex, nDateIndex, nCasesIndex

def count_nations(strDataFile):
    
    # download if required
    nHeaderSize = download_data(strDataFile)
    
    # find nations
    nCountryIndex, nDateIndex, nCasesIndex = getColumns(strDataFile)
    lstNewNations = []
    pBaseDate = datetime(2022, 4, 20)
    pToday = datetime.today()
    strDate = str(pToday.date())
    while pBaseDate < pToday:
        lstNewNations.append(set())
        pBaseDate += timedelta(days=1)
    pBaseDate = datetime(2022, 4, 20)
    
    with open(strDataFile) as inFile:
        inFile.readline() # discard header
        for strLine in inFile:
            lstMatches = reValue.findall(strLine)
            for strMatch in lstMatches: # step on commas in quoted strings
                strLine = strLine.replace(strMatch, strMatch.replace(",", "DNUSID"))
            lstLine = strLine.split(",")
            if len(lstLine) != nHeaderSize: continue
            nYear, nMonth, nDay = map(int, lstLine[nDateIndex].split("-"))
            pDate = datetime(nYear, nMonth, nDay)
            nDays = (pDate-pBaseDate).days
            lstNewNations[nDays].add(lstLine[nCountryIndex])
                
    setTotal = set()
    lstNationCount = []
    lstDays = []
    nDataStart = 0
    for nDay, setNations in enumerate(lstNewNations):
        setTotal = setTotal.union(setNations)
#        print(pBaseDate+timedelta(days=nDay), len(setTotal))
        lstDays.append(nDay)
        lstNationCount.append(len(setTotal))
        if not len(setTotal):
            nDataStart = nDay # set to last zero-day

    # linear fit above day 20
    nFitStart = nDataStart + 20
    lstCoeffs = np.polyfit(lstDays[nFitStart:], lstNationCount[nFitStart:], deg=1)
    fit = np.poly1d(lstCoeffs)
    fLogRMS = 0.0
    nCount = 0
    
    # dump to file
    with open("monkeypox_nation_count.csv", "w") as outFile:
        outFile.write("# Start day: "+str((pBaseDate+timedelta(days=nDataStart)).date())+"\n")
        for nI in range(nDataStart, len(lstDays)):
            outFile.write(str(nI-nDataStart)+" "+str(lstNationCount[nI])+" "+str(fit(nI))+"\n")

    print("Number of nations: ", lstNationCount[-1])

    # plot with dates
    lstDates = [pBaseDate+timedelta(days=x) for x in lstDays]
    pLocator = mdates.AutoDateLocator()
    pFormatter = mdates.AutoDateFormatter(pLocator)
    pFigure, pPlot = plt.subplots()
    pPlot.xaxis.set_major_locator(pLocator)
    pPlot.xaxis.set_major_formatter(pFormatter)
    pPlot.set_title("Number of Nations with Confirmed Monkeypox Cases")
        
    pPlot.set_xlabel("Date")
    pPlot.set_ylabel("Nations")
    pPlot.annotate('Slope: '+str(lstCoeffs[0])[0:4]+" nations/day",
                xy=(.14, .85), xycoords='figure fraction',
                horizontalalignment='left', verticalalignment='top',
                fontsize=8, color="r")            
    pPlot.annotate('Generated: '+strDate+" from https://ourworldindata.org/monkeypox",
                xy=(.3, .23), xycoords='figure fraction',
                horizontalalignment='left', verticalalignment='top',
                fontsize=8)
    pPlot.plot(lstDates[nDataStart:], lstNationCount[nDataStart:], "bx")
    pPlot.plot(lstDates[nFitStart:], [fit(x) for x in lstDays[nFitStart:]], "r")
    pFigure.autofmt_xdate()
    pFigure.savefig("monkeypox_nation_count.png")

###
strDataFile = "owid_monkeypox.csv"

# download if required
download_data(strDataFile)

count_nations(strDataFile)
