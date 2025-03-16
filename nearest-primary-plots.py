"""
This code creates the plots used in an article describing a method of measuring secondary schools relative to the
local community they reside in (based on the size proximity of those primary schools.)

The article is here:
https://trak.org.uk/whatshallicallthis?

The data was derived using another script "nearest-primary-v3.py". This compares 3,096 English secondary schools
against 16,060 primary schools (2025 data) to find the nearest dozen (but configurable) schools and calculate a
weighted proportion of children in receipt of Free School Meals (FSM) using this formula:
https://arachnoid.com/latex/?equ=%5Cdisplaystyle%20%5Csum%5En_%7B1%7D%20%5Cleft%5B%0A%5Cfrac%7B%5Cfrac%7Bc_n%7D%7Bd%5E2_n%7D%5Ctimes%20FSM_n%7D%0A%7B%5Csum%5En_%7B1%7D%5Cfrac%7Bc_n%7D%7Bd%5E2_n%7D%7D%20%5Cright%5D


"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# load 'nearest primaries' data.
sec = pd.read_csv('data/nearest_primary-v3.csv')

# Reduce ReligiousCharacter field values to either Faith=yes|no.
"""
# This method using a dictionary didn't work! 
dikt = {'Does not apply': 'No', 'None': 'No', np.nan: 'No', 'Roman Catholic': 'Yes', 'Church of England': 'Yes',
        'Catholic': 'Yes', 'Jewish': 'Yes', 'Roman CatholicChurch of England': 'Yes', 'Christian': 'Yes',
        'Church of EnglandRoman Catholic': 'Yes', 'Muslim': 'Yes', 'Church of EnglandChristian': 'Yes',
        'Hindu': 'Yes', 'Sikh': 'Yes', 'Greek Orthodox': 'Yes', 'AnglicanChurch of England': 'Yes'}
sec['ReligiousCharacter'] = sec['ReligiousCharacter'].replace(dikt, regex=True)
"""

# Rename the column first (less typing!)
sec = sec.rename(columns={'ReligiousCharacter': 'FaithSchool'})
sec['FaithSchool'] = sec.FaithSchool.fillna('No')
sec['FaithSchool'] = sec['FaithSchool'].replace(r'Does not apply|None', 'No', regex=True)
sec['FaithSchool'] = sec['FaithSchool'].replace(r'Church.*|.*Catholic.*', 'Yes', regex=True)
sec['FaithSchool'] = sec['FaithSchool'].replace(r'.*Greek.*|.*Anglican.*', 'Yes', regex=True)
sec['FaithSchool'] = sec['FaithSchool'].replace(r'Jewish|Christian|Muslim|Hindu|Sikh', 'Yes', regex=True)
# The above four lines could be replaced with a single one but that would be even less readable!

# next, fix AdmissionsPolicy
sec['AdmissionsPolicy'] = sec.AdmissionsPolicy.fillna('Non-selective')
sec['AdmissionsPolicy'] = sec['AdmissionsPolicy'].replace(r'Not applicable', 'Non-selective', regex=True)

# examine how the weights are distributed.
# First create an array with the sum of all (3k+) schools' nearest, second nearest ... etc weights.
x = 12

dist = []
for k in range(0, x):
    c = 'P' + str(k) + '_weight'
    dist.append(sec[c].sum())

# put that into a dataframe and normalise so the values add to 1
df = pd.DataFrame(dist)
df.columns = ['gross']
s = df.gross.sum()
df['norm'] = df['gross'] / s

# Create x-labels
for k in range(0, x):
    df.loc[k, 'nearest'] = str(k + 1)

# Plot the distribution of weights aspect ratio 2:1.
fig1, ax1 = plt.subplots(figsize=(12, 6))
sns.barplot(df, x='nearest', y='norm')
ax1.set_xlabel('nth nearest primary school')
ax1.set_ylabel('proportion of weight (Σ=1)')
fig1.subplots_adjust(left=0.05, bottom=0.08, right=0.98, top=0.98, wspace=0.2, hspace=0.2)
fig1.savefig('data/fig1-nearest-primary.png', format='png', dpi=300)

# Plot 'PercentageFSM' ~ 'localFSM' aspect ratio 1:1. This needs to be a filtered subset, but we can look at
# highlighting other factors. Start with a single local authority (fewer schools).
fig2, ax2 = plt.subplots(figsize=(9, 9))
# Filter only Kent schools. eg use data: sec.loc[(sec.LA == 'Kent')]
sns.scatterplot(sec.loc[(sec.LA == 'Kent')], x='localFSM', y='PercentageFSM',
                style='FaithSchool', hue='AdmissionsPolicy')
ax2.set_xlabel("%FSM in 'heart of community'")
ax2.set_ylabel('%FSM in specific secondary school')
# set axes limits.
plt.xlim(0, 65)
plt.ylim(0, 65)

# add y=x line
plt.plot([0, 65], [0, 65], color='black', linestyle=':')

fig2.suptitle('Kent secondary schools %FSM\ncompared to local community', fontsize=16, fontweight='bold', color='black')
fig2.savefig('data/fig2-nearest-primary.png', format='png', dpi=300)
# Figure 2 superceded by the following plotly plot
# For a more informative graph, use plotly to create DHTML graphs (mouse hover over text)
import plotly.express as px
import plotly.graph_objects as go

# Make a copy of Kent only
kent = sec.loc[(sec.LA == 'Kent')].copy()
# dataframe has 111 columns! Can simplify by concatenating the data for each primary like this:
# Primary 1: Priory Fields School, 354 pupils, FSM=65.3% FSM, d=0.965km, weight=6.2%
# This is a LOT of work and probably end up looking naff. Can always come back to this idea.

# minor defect in data creation code. Primary can be given as exact same location as secondary which gives division
# by zero. Work around for now for two schools in Kent by taking the primary's %FSM.
kent.loc[kent['localFSM'].isnull(), 'localFSM'] = kent['P0_PercentageFSM']

drop = ['URN', 'LA', 'SchoolCapacity', 'NumberOfPupils', 'TrustSchoolFlag',
        'ParliamentaryConstituency', 'UrbanRural', 'Easting', 'Northing']

sufxs = ['URN', 'EstablishmentName', 'NumberOfPupils', 'PercentageFSM', 'Easting', 'Northing', 'dist', 'weight']

for k in range(0, x):
    for suf in sufxs:
        drop.append('P' + str(k) + '_' + suf)

kent = kent.drop(columns=drop)
# Tidy up columns as these appear in mouse hover
kent.columns = ['Name', 'Type', 'Gender', 'FaithSchool', 'AdmissionsPolicy', 'School_FSM', 'Local_FSM']

# Create a category column which is FaithSchool × AdmissionsPolicy
kent['Category'] = kent.FaithSchool + kent.AdmissionsPolicy
dikt = {'NoNon-selective': 'Non-selective Secular', 'NoSelective': 'Selective Secular',
        'YesNon-selective': 'Non-selective Religious', 'YesSelective': 'Selective Religious'}

kent['Category'] = kent['Category'].replace(dikt, regex=True)

# add gap column
kent['%Gap'] = abs(kent.School_FSM - kent.Local_FSM)
# Tend end up with values like 42.000000000000000001 or 41.9999999999999 so ...
kent = kent.round(2)
kent = kent.sort_values(by=['Category'])  # should make the legend also sorted.

# title = "Kent secondary schools' disadvantage gap sizes"
# subtitle = "Circle sizes are proportional to the gap"
fig = px.scatter(kent, x='Local_FSM', y='School_FSM', color='Category',
                 hover_data=['Name', 'Type', 'School_FSM', 'Local_FSM'],
                 size='%Gap',
                 size_max=35,
                 title="Kent secondary schools' gap sizes<br>"
                       "<sup>Circle sizes are proportional to the disadvantage gap</sup>",
                 )

fig.add_trace(
    go.Scatter(x=[0, 65],
               y=[0, 65],
               mode='lines', line=go.scatter.Line(color='black', dash='longdash'),
               showlegend=False)
)

# set the axes limits
fig.update_layout(xaxis=dict(range=(0, 65), constrain='domain'),
                  yaxis=dict(range=(0, 65), constrain='domain')
                  )


fig.update_layout(yaxis=dict(scaleanchor='x', scaleratio=1))

# put the legend inside top left
fig.update_layout(legend=dict(
    yanchor='top', y=0.99,
    xanchor='left', x=1
))

title = "Kent secondary schools' disadvantage gap sizes"
fig.update_layout(title_text=title,
                  title_font_size=30)

fig.update_layout(title_text="Kent secondary schools' gap sizes<br>"
                             "<sup>Circle sizes proportional to the disadvantage gap</sup>",
                  title_font_size=30)

# Write a "full screen" version and load into browser.
fig.write_html('data/kent.html', auto_open=True)

# move the legend inside
fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
# remove axes labels ... also removes ticklables!
# fig.update_xaxes(visible=True, showticklabels=True)
# fig.update_yaxes(visible=True, showticklabels=True)

# Remove title and make minimal margins
fig.update_layout(title_text='')
fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
fig.write_html('data/kent-iframe.html', auto_open=True)

# Office for National statistics, National Travel Survey, NTS0614: Trips to and from school by age, trip length
# and main mode, aged 5 to 16: England, 2002 onwards.
# Accessed via https://www.gov.uk/government/statistical-data-sets/nts06-age-gender-and-modal-breakdown#school-travel
xls = pd.ExcelFile('data/nts0614.ods', engine='odf')
# Skip top four rows which contain explanatory comments.
nts = pd.read_excel(xls, 'NTS0614b_mode_by_length', skiprows=4)
# Bit of a faff to get the reassign the first row as index. May have been poss with the read_excel() but this works:
headers = nts.iloc[0].values
nts.columns = headers
nts.drop(index=0, axis=0, inplace=True)

# Delete all but 'all modes' rows.
nts = nts.loc[(nts['Main mode'] == 'All modes')]

# drop unwanted columns
nts = nts.drop(columns=['Main mode', 'All lengths (%)', 'Unweighted sample size: trips (thousands) (number)'])

# simplify rather verbose column headings!
cols = ['Year', 'Age', '< 1 mile', '1 - 2 miles', '2 - 5 miles', '> 5 miles']
nts.columns = cols
# Lose year/Age from cols array
cols = cols[2:]

for c in cols:
    nts[c] = nts[c].fillna(0.0).astype(float)
    # ... although pivot_table() seems to work perfectly well when dtype=object !

nts = nts.sort_values(by=['Age'], ascending=False)  # so it looks nice before being dispensed with ...
# ... create pivot with mean values then melt from wide to long.
piv = pd.pivot_table(nts, values=cols, index='Age', aggfunc=np.mean)
# Pandas is determined my data should be the opposite way around to what I want!
piv = piv.sort_index(ascending=False)
piv = piv.reset_index()
piv = pd.melt(piv, id_vars='Age', value_vars=cols)

fig3, ax3 = plt.subplots(figsize=(12, 6))
sns.barplot(piv, x='variable', y='value', hue='Age')
ax3.set_xlabel('Source: Office for National Statistics, National Travel Survey, NTS0614')
ax3.set_ylabel('%children travelling this distance')
fig3.subplots_adjust(left=0.05, bottom=0.08, right=0.98, top=0.98, wspace=0.2, hspace=0.2)
fig3.savefig('data/fig3-nearest-primary.png', format='png', dpi=300)

