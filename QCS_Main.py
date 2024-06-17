
#modulos do sistema
import os
import re
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO
from string import Template
from datetime import datetime as dt
from datetime import timedelta
#modulos do programa
import QCS_DataHandler as data
import QCS_DataView as view
import QCS_Tests as QC
import warnings

# ignore RuntimeWarning
warnings.filterwarnings("ignore", category=RuntimeWarning)
################################# Description ##################################
# Workflow for processing data which puts together the other scripts.
################################################################################

# input folder path
input_folder_path = input('\nInput folder path:')
print('\n')

#select type of data
opt = {
       1:'Seaguard data',
       2:'Unified hobo'
       }

for i in range(1, len(opt)+1):
    print('%d: %s' %(i, opt[i]))

e = int(input('\nSelect type of data:'))
################################################################################

os.chdir(input_folder_path)
#loading input
from input_file import INPUT, OUTPUT
from config_file import tsQualityTests, tsSettings, auxTests

################ QUALITY CONTROL FOR CTD AND AUXILIAR SENSORS ##################


# change to folder containing raw data
os.chdir(INPUT['raw_data_path'])

# opening raw files according to selected data type
if e == 1:
    if INPUT['profile'] == True:
        raw_data = data.read_ctd_profile_csv(INPUT['file_name'])
    else:
        raw_data = data.read_ctd_csv(INPUT['file_name'])
    for name in raw_data.columns:
        if re.search('time', name, re.IGNORECASE):
            if re.search('timer', name, re.IGNORECASE):
                pass
            else:
                raw_data = raw_data.rename(columns={name:'Datetime'})
        if re.search('prof', name, re.IGNORECASE):
                raw_data = raw_data.rename(columns={name:'Depth(m)'})
elif e == 3:
    fullFrame, tempFrame, lumiFrame = data.read_unified_hobo(INPUT['file_name'])
    raw_data = tempFrame
    for test in tsQualityTests:
        if re.search('spikes', test, re.IGNORECASE):
            tsQualityTests[test] = 'OFF'
        if re.search('rate of change', test, re.IGNORECASE):
            tsQualityTests[test] = 'OFF'
        if re.search('vertical gradient', test, re.IGNORECASE):
            tsQualityTests[test] = 'OFF'
# getting start and end time and measurement interval
start_time = raw_data['Datetime'].iloc[0]
end_time = raw_data['Datetime'].iloc[-1]
ms_interval = np.timedelta64(raw_data['Datetime'].iloc[1] - raw_data['Datetime'].iloc[0], 's')
INPUT['start_time'] = start_time
INPUT['end_time'] = end_time

# adjusting for GMT-3 hours
if e == 2:
    raw_data['Datetime'] = raw_data['Datetime'] - timedelta(hours=3)
    start_time = start_time - timedelta(hours=3)
    end_time = end_time - timedelta(hours=3)

# excluding other than main temperature sensors
t = 0
for name in raw_data.keys():
    if re.search('internal temperature', name, re.IGNORECASE):
        raw_data = raw_data.drop(columns={name})
    elif re.search('temperature', name, re.IGNORECASE):
        t += 1
        if t > 1:
            raw_data = raw_data.drop(columns={name})
# converting units to software standards and calculating depth from pressure
check = list()
for var in raw_data.columns:
    if re.search('conductivity|pressure', var, re.IGNORECASE):
        check.append(var)
if len(check) >= 1:
    raw_data = data.convert_tscp_units (raw_data, pressure_unit=INPUT['pressure_unit'], conductivity_unit=INPUT['conductivity_unit'])
    for name in raw_data.columns:
        if re.search('pressure', name, re.IGNORECASE):
            raw_data = raw_data.rename(columns={name:'Pressure(dbar)'})

dep, press = (0,0)
for name in raw_data.columns:
    if re.search('depth', name, re.IGNORECASE) and not re.search('pressure', name, re.IGNORECASE):
        dep += 1
    elif re.search('pressure', name, re.IGNORECASE):
        press += 1
if dep == 0 and press == 1:
    raw_data = data.pressure_to_depth(raw_data, latitude=17.5, adjust_for_atm=True)

# number of lines and cells
n_cel = 1
n_samples = len(raw_data)

#trimming first and last 3 samples if number of samples is greater than 50

#drop = list(range(n_samples)[:3])
#drop += list(range(n_samples)[-3:])
#if n_samples >= 50:
#    raw_data = raw_data.drop(drop, axis=0)
#    n_samples = len(raw_data)
#    raw_data.index = np.arange(n_samples)

# add sample number column
raw_data['Sample Number'] = raw_data.index + 1

#removing data equal (except for PAR) and under 0
exceptions = ['Datetime', 'Sample Number', 'Pitch[Deg]', 'Roll[Deg]', 'Timer[s]', 'Site']
for name in raw_data.columns:
    if re.search('par', name, re.IGNORECASE):
        raw_data.loc[raw_data[name]<0, name] = np.nan
    else:
        if name not in exceptions:
            raw_data.loc[raw_data[name]<=0, name] = np.nan

#removing data where depth is under 0.5 for profile data
if INPUT['profile'] == True:
    for name in raw_data.columns:
        if name not in exceptions:
            raw_data.loc[raw_data['Depth(m)'] < 0.5, name] = np.nan

#removing data reproved in depth range test
if auxTests['depth range test'] == 'ON':
    for name in raw_data.columns:
        if re.search('depth', name, re.IGNORECASE):
            #first round
            raw_data = QC.depth_range_test (raw_data, tsSettings['depth_range'])
            #second round
            raw_data = QC.depth_range_test (raw_data, tsSettings['depth_range'])

#selecting samples based on descending or ascendig equipment
from scipy import signal
if INPUT['select_profile_data'] == True:
    for name in raw_data.columns:
        if re.search('pressure', name, re.IGNORECASE):
            peak = int(signal.find_peaks(raw_data[name], width=20)[0])
            fig1 = plt.figure()
            ax1 = fig1.gca()
            ax1.plot(raw_data[name], label='Pressure (dbar)')
            ax1.plot(peak, raw_data[name].loc[peak], '.', c='red', linestyle='none')
            ax1.set_ylabel('Pressure (dbar)')
            plt.show(block=True)
            for subname in raw_data.columns:
                if re.search('temperature', subname, re.IGNORECASE):
                    temp = subname
                if re.search('depth', subname, re.IGNORECASE):
                    dep = subname
            desc = raw_data.loc[:peak]
            asc = raw_data.loc[peak:]


            fig2 = plt.figure()
            ax2 = fig2.gca()
            line1, = ax2.plot(raw_data.loc[desc.index, temp], raw_data.loc[desc.index, dep], label='descending data')
            line2, = ax2.plot(raw_data.loc[asc.index, temp], raw_data.loc[asc.index, dep], c='red', label='ascending data')
            ax2.set_title('click on the line to select it:')
            ax2.set_ylabel('Temperature(degC)')
            ax2.legend()
            ax2.invert_yaxis()
            ax2.grid()
            fig2.show()

            selected = None
            buffer = 0.1
            def on_pick(event):
                # get selected label
                global selected
                selected = event.artist.get_label()
                plt.close()
                #fig.canvas.mpl_disconnect(cid)

            line1.set_picker(True)
            line2.set_picker(True)
            fig2.canvas.mpl_connect('pick_event', on_pick)
            fig2.canvas.mpl_connect('motion_notify_event', data.on_motion)

            ans = input('\ndo you accept the data peak?(y/n)\n\n select:')

            if ans == 'y':
                if selected == 'descending data':
                    raw_data.loc[peak:] = np.nan
                elif selected == 'ascending data':
                    raw_data.loc[:peak] = np.nan
            plt.close(fig1)
            plt.close(fig2)

#if INPUT['check_pressure'] == True:
#    raw_data = trim_selected_data(raw_data, name)
if INPUT['check_variables'] == True:
    check_variables = ['O2 Level(uM)', 'Temperature(degC)','Conductivity(mS/cm)', 'Salinity(PSU)', 'Density(kg/m3)',
                       'PAR(umol/m2/s)', 'Turbidity(FTU)', 'Chlorophyll(ug/L)', 'Hydrogen Potential(pH)', 'Dissolved Organic Matter(ppb)']
    for name in check_variables:
        if name in raw_data.columns:
            raw_data = data.trim_selected_variable(raw_data, name)
#create list for flag codes
flags = ['' for n in range(len(raw_data))]

start = time.time()
# Range tests
ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('temperature', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['sensor_min_temp'], range_max=tsSettings['sensor_max_temp']) if tsQualityTests['temperature sensor range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Temperature sensor range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('salinity', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['sensor_min_sal'], range_max=tsSettings['sensor_max_sal']) if tsQualityTests['salinity sensor range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Salinity sensor range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('conductivity', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['sensor_min_cond'], range_max=tsSettings['sensor_max_cond']) if tsQualityTests['conductivity sensor range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Conductivity sensor range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('pressure', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['sensor_min_pres'], range_max=tsSettings['sensor_max_pres']) if tsQualityTests['pressure sensor range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Pressure sensor range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

##Environmental range tests
ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('temperature', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_temp'], range_max=tsSettings['env_max_temp']) if tsQualityTests['temperature environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Temperature environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('salinity', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_sal'], range_max=tsSettings['env_max_sal']) if tsQualityTests['salinity environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Salinity environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('conductivity', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_cond'], range_max=tsSettings['env_max_cond']) if tsQualityTests['conductivity environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Conductivity environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('pressure', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_pres'], range_max=tsSettings['env_max_pres']) if tsQualityTests['pressure environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Pressure environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('hydrogen potential\(pH\)', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_pH'], range_max=tsSettings['env_max_pH']) if tsQualityTests['pH environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('pH environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('chlorophyll\(ug/L\)', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_chl'], range_max=tsSettings['env_max_chl']) if tsQualityTests['chlorophyll environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Chlorophyll environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('o2', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_O2'], range_max=tsSettings['env_max_O2']) if tsQualityTests['dissolved oxygen environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Dissolved oxygen (O2) environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('organic matter', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_org'], range_max=tsSettings['env_max_org']) if tsQualityTests['dissolved organic matter environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Dissolved organic matter environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('turbidity\(ftu\)', name, re.IGNORECASE):
        a = 1
        flags = QC.range_test (raw_data[name], flags, range_min=tsSettings['env_min_tur'], range_max=tsSettings['env_max_tur']) if tsQualityTests['turbidity environmental range'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Turbidity environmental range test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

##testes de spikes (valores espurios)
ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('temperature', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['temperature spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Temperature spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('salinity', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['salinity spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Salinity spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('conductivity', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['conductivity spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Conductivity spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('pressure', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['pressure spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Pressure spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('hydrogen potential\(pH\)', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['pH spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('pH spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('chlorophyll\(ug/L\)', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['chlorophyll spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Chlorophyll spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('O2', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['dissolved oxygen spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Dissolved oxygen spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('organic matter', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['dissolved organic matter spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Dissolved organic matter spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('turbidity\(ftu\)', name, re.IGNORECASE):
        a = 1
        flags = QC.z_score_spike_test(raw_data, name, n_cel, flags, tsSettings['time_window'], ms_interval, tsSettings['fail_factor'], tsSettings['susp_factor']) if tsQualityTests['turbidity spikes'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Turbidity spikes test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

##teste de taxa de variacao
ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('temperature', name, re.IGNORECASE):
        a = 1
        flags = QC.sigma_rate_of_change_test (n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['temperature rate of change'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Temperature rate of change test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('salinity', name, re.IGNORECASE):
        a = 1
        flags = QC.sigma_rate_of_change_test (n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['salinity rate of change'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Salinity rate of change test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('conductivity', name, re.IGNORECASE):
        a = 1
        flags = QC.sigma_rate_of_change_test (n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['conductivity rate of change'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Conductivity rate of change test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('pressure', name, re.IGNORECASE):
        a = 1
        flags = QC.sigma_rate_of_change_test (n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['pressure rate of change'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Pressure rate of change test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

##testes de travemento do sensor/ sucessivos iguais
ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('temperature', name, re.IGNORECASE):
        a = 1
        flags = QC.single_flat_line_test (n_samples, n_cel, raw_data[name], flags, rep_cnt_fail=tsSettings['rep_cnt_fail'], rep_cnt_suspect=tsSettings['rep_cnt_susp'], eps=tsSettings['eps']) if tsQualityTests['temperature flat line'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Temperature flat line test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('salinity', name, re.IGNORECASE):
        a = 1
        flags = QC.single_flat_line_test (n_samples, n_cel, raw_data[name], flags, rep_cnt_fail=tsSettings['rep_cnt_fail'], rep_cnt_suspect=tsSettings['rep_cnt_susp'], eps=tsSettings['eps']) if tsQualityTests['salinity flat line'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Salinity flat line test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('conductivity', name, re.IGNORECASE):
        a = 1
        flags = QC.single_flat_line_test (n_samples, n_cel, raw_data[name], flags, rep_cnt_fail=tsSettings['rep_cnt_fail'], rep_cnt_suspect=tsSettings['rep_cnt_susp'], eps=tsSettings['eps']) if tsQualityTests['conductivity flat line'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Conductivity flat line test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

ti = time.time()
a = 0
for name in raw_data.columns:
    if re.search('pressure', name, re.IGNORECASE):
        a = 1
        flags = QC.single_flat_line_test (n_samples, n_cel, raw_data[name], flags, rep_cnt_fail=tsSettings['rep_cnt_fail'], rep_cnt_suspect=tsSettings['rep_cnt_susp'], eps=tsSettings['eps']) if tsQualityTests['pressure flat line'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
if a == 0:
    flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
tf = time.time()
N = data.count_test_bdata(flags)
print('Pressure flat line test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

##Testes de gradiente vertical
if INPUT['profile'] == True:
    ti = time.time()
    a = 0
    for name in raw_data.columns:
        if re.search('temperature', name, re.IGNORECASE):
            a = 1
            flags = QC.vertical_gradient_test(n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['temperature vertical gradient'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
    if a == 0:
        flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
    tf = time.time()
    N = data.count_test_bdata(flags)
    print('Temperature vertical gradient test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

    ti = time.time()
    a = 0
    for name in raw_data.columns:
        if re.search('salinity', name, re.IGNORECASE):
            a = 1
            flags = QC.vertical_gradient_test(n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['salinity vertical gradient'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
    if a == 0:
        flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
    tf = time.time()
    N = data.count_test_bdata(flags)
    print('Salinity vertical gradient test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

    ti = time.time()
    a = 0
    for name in raw_data.columns:
        if re.search('conductivity', name, re.IGNORECASE):
            a = 1
            flags = QC.vertical_gradient_test(n_samples, raw_data[name], n_cel, flags, ms_interval=ms_interval, time_window=tsSettings['time_window'], rc_fail=tsSettings['fail_factor'], rc_susp=tsSettings['susp_factor'], DIR=False) if tsQualityTests['conductivity vertical gradient'] == 'ON' else [flags[n]+'%d'%QC.QC_flags.DISMISSED for n in range(n_samples)]
    if a == 0:
        flags = [flags[n]+'%d'%QC.QC_flags.UNKNOWN for n in range(n_samples)]
    tf = time.time()
    N = data.count_test_bdata(flags)
    print('Conductivity vertical gradient test: %f s\nReproved: %i (%f%%)\n' %((tf - ti), N, (N/n_samples)*100))

end = time.time()
print('\nProcessing time: %f s\n' %(end - start))

print('\nCreating output table\n')
qualified_data, raw_data, T_bdata, S_bdata, C_bdata, P_bdata, pH_bdata, chl_bdata, O2_bdata, org_bdata, tur_bdata, T_sdata, S_sdata, C_sdata, P_sdata, pH_sdata, chl_sdata, O2_sdata, org_sdata, tur_sdata, T_mdata, S_mdata, C_mdata, P_mdata, pH_mdata, chl_mdata, O2_mdata, org_mdata, tur_mdata = data.handle_output_file (raw_data, flags, remove_suspect=OUTPUT['remove_suspect'], remove_bad=OUTPUT['remove_bad'], Profile=INPUT['profile'])

# add luminosity data to dataframe if input is hobo
if e == 4:
    qualified_data['Luminosity(lux)'] = lumiFrame['Luminosity(lux)']

qualified_data = data.order_var (qualified_data, n_cel, data_type='tscp')
# Fill column with site information
qualified_data['Site'] = INPUT['site']
# Fill column with site information
qualified_data['QCS Version'] = 'v1.0'
# Export qualified data to .csv/.xlsx file
os.chdir(OUTPUT['output_file_path'])
root_path = OUTPUT['output_file_path'] + '/' + re.search('^[^\.]+',INPUT['file_name']).group()
os.makedirs(root_path, exist_ok=True)
path = root_path + '/QCS qualified tscp data/'
os.makedirs(path, exist_ok=True)
dataview_path =  root_path + '/QCS DataView (fixed scale)/'
dataview_path2 = root_path + '/QCS DataView (unfixed scale)/'
if e != 4:
    os.makedirs(dataview_path, exist_ok=True)
    os.makedirs(dataview_path2, exist_ok=True)

if re.search('xlsx', OUTPUT['output_data_format'], re.IGNORECASE):
    qualified_data.to_excel(os.path.join(path, re.search('^[^\.]+',INPUT['file_name']).group())+'_QLF.xlsx', index=False) ##cria excel
if re.search('csv', OUTPUT['output_data_format'], re.IGNORECASE):
    qualified_data.to_csv(os.path.join(path, re.search('^[^\.]+',INPUT['file_name']).group())+'_QLF.xlsx', index=False) ##cria csv
print('\nExported data to: %s\n' %path)

print('\nExporting statistics table to: %s\n' %path)
stat_table = data.tscp_stats_table (qualified_data)
stat_table.to_csv(path + '/QCS_tscp_stat.csv', index=False)
print('\nExporting report to: %s\n' %path)
QCS_report = pd.DataFrame({'start': start_time,
                           'end': end_time,
                           'Total': len(qualified_data),
                           'Valid': len(qualified_data) - (len(T_bdata) + len(S_bdata) + len(C_bdata) + len(P_bdata)),
                           'T_bdata': len(T_bdata),
                           'S_bdata': len(S_bdata),
                           'C_bdata': len(C_bdata),
                           'P_bdata': len(P_bdata)}, index=[0])
QCS_report.to_csv(path + '/QCS_report.csv')

if e != 4:
    if INPUT['profile'] == True:
        exceptions = ['Datetime', 'Expedition', 'Pressure(dbar)',
                      'Site', 'Longitude', 'Latitude', 'Depth(m)',
                      'Battery Voltage(V)', 'flag', 'Sample Number']
        for variable in qualified_data.keys():
            if variable not in exceptions:
                view.plot_variable_profile(qualified_data, raw_data, variable, dataview_path, tsSettings, fixed_scale=True)
    else:
        for variable in qualified_data.keys():
            exceptions = ['Datetime', 'Expedition',
                          'Site', 'Longitude', 'Latitude',
                          'Battery Voltage(V)', 'flag', 'Sample Number']
            if variable not in exceptions:
                view.plot_variable(qualified_data, raw_data, variable, dataview_path, tsSettings, fixed_scale=True)

    if INPUT['profile'] == True:
        exceptions = ['Datetime', 'Expedition', 'Pressure(dbar)',
                      'Site', 'Longitude', 'Latitude', 'Depth(m)',
                      'Battery Voltage(V)', 'flag', 'Sample Number']
        for variable in qualified_data.keys():
            if variable not in exceptions:
                view.plot_variable_profile(qualified_data, raw_data, variable, dataview_path2, tsSettings, fixed_scale=False)
    else:
        for variable in qualified_data.keys():
            exceptions = ['Datetime', 'Expedition',
                          'Site', 'Longitude', 'Latitude',
                          'Battery Voltage(V)', 'flag', 'Sample Number']
            if variable not in exceptions:
                view.plot_variable(qualified_data, raw_data, variable, dataview_path2, tsSettings, fixed_scale=False)
elif e == 4:
    view.plot_hobo_split_site (database, dataview_path2)
