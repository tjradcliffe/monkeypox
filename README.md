# monkeypox
Simple application to download, analyze, and plot monkeypox data from Our World In Data (OWID).

The code has been tested on linux. If you're on a different platform you're on your own, as I don't have access to them. The only thing outside the standard library is matplot lib:

pip install matplotlib

or something like it should install that for you.

Run with:

python3 mpx_pandemic.py

to download the data from https://ourworldindata.org/monkeypox to owid_data.csv (only refreshes every 12 hours) and generate plots of the new confirmed world-wide cases as PNG images. Two images are generated: YYYY-MM-DD\_owid\_world.png and  YYYY-MM-DD\_owid\_world\_linear.png. The latter has an inset plot showing the data on log scale. The data files YYYY-MM-DD\_owid\_world.csv and YYYY-MM-DD\_fit\_world.csv contain the raw and fit data, respectively. The file monkeypox\_world\_daily.csv contains the daily numbers. These are all space-separated not comma-separated files.

python3 mpx_pandemic.py -n lists all nations that have cases, along with their ISO3 code and case numbers.

For a specific nation:

python3 mpx_pandemic.py ISO3

generates the data files with \_world\_ replaced by \_iso3\_, so for the US: 

python3 mpx_pandemic.py USA

produces YYYY-MM-DD\_owid\_usa.png and so on.

Normal operation looks only at confirmed cases. Adding a -c option will include suspected cases. This usually does not change the numbers much.

Analysis requires at least three weeks with more than 200 cases per week. This cuts off the early non-exponential growth where the shape of the curve is dominated by testing and reporting issues.

The analysis consists of fitting the log(weekly) counts to a line using np.polyfit(), so the contribution of each point to the error is log-weighted. The weekly counts are generated by iterating down from the current day, and the last three days of data are ignored as they are pretty laggy. Even so, the last week's point is corrected upward by 15% _after_ the fit is done to give better visuals. Otherwise it always looks like the data are about to turn over, which they have not done in the six weeks I've been running this: see final\_week\_progression.png for a demonstration of this fact over the past few weeks. The corrected final point in any given week is a good match to the uncorrected second-to-last point the next week, which is what one would expect if the correction was a reasonably good way to fill in for lagging data. Again: the correction is visual only. It is not used in the fit.

The fact that the data are analyzed from the most recent day down means that plots from day to day take in different divisions of time, so there tends to be some weekly variation in the doubling time, with longer times (by a day or two) coming after weekends as the data are more laggy then. That said, there does seem to be some slowdown in growth in past month, and the national data from Germany--where new case numbers are now flat or declining from week-to-week--is a significant factor in that.

python3 count\_nations.py 

generates a plot of the number of nations that have reported at least one monkeypox case: monkeypox\_nation\_count.png

