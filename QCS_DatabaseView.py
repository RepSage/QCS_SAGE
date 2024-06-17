import os
import re
import pandas as pd
import QCS_DataHandler as data
import QCS_DataView as view

opt = input('\nDo you want to join files to database (y/n):')

if re.search('y', opt, re.IGNORECASE):
    path = input('\nPath to files:')
    database_name = input('\nOutput database file name:')
    database = data.join_files_to_database(path, database_name)
else:
    path = input('\nPath to database file:')
    database_name = input('\nDatabase file name:')
    os.chdir(path)
    if re.search('.xlsx', database_name, re.IGNORECASE):
        database = pd.read_excel(database_name)
    if re.search('.xlsx', database_name, re.IGNORECASE):
        database = pd.read_csv(database_name)

database['Datetime'] = pd.to_datetime(database['Datetime'])
q1 = input('\nDo you want to sort data by datetime (y/n):')

if re.search('y', q1, re.IGNORECASE):
    database.index = database['Datetime']
    database = database.rename_axis('dt_index')
    database = database.sort_values(by='dt_index')
    database.index = range(len(database))

#database['Datetime'] = pd.to_datetime(database['Datetime'])
database_view_path = path + '/' + 'DatabaseView'
os.makedirs(database_view_path, exist_ok=True)
os.chdir(database_view_path)
#save file
if re.search('.xlsx', database_name, re.IGNORECASE):
    database.to_excel(database_name)
    if re.search('.csv', database_name, re.IGNORECASE):
        database.to_csv(database_name)

print('\nif you want to check avaible names type help')
site_names = input('\nPass the site names you want to view (case sensitive):')
if re.search('help', site_names, re.IGNORECASE):
    print('\nAvailable site names:\n' )
    for name in set(database['Site']):
        print(name)
    site_names = input('\nPass the site names you want to view (case sensitive):')
    #print(*set(database['Site']), sep=", ")
else:
    pass

parameter_names = input('\nPass the parameter names you want to view (case sensitive):')
if re.search('help', parameter_names, re.IGNORECASE):
    print('\nAvailable parameter names:\n' )
    for name in database.columns:
        if re.search('unnamed|datetime|depth|pressure|soundspeed|expedition|site|longitude|latitude|battery|flag|sample|version', name, re.IGNORECASE):
            pass
        else:
            print(name)
    parameter_names = input('\nPass the parameter names you want to view (case sensitive):')
else:
    pass


site_names = site_names.split(',')
parameter_names = parameter_names.split(',')

q2 = input('\nPlot type 1 panel (y/n):')
q3 = input('\nPlot type 2 panel (y/n):')

year = int(input('\nYear you want to view:'))
q4 = input('\nFit tendency lines (y/n):')
if re.search('y', q4, re.IGNORECASE):
    fit_lin_regression = True
else:
    fit_lin_regression = False
deg = int(input('\nTendency lines degree:'))
q5 = input('\nPlot using only points (y/n):')
if re.search('y', q5, re.IGNORECASE):
    points = True
else:
    points = False
q6 = input('\nView time as elapsed time (y/n):')
if re.search('y', q6, re.IGNORECASE):
    elapsed_time = True
else:
    elapsed_time = False
q7 = input('\nDo you want to change the dates to stack sites data at the same initial time (y/n):')
if re.search('y', q7, re.IGNORECASE):
    change_date = True
else:
    change_date = False

if re.search('y', q2, re.IGNORECASE):
    view.plot_database_panel1 (database, site_names, parameter_names, year, fit_lin_regression, deg, points)
if re.search('y', q3, re.IGNORECASE):
    view.plot_database_panel2 (database, site_names, parameter_names, year, fit_lin_regression, deg, points, elapsed_time, change_date)

plt.show()
