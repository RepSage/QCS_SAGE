
INPUT = {
         #file information
         'raw_data_path': 'C:\\Users\\JPedr\\Desktop\\projeto lab ufrj\\TESTE 1.0',
         'file_name': '[perfil] [sensores] 5650-2097-0-2021-03-22T16-37-57.905Z.csv',
         'site': 'CFRIO1',

         # unit conversion
         'pressure_unit': 'kPa',
         'conductivity_unit': 'mS/cm',
         'profile': True,
         'correct_gmt3h': False,
         'select_profile_data': True,
         'check_variables': True
        }

OUTPUT = {
          'output_file_path': 'C:\\Users\\JPedr\\Desktop\\projeto lab ufrj\\TESTE 1.0',
          'output_file_name': '[perfil] [sensores] 5650-2097-0-2021-03-22T16-37-57.905Z',
          'output_data_format': 'xlsx', ## [xlsx, csv]
          'remove_bad': True,
          'remove_suspect': False,
          }
