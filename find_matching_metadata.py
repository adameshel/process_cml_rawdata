import cml_rawdata_process as crp
from pathlib import Path
import os

raw_data_path = Path.joinpath(Path.cwd(), 'raw')
metadata_path = Path.joinpath(Path.cwd(), 'specific_metadata_files')
meta_files_list = sorted([f for f in os.listdir(metadata_path) if '.xls' in f])
print(meta_files_list)

for f,file in enumerate(meta_files_list):
    if f==0:
        raw_crp = crp.CmlRawdataProcessor(raw_data_path,
                                          metadata_path.joinpath(file)
                                          )
        raw_crp.execute()
    else:
        raw_crp.execute(process_rawdata=False)