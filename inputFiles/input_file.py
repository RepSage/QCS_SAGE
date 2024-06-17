
INPUT = {
         #file information
         'raw_data_path': 'C:/Users/JPedr/QCS-master/database/Unificada',
         'file_name': 'HOBO_UNIFICADA_250923.csv',
         #'start_time': '16/09/2019 16:20:00',
         #'end_time': '17/09/2019 16:50:00',
         #'measurement_interval': '600',
         'site': 'BUR',

         # unit conversion
         'pressure_unit': 'kPa',
         'conductivity_unit': 'mS/cm',
         'profile': False,
         'select_profile_data': False,
         'check_variables': True
        }

OUTPUT = {
          'output_file_path': 'C:/Users/JPedr/QCS-master/database/HOBO',
          'output_file_name': 'HOBO_padronizada_05012023_qlf.csv',
          'remove_bad': True,
          'remove_suspect': False,
          }
