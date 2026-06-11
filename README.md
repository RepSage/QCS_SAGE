"# QCS_SAGE" 


QCS_Main pyinstaller executable prompt:

pyinstaller --onefile --windowed --icon=qcsMainIcon.ico --name QCS_Qualification_Tool --hidden-import QCS_DataHandler --hidden-import QCS_DataView --hidden-import QCS_Tests --hidden-import openpyxl --hidden-import openpyxl.cell._writer --hidden-import openpyxl.styles.stylesheet --hidden-import openpyxl.worksheet._writer --hidden-import matplotlib.backends.backend_qt5agg --hidden-import matplotlib.backends.backend_tkagg --collect-all openpyxl --collect-all matplotlib.backends --add-data "qcsMainIcon.ico;." QCS_Main.py

QCS_DatabaseView pyinstaller executable prompt:

pyinstaller --onefile --windowed --icon=qcsDataViewIcon.ico --name QCS_Visualization_Tool --hidden-import QCS_DataHandler --hidden-import QCS_DataView --hidden-import openpyxl --hidden-import openpyxl.cell._writer --hidden-import openpyxl.styles.stylesheet --hidden-import openpyxl.worksheet._writer --hidden-import matplotlib.backends.backend_qt5agg --hidden-import matplotlib.backends.backend_tkagg --collect-all openpyxl --collect-all matplotlib.backends --add-data "qcsDataViewIcon.ico;." QCS_DatabaseView.py