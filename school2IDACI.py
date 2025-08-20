"""
Version 1
This script evaluates secondary schools' inclusivity by comparing their %FSM against Income Deprivation Affecting
Children Index (IDACI) by Lower Super Output Areas (LSOAs) weighted by size and inverse square of distance.
Fuller explanation here: https://trak.org.uk/mind-the-gap/

Takes a few hours to run on a cheap Dell desktop and doesn't report progress.

DATA
Lower layer Super Output Areas (December 2011) EW Population Weighted Centroids | Open Geography Portal
https://geoportal.statistics.gov.uk/datasets/ons::lower-layer-super-output-areas-december-2011-ew-population-weighted-centroids-1/explore?showTable=true

All the latest indexes of deprivation are here:
https://www.gov.uk/government/statistics/english-indices-of-deprivation-2019
Specifically:
File 5: scores for the indices of deprivation (MS Excel Spreadsheet, 5.14 MB)
https://assets.publishing.service.gov.uk/media/5d8b3b51ed915d036a455aa6/File_5_-_IoD2019_Scores.xlsx

https://get-information-schools.service.gov.uk/Downloads
Select "all data"
Download the zip file and extract all the files.
The required one is called (depending on the date) something like this:
edubasealldata20250310.csv


"""

import pandas as pd
import timeit

cols = {'URN': 'URN', 'EstablishmentName': 'EstablishmentName', 'EstablishmentStatus (name)': 'EstablishmentStatus',
        'PhaseOfEducation (name)': 'PhaseOfEducation', 'PercentageFSM': 'PercentageFSM', 'Easting': 'Easting',
        'NumberOfPupils': 'NumberOfPupils', 'Northing': 'Northing', 'LA (name)': 'LA',
        'TypeOfEstablishment (name)': 'TypeOfEstablishment', 'Gender (name)': 'Gender',
        'ReligiousCharacter (name)': 'ReligiousCharacter', 'AdmissionsPolicy (name)': 'AdmissionsPolicy',
        'SchoolCapacity': 'SchoolCapacity',         'TrustSchoolFlag (name)': 'TrustSchoolFlag',
        'ParliamentaryConstituency (name)': 'ParliamentaryConstituency', 'UrbanRural (name)': 'UrbanRural'}

# load ~50k rows covering all school types.
schools = pd.read_csv('data/extract/edubasealldata20250429.csv', usecols=cols.keys(), encoding='latin')
# Latin?! Don't ask. It works.

# rename all columns (makes the following code cleaner)
schools.rename(columns=cols, inplace=True)

# Keep only open schools.
schools = schools.loc[(schools.EstablishmentStatus == 'Open')]
schools = schools.drop(columns=['EstablishmentStatus'])
# Remove missing %FSM ****************************** MAYBE REVIEW THIS AS COMPARISON IS NOW AGAINST IDACI
# schools = schools.dropna(subset=['PercentageFSM'])
# 48 primary/secondary schools found with zero FSM which seems issue with DfE data.
# schools = schools.loc[(schools.PercentageFSM != 0)]
# schools = schools.loc[(schools.LA == 'Reading')]  # For testing

# Open DfE IDACI and ONS LSOA file to create a single dataframe with three fields, IDACI score, Eastings/Northings
xls = pd.ExcelFile('data/File_5_-_IoD2019_Scores.xlsx')
# load the
idaci = pd.read_excel(xls, 'IoD2019 Scores',
                      usecols=['LSOA code (2011)', 'Income Deprivation Affecting Children Index (IDACI) Score (rate)'])

# give columns some nicer names
idaci.columns = ['lsoa', 'idaci']

lsoas = pd.read_csv('data/LSOA_Dec_2011_PWC_in_England_and_Wales_2022_1923591000694358693.csv')
lsoas = lsoas.drop(columns=['OBJECTID', 'LSOA11NM', 'GlobalID'])
# set lsoa column name to match the idaci dataframe
lsoas.columns = ['lsoa', 'x', 'y']

lsoas = pd.merge(idaci, lsoas, on='lsoa', how='outer')
# lsoas.to_csv('data/lsoas.csv')  # to check
# 1,909 missing scores out of 34,753 - about half a percent ... and they're all Welsh!
# Select just English LSOAs.
lsoas = lsoas.loc[lsoas.lsoa.str.startswith('E')]
# could now drop the lsoa column but doesn't save much memory.

# create a dist[ance] column in lsoas. Initially zero.
lsoas['dist'] = 0


def local_idaci(e, n, i):
    """
    :param e: Eastings
    :param n: Northings
    :param i: Number of LSOAs to check
    :return:  Distance weighted IDACI score (should always be between 0 and 1)
    """
    lsoas['dist'] = lsoas.apply(lambda row: ((e - row.x) ** 2 + (n - row.y) ** 2) ** 0.5, axis=1)
    tdf = lsoas.sort_values('dist').head(i).copy()
    # modify 'dist' column so it contains the inverse square of distance in km.
    tdf['dist'] = 1 / (tdf['dist'] / 1000) ** 2
    # normalise dist so the column adds to 1
    dsum = tdf.dist.sum()
    tdf['dist'] = tdf['dist'] / dsum
    tdf['widaci'] = tdf.dist * tdf.idaci
    return tdf.widaci.sum()


"""
Testing the function with different iterations to get an idea where it settles.  

# Highdown School
for k in range(0, 20):
    print(k, 'nearest LSOAs', local_idaci(471232, 176358, k))

# Reading Girls
for k in range(0, 20):
    print(k, 'nearest LSOAs', local_idaci(472269, 171296, k))
    
# Q3 Academy Tipton 
for k in range(1, 21):
    print(k, 'nearest LSOAs', local_idaci(396634, 292677, k))

"""

# Create data for plotting and example of how the weighting works using Q3 academy in Tipton.
tipE, tipN = (396634, 292677)  # Coordinates of Tipton Q3
# same lambda apply as per the function but based on (tipE, tipN)
lsoas['dist'] = lsoas.apply(lambda row: ((tipE - row.x) ** 2 + (tipN - row.y) ** 2) ** 0.5, axis=1)
tipton = lsoas.sort_values('dist').head(30).copy()
tipton = tipton.reset_index(drop=True)
# remove lsoas original index
# tipton = tipton.drop(columns=['Unnamed: 0'], axis=1)
# add a column for the weighting based on k-nearest.
tipton['weighted'] = 0

for k in range(0, 30):
    # print(k, 'nearest LSOAs', local_idaci(396634, 292677, k))
    w = local_idaci(tipE, tipN, k + 1)
    tipton.loc[k, 'weighted'] = w
    print(k, 'nearest LSOAs', w, 'weighted IDACI')

tipton.to_csv('data/tipton.csv')


# apply the weighting to school table checking the 20 nearest LSOAs.
start_time = timeit.default_timer()
schools['localIDACI'] = schools.apply(lambda row: local_idaci(row.Easting, row.Northing, 20), axis=1)
elapsed = timeit.default_timer() - start_time
print('Execution time:', elapsed)

# write results.
schools.to_csv('data/school-to-idaci.csv', index=False)

