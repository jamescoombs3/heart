"""
This script evaluates secondary schools' inclusivity by comparing their %FSM against nearby primaries' %FSM
weighted by size and inverse square of distance. Fuller explanation here: https://trak.org.uk/mind-the-gap/

Version 1
V1 started out by comparing each secondary school against its (single) nearest primary school. Intention was to
look at a number of primary schools, weighted by distance to compare each secondary against its 'neighbourhood'
Original script enabled *anything* in the school level data to be compared but the main interest is social
equality. The usual metric (both sides of the atlantic) is to look at proportion of children in receipt of Free
School Meals (FSM)

I have overwritten version 1 because I forgot to 'save as'!

Version 2 changes:
# SOURCE DATA
https://get-information-schools.service.gov.uk/Downloads
Select "all data"
Download the zip file and extract all the files.
The required one is called (depending on the date) something like this:
edubasealldata20250310.csv

#2.2 Code programmatically preprends 'P_' to all the primary school fields rather than hard code.

Version 3 changes.
This will be a departure from the previous. The previous allowed any data values that appeared in the GIAS dataset
for a given secondary school to be compared against its nearest primary.
#3.1 After much contemplation the intention is to make this easier by just looking at %FSM but far more complex by
using a square law weighting to work out the FSM attributes of a dozen primary schools using this (latex) formula
\displaystyle \sum^n_{1} \left[
\frac{\frac{c_n}{d^2_n}\times FSM_n}
{\sum^n_{1}\frac{c_n}{d^2_n}} \right]
To view what that looks like graphically, click this link:
https://arachnoid.com/latex/?equ=%5Cdisplaystyle%20%5Csum%5En_%7B1%7D%20%5Cleft%5B%0A%5Cfrac%7B%5Cfrac%7Bc_n%7D%7Bd%5E2_n%7D%5Ctimes%20FSM_n%7D%0A%7B%5Csum%5En_%7B1%7D%5Cfrac%7Bc_n%7D%7Bd%5E2_n%7D%7D%20%5Cright%5D

#3.2. This version should still allow any attribute in the GIAS dataset which may explain differences in SES
inclusivity. The equivalent of explanatory factors in multiple linear regression (which is where the resulting
data will be sent.) First stage is to look at GIAS to identify what might be interesting and define two dictionaries.
One has the fields wanted for both primary and secondary like location, size and %FSM. The other has all the
explanatory variables. Defining these as dictionaries means they can be used to load and rename columns.

Version 4.(a)
There is a run time bug caused by (rare) situation where a secondary school's nearest primary is same postcode
(because it is the same school!) This leads to a divide by zero error. A simple solution is to just add one
metre to the distance if zero.
4.(b)
A request to change some of the school attribute fields including a concatenated address and output a subset of
the data in json format.

Version 5
The inverse square distance weighting results in some examples where two secondary schools are close to each other
and close to primary schools with very variable FSM rates have very different FSM rates for the 'local neighbouring
primaries' even though the schools are in the same locality. This version modifies the weight given to add a fixed
distance so the weight given to each primary is
c/k+d^2
where c is the cohort size, k a constant distance and d is the distance from the secondary school to the primary.

Version 6
Adds calibration. Prior to that the mode value of gap size was -1.03005975072902 %.
This also shows the method worked very well without those modifications. For example if the 'local area FSM'
was on average 10% more (or less) than in secondary schools there is a problem with the weighting.
"""

import pandas as pd

# fields for comparing schools (and some filtering)
comp = {'URN': 'URN', 'EstablishmentName': 'EstablishmentName', 'EstablishmentStatus (name)': 'EstablishmentStatus',
        'PhaseOfEducation (name)': 'PhaseOfEducation', 'PercentageFSM': 'PercentageFSM', 'Easting': 'Easting',
        'NumberOfPupils': 'NumberOfPupils', 'Northing': 'Northing'}

# potential explanatory variable fields (for secondary schools only).
expl = {'LA (name)': 'LA', 'TypeOfEstablishment (name)': 'TypeOfEstablishment',
        'Street': 'Street', 'Locality': 'Locality', 'Address3': 'Address',
        'Town': 'Town', 'County (name)': 'County', 'Postcode': 'Postcode',
        'Gender (name)': 'Gender',
        'ReligiousCharacter (name)': 'ReligiousCharacter', 'AdmissionsPolicy (name)': 'AdmissionsPolicy',
        'SchoolCapacity': 'SchoolCapacity',         'TrustSchoolFlag (name)': 'TrustSchoolFlag',
        'ParliamentaryConstituency (name)': 'ParliamentaryConstituency', 'UrbanRural (name)': 'UrbanRural'}

cols = []
for c in comp.keys():
    cols.append(c)

for c in expl.keys():
    cols.append(c)

# load ~50k rows covering all school types.
df = pd.read_csv('data/extract/edubasealldata20250429.csv', usecols=cols, encoding='latin')
# Latin?! Don't ask. It works.

# rename all columns (makes the code that comes later cleaner)
df.rename(columns=comp, inplace=True)
df.rename(columns=expl, inplace=True)

# Keep only open schools.
df = df.loc[(df.EstablishmentStatus == 'Open')]
df = df.drop(columns=['EstablishmentStatus'])
# Remove missing %FSM
df = df.dropna(subset=['PercentageFSM'])
# 48 primary/secondary schools found with zero FSM which seems issue with DfE data.
df = df.loc[(df.PercentageFSM != 0)]
df = df.dropna(subset=['SchoolCapacity'])

"""
# This code counts the number of nans in all columns. Should be zero for all numeric fields.  
# Not part of the script but can be run if a later data file contains missing numeric values. 
for c in df.columns:
    print(c, df[c].isna().sum())

"""
# Set any missing values to empty strings. Helps with creating a tidied up 'address' field.
df = df.fillna('')

# Create separate dataframes for primaries and secondaries using .copy()
sec = df.loc[(df.PhaseOfEducation == 'Secondary')].copy()
sec = sec.drop(columns=['PhaseOfEducation'])
# Concat all the other address values onto the first ('Street')
addrcols = ['Locality', 'Address', 'Town', 'County', 'Postcode']
for c in addrcols:
    sec['Street'] += ' ' + sec[c]

sec = sec.rename(columns={'Street': 'Full_Address'})
sec = sec.drop(columns=addrcols)

"""
# Selecting just 96 Kent secondary schools for testing (whilst retaining all the primaries) is roughly 1/3%.  
# This makes testing 300× faster!   
sec = sec.loc[(sec.LA == 'Kent')]  

"""

pri = df.loc[(df.PhaseOfEducation == 'Primary')].copy()
pri = pri.drop(columns=['PhaseOfEducation'])
# "pri" contains the explanatory variables which aren't needed. Not essential but drop those columns.
pri = pri.drop(columns=expl.values())

# Set the number of primary schools to check here.
x = 18
pcols = []
for k in range(0, x):
    for c in pri.columns:
        pcols.append('P' + str(k) + '_' + c)
    pcols.append('P' + str(k) + '_dist')
    pcols.append('P' + str(k) + '_weight')


def nearest_peas(e, n, k):
    """
    :param e: Eastings of Secondary school
    :param n: Northings of Secondary school
    :param k: constant distance added to the actual distance.
    :return: A series with the x nearest primary schools' attributes and their distances.
    nearest peas is a vegetarian pun.
    """
    # This next line applies the distance to primaries. Added a fixed value in version 5.
    # pri['dist'] = pri.apply(lambda roww: ((e - roww.Easting) ** 2 + (n - roww.Northing) ** 2) ** 0.5, axis=1)
    # k = 1000
    pri['dist'] = pri.apply(lambda roww: k + ((e - roww.Easting) ** 2 + (n - roww.Northing) ** 2) ** 0.5, axis=1)

    # create copy of just the x nearest primaries
    tdf = pri.sort_values('dist').head(x).copy()
    # If secondary and primary have same postcode the distance is zero which results in probs later.
    # So set this distance to 100 metres.
    tdf = tdf.reset_index(drop=True)
    if tdf.loc[0, 'dist'] == 0:
        tdf.loc[0, 'dist'] = 100

    # add a weight column
    tdf['w'] = tdf['NumberOfPupils'] / tdf['dist'] ** 2
    # normalise this so it sums to 1
    wsum = tdf.w.sum()
    tdf['w'] = tdf['w'] / wsum
    # Create an empty series for the function to return.
    s = pd.Series
    # 'unwrap' tdf to return a single series. This is applied to the secondary school dataframe outside this function.
    for kk in range(0, x):
        if kk == 0:
            s = tdf.iloc[kk]
        else:
            s = pd.concat([s, tdf.iloc[kk]])
    return s


# testSer = nearest_peas(471232, 176358, 1000)   # test the above function with a local secondary school (Reading)

const = 1000  # This constant is added to the distance to each primary to 'detune' the results.
for i, row in sec.iterrows():
    # print(i)
    sec.loc[i, pcols] = nearest_peas(row.Easting, row.Northing, const).values
    if i % 100 == 0:
        print(i, 'distances checked')  # Haven't quite figured out why this doesn't work as expected

print("The above counting doesn't work as expected but does provide some visual feedback that it's still running.")


# 'sec' is now a very wide dataframe with x sets of results for the nearest primaries.
# Finally, work out the "local" FSM rate

def local_fsm(r):
    """
    :param r: The current row from the sec(ondary) dataframe as Series.
    :return: Scalar value representing the 'local' %FSM based on the nearest x primary schools.
    This function adds up the products of fields P<k>_PercentageFSM × P<k>_weight
    """
    fsmsum = 0
    for kk in range(0, x):
        fsmsum += r['P' + str(kk) + '_PercentageFSM'] * r['P' + str(kk) + '_weight']
    return fsmsum


# The sec dataframe is defragmented so before continuing make a copy ...
sec2 = sec.copy()
del sec   # ... then delete orig to free up memory
# LocalFSM is a weighted value calculated using the function above.
sec2['localFSM'] = sec2.apply(lambda srow: local_fsm(srow), axis=1)

# Calculate the gap. NB *gap* is positive if the school admits less FSM than local
sec2['gap'] = sec2['localFSM'] - sec2['PercentageFSM']

# Calculating the quantile values needed to categorise 'inclusivity'
qt = {}
qt[10] = sec2.gap.quantile(q=0.1)
qt[25] = sec2.gap.quantile(q=0.25)
qt[75] = sec2.gap.quantile(q=0.75)
qt[90] = sec2.gap.quantile(q=0.9)

def cat(g):
    """
    provides an English language categorisation of 'inclusivity' relative to all other schools
    :param g: The gap between a secondary school and its neighbouring primaries
    :return: category (self-explanatory see below)
    """
    if g < qt[10]:
        return 'very inclusive'
    if g < qt[25]:
        return 'more inclusive than most'
    if g < qt[75]:
        return 'broadly typical'
    if g < qt[90]:
        return 'less inclusive than most'
    else:
        return 'among the least inclusive'


"""
Some testing ...
import numpy as np

for gg in np.arange(-15, 15, 1):
    print('gap =', gg, 'categorised as', cat(gg))
"""

sec2['cat'] = sec2['gap'].apply(lambda xx: cat(xx))

# write EVERYTHING to CSV including all interim workings so it can be checked.
sec2.to_csv('data/nearest_primary-v6-uncal.csv', index=False)

# Proportion of FSM children in schools should match that in community. The median gap is almost exactly -1%
# This section calibrates the gaps so there are an equal number of more inclusive schools as less inclusive ones.
# See https://trak.org.uk/mind-the-gap/ for fuller explanation.
medgap = sec2.gap.quantile(0.5)
print('The median gap is', medgap, 'Results will be calibrated by this amount')
print('(Uncalibrated data has been exported for reference.)')

# recalibrate localFSM by subtracting the median gap.
sec2['localFSM'] = sec2.localFSM - medgap
# recalculate the gap. (We could instead calibrate this and arrive at the same results but this way seems clearer.)
sec2['gap'] = sec2['localFSM'] - sec2['PercentageFSM']

medgap = sec2.gap.quantile(0.5)
print('The median gap is now', medgap)

# Round values to a single decimal point (matches DfE)
sec2 = sec2.round(1)

keep = ['URN', 'LA', 'EstablishmentName', 'TypeOfEstablishment', 'Gender', 'ReligiousCharacter', 'AdmissionsPolicy',
        'SchoolCapacity', 'NumberOfPupils', 'PercentageFSM', 'TrustSchoolFlag', 'Full_Address',
        'ParliamentaryConstituency', 'UrbanRural', 'localFSM', 'gap', 'cat']

gapdf = sec2[keep].copy()
gapdf.to_csv('data/gap_data-v6-calib.csv', index=False)
# keep = ['LA', 'PercentageFSM', 'Full_Address', 'localFSM', 'gap', 'cat']
# gapdf = gapdf[keep].copy()
gapdf.to_json('data/gap_data-v6-calib.json', orient='records')

