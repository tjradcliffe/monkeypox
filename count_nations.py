from datetime import datetime, timedelta
import re

import matplotlib
import matplotlib.dates as mdates
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from download_mpx_owid import download_data

# for dealing with commas in quoted fields
reValue = re.compile(r'"(.*?)"')

def count_nations(strDataFile):
    
    # download if required
    download_data(strDataFile)
    
    # find nations
    lstNewNations = []
    pBaseDate = datetime(2022, 4, 20)
    pToday = datetime.today()
    strDate = str(pToday.date())
    while pBaseDate < pToday:
        lstNewNations.append(set())
        pBaseDate += timedelta(days=1)
    pBaseDate = datetime(2022, 4, 20)
    
    with open(strDataFile) as inFile:
        for strLine in inFile:
            lstMatches = reValue.findall(strLine)
            for strMatch in lstMatches: # step on commas in quoted strings
                strLine = strLine.replace(strMatch, strMatch.replace(",", "DNUSID"))
            lstLine = strLine.split(",")
            if len(lstLine) != 32: continue
            if lstLine[1].lower() == "confirmed": 
                nYear, nMonth, nDay = map(int, lstLine[8].split("-"))
                pDate = datetime(nYear, nMonth, nDay)
                nDays = (pDate-pBaseDate).days
                lstNewNations[nDays].add(lstLine[4])
                
    setTotal = set()
    lstNationCount = []
    lstDays = []
    nFitStart = 0
    for nDay, setNations in enumerate(lstNewNations):
        setTotal = setTotal.union(setNations)
#        print(pBaseDate+timedelta(days=nDay), len(setTotal))
        lstDays.append(nDay)
        lstNationCount.append(len(setTotal))
        if not len(setTotal):
            nFitStart = nDay # set to last zero-day

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
    pPlot.annotate('Generated: '+strDate+" from https://ourworldindata.org/monkeypox",
                xy=(.14, .85), xycoords='figure fraction',
                horizontalalignment='left', verticalalignment='top',
                fontsize=8)
    pPlot.plot(lstDates[nFitStart:], lstNationCount[nFitStart:], "bx")
    pFigure.autofmt_xdate()
    pFigure.savefig("monkeypox_nation_count.png")

###
strDataFile = "owid_monkeypox.csv"

# download if required
download_data(strDataFile)

count_nations(strDataFile)
