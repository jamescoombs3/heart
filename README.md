# heart
"A data driven method to define the heart of a school's community."

In England, deregulated 'Academy' schools are state funded on the strict basis that they are "at the heart of the community" ... but this isn't defined. 

# Code
There are two scripts which measure inclusivity against the "local community". There is a longer description of the reasoning behind the mathematical models they use here https://trak.org.uk/mind-the-gap
1) nearest-primary-v6.py
Evaluates secondary schools' inclusivity by comparing their %FSM against nearby primaries' %FSM weighted by size and inverse square of distance.

2) school2IDACI.py
Evaluates secondary schools' inclusivity by comparing their %FSM against Income Deprivation Affecting Children Index (IDACI) by Lower Super Output Areas (LSOAs) weighted by size and inverse square of distance.

The input data is all published by gov.uk. Details of where the latest data can be found can be found in the comments in the scripts. 

# Output data
gap_data-v6-calib.csv   contains the output from the 'nearest primary' script. 
school-to-idaci.csv     contains the output from the IDACI script.  
