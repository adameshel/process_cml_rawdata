import pandas as pd
import numpy as np
import pyproj
from pathlib import Path
from os import listdir
from os.path import isfile, join, exists
import matplotlib.pyplot as plt
# import pickle as pkl

class CmlRawdataProcessor:
    def __init__(self,
                 raw_data_path,
                 metadata_path,
                 create_csv=True,
                 sel_links_path=None):
        """
        A class for processing raw-data and metadata, and combining them.
        At the moment it is working for Cellcom.
        :param raw_data_path: Path to the raw-data.
        :param metadata_path: Path to the metadata.
        :param create_csv: Bool. if `True` csv files will be dropped in a newly
        generated directory.
        :param sel_links_path: A path to a txt file with link names (if known
        in advance)
        """

        self.raw_data_path = raw_data_path
        self.metadata_path = metadata_path
        self.sel_links_path = sel_links_path
        self.create_csv = create_csv

    def cellcom_ids(self, site_id):
        ''' remove IP numbers from cellcom site_a_id/site_b_id,
        and also convert all letters to lower case'''
        if type(site_id) == float:
            return np.nan
        elif len(site_id.strip('.0123456789;')) == 0:
            return np.nan
        elif '; ' in site_id:
            site_id0 = site_id.split('; ')[0]
            site_id1 = site_id.split('; ')[1]
            if '.' in site_id0:
                return site_id1
            else:
                return site_id0
        else:
            return site_id[0:4]

    def process_cellcom(self, xlfile, col_names):
        ''' Process metadata for cellcom '''
        #     xl = pd.ExcelFile(xlfile)

        #     df = xl.parse('Sheet1', skiprows=1) # skip the first row of the excel file
        if '.xls' in xlfile:
            df = pd.read_excel(xlfile)
        else:
            df = pd.read_csv(xlfile)
        cols = ['STATUS', 'TX_FREQ_HIGH_MHZ', 'TX_FREQ_LOW_MHZ', 'POL',
                'LENGTH_KM', 'SITE1_NAME', 'ID_SITE1', 'EAST1', 'NORTH1',
                'HEIGHT_ABOVE_SEA1_M', 'SITE2_NAME', 'ID_SITE2', 'EAST2',
                'NORTH2', 'HEIGHT_ABOVE_SEA2_M']
        df = df[cols]
        # df['link_id'] = '-' #df['ID_SITE1'] + '-' + df['ID_SITE2']
        # df['link_id'] = df['link_id'].str.lower()
        df.insert(15, 'SLOTS', '')
        df.insert(0, 'SP', 'cellcom')
        df.columns = col_names

        # convert EAST/NORTH to LAT/LON decimal
        bng = pyproj.Proj(init='epsg:2039')
        wgs84 = pyproj.Proj(init='epsg:4326')
        # lon, lat = pyproj.transform(from,to,easting,northing)
        df['LON1'], df['LAT1'] = pyproj.transform(bng, wgs84, df['LON1'].values, df['LAT1'].values)
        df['LON2'], df['LAT2'] = pyproj.transform(bng, wgs84, df['LON2'].values, df['LAT2'].values)

        # process cellcom ids to fix problems
        df['SITE1_ID'] = df['SITE1_ID'].apply(self.cellcom_ids)
        df['SITE2_ID'] = df['SITE2_ID'].apply(self.cellcom_ids)
        df['link_id'] = df['SITE1_ID'] + '-' + df['SITE2_ID']
        df['link_id'] = df['link_id'].str.lower()

        # remove '-X' from cml_id
        # df['Link_num'] = df['Link_num'].str.partition('-')[0]
        return df

    def check_link_metadata_availability(self):
        """
        A function for initiating the connection between raw and metadata.
        :return: Drops 2 files into the output directory-
            1. A txt file with raw links and their locations in the metadata
            2. A csv metadata file which contains only the relevant links
            which have rawdata
        """
        links_in_rd = self.RD_rx['link_id'].unique()
        links_in_md = self.df_metadata['link_id'].unique()
        self.links_with_metadata = []
        idxs_metadata_with_rawdata = []
        f = open(self.out_path.joinpath('metadata_rawdata_matching_links.txt'), "w")
        f.write("link_id_rawdata,metadata_index,metadata_file_name" + "\r\n")
        for l,link in enumerate(links_in_rd):
            if link in links_in_md:
                self.links_with_metadata.append(link)
                temp_idx = self.df_metadata[self.df_metadata['link_id']==link].\
                    index.values.astype(int)[0]
                idxs_metadata_with_rawdata.append(temp_idx)
                print('Link %s is in line %i in %s' % (link,
                                                       temp_idx,
                                                       self.metadata_path.name)
                      )
                f.write("%s,%i,%s\r\n" %(link,temp_idx,self.metadata_path.name))
        f.close()

        self.df_metadata_relevant = self.df_metadata.iloc[idxs_metadata_with_rawdata]
        cols = ['SP','link_id','Frequency1','Frequency2','Length_KM','LON1','LAT1','LON2','LAT2']
        self.df_metadata_relevant = self.df_metadata_relevant[cols]
        self.df_metadata_relevant.reset_index(drop=True, inplace=True)
        ## change to names which are compatible with draw_cmls_on_folium_map and Omnisol
        new_col_names = ['carrier', 'link_id', 'frequency_1', 'frequency_2', 'length_mk',
                         'tx_site_longitude', 'tx_site_latitude', 'rx_site_longitude',
                         'rx_site_latitude']
        self.df_metadata_relevant.columns = [new_col_names]
        if self.create_csv:
            self.df_metadata_relevant.to_csv(
                self.out_path.joinpath('metadata_relevant.csv'),
                index=False
            )

    def metadata_processor(self):
        # process all the metadata
        col_names = ['SP', 'Status', 'Frequency1',
                     'Frequency2', 'Polarization', 'Length_KM',
                     'SITE1_Name', 'SITE1_ID', 'LON1', 'LAT1',
                     'Height_above_sea1', 'SITE2_Name', 'SITE2_ID',
                     'LON2', 'LAT2', 'Height_above_sea2', 'SLOTS']
        MD = self.process_cellcom(str(self.metadata_path), col_names)

        # convert object to numeric values with additional processing
        # MD.loc[:,'Link_num'] = pd.to_string(MD.loc[:,'Link_num'], errors='coerce')

        # convert MHz to GHz
        MD.loc[:, 'Frequency1'] = pd.to_numeric(MD.loc[:, 'Frequency1'], errors='coerce') * 1e9 / 1000
        MD.loc[:, 'Frequency2'] = pd.to_numeric(MD.loc[:, 'Frequency2'], errors='coerce') * 1e9 / 1000

        MD.loc[:, 'LAT1'] = pd.to_numeric(MD.loc[:, 'LAT1'], errors='coerce')
        MD.loc[:, 'LON1'] = pd.to_numeric(MD.loc[:, 'LON1'], errors='coerce')
        MD.loc[:, 'LAT2'] = pd.to_numeric(MD.loc[:, 'LAT2'], errors='coerce')
        MD.loc[:, 'LON2'] = pd.to_numeric(MD.loc[:, 'LON2'], errors='coerce')
        MD.loc[:, 'Length_KM'] = pd.to_numeric(MD.loc[:, 'Length_KM'], errors='coerce')

        MD.loc[:, 'Height_above_sea1'] = pd.to_numeric(MD.loc[:, 'Height_above_sea1'], errors='coerce')
        MD.loc[:, 'Height_above_sea2'] = pd.to_numeric(MD.loc[:, 'Height_above_sea2'], errors='coerce')
        self.df_metadata = MD
        if self.create_csv:
            self.df_metadata.to_csv(self.out_path.joinpath('metadata.csv'))

    def rawdata_processor(self):
        # select raw-data files to open
        only_files = sorted([f for f in listdir(self.raw_data_path) if '.txt' in f])

        if self.sel_links_path:
            print('Filtering selected links')
            sel_links = list(np.genfromtxt(str(sel_links_path), dtype='str'))
            sites = []
            for i, link in enumerate(sel_links):
                l = str(link).partition('-')
                sites.append(l[0].lower())
                sites.append(l[-1].lower())

        self.RD_rx = []  # gather all RADIO_SINK
        self.RD_tx = []  # gather all RADIO_SOURCE

        for rdfile in only_files:
            rdfile = str(self.raw_data_path.joinpath(rdfile))
            RD = pd.read_csv(rdfile, index_col=False)
            RD.insert(6, 'Site', '')
            RD['Site'] = RD['NeAlias'].str.partition('_')[0]
            RD['Site'] = RD['Site'].str.lower()
            RD['NeAlias'] = RD['NeAlias'].str.rpartition('_')[2]
            RD['NeAlias'] = RD['NeAlias'].str.rpartition('.')[0]

            if self.sel_links_path:
                RD = RD.loc[RD['Site'].isin(sites)]

                # separate to RX and TX
            if str.find(rdfile, 'RADIO_SINK') != -1:
                RD = RD[['Time', 'Interval', 'Site', 'NeAlias', 'PowerRLTMmin', 'PowerRLTMmax']]
                self.RD_rx.append(RD)

            elif str.find(rdfile, 'RADIO_SOURCE') != -1:
                RD = RD[['Time', 'Interval', 'Site', 'NeAlias', 'PowerTLTMmin', 'PowerTLTMmax']]
                self.RD_tx.append(RD)

        self.RD_rx = pd.concat(self.RD_rx)  # the min/max RSL
        self.RD_tx = pd.concat(self.RD_tx)  # the min/max TSL

        # replace NeAlias with link_number
        self.RD_rx = self.RD_rx.rename(columns={'NeAlias': 'Hop_number', 'Site': 'Measuring_site'})
        self.RD_tx = self.RD_tx.rename(columns={'NeAlias': 'Hop_number', 'Site': 'Measuring_site'})

        # take only 15 minute data
        self.RD_rx = self.RD_rx[self.RD_rx['Interval'] == 15]
        self.RD_tx = self.RD_tx[self.RD_tx['Interval'] == 15]

        hops = []
        hops.append(self.RD_tx['Hop_number'].unique())
        self.hops = list(hops[0])
        self.RD_rx['link_id'] = '-'
        self.RD_tx['link_id'] = '-'
        hops_to_drop = []
        for h, hop in enumerate(self.hops):
            rsl = self.RD_rx[self.RD_rx['Hop_number'] == hop]
            rsl_temp_sites = sorted(rsl['Measuring_site'].unique())
            tsl = self.RD_tx[self.RD_tx['Hop_number'] == hop]
            tsl_temp_sites = sorted(tsl['Measuring_site'].unique())

            if (rsl_temp_sites == tsl_temp_sites) & (len(tsl_temp_sites) == 2):
                down_link = tsl_temp_sites[0] + '-' + rsl_temp_sites[1]
                up_link = tsl_temp_sites[1] + '-' + rsl_temp_sites[0]
                ##Rx up
                self.RD_rx['link_id'] = np.where(
                    (self.RD_rx['Hop_number'] == hop) &
                    (self.RD_rx['Measuring_site'] == rsl_temp_sites[0]),
                    up_link,
                    self.RD_rx['link_id']
                )
                ##Rx down
                self.RD_rx['link_id'] = np.where(
                    (self.RD_rx['Hop_number'] == hop) &
                    (self.RD_rx['Measuring_site'] == rsl_temp_sites[1]),
                    down_link,
                    self.RD_rx['link_id']
                )
                ## Tx up
                self.RD_tx['link_id'] = np.where(
                    (self.RD_tx['Hop_number'] == hop) &
                    (self.RD_tx['Measuring_site'] == tsl_temp_sites[1]),
                    up_link,
                    self.RD_tx['link_id']
                )
                ## Tx down
                self.RD_tx['link_id'] = np.where(
                    (self.RD_tx['Hop_number'] == hop) &
                    (self.RD_tx['Measuring_site'] == tsl_temp_sites[0]),
                    down_link,
                    self.RD_tx['link_id']
                )
            else:
                hops_to_drop.append(hop)

        self.RD_tx = self.RD_tx[~self.RD_tx['Hop_number'].isin(hops_to_drop)]
        self.RD_rx = self.RD_rx[~self.RD_rx['Hop_number'].isin(hops_to_drop)]

        ## Export rawdata to csv
        if self.create_csv:
            self.RD_rx.to_csv(self.out_path.joinpath('rd_rx.csv'))
            self.RD_tx.to_csv(self.out_path.joinpath('rd_tx.csv'))

    def execute(self,
                process_rawdata=True,
                process_metadata=True,
                check_availability=True):
        """
        Execute the class.
        :param process_rawdata: Bool. If 'True' the class will process the
        rawdata.
        :param process_metadata: Bool. If 'True' the class will process the
        metadata.
        :param check_availability: Bool. If 'True' the class will make the
        connection between the raw and metadata.
        :return:
        """
        self.process_metadata = process_metadata
        self.process_rawdata = process_rawdata

        for i in range(1000):
            temp_str = 'output_' + str(i)
            out_path = Path.joinpath(Path.cwd(),temp_str)
            if not Path(out_path).is_dir():
                Path.mkdir(out_path)
                self.out_path = out_path
                break
            if i==999:
                raise Exception("You seem to have too many output directories...")

        if self.process_metadata:
            self.metadata_processor()

        if self.process_rawdata:
            self.rawdata_processor()

        if check_availability:
            self.check_link_metadata_availability()

        print('All outputs were generated in:')
        print(str(self.out_path))
        ## create attenuation csv
        # df_atten =

if __name__ == "__main__":
    raw_data_path = Path.joinpath(Path.cwd(), 'raw')
    metadata_path = Path.joinpath(Path.cwd(), 'metadata').joinpath(
        'New_Celltable_final_converted.xls'
    )
    ## a list of pre-selected links ["site1-site2", ...] (optional)
    sel_links_path = Path(
        '/Users/adameshel/Documents/Python_scripts/process_cml_rawdata/selected_links.txt'
    )
    crp = CmlRawdataProcessor(raw_data_path,metadata_path,create_csv=True)
    crp.execute()