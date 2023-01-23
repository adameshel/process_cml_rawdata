import cml_rawdata_process as crp
from pathlib import Path
import os

raw_data_path = Path.joinpath(Path.cwd(), 'raw')
metadata_path = Path.joinpath(Path.cwd(), 'metadata')
print(metadata_path)
meta_files_list = sorted([f for f in os.listdir(metadata_path) if '.xls' in f])
print(meta_files_list)
for f,file_path in enumerate(meta_files_list):
    raw_crp = crp.CmlRawdataProcessor(raw_data_path,Path(file_path))
    raw_crp.execute()


# ## a list of pre-selected links ["site1-site2", ...] (optional)
# sel_links_path = Path(
#     '/Users/adameshel/Documents/Python_scripts/process_cml_rawdata/selected_links.txt'
# )
# crp = CmlRawdataProcessor(raw_data_path, metadata_path, create_csv=True)
# crp.execute()
