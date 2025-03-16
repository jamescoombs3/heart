"""
Prerequisites:
"School data with location" worksheet needs to be saved as csv file.

Version 1
V1 started out by comparing each secondary school against its (single) nearest primary school. Intention was to
look at a number of primary schools, weighted by distance to compare each secondary against its 'neighbourhood'
Original script enabled *anything* in the school level data to be compared but the main interest is social
equality. The usual metric (both sides of the atlantic) is to look at proportion of children in receipt of Free
School Meals (FSM)

I have overwritten version 1 because I forgot to 'save as'!

Version 2 changes:
#2.1 Find definitive source so others can repeat or modify this code.
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

"""

import pandas as pd

# fields for comparing schools (and some filtering)
comp = {'URN': 'URN', 'EstablishmentName': 'EstablishmentName', 'EstablishmentStatus (name)': 'EstablishmentStatus',
        'PhaseOfEducation (name)': 'PhaseOfEducation', 'PercentageFSM': 'PercentageFSM', 'Easting': 'Easting',
        'NumberOfPupils': 'NumberOfPupils', 'Northing': 'Northing'}

# potential explanatory variable fields (for secondary schools only).
expl = {'LA (name)': 'LA', 'TypeOfEstablishment (name)': 'TypeOfEstablishment', 'Gender (name)': 'Gender',
        'ReligiousCharacter (name)': 'ReligiousCharacter', 'AdmissionsPolicy (name)': 'AdmissionsPolicy',
        'SchoolCapacity': 'SchoolCapacity',         'TrustSchoolFlag (name)': 'TrustSchoolFlag',
        'ParliamentaryConstituency (name)': 'ParliamentaryConstituency', 'UrbanRural (name)': 'UrbanRural'}

cols = []
for c in comp.keys():
    cols.append(c)

for c in expl.keys():
    cols.append(c)

# load ~50k rows covering all school types.
df = pd.read_csv('data/extract/edubasealldata20250310.csv', usecols=cols, encoding='latin')
# Latin?! Don't ask. It works.

# rename all columns (makes following code cleaner)
df.rename(columns=comp, inplace=True)
df.rename(columns=expl, inplace=True)

# Keep only open schools.
df = df.loc[(df.EstablishmentStatus == 'Open')]
df = df.drop(columns=['EstablishmentStatus'])
# Remove missing %FSM
df = df.dropna(subset=['PercentageFSM'])
# 48 primary/secondary schools found with zero FSM which seems issue with DfE data.
df = df.loc[(df.PercentageFSM != 0)]
# df = df.loc[(df.LA == 'Reading')]  # For testing

# Create separate dataframes for primaries and secondaries using .copy()
sec = df.loc[(df.PhaseOfEducation == 'Secondary')].copy()
sec = sec.drop(columns=['PhaseOfEducation'])
# sec = sec.loc[(sec.LA == 'Kent')]  # For testing
pri = df.loc[(df.PhaseOfEducation == 'Primary')].copy()
pri = pri.drop(columns=['PhaseOfEducation'])
# "pri" contains the explanatory variables which aren't needed. Not essential but drop those columns.
pri = pri.drop(columns=expl.values())

# Set the number of primary schools to check here.
x = 12
pcols = []
for k in range(0, x):
    for c in pri.columns:
        pcols.append('P' + str(k) + '_' + c)
    pcols.append('P' + str(k) + '_dist')
    pcols.append('P' + str(k) + '_weight')


def nearest_peas(e, n):
    """
    :param e: Eastings of Secondary school
    :param n: Northings of Secondary school
    :return: A series with the x nearest primary schools' attributes and their distances.
    nearest peas is a vegetarian pun.
    """
    pri['dist'] = pri.apply(lambda roww: ((e - roww.Easting) ** 2 + (n - roww.Northing) ** 2) ** 0.5, axis=1)
    # create copy of just the x nearest primaries
    tdf = pri.sort_values('dist').head(x).copy()
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


# testSer = nearest_peas(471232, 176358)

for i, row in sec.iterrows():
    # print(i)
    sec.loc[i, pcols] = nearest_peas(row.Easting, row.Northing).values
    if i % 100 == 0:
        print(i, 'secondary schools processed')


# 'sec' is now a very wide dataframe with x sets of results for the nearest primaries.

def local_fsm(r):
    """
    :param r: The current row from the sec(ondary) dataframe as Series.
    :return: Scalar value representing the 'local' %FSM based on the nearest x primary schools.
    This function add up the product of fields P<k>_PercentageFSM × P<k>_weight
    """
    fsmsum = 0
    for kk in range(0, x):
        fsmsum += r['P' + str(kk) + '_PercentageFSM'] * r['P' + str(kk) + '_weight']
    return fsmsum


sec['localFSM'] = sec.apply(lambda srow: local_fsm(srow), axis=1)

# write results.

sec.to_csv('data/nearest_primary-v3.csv', index=False)

# quickly determine distribution of weights (albeit to std-out!)
for k in range(0, x):
    c = 'P' + str(k) + '_weight'
    print(sec[c].sum())



# pri.to_csv('data/nearest_primary-check-v2.csv')
