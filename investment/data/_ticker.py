# -*- coding: utf-8 -*-

#  Author: Investment Prediction Enthusiast <investment.ml.prediction@gmail.com>
#
#  License: LGPL-3.0

from ..math_and_stats import sigmoid

import pandas as pd

from datetime import datetime, timedelta, timezone
from calendar import day_name

import socket

import ftplib

import os
from os.path import join
import pathlib

# NASDAQ Composite Components:
# https://indexes.nasdaqomx.com/Index/Weighting/COMP -> Export
# 2,892 components as of 12/11/2020
# https://quant.stackexchange.com/questions/1640/where-to-download-list-of-all-common-stocks-traded-on-nyse-nasdaq-and-amex
# ftp.nasdaqtrader.com
# http://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs

# Russell 1000, 2000, 3000 Components
# https://www.ftserussell.com/resources/russell-reconstitution (download PDF)
# https://www.adobe.com/acrobat/online/pdf-to-excel.html (PDF to Excel conversion)

###########################################################################################

nasdaqlisted_df = pd.DataFrame()
otherlisted_df = pd.DataFrame()
options_df = pd.DataFrame()
global_data_root_dir = join(str(pathlib.Path.home()), ".investment")

###########################################################################################

def Internet_connection_available():
    try:
        sock = socket.create_connection(("www.google.com", 80))
        if sock is not None:
            sock.close
        return True
    except OSError:
        pass
    return False

# references:
# https://quant.stackexchange.com/questions/1640/where-to-download-list-of-all-common-stocks-traded-on-nyse-nasdaq-and-amex
# http://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs
def download_nasdaqtrader_data(data_root_dir: str = None):
    if data_root_dir is None:
         raise ValueError("Error: data_root_dir cannot be None")

    data_dir = join(data_root_dir, "ticker_data/nasdaqtrader")
    if not os.path.exists(data_dir):
        try:
            pathlib.Path(data_dir).mkdir(parents=True, exist_ok=True)
        except:
            raise IOError(f"cannot create data dir: {data_dir}")
    ftp_server = 'ftp.nasdaqtrader.com'
    ftp_username = 'anonymous'
    ftp_password = 'anonymous'
    ftp = ftplib.FTP(ftp_server)
    ftp.login(ftp_username, ftp_password)
    files = [('SymbolDirectory/nasdaqlisted.txt', join(data_dir, 'nasdaqlisted.txt')), 
             ('SymbolDirectory/otherlisted.txt',  join(data_dir, 'otherlisted.txt' )),
             ('SymbolDirectory/options.txt',      join(data_dir, 'options.txt'     ))]
    for file_ in files:
        with open(file_[1], "wb") as f:
            ftp.retrbinary("RETR " + file_[0], f.write)
    ftp.quit()


def load_nasdaqtrader_data(data_root_dir: str = None):

    from ._data import timedata

    if data_root_dir is None:
        raise ValueError("Error: data_root_dir cannot be None")

    file1 = pathlib.Path(join(data_root_dir, "ticker_data/nasdaqtrader/nasdaqlisted.txt"))
    file2 = pathlib.Path(join(data_root_dir, "ticker_data/nasdaqtrader/otherlisted.txt"))
    file3 = pathlib.Path(join(data_root_dir, "ticker_data/nasdaqtrader/options.txt"))

    to_download = False

    if file1.exists():
        if timedata().now.datetime - timedata(time_stamp=file1.stat().st_ctime).datetime > timedelta(days=3): # creation time
            to_download = True
    else:
        to_download = True

    if file2.exists():
        if timedata().now.datetime - timedata(time_stamp=file2.stat().st_ctime).datetime > timedelta(days=3): # creation time
            to_download = True
    else:
        to_download = True

    if file3.exists():
        if timedata().now.datetime - timedata(time_stamp=file3.stat().st_ctime).datetime > timedelta(days=3): # creation time
            to_download = True
    else:
        to_download = True

    if not Internet_connection_available():
        to_download = False
        if (not file1.exists()) or (not file2.exists()) or (not file3.exists()):
            raise RuntimeError("Internet is unavailable but the system depends on certain nasdaqtrader files to run")

    if to_download:
        print('Download data from ftp.nasdaqtrader.com ...', end='')
        download_nasdaqtrader_data(data_root_dir = data_root_dir) # always get the most up-to-date version
        print(' Done')
        
    global nasdaqlisted_df
    global otherlisted_df
    global options_df

    #
    preprocessed_file = pathlib.Path(join(data_root_dir, "ticker_data/nasdaqtrader/preprocessed.h5"))
    if to_download or (not preprocessed_file.exists()):
        #print('Creating preprocessed.h5 ...', end='')
        #
        nasdaqlisted_df = pd.read_csv(file1,sep='|',header=0,skipfooter=1,engine='python')
        otherlisted_df = pd.read_csv(file2,sep='|',header=0,skipfooter=1,engine='python')
        #options_df = pd.read_csv(file3,sep='|',header=0,skipfooter=1,engine='python')
        #
        nasdaqlisted_df['ticker'] = nasdaqlisted_df['Symbol'].str.replace('\.','\-').str.replace('\\','')
        otherlisted_df['ticker'] = otherlisted_df['NASDAQ Symbol'].str.replace('\.','\-').str.replace('\\','').str.replace('ACIC=','ACIC-UN').str.replace('AJAX=','AJAX-UN').str.replace('PRIF-A','PRIF-PA').str.replace('PRIF-B','PRIF-PB').str.replace('PRIF-C','PRIF-PC').str.replace('PRIF-D','PRIF-PD').str.replace('PRIF-E','PRIF-PE').str.replace('PRIF-F','PRIF-PF')
        #options_df['ticker'] = options_df['Underlying Symbol'].str.replace('\.','\-').str.replace('\\','')
        #
        nasdaqlisted_df = nasdaqlisted_df[ (nasdaqlisted_df['Test Issue'] == 'N') & (nasdaqlisted_df['NextShares'] == 'N') ].drop(['Test Issue','Symbol','NextShares','Round Lot Size'], axis=1)
        otherlisted_df = otherlisted_df[ otherlisted_df['Test Issue'] == 'N' ].drop(['Test Issue','NASDAQ Symbol','ACT Symbol','CQS Symbol','Round Lot Size'], axis=1)
        #options_df = options_df.drop(['Underlying Symbol'], axis=1)
        #
        data_store = pd.HDFStore(preprocessed_file)
        data_store['nasdaqlisted_df'] = nasdaqlisted_df
        data_store['otherlisted_df'] = otherlisted_df
        #data_store['options_df'] = options_df
        data_store.close()
        #print('Done')
    else:
        #print('Reading preprocessed.h5 ... ', end='')
        data_store = pd.HDFStore(preprocessed_file)
        nasdaqlisted_df = data_store['nasdaqlisted_df']
        otherlisted_df = data_store['otherlisted_df']
        #options_df = data_store['options_df']
        data_store.close()
        #print('Done')

load_nasdaqtrader_data(data_root_dir=global_data_root_dir)
   
###########################################################################################

# this one can be modified
ticker_group_dict = {'All': [],
                     'Basic Materials': ['DOW','HUN','EXP','AVTR','ECL','APD','DD','FNV','NEM','GDX','XLB'],
                     'Communication Services': ['CMCSA','DIS','EA','FB','GOOG','GOOGL','NFLX','ROKU','TMUS','VZ','ZM','T','TWTR','IRDM','TWLO','ESPO','XLC'],
                     'Consumer Cyclical': ['AMZN','BABA','HD','LOW','F','FIVE','JD','M','MCD','LGIH','MELI','PTON','NIO','NKE','OSTK','TSLA','TM','ARD','BERY','SBUX','BKNG','NCLH','W','XLY','FCAU'],
                     'Consumer Defensive': ['BYND','KO','PG','COST','TGT','WMT','GIS','ACI','OLLI','SAM','PEP','XLP'],
                     'Energy': ['CVX','MUR','VLO','EQT','XOM','TOT','XLE'],
                     'Financial Services': ['AXP','BAC', 'BRK-B','C','GS','JPM','TRV','V','MA','WFC','MS','XLF','PYPL','BHF','MSCI','JEF'],
                     'Healthcare': ['ABT','ALGN','AMGN','BMY','INO','JNJ','MRK','MRNA','PFE','UNH','NVS','WBA','ABBV','BIIB','QDEL','LVGO','TLRY','ISRG','GILD','TMO','XLV'],
                     'Industrials': ['BA', 'CAT', 'DAL', 'FDX', 'HON', 'MMM','SPCE','LMT','UAL','EAF','ENR','GNRC','KODK','RTX','GE','WM','AAL','XLI'],
                     'Technology': ['AAPL','ADBE','AMD','AYX','CLDR','CRM','CRWD','CSCO','ENPH','FEYE','IBM','INTC','MSFT','NVDA','NVMI','NLOK','ONTO','QCOM','SPLK','TSM','UBER','FIT','SQ','CTXS','DOCU','LRCX','MCHP','MU','NXPI','SHOP','STMP','TXN','NOW','SNE','WDAY','XLK'],
                     'Utilities': ['PCG','D','DUK','XEL','NRG','ES','XLU'],
                     'Real Estate': ['AMT','CCI','PLD','BPYU','BDN','CSGP','XLRE'],
                     'Dividend Stocks (11/2020)': ['BMY','WMT','HD','AAPL','MSFT'],
                     'Growth Stocks (11/2020)': ['ALGN','FIVE','LGIH','MELI','PTON'],
                     'COVID-19': ['ALT','MRNA','INO','GILD','JNJ','PFE','RCL','CCL','NCLH','ZM','AZN','ARCT','QDEL','ABT','HOLX','DGX','GME','CHWY','AMC'],
                     'Cyber Security': ['SWI','CYBR','CHKP','PANW','ZS','CRWD','FEYE','SCWX','VMW','MSFT','FTNT','MIME','HACK','PFPT','QLYS','RPD','TENB','VRNS','CIBR'],
                     '5G': ['AAPL','TMUS','VZ','T','QCOM','QRVO','ERIC','TSM','NVDA','SWKS','ADI','MRVL','AVGO','XLNX'],
                     'Innovation': ['ARKK','ARKQ','ARKW','ARKG','ARKF','EDIT','CRSP','NTLA'],
                     'ETF': ['JETS', 'ONEQ', 'IEMG', 'VTHR', 'IWB', 'IWM', 'IWV', 'IWF', 'VTV', 'SCHD', 'USMV', 'VEA', 'VWO', 'AGG', 'LQD', 'GLD', 'VTI', 'DIA', 'OILU', 'OILD', 'TQQQ', 'SQQQ', 'UDOW', 'SDOW', 'UVXY', 'SVXY', 'KORU', 'YANG', 'YINN', 'QQQ', 'VOO','SPY','IVV','TMF','TMV','TBF','TLT','ESPO','GDX','XLC','XLI','XLF','XLE','XLV','XLB','XLK','XLU','XLP','XLY','XLRE'],
                     'ETF database': [],
                     'Major Market Indexes': ['^DJI','^NDX','^GSPC','^IXIC','^RUT','^VIX','DIA','SPLG','IVV','VOO','SPY','QQQ','ONEQ','IWM','VTWO','VXX'],
                     'Non-US World Market Indexes': ['^FTSE',],
                     'DOW 30': ['^DJI', 'GS','WMT','MCD','CRM','DIS','NKE','CAT','TRV','VZ','JPM','IBM','HD','INTC','AAPL','MMM','MSFT','JNJ','CSCO','V','DOW','MRK','PG','AXP','KO','AMGN','HON','UNH','WBA','CVX','BA'],
                     'NASDAQ 100': ['^NDX', 'AAPL', 'ADBE', 'ADI', 'ADP', 'ADSK', 'ALGN', 'ALXN', 'AMAT', 'AMD', 'AMGN', 'AMZN', 'ANSS', 'ASML', 'ATVI', 'AVGO', 'BIDU', 'BIIB', 'BKNG', 'BMRN', 'CDNS', 'CDW', 'CERN', 'CHKP', 'CHTR', 'CMCSA', 'COST', 'CPRT', 'CSCO', 'CSX', 'CTAS', 'CTSH', 'CTXS', 'DLTR', 'DOCU', 'DXCM', 'EA', 'EBAY', 'EXC', 'EXPE', 'FAST', 'FB', 'FISV', 'FOX', 'FOXA', 'GILD', 'GOOG', 'GOOGL', 'IDXX', 'ILMN', 'INCY', 'INTC', 'INTU', 'ISRG', 'JD', 'KDP', 'KHC', 'KLAC', 'LBTYA', 'LBTYK', 'LRCX', 'LULU', 'MAR', 'MCHP', 'MDLZ', 'MELI', 'MNST', 'MRNA', 'MSFT', 'MU', 'MXIM', 'NFLX', 'NTES', 'NVDA', 'NXPI', 'ORLY', 'PAYX', 'PCAR', 'PDD', 'PEP', 'PYPL', 'QCOM', 'REGN', 'ROST', 'SBUX', 'SGEN', 'SIRI', 'SNPS', 'SPLK', 'SWKS', 'TCOM', 'TMUS', 'TSLA', 'TTWO', 'TXN', 'ULTA', 'VRSK', 'VRSN', 'VRTX', 'WBA', 'WDAY', 'XEL', 'XLNX', 'ZM'],
                     'S&P 500': ['^GSPC', 'VOO','SPY','IVV','MMM','ABT','ABBV','ABMD','ACN','ATVI','ADBE','AMD','AAP','AES','AFL','A','APD','AKAM','ALK','ALB','ARE','ALXN','ALGN','ALLE','LNT','ALL','GOOGL','GOOG','MO','AMZN','AMCR','AEE','AAL','AEP','AXP','AIG','AMT','AWK','AMP','ABC','AME','AMGN','APH','ADI','ANSS','ANTM','AON','AOS','APA','AIV','AAPL','AMAT','APTV','ADM','ANET','AJG','AIZ','T','ATO','ADSK','ADP','AZO','AVB','AVY','BKR','BLL','BAC','BK','BAX','BDX','BRK-B','BBY','BIO','BIIB','BLK','BA','BKNG','BWA','BXP','BSX','BMY','AVGO','BR','BF-B','CHRW','COG','CDNS','CPB','COF','CAH','KMX','CCL','CARR','CTLT','CAT','CBOE','CBRE','CDW','CE','CNC','CNP','CERN','CF','SCHW','CHTR','CVX','CMG','CB','CHD','CI','CINF','CTAS','CSCO','C','CFG','CTXS','CLX','CME','CMS','KO','CTSH','CL','CMCSA','CMA','CAG','CXO','COP','ED','STZ','COO','CPRT','GLW','CTVA','COST','CCI','CSX','CMI','CVS','DHI','DHR','DRI','DVA','DE','DAL','XRAY','DVN','DXCM','FANG','DLR','DFS','DISCA','DISCK','DISH','DG','DLTR','D','DPZ','DOV','DOW','DTE','DUK','DRE','DD','DXC','EMN','ETN','EBAY','ECL','EIX','EW','EA','EMR','ETR','EOG','EFX','EQIX','EQR','ESS','EL','ETSY','EVRG','ES','RE','EXC','EXPE','EXPD','EXR','XOM','FFIV','FB','FAST','FRT','FDX','FIS','FITB','FE','FRC','FISV','FLT','FLIR','FLS','FMC','F','FTNT','FTV','FBHS','FOXA','FOX','BEN','FCX','GPS','GRMN','IT','GD','GE','GIS','GM','GPC','GILD','GL','GPN','GS','GWW','HAL','HBI','HIG','HAS','HCA','PEAK','HSIC','HSY','HES','HPE','HLT','HFC','HOLX','HD','HON','HRL','HST','HWM','HPQ','HUM','HBAN','HII','IEX','IDXX','INFO','ITW','ILMN','INCY','IR','INTC','ICE','IBM','IP','IPG','IFF','INTU','ISRG','IVZ','IPGP','IQV','IRM','JKHY','J','JBHT','SJM','JNJ','JCI','JPM','JNPR','KSU','K','KEY','KEYS','KMB','KIM','KMI','KLAC','KHC','KR','LB','LHX','LH','LRCX','LW','LVS','LEG','LDOS','LEN','LLY','LNC','LIN','LYV','LKQ','LMT','L','LOW','LUMN','LYB','MTB','MRO','MPC','MKTX','MAR','MMC','MLM','MAS','MA','MKC','MXIM','MCD','MCK','MDT','MRK','MET','MTD','MGM','MCHP','MU','MSFT','MAA','MHK','TAP','MDLZ','MNST','MCO','MS','MOS','MSI','MSCI','NDAQ','NOV','NTAP','NFLX','NWL','NEM','NWSA','NWS','NEE','NLSN','NKE','NI','NSC','NTRS','NOC','NLOK','NCLH','NRG','NUE','NVDA','NVR','ORLY','OXY','ODFL','OMC','OKE','ORCL','OTIS','PCAR','PKG','PH','PAYX','PAYC','PYPL','PNR','PBCT','PEP','PKI','PRGO','PFE','PM','PSX','PNW','PXD','PNC','POOL','PPG','PPL','PFG','PG','PGR','PLD','PRU','PEG','PSA','PHM','PVH','QRVO','PWR','QCOM','DGX','RL','RJF','RTX','O','REG','REGN','RF','RSG','RMD','RHI','ROK','ROL','ROP','ROST','RCL','SPGI','CRM','SBAC','SLB','STX','SEE','SRE','NOW','SHW','SPG','SWKS','SLG','SNA','SO','LUV','SWK','SBUX','STT','STE','SYK','SIVB','SYF','SNPS','SYY','TMUS','TROW','TTWO','TPR','TGT','TEL','FTI','TDY','TFX','TER','TSLA','TXT','TMO','TIF','TJX','TSCO','TT','TDG','TRV','TFC','TWTR','TYL','TSN','UDR','ULTA','USB','UAA','UA','UNP','UAL','UNH','UPS','URI','UHS','UNM','VLO','VAR','VTR','VTRS','VRSN','VRSK','VZ','VRTX','VFC','VIAC','V','VNT','VNO','VMC','WRB','WAB','WMT','WBA','DIS','WM','WAT','WEC','WFC','WELL','WST','WDC','WU','WRK','WY','WHR','WMB','WLTW','WYNN','XEL','XRX','XLNX','XYL','YUM','ZBRA','ZBH','ZION','ZTS'],
                     'NASDAQ Composite': ['^IXIC', 'AACG', 'AACQ', 'AAL', 'AAME', 'AAOI', 'AAON', 'AAPL', 'AAWW', 'AAXN', 'ABCB', 'ABCM', 'ABEO', 'ABIO', 'ABMD', 'ABNB', 'ABST', 'ABTX', 'ABUS', 'ACAD', 'ACAM', 'ACBI', 'ACCD', 'ACER', 'ACET', 'ACEV', 'ACGL', 'ACHC', 'ACHV', 'ACIA', 'ACIU', 'ACIW', 'ACLS', 'ACMR', 'ACNB', 'ACOR', 'ACRS', 'ACRX', 'ACST', 'ACTC', 'ACTG', 'ADAP', 'ADBE', 'ADES', 'ADI', 'ADIL', 'ADMA', 'ADMP', 'ADMS', 'ADOC', 'ADP', 'ADPT', 'ADSK', 'ADTN', 'ADTX', 'ADUS', 'ADV', 'ADVM', 'ADXN', 'ADXS', 'AEGN', 'AEHL', 'AEHR', 'AEIS', 'AEMD', 'AEP', 'AERI', 'AESE', 'AEY', 'AEYE', 'AEZS', 'AFIB', 'AFIN', 'AFMD', 'AFYA', 'AGBA', 'AGC', 'AGEN', 'AGFS', 'AGIO', 'AGLE', 'AGMH', 'AGNC', 'AGRX', 'AGTC', 'AGYS', 'AHAC', 'AHCO', 'AHPI', 'AIH', 'AIHS', 'AIKI', 'AIMC', 'AIRG', 'AIRT', 'AKAM', 'AKBA', 'AKER', 'AKRO', 'AKTS', 'AKTX', 'AKU', 'AKUS', 'ALAC', 'ALBO', 'ALCO', 'ALDX', 'ALEC', 'ALGM', 'ALGN', 'ALGS', 'ALGT', 'ALIM', 'ALJJ', 'ALKS', 'ALLK', 'ALLO', 'ALLT', 'ALNA', 'ALNY', 'ALOT', 'ALPN', 'ALRM', 'ALRN', 'ALRS', 'ALSK', 'ALT', 'ALTA', 'ALTM', 'ALTR', 'ALVR', 'ALXN', 'ALXO', 'ALYA', 'AMAL', 'AMAT', 'AMBA', 'AMCI', 'AMCX', 'AMD', 'AMED', 'AMEH', 'AMGN', 'AMHC', 'AMKR', 'AMNB', 'AMOT', 'AMPH', 'AMRB', 'AMRH', 'AMRK', 'AMRN', 'AMRS', 'AMSC', 'AMSF', 'AMST', 'AMSWA', 'AMTB', 'AMTBB', 'AMTI', 'AMTX', 'AMWD', 'AMYT', 'AMZN', 'ANAB', 'ANAT', 'ANCN', 'ANDA', 'ANDE', 'ANGI', 'ANGO', 'ANIK', 'ANIP', 'ANIX', 'ANNX', 'ANPC', 'ANSS', 'ANTE', 'ANY', 'AOSL', 'AOUT', 'APA', 'APDN', 'APEI', 'APEN', 'APHA', 'API', 'APLS', 'APLT', 'APM', 'APOG', 'APOP', 'APPF', 'APPN', 'APPS', 'APRE', 'APTO', 'APTX', 'APVO', 'APWC', 'APXT', 'APYX', 'AQB', 'AQMS', 'AQST', 'ARAV', 'ARAY', 'ARCB', 'ARCE', 'ARCT', 'ARDS', 'ARDX', 'AREC', 'ARGX', 'ARKR', 'ARLP', 'ARNA', 'AROW', 'ARPO', 'ARQT', 'ARRY', 'ARTL', 'ARTNA', 'ARTW', 'ARVN', 'ARWR', 'ARYA', 'ASLN', 'ASMB', 'ASML', 'ASND', 'ASO', 'ASPS', 'ASPU', 'ASRT', 'ASRV', 'ASTC', 'ASTE', 'ASUR', 'ASYS', 'ATAX', 'ATCX', 'ATEC', 'ATEX', 'ATHA', 'ATHE', 'ATHX', 'ATIF', 'ATLC', 'ATLO', 'ATNF', 'ATNI', 'ATNX', 'ATOM', 'ATOS', 'ATRA', 'ATRC', 'ATRI', 'ATRO', 'ATRS', 'ATSG', 'ATVI', 'ATXI', 'AUB', 'AUBN', 'AUDC', 'AUPH', 'AUTL', 'AUTO', 'AUVI', 'AVAV', 'AVCO', 'AVCT', 'AVDL', 'AVEO', 'AVGO', 'AVGR', 'AVID', 'AVIR', 'AVNW', 'AVO', 'AVRO', 'AVT', 'AVXL', 'AWH', 'AWRE', 'AXAS', 'AXDX', 'AXGN', 'AXLA', 'AXNX', 'AXSM', 'AXTI', 'AY', 'AYLA', 'AYRO', 'AYTU', 'AZN', 'AZPN', 'AZRX', 'AZYO', 'BAND', 'BANF', 'BANR', 'BASI', 'BATRA', 'BATRK', 'BBBY', 'BBCP', 'BBGI', 'BBI', 'BBIG', 'BBIO', 'BBQ', 'BBSI', 'BCBP', 'BCDA', 'BCEL', 'BCLI', 'BCML', 'BCOR', 'BCOV', 'BCOW', 'BCPC', 'BCRX', 'BCTG', 'BCYC', 'BDGE', 'BDSI', 'BDSX', 'BDTX', 'BEAM', 'BEAT', 'BECN', 'BEEM', 'BELFA', 'BELFB', 'BFC', 'BFIN', 'BFRA', 'BFST', 'BGCP', 'BGFV', 'BGNE', 'BHAT', 'BHF', 'BHTG', 'BIDU', 'BIGC', 'BIIB', 'BILI', 'BIMI', 'BIOC', 'BIOL', 'BIVI', 'BJRI', 'BKEP', 'BKNG', 'BKSC', 'BKYI', 'BL', 'BLBD', 'BLCM', 'BLCT', 'BLDP', 'BLDR', 'BLFS', 'BLI', 'BLIN', 'BLKB', 'BLMN', 'BLNK', 'BLPH', 'BLRX', 'BLSA', 'BLU', 'BLUE', 'BMCH', 'BMRA', 'BMRC', 'BMRN', 'BMTC', 'BNFT', 'BNGO', 'BNR', 'BNSO', 'BNTC', 'BNTX', 'BOCH', 'BOKF', 'BOMN', 'BOOM', 'BOSC', 'BOTJ', 'BOWX', 'BOXL', 'BPFH', 'BPMC', 'BPOP', 'BPRN', 'BPTH', 'BPY', 'BPYU', 'BRID', 'BRKL', 'BRKR', 'BRKS', 'BRLI', 'BROG', 'BRP', 'BRPA', 'BRQS', 'BRY', 'BSBK', 'BSET', 'BSGM', 'BSQR', 'BSRR', 'BSVN', 'BSY', 'BTAI', 'BTAQ', 'BTBT', 'BTWN', 'BUSE', 'BVXV', 'BWAY', 'BWB', 'BWEN', 'BWFG', 'BWMX', 'BXRX', 'BYFC', 'BYND', 'BYSI', 'BZUN', 'CAAS', 'CABA', 'CAC', 'CACC', 'CAKE', 'CALA', 'CALB', 'CALM', 'CALT', 'CAMP', 'CAMT', 'CAN', 'CAPA', 'CAPR', 'CAR', 'CARA', 'CARE', 'CARG', 'CARV', 'CASA', 'CASH', 'CASI', 'CASS', 'CASY', 'CATB', 'CATC', 'CATM', 'CATY', 'CBAN', 'CBAT', 'CBAY', 'CBFV', 'CBIO', 'CBLI', 'CBMB', 'CBMG', 'CBNK', 'CBPO', 'CBRL', 'CBSH', 'CBTX', 'CCAP', 'CCB', 'CCBG', 'CCCC', 'CCLP', 'CCMP', 'CCNC', 'CCNE', 'CCOI', 'CCRC', 'CCRN', 'CCXI', 'CD', 'CDAK', 'CDEV', 'CDK', 'CDLX', 'CDMO', 'CDNA', 'CDNS', 'CDTX', 'CDW', 'CDXC', 'CDXS', 'CDZI', 'CECE', 'CELC', 'CELH', 'CEMI', 'CENT', 'CENTA', 'CENX', 'CERC', 'CERE', 'CERN', 'CERS', 'CETX', 'CEVA', 'CFB', 'CFBI', 'CFBK', 'CFFI', 'CFFN', 'CFII', 'CFMS', 'CFRX', 'CG', 'CGC', 'CGEN', 'CGIX', 'CGNX', 'CGRO', 'CHCI', 'CHCO', 'CHDN', 'CHEF', 'CHEK', 'CHFS', 'CHKP', 'CHMA', 'CHMG', 'CHNG', 'CHNR', 'CHPM', 'CHRS', 'CHRW', 'CHTR', 'CHUY', 'CIDM', 'CIGI', 'CIH', 'CIIC', 'CINF', 'CIVB', 'CIZN', 'CJJD', 'CKPT', 'CLAR', 'CLBK', 'CLBS', 'CLCT', 'CLDB', 'CLDX', 'CLEU', 'CLFD', 'CLGN', 'CLIR', 'CLLS', 'CLMT', 'CLNE', 'CLPS', 'CLPT', 'CLRB', 'CLRO', 'CLSD', 'CLSK', 'CLSN', 'CLVS', 'CLWT', 'CLXT', 'CMBM', 'CMCO', 'CMCSA', 'CMCT', 'CME', 'CMLF', 'CMLS', 'CMPI', 'CMPR', 'CMPS', 'CMRX', 'CMTL', 'CNBKA', 'CNCE', 'CNDT', 'CNET', 'CNFR', 'CNNB', 'CNOB', 'CNSL', 'CNSP', 'CNST', 'CNTG', 'CNTY', 'CNXC', 'CNXN', 'COCP', 'CODA', 'CODX', 'COFS', 'COGT', 'COHR', 'COHU', 'COKE', 'COLB', 'COLL', 'COLM', 'COMM', 'CONE', 'CONN', 'COOP', 'CORE', 'CORT', 'COST', 'COUP', 'COWN', 'CPAH', 'CPHC', 'CPIX', 'CPLP', 'CPRT', 'CPRX', 'CPSH', 'CPSI', 'CPSS', 'CPST', 'CPTA', 'CRAI', 'CRBP', 'CRDF', 'CREE', 'CREG', 'CRESY', 'CREX', 'CRIS', 'CRMT', 'CRNC', 'CRNT', 'CRNX', 'CRON', 'CROX', 'CRSA', 'CRSP', 'CRSR', 'CRTD', 'CRTO', 'CRTX', 'CRUS', 'CRVL', 'CRVS', 'CRWD', 'CRWS', 'CSBR', 'CSCO', 'CSCW', 'CSGP', 'CSGS', 'CSII', 'CSIQ', 'CSOD', 'CSPI', 'CSSE', 'CSTE', 'CSTL', 'CSTR', 'CSWC', 'CSWI', 'CSX', 'CTAS', 'CTBI', 'CTG', 'CTHR', 'CTIB', 'CTIC', 'CTMX', 'CTRE', 'CTRM', 'CTRN', 'CTSH', 'CTSO', 'CTXR', 'CTXS', 'CUE', 'CURI', 'CUTR', 'CVAC', 'CVBF', 'CVCO', 'CVCY', 'CVET', 'CVGI', 'CVGW', 'CVLB', 'CVLG', 'CVLT', 'CVLY', 'CVV', 'CWBC', 'CWBR', 'CWCO', 'CWST', 'CXDC', 'CXDO', 'CYAD', 'CYAN', 'CYBE', 'CYBR', 'CYCC', 'CYCN', 'CYRN', 'CYRX', 'CYTH', 'CYTK', 'CZNC', 'CZR', 'CZWI', 'DADA', 'DAIO', 'DAKT', 'DARE', 'DBDR', 'DBVT', 'DBX', 'DCBO', 'DCOM', 'DCPH', 'DCT', 'DCTH', 'DDOG', 'DENN', 'DFFN', 'DFHT', 'DFPH', 'DGICA', 'DGICB', 'DGII', 'DGLY', 'DGNS', 'DHC', 'DHIL', 'DIOD', 'DISCA', 'DISCB', 'DISCK', 'DISH', 'DJCO', 'DKNG', 'DLHC', 'DLPN', 'DLTH', 'DLTR', 'DMAC', 'DMLP', 'DMRC', 'DMTK', 'DNKN', 'DNLI', 'DOCU', 'DOGZ', 'DOMO', 'DOOO', 'DORM', 'DOX', 'DOYU', 'DRAD', 'DRIO', 'DRNA', 'DRRX', 'DRTT', 'DSAC', 'DSGX', 'DSKE', 'DSPG', 'DSWL', 'DTEA', 'DTIL', 'DTSS', 'DUO', 'DUOT', 'DVAX', 'DWSN', 'DXCM', 'DXLG', 'DXPE', 'DXYN', 'DYAI', 'DYN', 'DYNT', 'DZSI', 'EA', 'EAR', 'EARS', 'EAST', 'EBAY', 'EBC', 'EBIX', 'EBMT', 'EBON', 'EBSB', 'EBTC', 'ECHO', 'ECOL', 'ECOR', 'ECPG', 'EDAP', 'EDIT', 'EDRY', 'EDSA', 'EDTK', 'EDUC', 'EEFT', 'EFOI', 'EFSC', 'EGAN', 'EGBN', 'EGLE', 'EGOV', 'EGRX', 'EH', 'EHTH', 'EIDX', 'EIGI', 'EIGR', 'EKSO', 'ELOX', 'ELSE', 'ELTK', 'ELYS', 'EMCF', 'EMKR', 'EML', 'ENDP', 'ENG', 'ENLV', 'ENOB', 'ENPH', 'ENSG', 'ENTA', 'ENTG', 'ENTX', 'EOLS', 'EOSE', 'EPAY', 'EPIX', 'EPSN', 'EPZM', 'EQ', 'EQBK', 'EQIX', 'EQOS', 'ERES', 'ERIC', 'ERIE', 'ERII', 'ERYP', 'ESBK', 'ESCA', 'ESEA', 'ESGR', 'ESLT', 'ESPR', 'ESQ', 'ESSA', 'ESSC', 'ESTA', 'ESXB', 'ETAC', 'ETNB', 'ETON', 'ETSY', 'ETTX', 'EVBG', 'EVER', 'EVFM', 'EVGN', 'EVK', 'EVLO', 'EVOK', 'EVOL', 'EVOP', 'EWBC', 'EXAS', 'EXC', 'EXEL', 'EXFO', 'EXLS', 'EXPC', 'EXPD', 'EXPE', 'EXPI', 'EXPO', 'EXTR', 'EYE', 'EYEG', 'EYEN', 'EYES', 'EYPT', 'EZPW', 'FAMI', 'FANG', 'FANH', 'FARM', 'FARO', 'FAST', 'FAT', 'FATE', 'FB', 'FBIO', 'FBIZ', 'FBMS', 'FBNC', 'FBRX', 'FBSS', 'FCAC', 'FCAP', 'FCBC', 'FCBP', 'FCCO', 'FCCY', 'FCEL', 'FCFS', 'FCNCA', 'FDBC', 'FEIM', 'FELE', 'FENC', 'FEYE', 'FFBC', 'FFBW', 'FFHL', 'FFIC', 'FFIN', 'FFIV', 'FFNW', 'FFWM', 'FGBI', 'FGEN', 'FHB', 'FHTX', 'FIBK', 'FIII', 'FISI', 'FISV', 'FITB', 'FIVE', 'FIVN', 'FIXX', 'FIZZ', 'FLDM', 'FLEX', 'FLGT', 'FLIC', 'FLIR', 'FLL', 'FLMN', 'FLNT', 'FLUX', 'FLWS', 'FLXN', 'FLXS', 'FMAO', 'FMBH', 'FMBI', 'FMNB', 'FMTX', 'FNCB', 'FNHC', 'FNKO', 'FNLC', 'FNWB', 'FOCS', 'FOLD', 'FONR', 'FORD', 'FORM', 'FORR', 'FORTY', 'FOSL', 'FOX', 'FOXA', 'FOXF', 'FPAY', 'FPRX', 'FRAF', 'FRAN', 'FRBA', 'FRBK', 'FREE', 'FREQ', 'FRG', 'FRGI', 'FRHC', 'FRLN', 'FRME', 'FROG', 'FRPH', 'FRPT', 'FRSX', 'FRTA', 'FSBW', 'FSDC', 'FSEA', 'FSFG', 'FSLR', 'FSRV', 'FSTR', 'FSTX', 'FSV', 'FTDR', 'FTEK', 'FTFT', 'FTHM', 'FTIV', 'FTNT', 'FTOC', 'FULC', 'FULT', 'FUNC', 'FUSB', 'FUSN', 'FUTU', 'FUV', 'FVAM', 'FVCB', 'FVE', 'FWONA', 'FWONK', 'FWP', 'FWRD', 'FXNC', 'GABC', 'GAIA', 'GALT', 'GAN', 'GASS', 'GBCI', 'GBIO', 'GBLI', 'GBT', 'GCBC', 'GCMG', 'GDEN', 'GDRX', 'GDS', 'GDYN', 'GEC', 'GENC', 'GENE', 'GEOS', 'GERN', 'GEVO', 'GFED', 'GFN', 'GGAL', 'GH', 'GHIV', 'GHSI', 'GIFI', 'GIGM', 'GIII', 'GILD', 'GILT', 'GLBS', 'GLBZ', 'GLDD', 'GLG', 'GLIBA', 'GLMD', 'GLNG', 'GLPG', 'GLPI', 'GLRE', 'GLSI', 'GLTO', 'GLUU', 'GLYC', 'GMAB', 'GMBL', 'GMDA', 'GMLP', 'GNCA', 'GNFT', 'GNLN', 'GNMK', 'GNPX', 'GNRS', 'GNSS', 'GNTX', 'GNTY', 'GNUS', 'GO', 'GOCO', 'GOGL', 'GOGO', 'GOOD', 'GOOG', 'GOOGL', 'GOSS', 'GOVX', 'GP', 'GPP', 'GPRE', 'GPRO', 'GRAY', 'GRBK', 'GRCY', 'GRFS', 'GRIF', 'GRIL', 'GRIN', 'GRMN', 'GRNQ', 'GRNV', 'GROW', 'GRPN', 'GRSV', 'GRTS', 'GRTX', 'GRVY', 'GRWG', 'GSBC', 'GSHD', 'GSIT', 'GSKY', 'GSM', 'GSMG', 'GSUM', 'GT', 'GTEC', 'GTH', 'GTHX', 'GTIM', 'GTLS', 'GTYH', 'GURE', 'GVP', 'GWAC', 'GWGH', 'GWPH', 'GWRS', 'GXGX', 'GYRO', 
                                          'HA', 'HAFC', 'HAIN', 'HALL', 'HALO', 'HAPP', 'HARP', 'HAS', 'HAYN', 'HBAN', 'HBCP', 'HBIO', 'HBMD', 'HBNC', 'HBP', 'HBT', 'HCAC', 'HCAP', 'HCAT', 'HCCI', 'HCDI', 'HCKT', 'HCM', 'HCSG', 'HDS', 'HDSN', 'HEAR', 'HEC', 'HEES', 'HELE', 'HEPA', 'HFBL', 'HFEN', 'HFFG', 'HFWA', 'HGBL', 'HGEN', 'HGSH', 'HHR', 'HIBB', 'HIFS', 'HIHO', 'HIMX', 'HJLI', 'HLG', 'HLIO', 'HLIT', 'HLNE', 'HLXA', 'HMHC', 'HMNF', 'HMST', 'HMSY', 'HMTV', 'HNNA', 'HNRG', 'HOFT', 'HOFV', 'HOL', 'HOLI', 'HOLX', 'HOMB', 'HONE', 'HOOK', 'HOPE', 'HOTH', 'HPK', 'HQI', 'HQY', 'HRMY', 'HROW', 'HRTX', 'HRZN', 'HSAQ', 'HSDT', 'HSIC', 'HSII', 'HSKA', 'HSON', 'HST', 'HSTM', 'HSTO', 'HTBI', 'HTBK', 'HTBX', 'HTGM', 'HTHT', 'HTLD', 'HTLF', 'HTOO', 'HUBG', 'HUGE', 'HUIZ', 'HURC', 'HURN', 'HUSN', 'HVBC', 'HWBK', 'HWC', 'HWCC', 'HWKN', 'HX', 'HYAC', 'HYFM', 'HYMC', 'HYRE', 'HZNP', 'IAC', 'IART', 'IBCP', 'IBEX', 'IBKR', 'IBOC', 'IBTX', 'ICAD', 'ICBK', 'ICCC', 'ICCH', 'ICFI', 'ICHR', 'ICLK', 'ICLR', 'ICMB', 'ICON', 'ICPT', 'ICUI', 'IDCC', 'IDEX', 'IDN', 'IDRA', 'IDXG', 'IDXX', 'IDYA', 'IEA', 'IEC', 'IEP', 'IESC', 'IFMK', 'IFRX', 'IGAC', 'IGIC', 'IGMS', 'IHRT', 'III', 'IIIN', 'IIIV', 'IIN', 'IIVI', 'IKNX', 'ILMN', 'ILPT', 'IMAB', 'IMAC', 'IMBI', 'IMGN', 'IMKTA', 'IMMP', 'IMMR', 'IMNM', 'IMOS', 'IMRA', 'IMRN', 'IMTE', 'IMTX', 'IMUX', 'IMV', 'IMVT', 'IMXI', 'INAQ', 'INBK', 'INBX', 'INCY', 'INDB', 'INFI', 'INFN', 'INGN', 'INM', 'INMB', 'INMD', 'INO', 'INOD', 'INOV', 'INPX', 'INSE', 'INSG', 'INSM', 'INTC', 'INTG', 'INTU', 'INTZ', 'INVA', 'INVE', 'INVO', 'INZY', 'IONS', 'IOSP', 'IOVA', 'IPAR', 'IPDN', 'IPGP', 'IPHA', 'IPHI', 'IPWR', 'IQ', 'IRBT', 'IRCP', 'IRDM', 'IRIX', 'IRMD', 'IROQ', 'IRTC', 'IRWD', 'ISBC', 'ISEE', 'ISIG', 'ISNS', 'ISRG', 'ISSC', 'ISTR', 'ITAC', 'ITCI', 'ITI', 'ITIC', 'ITMR', 'ITOS', 'ITRI', 'ITRM', 'ITRN', 'IVA', 'IVAC', 'IZEA', 'JACK', 'JAGX', 'JAKK', 'JAMF', 'JAN', 'JAZZ', 'JBHT', 'JBLU', 'JBSS', 'JCOM', 'JCS', 'JCTCF', 'JD', 'JFIN', 'JFU', 'JG', 'JJSF', 'JKHY', 'JNCE', 'JOBS', 'JOUT', 'JRJC', 'JRSH', 'JRVR', 'JUPW', 'JVA', 'JYAC', 'JYNT', 'KALA', 'KALU', 'KALV', 'KBAL', 'KBNT', 'KBSF', 'KC', 'KDMN', 'KDNY', 'KDP', 'KE', 'KELYA', 'KELYB', 'KEQU', 'KERN', 'KFFB', 'KFRC', 'KHC', 'KIDS', 'KIN', 'KINS', 'KIRK', 'KLAC', 'KLDO', 'KLIC', 'KLXE', 'KMDA', 'KNDI', 'KNSA', 'KNSL', 'KNTE', 'KOD', 'KOPN', 'KOR', 'KOSS', 'KPTI', 'KRBP', 'KRKR', 'KRMD', 'KRNT', 'KRNY', 'KRON', 'KROS', 'KRTX', 'KRUS', 'KRYS', 'KSMT', 'KSPN', 'KTCC', 'KTOS', 'KTOV', 'KTRA', 'KURA', 'KVHI', 'KXIN', 'KYMR', 'KZIA', 'KZR', 'LACQ', 'LAKE', 'LAMR', 'LANC', 'LAND', 'LARK', 'LASR', 'LATN', 'LAUR', 'LAWS', 'LAZR', 'LAZY', 'LBAI', 'LBC', 'LBRDA', 'LBRDK', 'LBTYA', 'LBTYB', 'LBTYK', 'LCA', 'LCAP', 'LCNB', 'LCUT', 'LCY', 'LE', 'LECO', 'LEDS', 'LEGH', 'LEGN', 'LESL', 'LEVL', 'LFAC', 'LFUS', 'LFVN', 'LGHL', 'LGIH', 'LGND', 'LHCG', 'LI', 'LIFE', 'LILA', 'LILAK', 'LINC', 'LIND', 'LIQT', 'LITE', 'LIVE', 'LIVK', 'LIVN', 'LIVX', 'LIXT', 'LIZI', 'LJPC', 'LKCO', 'LKFN', 'LKQ', 'LLIT', 'LLNW', 'LMAT', 'LMB', 'LMFA', 'LMNL', 'LMNR', 'LMNX', 'LMPX', 'LMRK', 'LMST', 'LNDC', 'LNSR', 'LNT', 'LNTH', 'LOAC', 'LOAN', 'LOB', 'LOCO', 'LOGC', 'LOGI', 'LOOP', 'LOPE', 'LORL', 'LOVE', 'LPCN', 'LPLA', 'LPRO', 'LPSN', 'LPTH', 'LPTX', 'LQDA', 'LQDT', 'LRCX', 'LRMR', 'LSAC', 'LSAQ', 'LSBK', 'LSCC', 'LSTR', 'LSXMA', 'LSXMB', 'LSXMK', 'LTBR', 'LTRN', 'LTRPA', 'LTRPB', 'LTRX', 'LULU', 'LUMO', 'LUNA', 'LUNG', 'LWAY', 'LX', 'LXEH', 'LXRX', 'LYFT', 'LYL', 'LYRA', 'LYTS', 'MAAC', 'MACK', 'MACU', 'MAGS', 'MANH', 'MANT', 'MAR', 'MARA', 'MARK', 'MARPS', 'MASI', 'MAT', 'MATW', 'MAXN', 'MAYS', 'MBCN', 'MBII', 'MBIN', 'MBIO', 'MBOT', 'MBRX', 'MBUU', 'MBWM', 'MCAC', 'MCBC', 'MCBS', 'MCEP', 'MCFE', 'MCFT', 'MCHP', 'MCHX', 'MCMJ', 'MCRB', 'MCRI', 'MDB', 'MDCA', 'MDGL', 'MDGS', 'MDIA', 'MDJH', 'MDLZ', 'MDNA', 'MDRR', 'MDRX', 'MDVL', 'MDWD', 'MDXG', 'MEDP', 'MEDS', 'MEIP', 'MELI', 'MEOH', 'MERC', 'MESA', 'MESO', 'METC', 'METX', 'MFH', 'MFIN', 'MFNC', 'MGEE', 'MGEN', 'MGI', 'MGIC', 'MGLN', 'MGNI', 'MGNX', 'MGPI', 'MGRC', 'MGTA', 'MGTX', 'MGYR', 'MHLD', 'MICT', 'MIDD', 'MIK', 'MIME', 'MIND', 'MIRM', 'MIST', 'MITK', 'MITO', 'MKD', 'MKGI', 'MKSI', 'MKTX', 'MLAB', 'MLAC', 'MLCO', 'MLHR', 'MLND', 'MLVF', 'MMAC', 'MMLP', 'MMSI', 'MMYT', 'MNCL', 'MNDO', 'MNKD', 'MNOV', 'MNPR', 'MNRO', 'MNSB', 'MNST', 'MNTX', 'MOFG', 'MOGO', 'MOHO', 'MOMO', 'MOR', 'MORF', 'MORN', 'MOSY', 'MOTS', 'MOXC', 'MPAA', 'MPB', 'MPWR', 'MRAM', 'MRBK', 'MRCY', 'MREO', 'MRIN', 'MRKR', 'MRLN', 'MRNA', 'MRNS', 'MRSN', 'MRTN', 'MRTX', 'MRUS', 'MRVI', 'MRVL', 'MSBI', 'MSEX', 'MSFT', 'MSON', 'MSTR', 'MSVB', 'MTBC', 'MTC', 'MTCH', 'MTCR', 'MTEM', 'MTEX', 'MTLS', 'MTP', 'MTRX', 'MTSC', 'MTSI', 'MTSL', 'MU', 'MVBF', 'MVIS', 'MWK', 'MXIM', 'MYFW', 'MYGN', 'MYRG', 'MYSZ', 'MYT', 'NAII', 'NAKD', 'NAOV', 'NARI', 'NATH', 'NATI', 'NATR', 'NAVI', 'NBAC', 'NBEV', 'NBIX', 'NBLX', 'NBN', 'NBRV', 'NBSE', 'NBTB', 'NCBS', 'NCMI', 'NCNA', 'NCNO', 'NCSM', 'NCTY', 'NDAQ', 'NDLS', 'NDRA', 'NDSN', 'NEO', 'NEOG', 'NEON', 'NEOS', 'NEPH', 'NEPT', 'NERV', 'NESR', 'NETE', 'NEWA', 'NEWT', 'NEXT', 'NFBK', 'NFE', 'NFLX', 'NGAC', 'NGHC', 'NGM', 'NGMS', 'NH', 'NHIC', 'NHLD', 'NHTC', 'NICE', 'NICK', 'NISN', 'NIU', 'NK', 'NKLA', 'NKSH', 'NKTR', 'NKTX', 'NLOK', 'NLTX', 'NMCI', 'NMFC', 'NMIH', 'NMMC', 'NMRD', 'NMRK', 'NMTR', 'NNBR', 'NNDM', 'NNOX', 'NODK', 'NOVN', 'NOVS', 'NOVT', 'NPA', 'NRBO', 'NRC', 'NRIM', 'NRIX', 'NSEC', 'NSIT', 'NSSC', 'NSTG', 'NSYS', 'NTAP', 'NTCT', 'NTEC', 'NTES', 'NTGR', 'NTIC', 'NTLA', 'NTNX', 'NTRA', 'NTRS', 'NTUS', 'NTWK', 'NUAN', 'NURO', 'NUVA', 'NUZE', 'NVAX', 'NVCN', 'NVCR', 'NVDA', 'NVEC', 'NVEE', 'NVFY', 'NVIV', 'NVMI', 'NVUS', 'NWBI', 'NWE', 'NWFL', 'NWL', 'NWLI', 'NWPX', 'NWS', 'NWSA', 'NXGN', 'NXPI', 'NXST', 'NXTC', 'NXTD', 'NYMT', 'NYMX', 'OAS', 'OBAS', 'OBCI', 'OBLN', 'OBNK', 'OBSV', 'OCC', 'OCFC', 'OCGN', 'OCUL', 'OCUP', 'ODFL', 'ODP', 'ODT', 'OEG', 'OESX', 'OFED', 'OFIX', 'OFLX', 'OGI', 'OIIM', 'OKTA', 'OLB', 'OLED', 'OLLI', 'OLMA', 'OM', 'OMAB', 'OMCL', 'OMER', 'OMEX', 'OMP', 'ON', 'ONB', 'ONCR', 'ONCS', 'ONCT', 'ONCY', 'ONDS', 'ONEM', 'ONEW', 'ONTX', 'ONVO', 'OPBK', 'OPCH', 'OPES', 'OPGN', 'OPHC', 'OPI', 'OPK', 'OPNT', 'OPOF', 'OPRA', 'OPRT', 'OPRX', 'OPT', 'OPTN', 'OPTT', 'ORBC', 'ORGO', 'ORGS', 'ORIC', 'ORLY', 'ORMP', 'ORPH', 'ORRF', 'ORTX', 'OSBC', 'OSIS', 'OSMT', 'OSN', 'OSPN', 'OSS', 'OSTK', 'OSUR', 'OSW', 'OTEL', 'OTEX', 'OTIC', 'OTLK', 'OTRK', 'OTTR', 'OVBC', 'OVID', 'OVLY', 'OXBR', 'OXFD', 'OYST', 'OZK', 'OZON', 'PAAS', 'PACB', 'PACW', 'PAE', 'PAHC', 'PAIC', 'PAND', 'PANL', 'PASG', 'PATI', 'PATK', 'PAVM', 'PAYA', 'PAYS', 'PAYX', 'PBCT', 'PBFS', 'PBHC', 'PBIP', 'PBLA', 'PBPB', 'PBTS', 'PBYI', 'PCAR', 'PCB', 'PCH', 'PCOM', 'PCRX', 'PCSA', 'PCSB', 'PCTI', 'PCTY', 'PCVX', 'PCYG', 'PCYO', 'PDCE', 'PDCO', 'PDD', 'PDEX', 'PDFS', 'PDLB', 'PDLI', 'PDSB', 'PEBK', 'PEBO', 'PECK', 'PEGA', 'PEIX', 'PENN', 'PEP', 'PERI', 'PESI', 'PETQ', 'PETS', 'PETZ', 'PFBC', 'PFBI', 'PFC', 'PFG', 'PFHD', 'PFIE', 'PFIN', 'PFIS', 'PFMT', 'PFPT', 'PFSW', 'PGC', 'PGEN', 'PGNY', 'PHAS', 'PHAT', 'PHCF', 'PHIO', 'PHUN', 'PI', 'PICO', 'PIH', 'PINC', 'PIRS', 'PIXY', 'PKBK', 'PKOH', 'PLAB', 'PLAY', 'PLBC', 'PLCE', 'PLIN', 'PLL', 'PLMR', 'PLPC', 'PLRX', 'PLSE', 'PLUG', 'PLUS', 'PLXP', 'PLXS', 'PLYA', 'PMBC', 'PMD', 'PME', 'PMVP', 'PNBK', 'PNFP', 'PNRG', 'PNTG', 'POAI', 'PODD', 'POLA', 'POOL', 'POWI', 'POWL', 'POWW', 'PPBI', 'PPC', 'PPD', 'PPIH', 'PPSI', 'PRAA', 'PRAH', 'PRAX', 'PRCP', 'PRDO', 'PRFT', 'PRFX', 'PRGS', 'PRGX', 'PRIM', 'PRLD', 'PROF', 'PROG', 'PROV', 'PRPH', 'PRPL', 'PRPO', 'PRQR', 'PRSC', 'PRTA', 'PRTC', 'PRTH', 'PRTK', 'PRTS', 'PRVB', 'PRVL', 'PS', 'PSAC', 'PSHG', 'PSMT', 'PSNL', 'PSTI', 'PSTV', 'PSTX', 'PT', 'PTAC', 'PTC', 'PTCT', 'PTE', 'PTEN', 'PTGX', 'PTI', 'PTNR', 'PTON', 'PTPI', 'PTRS', 'PTSI', 'PTVCA', 'PTVCB', 'PTVE', 'PUBM', 'PULM', 'PUYI', 'PVAC', 'PVBC', 'PWFL', 'PWOD', 'PXLW', 'PXS', 'PYPD', 'PYPL', 'PZZA', 'QADA', 'QADB', 'QCOM', 'QCRH', 'QDEL', 'QELL', 'QFIN', 'QH', 'QIWI', 'QK', 'QLGN', 'QLYS', 'QMCO', 'QNST', 'QRHC', 'QRTEA', 'QRTEB', 'QRVO', 'QTNT', 'QTRX', 'QTT', 'QUIK', 'QUMU', 'QURE', 'RACA', 'RADA', 'RADI', 'RAIL', 'RAPT', 'RARE', 'RAVE', 'RAVN', 'RBB', 'RBBN', 'RBCAA', 'RBCN', 'RBKB', 'RBNC', 'RCEL', 'RCHG', 'RCII', 'RCKT', 'RCKY', 'RCM', 'RCMT', 'RCON', 'RDCM', 'RDFN', 'RDHL', 'RDI', 'RDIB', 'RDNT', 'RDUS', 'RDVT', 'RDWR', 'REAL', 'REDU', 'REED', 'REFR', 'REG', 'REGI', 'REGN', 'REKR', 'RELL', 'RELV', 'REPH', 'REPL', 'RESN', 'RETA', 'RETO', 'REYN', 'RFIL', 'RGCO', 'RGEN', 'RGLD', 'RGLS', 'RGNX', 'RGP', 'RIBT', 'RICK', 'RIDE', 'RIGL', 'RILY', 'RIOT', 'RIVE', 'RKDA', 'RLAY', 'RLMD', 'RMBI', 'RMBL', 'RMBS', 'RMCF', 'RMNI', 'RMR', 'RMTI', 'RNA', 'RNDB', 'RNET', 'RNLX', 'RNST', 'RNWK', 'ROAD', 'ROCH', 'ROCK', 'ROIC', 'ROKU', 'ROLL', 'ROOT', 'ROST', 'RP', 'RPAY', 'RPD', 'RPRX', 'RPTX', 'RRBI', 'RRGB', 'RRR', 'RSSS', 'RTLR', 'RUBY', 'RUHN', 'RUN', 'RUSHA', 'RUSHB', 'RUTH', 'RVMD', 'RVNC', 'RVSB', 'RWLK', 'RXT', 'RYAAY', 'RYTM', 'RZLT', 'SABR', 'SAFM', 'SAFT', 'SAGE', 'SAIA', 'SAII', 'SAL', 'SALM', 'SAMA', 'SAMG', 'SANM', 'SANW', 'SASR', 'SATS', 'SAVA', 'SBAC', 'SBBP', 'SBCF', 'SBFG', 'SBGI', 'SBLK', 'SBNY', 'SBRA', 'SBSI', 'SBT', 'SBTX', 'SBUX', 'SCHL', 'SCHN', 'SCKT', 'SCOR', 'SCPH', 'SCPL', 
                                          'SCSC', 'SCVL', 'SCWX', 'SCYX', 'SDC', 'SDGR', 'SEAC', 'SECO', 'SEDG', 'SEED', 'SEEL', 'SEER', 'SEIC', 'SELB', 'SELF', 'SENEA', 'SENEB', 'SESN', 'SFBC', 'SFBS', 'SFET', 'SFIX', 'SFM', 'SFNC', 'SFST', 'SFT', 'SG', 'SGA', 'SGAM', 'SGBX', 'SGC', 'SGEN', 'SGH', 'SGLB', 'SGMA', 'SGMO', 'SGMS', 'SGOC', 'SGRP', 'SGRY', 'SGTX', 'SHBI', 'SHC', 'SHEN', 'SHIP', 'SHOO', 'SHSP', 'SHYF', 'SIBN', 'SIC', 'SIEB', 'SIEN', 'SIFY', 'SIGA', 'SIGI', 'SILC', 'SILK', 'SIMO', 'SINA', 'SINO', 'SINT', 'SIOX', 'SIRI', 'SITM', 'SIVB', 'SJ', 'SKYW', 'SLAB', 'SLCT', 'SLDB', 'SLGG', 'SLGL', 'SLGN', 'SLM', 'SLN', 'SLNO', 'SLP', 'SLRX', 'SLS', 'SMBC', 'SMBK', 'SMCI', 'SMED', 'SMID', 'SMIT', 'SMMC', 'SMMF', 'SMMT', 'SMPL', 'SMSI', 'SMTC', 'SMTI', 'SMTX', 'SNBR', 'SNCA', 'SNCR', 'SND', 'SNDE', 'SNDL', 'SNDX', 'SNES', 'SNEX', 'SNFCA', 'SNGX', 'SNOA', 'SNPS', 'SNSS', 'SNY', 'SOHO', 'SOHU', 'SOLO', 'SOLY', 'SONA', 'SONM', 'SONN', 'SONO', 'SP', 'SPCB', 'SPFI', 'SPI', 'SPKE', 'SPLK', 'SPNE', 'SPNS', 'SPOK', 'SPPI', 'SPRB', 'SPRO', 'SPRT', 'SPSC', 'SPT', 'SPTN', 'SPWH', 'SPWR', 'SQBG', 'SQFT', 'SRAC', 'SRAX', 'SRCE', 'SRCL', 'SRDX', 'SREV', 'SRGA', 'SRNE', 'SRPT', 'SRRA', 'SRRK', 'SRTS', 'SSB', 'SSBI', 'SSKN', 'SSNC', 'SSNT', 'SSP', 'SSPK', 'SSRM', 'SSTI', 'SSYS', 'STAA', 'STAF', 'STAY', 'STBA', 'STCN', 'STEP', 'STFC', 'STIM', 'STKL', 'STKS', 'STLD', 'STMP', 'STND', 'STNE', 'STOK', 'STRA', 'STRL', 'STRM', 'STRO', 'STRS', 'STRT', 'STSA', 'STTK', 'STWO', 'STX', 'STXB', 'SUMO', 'SUMR', 'SUNW', 'SUPN', 'SURF', 'SV', 'SVA', 'SVAC', 'SVBI', 'SVC', 'SVMK', 'SVRA', 'SWAV', 'SWBI', 'SWIR', 'SWKH', 'SWKS', 'SWTX', 'SXTC', 'SY', 'SYBT', 'SYBX', 'SYKE', 'SYNA', 'SYNC', 'SYNH', 'SYNL', 'SYPR', 'SYRS', 'SYTA', 'TA', 'TACO', 'TACT', 'TAIT', 'TANH', 'TAOP', 'TARA', 'TARS', 'TAST', 'TATT', 'TAYD', 'TBBK', 'TBIO', 'TBK', 'TBLT', 'TBNK', 'TBPH', 'TC', 'TCBI', 'TCBK', 'TCCO', 'TCDA', 'TCF', 'TCFC', 'TCMD', 'TCOM', 'TCON', 'TCRR', 'TCX', 'TDAC', 'TEAM', 'TECH', 'TEDU', 'TELA', 'TELL', 'TENB', 'TENX', 'TER', 'TESS', 'TFFP', 'TFSL', 'TGA', 'TGLS', 'TGTX', 'TH', 'THBR', 'THCA', 'THCB', 'THFF', 'THMO', 'THRM', 'THRY', 'THTX', 'TIG', 'TIGO', 'TIGR', 'TILE', 'TIPT', 'TITN', 'TLC', 'TLGT', 'TLMD', 'TLND', 'TLRY', 'TLS', 'TLSA', 'TMDI', 'TMDX', 'TMTS', 'TMUS', 'TNAV', 'TNDM', 'TNXP', 'TOMZ', 'TOPS', 'TOTA', 'TOUR', 'TOWN', 'TPCO', 'TPIC', 'TPTX', 'TRCH', 'TREE', 'TRHC', 'TRIB', 'TRIL', 'TRIP', 'TRIT', 'TRMB', 'TRMD', 'TRMK', 'TRMT', 'TRNS', 'TROW', 'TRS', 'TRST', 'TRUE', 'TRUP', 'TRVG', 'TRVI', 'TRVN', 'TSBK', 'TSC', 'TSCO', 'TSEM', 'TSHA', 'TSLA', 'TSRI', 'TTCF', 'TTD', 'TTEC', 'TTEK', 'TTGT', 'TTMI', 'TTNP', 'TTOO', 'TTWO', 'TUSK', 'TVTX', 'TVTY', 'TW', 'TWCT', 'TWIN', 'TWNK', 'TWOU', 'TWST', 'TXG', 'TXMD', 'TXN', 'TXRH', 'TYHT', 'TYME', 'TZAC', 'TZOO', 'UAL', 'UBCP', 'UBFO', 'UBOH', 'UBSI', 'UBX', 'UCBI', 'UCL', 'UCTT', 'UEIC', 'UEPS', 'UFCS', 'UFPI', 'UFPT', 'UG', 'UHAL', 'UIHC', 'UK', 'ULBI', 'ULH', 'ULTA', 'UMBF', 'UMPQ', 'UNAM', 'UNB', 'UNIT', 'UNTY', 'UONE', 'UONEK', 'UPLD', 'UPWK', 'URBN', 'URGN', 'UROV', 'USAK', 'USAP', 'USAT', 'USAU', 'USCR', 'USEG', 'USIO', 'USLM', 'USWS', 'UTHR', 'UTMD', 'UTSI', 'UVSP', 'UXIN', 'VACQ', 'VALU', 'VBFC', 'VBIV', 'VBLT', 'VBTX', 'VC', 'VCEL', 'VCNX', 'VCTR', 'VCYT', 'VECO', 'VEON', 'VERB', 'VERI', 'VERO', 'VERU', 'VERX', 'VERY', 'VFF', 'VG', 'VIAC', 'VIACA', 'VIAV', 'VICR', 'VIE', 'VIH', 'VIOT', 'VIR', 'VIRC', 'VIRT', 'VISL', 'VITL', 'VIVE', 'VIVO', 'VJET', 'VKTX', 'VLDR', 'VLGEA', 'VLY', 'VMAC', 'VMAR', 'VMD', 'VNDA', 'VNET', 'VNOM', 'VOD', 'VOXX', 'VRA', 'VRAY', 'VRCA', 'VREX', 'VRM', 'VRME', 'VRNA', 'VRNS', 'VRNT', 'VRRM', 'VRSK', 'VRSN', 'VRTS', 'VRTU', 'VRTX', 'VSAT', 'VSEC', 'VSPR', 'VSTA', 'VSTM', 'VTGN', 'VTNR', 'VTRS', 'VTRU', 'VTSI', 'VTVT', 'VUZI', 'VVPR', 'VXRT', 'VYGR', 'VYNE', 'WABC', 'WAFD', 'WAFU', 'WASH', 'WATT', 'WB', 'WBA', 'WDAY', 'WDC', 'WDFC', 'WEN', 'WERN', 'WETF', 'WEYS', 'WHLM', 'WHLR', 'WIFI', 'WILC', 'WIMI', 'WINA', 'WING', 'WINT', 'WIRE', 'WISA', 'WIX', 'WKEY', 'WKHS', 'WLDN', 'WLFC', 'WLTW', 'WMG', 'WNEB', 'WORX', 'WPRT', 'WRAP', 'WRLD', 'WSBC', 'WSBF', 'WSC', 'WSFS', 'WSG', 'WSTG', 'WTBA', 'WTER', 'WTFC', 'WTRE', 'WTRH', 'WVE', 'WVFC', 'WVVI', 'WW', 'WWD', 'WWR', 'WYNN', 'XAIR', 'XBIO', 'XBIT', 'XCUR', 'XEL', 'XELA', 'XELB', 'XENE', 'XENT', 'XERS', 'XFOR', 'XGN', 'XLNX', 'XLRN', 'XNCR', 'XNET', 'XOMA', 'XONE', 'XP', 'XPEL', 'XPER', 'XRAY', 'XSPA', 'XTLB', 'YGMZ', 'YI', 'YJ', 'YMAB', 'YNDX', 'YORW', 'YQ', 'YRCW', 'YSAC', 'YTEN', 'YTRA', 'YVR', 'YY', 'Z', 'ZAGG', 'ZBRA', 'ZCMD', 'ZEAL', 'ZEUS', 'ZG', 'ZGNX', 'ZGYH', 'ZI', 'ZION', 'ZIOP', 'ZIXI', 'ZKIN', 'ZLAB', 'ZM', 'ZNGA', 'ZNTL', 'ZS', 'ZSAN', 'ZUMZ', 'ZVO', 'ZYNE', 'ZYXI',],
                     'Russell 1000': ['A', 'AAL', 'AAP', 'AAPL', 'AAXN', 'ABBV', 'ABC', 'ABMD', 'ABT', 'ACAD', 'ACC', 'ACGL', 'ACHC', 'ACM', 'ACN', 'ADBE', 'ADI', 'ADM', 'ADP', 'ADPT', 'ADS', 'ADSK', 'ADT', 'AEE', 'AEP', 'AES', 'AFG', 'AFL', 'AGCO', 'AGIO', 'AGNC', 'AGO', 'AGR', 'AIG', 'AIV', 'AIZ', 'AJG', 'AKAM', 'AL', 'ALB', 'ALGN', 'ALK', 'ALKS', 'ALL', 'ALLE', 'ALLY', 'ALNY', 'ALSN', 'ALXN', 'AM', 'AMAT', 'AMCR', 'AMD', 'AME', 'AMED', 'AMG', 'AMGN', 'AMH', 'AMP', 'AMT', 'AMTD', 'AMZN', 'AN', 'ANAT', 'ANET', 'ANSS', 'ANTM', 'AON', 'AOS', 'APA', 'APD', 'APH', 'APLE', 'APO', 'APTV', 'ARD', 'ARE', 'ARES', 'ARMK', 'ARW', 'ASB', 'ASH', 'ATH', 'ATO', 'ATR', 'ATUS', 'ATVI', 'AVB', 'AVGO', 'AVLR', 'AVT', 'AVTR', 'AVY', 'AWI', 'AWK', 'AXP', 'AXS', 'AXTA', 'AYI', 'AYX', 'AZO', 'AZPN', 'BA', 'BAC', 'BAH', 'BAX', 'BBY', 'BC', 'BDN', 'BDX', 'BEN', 'BERY', 'BF-A', 'BF-B', 'BFAM', 'BG', 'BHF', 'BIIB', 'BILL', 'BIO', 'BK', 'BKI', 'BKNG', 'BKR', 'BLK', 'BLL', 'BLUE', 'BMRN', 'BMY', 'BOH', 'BOKF', 'BPOP', 'BPYU', 'BR', 'BRK-B', 'BRKR', 'BRO', 'BRX', 'BSX', 'BURL', 'BWA', 'BWXT', 'BXP', 'BYND', 'C', 'CABO', 'CACC', 'CACI', 'CAG', 'CAH', 'CARR', 'CASY', 'CAT', 'CB', 'CBOE', 'CBRE', 'CBSH', 'CBT', 'CC', 'CCI', 'CCK', 'CCL', 'CDAY', 'CDK', 'CDNS', 'CDW', 'CE', 'CERN', 'CF', 'CFG', 'CFR', 'CFX', 'CG', 'CGNX', 'CHD', 'CHE', 'CHGG', 'CHH', 'CHNG', 'CHRW', 'CHTR', 'CI', 'CIEN', 'CINF', 'CL', 'CLGX', 'CLH', 'CLR', 'CLX', 'CMA', 'CMCSA', 'CME', 'CMG', 'CMI', 'CMS', 'CNA', 'CNC', 'CNP', 'COF', 'COG', 'COHR', 'COLD', 'COLM', 'COMM', 'CONE', 'COO', 'COP', 'COR', 'COST', 'COTY', 'COUP', 'CPA', 'CPB', 'CPRI', 'CPRT', 'CPT', 'CR', 'CREE', 'CRI', 'CRL', 'CRM', 'CRUS', 'CRWD', 'CSCO', 'CSGP', 'CSL', 'CSX', 'CTAS', 'CTL', 'CTLT', 'CTSH', 'CTVA', 'CTXS', 'CUBE', 'CUZ', 'CVNA', 'CVS', 'CVX', 'CW', 'CXO', 'CZR', 'D', 'DAL', 'DBX', 'DCI', 'DD', 'DDOG', 'DE', 'DEI', 'DELL', 'DFS', 'DG', 'DGX', 'DHI', 'DHR', 'DIS', 'DISCA', 'DISCK', 'DISH', 'DKS', 'DLB', 'DLR', 'DLTR', 'DNKN', 'DOCU', 'DOV', 'DOW', 'DOX', 'DPZ', 'DRE', 'DRI', 'DT', 'DTE', 'DUK', 'DVA', 'DVN', 'DXC', 'DXCM', 'EA', 'EAF', 'EBAY', 'ECL', 'ED', 'EEFT', 'EFX', 'EHC', 'EIX', 'EL', 'ELAN', 'ELS', 'EMN', 'EMR', 'ENPH', 'ENR', 'ENTG', 'EOG', 'EPAM', 'EPR', 'EQC', 'EQH', 'EQIX', 'EQR', 'EQT', 'ERIE', 'ES', 'ESI', 'ESRT', 'ESS', 'ESTC', 'ETFC', 'ETN', 'ETR', 'ETRN', 'ETSY', 'EV', 'EVBG', 'EVR', 'EVRG', 'EW', 'EWBC', 'EXAS', 'EXC', 'EXEL', 'EXP', 'EXPD', 'EXPE', 'EXR', 'F', 'FAF', 'FANG', 'FAST', 'FB', 'FBHS', 'FCN', 'FCNCA', 'FCX', 'FDS', 'FDX', 'FE', 'FEYE', 'FFIV', 'FHB', 'FHN', 'FICO', 'FIS', 'FISV', 'FITB', 'FIVE', 'FIVN', 'FL', 'FLIR', 'FLO', 'FLS', 'FLT', 'FMC', 'FNB', 'FND', 'FNF', 'FOX', 'FOXA', 'FR', 'FRC', 'FRT', 'FSLR', 'FSLY', 'FTDR', 'FTNT', 'FTV', 'FWONA', 'FWONK', 'G', 'GBT', 'GD', 'GDDY', 'GE', 'GGG', 'GH', 'GHC', 'GILD', 'GIS', 'GL', 'GLIBA', 'GLOB', 'GLPI', 'GLW', 'GM', 'GMED', 'GNRC', 'GNTX', 'GO', 'GOOG', 'GOOGL', 'GPC', 'GPK', 'GPN', 'GPS', 'GRA', 'GRMN', 'GRUB', 'GS', 'GTES', 'GWRE', 'GWW', 'H', 'HAE', 'HAIN', 'HAL', 'HAS', 'HBAN', 'HBI', 'HCA', 'HD', 'HDS', 'HE', 'HEI', 'HEI-A', 'HES', 'HFC', 'HHC', 'HIG', 'HII', 'HIW', 'HLF', 'HLT', 'HOG', 'HOLX', 'HON', 'HP', 'HPE', 'HPP', 'HPQ', 'HRB', 'HRC', 'HRL', 'HSIC', 'HST', 'HSY', 'HTA', 'HUBB', 'HUBS', 'HUM', 'HUN', 'HWM', 'HXL', 'HZNP', 'IAA', 'IAC', 'IART', 'IBKR', 'IBM', 'ICE', 'ICUI', 'IDA', 'IDXX', 'IEX', 'IFF', 'ILMN', 'IMMU', 'INCY', 'INFO', 'INGR', 'INTC', 'INTU', 'INVH', 'IONS', 'IOVA', 'IP', 'IPG', 'IPGP', 'IPHI', 'IQV', 'IR', 'IRM', 'ISRG', 'IT', 'ITT', 'ITW', 'IVZ', 'J', 'JAZZ', 'JBGS', 'JBHT', 'JBL', 'JBLU', 'JCI', 'JEF', 'JKHY', 'JLL', 'JNJ', 'JNPR', 'JPM', 'JW-A', 'JWN', 'K', 'KDP', 'KEX', 'KEY', 'KEYS', 'KHC', 'KIM', 'KKR', 'KLAC', 'KMB', 'KMI', 'KMPR', 'KMX', 'KNX', 'KO', 'KR', 'KRC', 'KSS', 'KSU', 'L', 'LAMR', 'LAZ', 'LB', 'LBRDA', 'LBRDK', 'LDOS', 'LEA', 'LECO', 'LEG', 'LEN', 'LEN-B', 'LFUS', 'LGF-A', 'LGF-B', 'LH', 'LHX', 'LII', 'LIN', 'LITE', 'LKQ', 'LLY', 'LM', 'LMT', 'LNC', 'LNG', 'LNT', 'LOGM', 'LOPE', 'LOW', 'LPLA', 'LRCX', 'LSI', 'LSTR', 'LSXMA', 'LSXMK', 'LULU', 'LUV', 'LVGO', 'LVS', 'LW', 'LYB', 'LYFT', 'LYV', 'MA', 'MAA', 'MAN', 'MANH', 'MAR', 'MAS', 'MASI', 'MAT', 'MCD', 'MCHP', 'MCK', 'MCO', 'MCY', 'MDB', 'MDLA', 'MDLZ', 'MDT', 'MDU', 'MET', 'MGM', 'MHK', 'MIC', 'MIDD', 'MKC', 'MKL', 'MKSI', 'MKTX', 'MLM', 'MMC', 'MMM', 'MNST', 'MO', 'MOH', 'MORN', 'MOS', 'MPC', 'MPW', 'MPWR', 'MRCY', 'MRK', 'MRNA', 'MRO', 'MRVL', 'MS', 'MSA', 'MSCI', 'MSFT', 'MSGE', 'MSGS', 'MSI', 'MSM', 'MTB', 'MTCH', 'MTD', 'MTG', 'MTN', 'MU', 'MUR', 'MXIM', 'MYL', 'NATI', 'NBIX', 'NBL', 'NCLH', 'NCR', 'NDAQ', 'NDSN', 'NEE', 'NEM', 'NET', 'NEU', 'NEWR', 'NFG', 'NFLX', 'NI', 'NKE', 'NKTR', 'NLOK', 'NLSN', 'NLY', 'NNN', 'NOC', 'NOV', 'NOW', 'NRG', 'NRZ', 'NSC', 'NTAP', 'NTNX', 'NTRS', 'NUAN', 'NUE', 'NUS', 'NVCR', 'NVDA', 'NVR', 'NVST', 'NVT', 'NWL', 'NWS', 'NWSA', 'NXST', 'NYCB', 'NYT', 'O', 'OC', 'ODFL', 'OFC', 'OGE', 'OHI', 'OKE', 'OKTA', 'OLED', 'OLLI', 'OLN', 'OMC', 'OMF', 'ON', 'ORCL', 'ORI', 'ORLY', 'OSK', 'OTIS', 'OUT', 'OXY', 'OZK', 'PACW', 'PAG', 'PANW', 'PAYC', 'PAYX', 'PB', 'PBCT', 'PCAR', 'PCG', 'PCTY', 'PD', 'PE', 'PEAK', 'PEG', 'PEGA', 'PEN', 'PEP', 'PFE', 'PFG', 'PFPT', 'PG', 'PGR', 'PGRE', 'PH', 'PHM', 'PII', 'PINC', 'PINS', 'PK', 'PKG', 'PKI', 'PLAN', 'PLD', 'PLNT', 'PM', 'PNC', 'PNFP', 'PNR', 'PNW', 'PODD', 'POOL', 'POST', 'PPC', 'PPD', 'PPG', 'PPL', 'PRAH', 'PRGO', 'PRI', 'PRU', 'PS', 'PSA', 'PSTG', 'PSX', 'PTC', 'PTON', 'PVH', 'PWR', 'PXD', 'PYPL', 'QCOM', 'QDEL', 'QGEN', 'QRTEA', 'QRVO', 'R', 'RBC', 'RCL', 'RE', 'REG', 'REGN', 'RETA', 'REXR', 'REYN', 'RF', 'RGA', 'RGEN', 'RGLD', 'RHI', 'RJF', 'RL', 'RMD', 'RNG', 'RNR', 'ROK', 'ROKU', 'ROL', 'ROP', 'ROST', 'RP', 'RPM', 'RS', 'RSG', 'RTX', 'RYN', 'SABR', 'SAGE', 'SAIC', 'SAM', 'SATS', 'SBAC', 'SBNY', 'SBUX', 'SC', 'SCCO', 'SCHW', 'SCI', 'SEB', 'SEDG', 'SEE', 'SEIC', 'SERV', 'SFM', 'SGEN', 'SHW', 'SIRI', 'SIVB', 'SIX', 'SJM', 'SKX', 'SLB', 'SLG', 'SLGN', 'SLM', 'SMAR', 'SMG', 'SNA', 'SNDR', 'SNPS', 'SNV', 'SNX', 'SO', 'SON', 'SPB', 'SPCE', 'SPG', 'SPGI', 'SPLK', 'SPOT', 'SPR', 'SQ', 'SRC', 'SRCL', 'SRE', 'SRPT', 'SSNC', 'ST', 'STAY', 'STE', 'STL', 'STLD', 'STNE', 'STOR', 'STT', 'STWD', 'STZ', 'SUI', 'SWCH', 'SWI', 'SWK', 'SWKS', 'SYF', 'SYK', 'SYNH', 'SYY', 'T', 'TAP', 'TCF', 'TCO', 'TDC', 'TDG', 'TDOC', 'TDS', 'TDY', 'TEAM', 'TECH', 'TER', 'TFC', 'TFSL', 'TFX', 'TGT', 'THG', 'THO', 'THS', 'TIF', 'TJX', 'TKR', 'TMO', 'TMUS', 'TNDM', 'TOL', 'TPR', 'TPX', 'TREE', 'TREX', 'TRGP', 'TRIP', 'TRMB', 'TRN', 'TROW', 'TRU', 'TRV', 'TSCO', 'TSLA', 'TSN', 'TT', 'TTC', 'TTD', 'TTWO', 'TW', 'TWLO', 'TWOU', 'TWTR', 'TXG', 'TXN', 'TXT', 'TYL', 'UA', 'UAA', 'UAL', 'UBER', 'UDR', 'UGI', 'UHAL', 'UHS', 'UI', 'ULTA', 'UMPQ', 'UNH', 'UNM', 'UNP', 'UNVR', 'UPS', 'URI', 'USB', 'USFD', 'USM', 'UTHR', 'V', 'VAR', 'VEEV', 'VER', 'VFC', 'VIAC', 'VIACA', 'VICI', 'VIRT', 'VLO', 'VMC', 'VMI', 'VMW', 'VNO', 'VOYA', 'VRSK', 'VRSN', 'VRT', 'VRTX', 'VSAT', 'VST', 'VTR', 'VVV', 'VZ', 'W', 'WAB', 'WAL', 'WAT', 'WBA', 'WBS', 'WDAY', 'WDC', 'WEC', 'WELL', 'WEN', 'WEX', 'WFC', 'WH', 'WHR', 'WLK', 'WLTW', 'WM', 'WMB', 'WMT', 'WORK', 'WPC', 'WPX', 'WRB', 'WRI', 'WRK', 'WSM', 'WSO', 'WST', 'WTFC', 'WTM', 'WTRG', 'WU', 'WWD', 'WWE', 'WY', 'WYND', 'WYNN', 'XEC', 'XEL', 'XLNX', 'XLRN', 'XOM', 'XPO', 'XRAY', 'XRX', 'XYL', 'Y', 'YUM', 'YUMC', 'Z', 'ZBH', 'ZBRA', 'ZEN', 'ZG', 'ZION', 'ZM', 'ZNGA', 'ZS', 'ZTS'],
                     'Russell 2000': ['^RUT', 'AA', 'AAN', 'AAOI', 'AAON', 'AAT', 'AAWW', 'ABCB', 'ABEO', 'ABG', 'ABM', 'ABR', 'ABTX', 'AC', 'ACA', 'ACBI', 'ACCO', 'ACEL', 'ACIA', 'ACIW', 'ACLS', 'ACNB', 'ACRE', 'ACRX', 'ACTG', 'ADC', 'ADES', 'ADMA', 'ADNT', 'ADRO', 'ADSW', 'ADTN', 'ADUS', 'ADVM', 'AE', 'AEGN', 'AEIS', 'AEL', 'AEO', 'AERI', 'AFIN', 'AFMD', 'AGEN', 'AGFS', 'AGLE', 'AGM', 'AGRX', 'AGS', 'AGTC', 'AGX', 'AGYS', 'AHCO', 'AHH', 'AI', 'AIMC', 'AIMT', 'AIN', 'AIR', 'AIT', 'AJRD', 'AJX', 'AKBA', 'AKCA', 'AKR', 'AKRO', 'AKTS', 'ALBO', 'ALCO', 'ALE', 'ALEC', 'ALEX', 'ALG', 'ALGT', 'ALLK', 'ALLO', 'ALRM', 'ALRS', 'ALSK', 'ALTG', 'ALTR', 'ALX', 'AMAG', 'AMAL', 'AMBA', 'AMBC', 'AMC', 'AMCX', 'AMEH', 'AMK', 'AMKR', 'AMN', 'AMNB', 'AMOT', 'AMPH', 'AMRC', 'AMRK', 'AMRS', 'AMRX', 'AMSC', 'AMSF', 'AMSWA', 'AMTB', 'AMWD', 'ANAB', 'ANDE', 'ANF', 'ANGO', 'ANH', 'ANIK', 'ANIP', 'AOSL', 'APAM', 'APEI', 'APG', 'APLS', 'APLT', 'APOG', 'APPF', 'APPN', 'APPS', 'APRE', 'APT', 'APTS', 'APTX', 'APYX', 'AQST', 'AQUA', 'AR', 'ARA', 'ARAV', 'ARAY', 'ARCB', 'ARCH', 'ARCT', 'ARDX', 'ARGO', 'ARI', 'ARL', 'ARLO', 'ARNA', 'ARNC', 'AROC', 'AROW', 'ARQT', 'ARR', 'ARTNA', 'ARVN', 'ARWR', 'ASC', 'ASGN', 'ASIX', 'ASMB', 'ASPN', 'ASPS', 'ASPU', 'ASTE', 'ASUR', 'AT', 'ATEC', 'ATEN', 'ATEX', 'ATGE', 'ATHX', 'ATI', 'ATKR', 'ATLC', 'ATLO', 'ATNI', 'ATNX', 'ATOM', 'ATRA', 'ATRC', 'ATRI', 'ATRO', 'ATRS', 'ATSG', 'ATXI', 'AUB', 'AUBN', 'AVA', 'AVAV', 'AVCO', 'AVD', 'AVEO', 'AVID', 'AVNS', 'AVRO', 'AVXL', 'AVYA', 'AWH', 'AWR', 'AX', 'AXDX', 'AXGN', 'AXL', 'AXLA', 'AXNX', 'AXSM', 'AXTI', 'AYTU', 'AZZ', 'B', 'BANC', 'BAND', 'BANF', 'BANR', 'BATRA', 'BATRK', 'BBBY', 'BBCP', 'BBIO', 'BBSI', 'BBX', 'BCBP', 'BCC', 'BCEI', 'BCEL', 'BCLI', 'BCML', 'BCO', 'BCOR', 'BCOV', 'BCPC', 'BCRX', 'BDC', 'BDGE', 'BDSI', 'BDTX', 'BE', 'BEAM', 'BEAT', 'BECN', 'BELFB', 'BFC', 'BFIN', 'BFS', 'BFST', 'BFYT', 'BGCP', 'BGS', 'BGSF', 'BH', 'BH-A', 'BHB', 'BHE', 'BHLB', 'BHVN', 'BIG', 'BIPC', 'BJ', 'BJRI', 'BKD', 'BKE', 'BKH', 'BKU', 'BL', 'BLBD', 'BLD', 'BLDR', 'BLFS', 'BLKB', 'BLMN', 'BLPH', 'BLX', 'BMCH', 'BMI', 'BMRC', 'BMTC', 'BNFT', 'BOCH', 'BOMN', 'BOOM', 'BOOT', 'BOX', 'BPFH', 'BPMC', 'BPRN', 'BRBR', 'BRC', 'BREW', 'BRG', 'BRID', 'BRKL', 'BRKS', 'BRMK', 'BRP', 'BRT', 'BRY', 'BSBK', 'BSGM', 'BSIG', 'BSRR', 'BSTC', 'BSVN', 'BTAI', 'BTU', 'BUSE', 'BV', 'BWB', 'BWFG', 'BXG', 'BXMT', 'BXS', 'BY', 'BYD', 'BYSI', 'BZH', 'CABA', 'CAC', 'CADE', 'CAI', 'CAKE', 'CAL', 'CALA', 'CALB', 'CALM', 'CALX', 'CAMP', 'CAR', 'CARA', 'CARE', 'CARG', 'CARS', 'CASA', 'CASH', 'CASI', 'CASS', 'CATB', 'CATC', 'CATM', 'CATO', 'CATS', 'CATY', 'CBAN', 'CBAY', 'CBB', 'CBFV', 'CBIO', 'CBMG', 'CBNK', 'CBRL', 'CBTX', 'CBU', 'CBZ', 'CCB', 'CCBG', 'CCF', 'CCMP', 'CCNE', 'CCOI', 'CCRN', 'CCS', 'CCXI', 'CDE', 'CDLX', 'CDMO', 'CDNA', 'CDTX', 'CDXC', 'CDXS', 'CDZI', 'CECE', 'CEIX', 'CELH', 'CEMI', 'CENT', 'CENTA', 'CENX', 'CERC', 'CERS', 'CETV', 'CEVA', 'CFB', 'CFFI', 'CFFN', 'CFRX', 'CHCO', 'CHCT', 'CHDN', 'CHEF', 'CHK', 'CHMA', 'CHMG', 'CHMI', 'CHRS', 'CHS', 'CHUY', 'CHX', 'CIA', 'CIM', 'CIO', 'CIR', 'CIT', 'CIVB', 'CIX', 'CIZN', 'CKH', 'CKPT', 'CLAR', 'CLBK', 'CLCT', 'CLDR', 'CLDT', 'CLF', 'CLFD', 'CLI', 'CLNC', 'CLNE', 'CLNY', 'CLPR', 'CLVS', 'CLW', 'CLXT', 'CMBM', 'CMC', 'CMCL', 'CMCO', 'CMCT', 'CMD', 'CMO', 'CMP', 'CMPR', 'CMRE', 'CMRX', 'CMTL', 'CNBKA', 'CNCE', 'CNDT', 'CNK', 'CNMD', 'CNNE', 'CNO', 'CNOB', 'CNR', 'CNS', 'CNSL', 'CNST', 'CNTG', 'CNTY', 'CNX', 'CNXN', 'CODX', 'COFS', 'COHU', 'COKE', 'COLB', 'COLL', 'CONN', 'COOP', 'CORE', 'CORR', 'CORT', 'COWN', 'CPF', 'CPK', 'CPLG', 'CPRX', 'CPS', 'CPSI', 'CRAI', 'CRBP', 'CRC', 'CRD-A', 'CRK', 'CRMD', 'CRMT', 'CRNC', 'CRNX', 'CROX', 'CRS', 'CRTX', 'CRVL', 'CRY', 'CSBR', 'CSGS', 'CSII', 'CSOD', 'CSPR', 'CSTE', 'CSTL', 'CSTR', 'CSV', 'CSWI', 'CTB', 'CTBI', 'CTMX', 'CTO', 'CTRE', 'CTRN', 'CTS', 'CTSO', 'CTT', 'CUB', 'CUBI', 'CUE', 'CURO', 'CUTR', 'CVA', 'CVBF', 'CVCO', 'CVCY', 'CVET', 'CVGW', 'CVI', 'CVLT', 'CVLY', 'CVM', 'CVTI', 'CWBR', 'CWCO', 'CWEN', 'CWEN-A', 'CWH', 'CWK', 'CWST', 'CWT', 'CXP', 'CXW', 'CYBE', 'CYCN', 'CYH', 'CYRX', 'CYTK', 'CZNC', 'DAKT', 'DAN', 'DAR', 'DBCP', 'DBD', 'DBI', 'DCO', 'DCOM', 'DCPH', 'DDD', 'DDS', 'DEA', 'DECK', 'DENN', 'DFIN', 'DGICA', 'DGII', 'DHC', 'DHIL', 'DHT', 'DHX', 'DIN', 'DIOD', 'DJCO', 'DK', 'DLTH', 'DLX', 'DMRC', 'DMTK', 'DNLI', 'DNOW', 'DOC', 'DOMO', 'DOOR', 'DORM', 'DRH', 'DRNA', 'DRQ', 'DRRX', 'DSKE', 'DSPG', 'DSSI', 'DTIL', 'DVAX', 'DX', 'DXPE', 'DY', 'DYAI', 'DZSI', 'EARN', 'EAT', 'EB', 'EBF', 'EBIX', 'EBMT', 'EBS', 'EBSB', 'EBTC', 'ECHO', 'ECOL', 'ECOM', 'ECPG', 'EDIT', 'EE', 'EEX', 'EFC', 'EFSC', 'EGAN', 'EGBN', 'EGHT', 'EGLE', 'EGOV', 'EGP', 'EGRX', 'EHTH', 'EIDX', 'EIG', 'EIGI', 'EIGR', 'ELA', 'ELF', 'ELMD', 'ELOX', 'ELY', 'EME', 'EML', 'ENDP', 'ENOB', 'ENS', 'ENSG', 'ENTA', 'ENV', 'ENVA', 'ENZ', 'EOLS', 'EPAC', 'EPAY', 'EPC', 'EPM', 'EPRT', 'EPZM', 'EQBK', 'ERI', 'ERII', 'EROS', 'ESCA', 'ESE', 'ESGR', 'ESNT', 'ESPR', 'ESQ', 'ESSA', 'ESTE', 'ESXB', 'ETH', 'ETM', 'ETNB', 'ETON', 'EVBN', 'EVC', 'EVER', 'EVFM', 'EVH', 'EVI', 'EVLO', 'EVOP', 'EVRI', 'EVTC', 'EXLS', 'EXPI', 'EXPO', 'EXPR', 'EXTN', 'EXTR', 'EYE', 'EZPW', 'FARM', 'FARO', 'FATE', 'FBC', 'FBIO', 'FBIZ', 'FBK', 'FBM', 'FBMS', 'FBNC', 'FBP', 'FC', 'FCAP', 'FCBC', 'FCBP', 'FCCO', 'FCCY', 'FCEL', 'FCF', 'FCFS', 'FCPT', 'FDBC', 'FDP', 'FELE', 'FENC', 'FF', 'FFBC', 'FFG', 'FFIC', 'FFIN', 'FFWM', 'FGBI', 'FGEN', 'FHI', 'FI', 'FIBK', 'FISI', 'FIT', 'FIX', 'FIXX', 'FIZZ', 'FLDM', 'FLGT', 'FLIC', 'FLMN', 'FLNT', 'FLOW', 'FLR', 'FLWS', 'FLXN', 'FMAO', 'FMBH', 'FMBI', 'FMNB', 'FN', 'FNCB', 'FNHC', 'FNKO', 'FNLC', 'FNWB', 'FOCS', 'FOE', 'FOLD', 'FONR', 'FOR', 'FORM', 'FORR', 'FOSL', 'FOXF', 'FPI', 'FPRX', 'FRAF', 'FRBA', 'FRBK', 'FREQ', 'FRG', 'FRGI', 'FRME', 'FRO', 'FRPH', 'FRPT', 'FRTA', 'FSB', 'FSBW', 'FSCT', 'FSFG', 'FSP', 'FSS', 'FSTR', 'FUL', 'FULC', 'FULT', 'FUNC', 'FVCB', 'FVE', 'FWRD', 'GABC', 'GAIA', 'GALT', 'GAN', 'GATX', 'GBCI', 'GBL', 'GBLI', 'GBX', 'GCAP', 'GCBC', 'GCI', 'GCO', 'GCP', 'GDEN', 'GDOT', 'GDP', 'GDYN', 'GEF', 'GEF-B', 'GENC', 'GEO', 'GERN', 'GES', 'GFF', 'GFN', 'GHL', 'GHM', 'GIII', 'GKOS', 'GLDD', 'GLNG', 'GLRE', 'GLT', 'GLUU', 'GLYC', 'GME', 'GMRE', 'GMS', 'GNE', 'GNK', 'GNL', 'GNLN', 'GNMK', 'GNPX', 'GNSS', 'GNTY', 'GNW', 'GOGO', 'GOLF', 'GOOD', 'GORO', 'GOSS', 'GPI', 'GPMT', 'GPOR', 'GPRE', 'GPRO', 'GPX', 'GRBK', 'GRC', 'GRIF', 'GRPN', 'GRTS', 'GRTX', 'GRWG', 'GSB', 'GSBC', 'GSHD', 'GSIT', 'GSKY', 'GT', 'GTHX', 'GTLS', 'GTN', 'GTS', 'GTT', 'GTY', 'GTYH', 'GVA', 'GWB', 'GWGH', 'GWRS', 'HA', 'HAFC', 'HALO', 'HARP', 'HASI', 'HAYN', 'HBB', 'HBCP', 'HBIO', 'HBMD', 'HBNC', 'HBT', 'HCAT', 'HCC', 'HCCI', 'HCHC', 'HCI', 'HCKT', 'HCSG', 'HEAR', 'HEES', 'HELE', 'HFFG', 'HFWA', 'HGV', 'HI', 'HIBB', 'HIFS', 'HL', 'HLI', 'HLIO', 'HLIT', 'HLNE', 'HLX', 'HMHC', 'HMN', 'HMST', 'HMSY', 'HMTV', 'HNGR', 'HNI', 'HOFT', 'HOMB', 'HOME', 'HONE', 'HOOK', 'HOPE', 'HQY', 'HR', 'HRI', 'HROW', 'HRTG', 'HRTX', 'HSC', 'HSII', 'HSKA', 'HSTM', 'HT', 'HTBI', 'HTBK', 'HTH', 'HTLD', 'HTLF', 'HTZ', 'HUBG', 'HUD', 'HURC', 'HURN', 'HVT', 'HWBK', 'HWC', 'HWKN', 'HY', 'HZO', 'IBCP', 'IBIO', 'IBKC', 'IBOC', 'IBP', 'IBTX', 'ICAD', 'ICBK', 'ICFI', 'ICHR', 'ICPT', 'IDCC', 'IDN', 'IDT', 'IDYA', 'IESC', 'IGMS', 'IGT', 'IHC', 'IHRT', 'III', 'IIIN', 'IIIV', 'IIN', 'IIPR', 'IIVI', 'ILPT', 'IMAX', 'IMGN', 'IMKTA', 'IMMR', 'IMRA', 'IMUX', 'IMVT', 'IMXI', 'INBK', 'INDB', 'INFN', 'INFU', 
                                      'INGN', 'INN', 'INO', 'INOV', 'INS', 'INSG', 'INSM', 'INSP', 'INSW', 'INT', 'INTL', 'INVA', 'IOSP', 'IPAR', 'IPI', 'IRBT', 'IRDM', 'IRET', 'IRMD', 'IRT', 'IRTC', 'IRWD', 'ISBC', 'ISEE', 'ISTR', 'ITCI', 'ITGR', 'ITI', 'ITIC', 'ITRI', 'IVAC', 'IVC', 'IVR', 'JACK', 'JBSS', 'JBT', 'JCAP', 'JCOM', 'JELD', 'JJSF', 'JNCE', 'JOE', 'JOUT', 'JRVR', 'JYNT', 'KAI', 'KALA', 'KALU', 'KALV', 'KAMN', 'KAR', 'KBAL', 'KBH', 'KBR', 'KDMN', 'KE', 'KELYA', 'KERN', 'KFRC', 'KFY', 'KIDS', 'KIN', 'KLDO', 'KMT', 'KN', 'KNL', 'KNSA', 'KNSL', 'KOD', 'KODK', 'KOP', 'KOS', 'KPTI', 'KRA', 'KREF', 'KRG', 'KRMD', 'KRNY', 'KRO', 'KROS', 'KRTX', 'KRUS', 'KRYS', 'KTB', 'KTOS', 'KURA', 'KVHI', 'KW', 'KWR', 'KZR', 'LAD', 'LADR', 'LAKE', 'LANC', 'LAND', 'LARK', 'LASR', 'LAUR', 'LAWS', 'LBAI', 'LBC', 'LBRT', 'LC', 'LCI', 'LCII', 'LCNB', 'LCUT', 'LDL', 'LE', 'LEGH', 'LEVL', 'LFVN', 'LGIH', 'LGND', 'LHCG', 'LILA', 'LILAK', 'LIND', 'LIVN', 'LIVX', 'LJPC', 'LKFN', 'LL', 'LLNW', 'LMAT', 'LMNR', 'LMNX', 'LMST', 'LNDC', 'LNN', 'LNTH', 'LOB', 'LOCO', 'LOGC', 'LORL', 'LOVE', 'LPG', 'LPSN', 'LPX', 'LQDA', 'LQDT', 'LRN', 'LSCC', 'LTC', 'LTHM', 'LTRPA', 'LUNA', 'LXFR', 'LXP', 'LXRX', 'LYRA', 'LYTS', 'LZB', 'M', 'MAC', 'MANT', 'MATW', 'MATX', 'MAXR', 'MBCN', 'MBI', 'MBII', 'MBIN', 'MBIO', 'MBUU', 'MBWM', 'MC', 'MCB', 'MCBC', 'MCBS', 'MCF', 'MCFT', 'MCRB', 'MCRI', 'MCS', 'MD', 'MDC', 'MDGL', 'MDP', 'MDRX', 'MEC', 'MED', 'MEDP', 'MEET', 'MEI', 'MEIP', 'MESA', 'MFA', 'MFNC', 'MG', 'MGEE', 'MGI', 'MGLN', 'MGNX', 'MGPI', 'MGRC', 'MGTA', 'MGTX', 'MGY', 'MHH', 'MHO', 'MIK', 'MIME', 'MINI', 'MIRM', 'MITK', 'MJCO', 'MLAB', 'MLHR', 'MLI', 'MLP', 'MLR', 'MLSS', 'MMAC', 'MMI', 'MMS', 'MMSI', 'MNK', 'MNKD', 'MNLO', 'MNOV', 'MNR', 'MNRL', 'MNRO', 'MNSB', 'MNTA', 'MOBL', 'MOD', 'MODN', 'MOFG', 'MOG-A', 'MORF', 'MOV', 'MPAA', 'MPB', 'MPX', 'MR', 'MRBK', 'MRC', 'MRKR', 'MRLN', 'MRNS', 'MRSN', 'MRTN', 'MRTX', 'MSBI', 'MSEX', 'MSGN', 'MSON', 'MSTR', 'MTDR', 'MTEM', 'MTH', 'MTOR', 'MTRN', 'MTRX', 'MTSC', 'MTSI', 'MTW', 'MTX', 'MTZ', 'MUSA', 'MVBF', 'MWA', 'MXL', 'MYE', 'MYFW', 'MYGN', 'MYOK', 'MYRG', 'NAT', 'NATH', 'NATR', 'NAV', 'NAVI', 'NBEV', 'NBHC', 'NBN', 'NBR', 'NBSE', 'NBTB', 'NC', 'NCBS', 'NCMI', 'NDLS', 'NEO', 'NEOG', 'NERV', 'NESR', 'NEX', 'NEXT', 'NFBK', 'NG', 'NGHC', 'NGM', 'NGVC', 'NGVT', 'NH', 'NHC', 'NHI', 'NJR', 'NK', 'NKSH', 'NL', 'NLS', 'NLTX', 'NMIH', 'NMRD', 'NMRK', 'NNBR', 'NNI', 'NODK', 'NOVA', 'NOVT', 'NP', 'NPK', 'NPO', 'NPTN', 'NR', 'NRBO', 'NRC', 'NRIM', 'NSA', 'NSCO', 'NSIT', 'NSP', 'NSSC', 'NSTG', 'NTB', 'NTCT', 'NTGR', 'NTLA', 'NTRA', 'NTUS', 'NUVA', 'NVAX', 'NVEC', 'NVEE', 'NVRO', 'NVTA', 'NWBI', 'NWE', 'NWFL', 'NWLI', 'NWN', 'NWPX', 'NX', 'NXGN', 'NXRT', 'NXTC', 'NYMT', 'NYMX', 'OBNK', 'OCFC', 'OCUL', 'OCX', 'ODC', 'ODP', 'ODT', 'OEC', 'OESX', 'OFED', 'OFG', 'OFIX', 'OFLX', 'OGS', 'OI', 'OII', 'OIS', 'OLP', 'OMCL', 'OMER', 'OMI', 'ONB', 'ONEM', 'ONEW', 'ONTO', 'OOMA', 'OPBK', 'OPCH', 'OPI', 'OPK', 'OPRT', 'OPRX', 'OPTN', 'OPY', 'ORA', 'ORBC', 'ORC', 'ORGO', 'ORGS', 'ORIC', 'ORRF', 'OSBC', 'OSG', 'OSIS', 'OSMT', 'OSPN', 'OSTK', 'OSUR', 'OSW', 'OTTR', 'OVBC', 'OVID', 'OVLY', 'OVV', 'OXM', 'OYST', 'PACB', 'PACK', 'PAE', 'PAHC', 'PANL', 'PAR', 'PARR', 'PASG', 'PATK', 'PAVM', 'PAYS', 'PBF', 'PBFS', 'PBH', 'PBI', 'PBIP', 'PBYI', 'PCB', 'PCH', 'PCRX', 'PCSB', 'PCTI', 'PCYG', 'PCYO', 'PDCE', 'PDCO', 'PDFS', 'PDLB', 'PDLI', 'PDM', 'PEB', 'PEBK', 'PEBO', 'PENN', 'PETQ', 'PETS', 'PFBC', 'PFBI', 'PFC', 'PFGC', 'PFHD', 'PFIS', 'PFNX', 'PFS', 'PFSI', 'PFSW', 'PGC', 'PGEN', 'PGNY', 'PGTI', 'PHAS', 'PHAT', 'PHR', 'PI', 'PICO', 'PINE', 'PING', 'PIPR', 'PIRS', 'PJT', 'PKBK', 'PKE', 'PKOH', 'PLAB', 'PLAY', 'PLBC', 'PLCE', 'PLMR', 'PLOW', 'PLPC', 'PLSE', 'PLT', 'PLUG', 'PLUS', 'PLXS', 'PLYM', 'PMT', 'PNM', 'PNRG', 'PNTG', 'POL', 'POR', 'POWI', 'POWL', 'PPBI', 'PQG', 'PRA', 'PRAA', 'PRDO', 'PRFT', 'PRGS', 'PRIM', 'PRK', 'PRLB', 'PRMW', 'PRNB', 'PRO', 'PROS', 'PROV', 'PRPL', 'PRSC', 'PRSP', 'PRTA', 'PRTH', 'PRTK', 'PRTS', 'PRVB', 'PRVL', 'PSB', 'PSMT', 'PSN', 'PSNL', 'PTCT', 'PTEN', 'PTGX', 'PTLA', 'PTSI', 'PTVCB', 'PUB', 'PUMP', 'PVAC', 'PVBC', 'PWFL', 'PWOD', 'PXLW', 'PZN', 'PZZA', 'QADA', 'QCRH', 'QLYS', 'QMCO', 'QNST', 'QTNT', 'QTRX', 'QTS', 'QTWO', 'QUAD', 'QUOT', 'RAD', 'RAMP', 'RAPT', 'RARE', 'RAVN', 'RBB', 'RBBN', 'RBCAA', 'RBNC', 'RC', 'RCII', 'RCKT', 'RCKY', 'RCM', 'RCUS', 'RDFN', 'RDN', 'RDNT', 'RDUS', 'RDVT', 'REAL', 'REFR', 'REGI', 'REPH', 'REPL', 'RES', 'RESI', 'RESN', 'REV', 'REVG', 'REX', 'REZI', 'RFL', 'RGCO', 'RGNX', 'RGP', 'RGR', 'RGS', 'RH', 'RHP', 'RICK', 'RIG', 'RIGL', 'RILY', 'RLGT', 'RLGY', 'RLI', 'RLJ', 'RLMD', 'RM', 'RMAX', 'RMBI', 'RMBS', 'RMNI', 'RMR', 'RMTI', 'RNST', 'ROAD', 'ROCK', 'ROG', 'ROIC', 'ROLL', 'RPAI', 'RPAY', 'RPD', 'RPT', 'RRBI', 'RRC', 'RRGB', 'RRR', 'RST', 'RTIX', 'RTRX', 'RUBI', 'RUBY', 'RUN', 'RUSHA', 'RUSHB', 'RUTH', 'RVI', 'RVMD', 'RVNC', 'RVP', 'RVSB', 'RWT', 'RXN', 'RYAM', 'RYI', 'RYTM', 'SAFE', 'SAFM', 'SAFT', 'SAH', 'SAIA', 'SAIL', 'SAL', 'SALT', 'SAMG', 'SANM', 'SASR', 'SAVA', 'SAVE', 'SB', 'SBBP', 'SBBX', 'SBCF', 'SBFG', 'SBGI', 'SBH', 'SBRA', 'SBSI', 'SBT', 'SCHL', 'SCHN', 'SCL', 'SCOR', 'SCPH', 'SCS', 'SCSC', 'SCU', 'SCVL', 'SCWX', 'SDGR', 'SEAC', 'SEAS', 'SELB', 'SEM', 'SENEA', 'SF', 'SFBS', 'SFE', 'SFIX', 'SFL', 'SFNC', 'SFST', 'SGA', 'SGC', 'SGH', 'SGMO', 'SGMS', 'SGRY', 'SHAK', 'SHBI', 'SHEN', 'SHO', 'SHOO', 'SHYF', 'SI', 'SIBN', 'SIEB', 'SIEN', 'SIG', 'SIGA', 'SIGI', 'SILK', 'SITC', 'SITE', 'SITM', 'SJI', 'SJW', 'SKT', 'SKY', 'SKYW', 'SLAB', 'SLCA', 'SLCT', 'SLDB', 'SLNO', 'SLP', 'SM', 'SMBC', 'SMBK', 'SMCI', 'SMED', 'SMMF', 'SMP', 'SMPL', 'SMSI', 'SMTC', 'SNBR', 'SNCR', 'SNDX', 'SNFCA', 'SNR', 'SOI', 'SOLY', 'SONA', 'SONO', 'SP', 'SPFI', 'SPKE', 'SPNE', 'SPNS', 'SPOK', 'SPPI', 'SPRO', 'SPSC', 'SPT', 'SPTN', 'SPWH', 'SPWR', 'SPXC', 'SR', 'SRCE', 'SRDX', 'SREV', 'SRG', 'SRI', 'SRNE', 'SRRK', 'SRT', 'SSB', 'SSD', 'SSP', 'SSTI', 'SSTK', 'STAA', 'STAG', 'STAR', 'STBA', 'STC', 'STFC', 'STMP', 'STND', 'STNG', 'STOK', 'STRA', 'STRL', 'STRO', 'STRS', 'STSA', 'STXB', 'STXS', 'SUM', 'SUPN', 'SVC', 'SVMK', 'SVRA', 'SWAV', 'SWBI', 'SWKH', 'SWM', 'SWN', 'SWTX', 'SWX', 'SXC', 'SXI', 'SXT', 'SYBT', 'SYKE', 'SYNA', 'SYRS', 'SYX', 'TACO', 'TALO', 'TARA', 'TAST', 'TBBK', 'TBI', 'TBIO', 'TBK', 'TBNK', 'TBPH', 'TCBI', 'TCBK', 'TCDA', 'TCFC', 'TCI', 'TCMD', 'TCRR', 'TCS', 'TCX', 'TDW', 'TELA', 'TELL', 'TEN', 'TENB', 'TERP', 'TEX', 'TG', 'TGH', 'TGI', 'TGNA', 'TGTX', 'TH', 'THC', 'THFF', 'THR', 'THRM', 'TILE', 'TIPT', 'TISI', 'TITN', 'TLYS', 'TMDX', 'TMHC', 'TMP', 'TMST', 'TNAV', 'TNC', 'TNET', 'TOWN', 'TPB', 'TPC', 'TPCO', 'TPH', 'TPIC', 'TPRE', 'TPTX', 'TR', 'TRC', 'TREC', 'TRHC', 'TRMK', 'TRNO', 'TRNS', 'TROX', 'TRS', 'TRST', 'TRTN', 'TRTX', 'TRUE', 'TRUP', 'TRWH', 'TSBK', 'TSC', 'TSE', 'TTEC', 'TTEK', 'TTGT', 'TTMI', 'TUP', 'TVTY', 'TWNK', 'TWO', 'TWST', 'TXMD', 'TXRH', 'TYME', 'UBA', 'UBFO', 'UBSI', 'UBX', 'UCBI', 'UCTT', 'UE', 'UEC', 'UEIC', 'UFCS', 'UFI', 'UFPI', 'UFPT', 'UFS', 'UHT', 'UIHC', 'UIS', 'ULBI', 'ULH', 'UMBF', 'UMH', 'UNF', 'UNFI', 'UNIT', 'UNTY', 'UPLD', 'UPWK', 'URBN', 'URGN', 'USCR', 'USLM', 'USNA', 'USPH', 'USX', 'UTI', 'UTL', 'UTMD', 'UUUU', 'UVE', 'UVSP', 'UVV', 'VAC', 'VALU', 'VAPO', 'VBIV', 'VBTX', 'VC', 'VCEL', 'VCRA', 'VCYT', 'VEC', 'VECO', 'VERI', 'VERO', 'VERU', 'VERY', 'VG', 'VGR', 'VHC', 'VIAV', 'VICR', 'VIE', 'VIR', 'VIVO', 'VKTX', 'VLGEA', 'VLY', 'VMD', 'VNDA', 'VNRX', 'VOXX', 'VPG', 'VRA', 'VRAY', 'VRCA', 'VREX', 'VRNS', 'VRNT', 'VRRM', 'VRS', 'VRTS', 'VRTU', 'VRTV', 'VSEC', 'VSH', 'VSLR', 'VSTM', 'VSTO', 'VTOL', 'VTVT', 'VVI', 'VVNT', 'VXRT', 'VYGR', 'WABC', 'WAFD', 'WASH', 'WBT', 'WCC', 'WD', 'WDFC', 'WDR', 'WERN', 'WETF', 'WEYS', 'WGO', 'WHD', 'WHG', 'WIFI', 'WINA', 'WING', 'WIRE', 'WK', 'WKHS', 'WLDN', 'WLFC', 'WLL', 'WMC', 'WMGI', 'WMK', 'WMS', 'WNC', 'WNEB', 'WOR', 'WOW', 'WRE', 'WRLD', 'WRTC', 'WSBC', 'WSBF', 'WSC', 'WSFS', 'WSR', 'WTBA', 'WTI', 'WTRE', 'WTRH', 'WTS', 'WTTR', 'WVE', 'WW', 'WWW', 'X', 'XAIR', 'XBIT', 'XCUR', 'XENT', 'XERS', 'XFOR', 'XGN', 'XHR', 'XNCR', 'XOMA', 'XONE', 'XPEL', 'XPER', 'YELP', 'YETI', 'YEXT', 'YMAB', 'YORW', 'ZEUS', 'ZGNX', 'ZIOP', 'ZIXI', 'ZNTL', 'ZUMZ', 'ZUO', 'ZYXI',],
                     'Russell 3000': [],
                     'Equity database': [],
                     'Volatility': ['^VIX','VIXY','VXX','^VOLQ'],
                     'Treasury Yield': ['^TNX','SHV','TIP','FLOT','VUT','BND'],
                     'OTC Market': ['JCPNQ',],
                     'Others': ['JWN','KSS','HMC','BRK-A','PROG','DS','OBSV']}

ticker_group_dict['Russell 3000'] = sorted(ticker_group_dict['Russell 1000'] + ticker_group_dict['Russell 2000'])

###########################################################################################

df1 = nasdaqlisted_df[['ticker', 'ETF']]
df2 = otherlisted_df[['ticker', 'ETF']]        
df = pd.concat([df1, df2],axis=0)[['ticker', 'ETF']].reset_index().drop(['index'],axis=1) # axis=0 (1): row (column)
ticker_group_dict['ETF database'] = df[ df['ETF'] == 'Y' ]['ticker'].tolist()
ticker_group_dict['Equity database'] = df[ df['ETF'] == 'N' ]['ticker'].tolist()

###########################################################################################

# Note: there are 145 industries, and their names are unique
subgroup_group_dict = {'All': [],
                       'Basic Materials': ['Aluminum','Specialty Chemicals','Chemicals','Coking Coal','Agricultural Inputs','Lumber & Wood Production','Gold','Other Industrial Metals & Mining','Steel','Paper & Paper Products','Building Materials','Copper','Other Precious Metals & Mining','Silver',],
                       'Communication Services': ['Entertainment','Telecom Services','Broadcasting','Internet Content & Information','Electronic Gaming & Multimedia','Advertising Agencies','Publishing',],
                       'Consumer Cyclical': ['Specialty Retail','Auto & Truck Dealerships','Gambling','Auto Parts','Apparel Retail','Textile Manufacturing','Packaging & Containers','Furnishings, Fixtures & Appliances','Internet Retail','Leisure','Restaurants','Auto Manufacturers','Personal Services','Travel Services','Resorts & Casinos','Residential Construction','Footwear & Accessories','Lodging','Apparel Manufacturing','Luxury Goods','Recreational Vehicles','Department Stores','Home Improvement Retail',],
                       'Consumer Defensive': ['Education & Training Services','Grocery Stores','Farm Products','Food Distribution','Beverages—Wineries & Distilleries','Packaged Foods','Discount Stores','Beverages—Non-Alcoholic','Household & Personal Products','Confectioners','Tobacco','Beverages—Brewers',],
                       'Energy': ['Oil & Gas Integrated','Oil & Gas Midstream','Oil & Gas Refining & Marketing','Oil & Gas E&P','Thermal Coal','Oil & Gas Equipment & Services','Oil & Gas Drilling','Uranium',],
                       'Financial Services': ['Shell Companies','Insurance—Life','Banks—Regional','Capital Markets','Insurance—Diversified','Credit Services','Insurance—Property & Casualty','Insurance—Specialty','Insurance Brokers','Asset Management','Mortgage Finance','Banks—Diversified','Financial Data & Stock Exchanges','Insurance—Reinsurance','Financial Conglomerates',],
                       'Healthcare': ['Diagnostics & Research','Drug Manufacturers—General','Medical Distribution','Biotechnology','Medical Devices','Health Information Services','Medical Care Facilities','Drug Manufacturers—Specialty & Generic','Medical Instruments & Supplies','Healthcare Plans','Pharmaceutical Retailers',],
                       'Industrials': ['Airlines','Building Products & Equipment','Airports & Air Services','Aerospace & Defense','Specialty Business Services','Infrastructure Operations','Business Equipment & Supplies','Engineering & Construction','Pollution & Treatment Controls','Staffing & Employment Services','Security & Protection Services','Electrical Equipment & Parts','Farm & Heavy Construction Machinery','Specialty Industrial Machinery','Integrated Freight & Logistics','Industrial Distribution','Rental & Leasing Services','Waste Management','Trucking','Marine Shipping','Metal Fabrication','Consulting Services','Railroads','Tools & Accessories','Conglomerates',],
                       'Real Estate': ['REIT—Diversified','REIT—Mortgage','REIT—Residential','REIT—Retail','REIT—Specialty','REIT—Hotel & Motel','REIT—Office','Real Estate—Development','Real Estate Services','Real Estate—Diversified','REIT—Healthcare Facilities','REIT—Industrial',],
                       'Technology': ['Semiconductors','Consumer Electronics','Software—Application','Communication Equipment','Software—Infrastructure','Semiconductor Equipment & Materials','Information Technology Services','Electronics & Computer Distribution','Computer Hardware','Electronic Components','Solar','Scientific & Technical Instruments',],
                       'Utilities': ['Utilities—Regulated Electric','Utilities—Diversified','Utilities—Regulated Water','Utilities—Independent Power Producers','Utilities—Regulated Gas','Utilities—Renewable',],}

# this one is fixed for now (but can be re-generated by find_value_stock() if ticker_group_dict is substantially modified)
# Note: there are 145 industries, and their names are unique
ticker_subgroup_dict = {'Agricultural Inputs': ['AVD','CF','CTVA','FMC','IPI','MBII','MOS','RKDA','SEED','SMG','YTEN',],
                        'Aluminum': ['AA','CENX','KALU',],
                        'Building Materials': ['CSCW','EXP','MDU','MLM','RETO','SMID','SUM','USCR','USLM','VMC',],
                        'Chemicals': ['APD','ASH','ASIX','CE','DD','DOW','EMN','FF','HUN','MEOH','MKD','MTX','RYAM','TROX','UNVR',],
                        'Coking Coal': ['AREC','HCC','METC','SXC',],
                        'Copper': ['FCX','SCCO',],
                        'Gold': ['CDE','CMCL','FNV','GORO','HL','NEM','NG','RGLD','SSRM','USAU',],
                        'Lumber & Wood Production': ['BCC','JCTCF','UFPI',],
                        'Other Industrial Metals & Mining': ['CHNR','CMP','GSM','MTRN','PLL','WWR',],
                        'Other Precious Metals & Mining': ['HYMC',],
                        'Paper & Paper Products': ['CLW','GLT','MERC','NP','SWM','UFS','VRS',],
                        'Silver': ['PAAS',],
                        'Specialty Chemicals': ['ALB','AMRS','AVTR','AXTA','BCPC','CBT','CC','CCF','ECL','ESI','FOE','FUL','GCP','GEVO','GPRE','GRA','GURE','HDSN','HWKN','IFF','IKNX','IOSP','KOP','KRA','KRO','KWR','LIN','LOOP','LTHM','LYB','NEU','NGVT','NTIC','ODC','OEC','OLN','PPG','PQG','RPM','SCL','SHW','SNES','SXT','TG','TREC','TSE','WDFC','WLK',],
                        'Steel': ['CLF','CMC','NUE','RS','SCHN','STLD','SYNL','TMST','USAP','X','ZEUS','ZKIN',],
                        'Advertising Agencies': ['BOMN','CMPR','CNET','CRTO','DLX','EEX','FLNT','ICLK','IPG','ISIG','MCHX','MDCA','MGNI','NCMI','OMC','QNST','QUOT','SCOR','SRAX','WIMI','XNET',],
                        'Broadcasting': ['AMCX','BBGI','CMLS','CSSE','ETM','EVC','FOX','FOXA','FWONA','FWONK','GSMG','GTN','IHRT','LSXMA','LSXMB','LSXMK','MDIA','NWS','NWSA','NXST','SALM','SBGI','SGA','SIRI','SJ','SSP','TGNA','UONE','UONEK',],
                        'Electronic Gaming & Multimedia': ['ATVI','AVID','BHAT','BILI','EA','GIGM','GLUU','GRVY','INSE','NCTY','RNWK','SCPL','SLGG','TTWO','YVR','ZNGA',],
                        'Entertainment': ['AESE','AMC','BATRA','BATRK','CHTR','CIDM','CMCSA','CNK','DIS','DISCA','DISCB','DISCK','DISH','DLB','DLPN','GNUS','HMTV','HOFV','IMAX','LBRDA','LBRDK','LBTYA','LBTYB','LBTYK','LGF-A','LGF-B','LYV','MCS','MSGE','MSGN','MSGS','NFLX','RDI','RDIB','ROKU','VIAC','VIACA','WMG','WOW','WSG','WWE',],
                        'Internet Content & Information': ['ANGI','AUTO','BIDU','BLCT','CARG','CDLX','CRTD','DOYU','EVER','FB','GAIA','GOOG','GOOGL','GRPN','GRUB','IAC','IQ','IZEA','JFIN','KRKR','LIZI','LKCO','LTRPA','LTRPB','MARK','MOMO','MOXC','MTCH','NTES','PCOM','PERI','PINS','QTT','SINA','SOHU','SPOT','SSTK','TC','TRUE','TRVG','TTGT','TWLO','TWTR','UXIN','WB','YELP','YNDX','YY','Z','ZG',],
                        'Publishing': ['DJCO','EDUC','GCI','JW-A','MDP','NYT','SCHL','TPCO',],
                        'Telecom Services': ['ALSK','ANTE','ATEX','ATNI','ATUS','CABO','CBB','CCOI','CNSL','GLIBA','GOGO','GTT','HCHC','IDCC','IDT','IRDM','LILA','LILAK','LORL','LUMN','MTSL','OOMA','ORBC','OTEL','PTNR','RBBN','RDCM','SHEN','SIFY','SPOK','T','TDS','TIGO','TMUS','UCL','USM','VEON','VG','VOD','VZ','WIFI','ZM',],
                        'Apparel Manufacturing': ['COLM','CPRI','EVK','HBI','ICON','JRSH','KBSF','KTB','LAKE','NAKD','OXM','PVH','RL','SGC','SQBG','UA','UAA','VFC','XELB',],
                        'Apparel Retail': ['AEO','ANF','BKE','BOOT','BURL','CATO','CHS','CRI','CTRN','DBI','DLTH','DXLG','EXPR','FRAN','GCO','GES','GIII','GPS','LB','LULU','PLCE','ROST','SCVL','TJX','TLYS','URBN','ZUMZ',],
                        'Auto & Truck Dealerships': ['ABG','AN','CARS','CRMT','GPI','KMX','KXIN','LAD','LAZY','LMPX','PAG','RMBL','RUSHA','RUSHB','SAH','VRM',],
                        'Auto Manufacturers': ['AYRO','BLBD','F','FCAU','GM','GP','HMC','LI','NIO','NIU','NKLA','SOLO','TM','TSLA','WKHS',],
                        'Auto Parts': ['ADNT','ALSN','APTV','AXL','BWA','CAAS','CPS','CTB','CVGI','CXDC','DAN','DORM','FRSX','GNTX','GT','KNDI','LEA','LKQ','MLR','MNRO','MOD','MPAA','MTOR','PLOW','SMP','SRI','STRT','SYPR','TEN','THRM','VC','WPRT','XPEL',],
                        'Department Stores': ['DDS','JWN','KSS','M',],
                        'Footwear & Accessories': ['CAL','CROX','DECK','FL','FORD','NKE','RCKY','SHOO','SKX','VRA','WEYS','WWW',],
                        'Furnishings, Fixtures & Appliances': ['AMWD','AUVI','BSET','CSPR','EFOI','ETH','FBHS','FLXS','HOFT','KBAL','KEQU','LCUT','LEG','LOVE','LZB','MHK','MLHR','NVFY','SNBR','TILE','TPX','VIRC','WHR',],
                        'Gambling': ['ACEL','AGS','CHDN','CPHC','DKNG','ELYS','EVRI','GAN','GMBL','IGT','SGMS',],
                        'Home Improvement Retail': ['FND','GRWG','HD','HVT','LESL','LL','LOW',],
                        'Internet Retail': ['AMZN','BABA','BZUN','CVNA','DADA','EBAY','ETSY','IMBI','JD','LQDT','MELI','MOHO','NHTC','OSTK','PDD','PRTS','QRTEA','QRTEB','RUHN','SECO','W','YJ',],
                        'Leisure': ['AOUT','BBIG','BC','CLAR','DS','ELY','ESCA','FNKO','GOLF','HAS','JAKK','JOUT','MAT','NLS','OSW','PLNT','POOL','PTON','SEAS','SIX','SPWH','VSTO',],
                        'Lodging': ['CHH','H','HLT','HTHT','INTG','MAR','STAY','WH','WYND',],
                        'Luxury Goods': ['CTHR','FOSL','MOV','SIG','TIF','TPR',],
                        'Packaging & Containers': ['AMCR','ARD','ATR','BERY','BLL','CCK','FFHL','GEF','GEF-B','GPK','IP','MYE','OI','PACK','PKG','PTVE','REYN','SEE','SLGN','SON','TUP','UFPT','WRK',],
                        'Personal Services': ['BFAM','CSV','FRG','FTDR','HRB','MED','RGS','ROL','SCI','TMX','WW','XSPA',],
                        'Recreational Vehicles': ['CWH','DOOO','FOXF','FUV','HOG','LCII','MBUU','MCFT','MPX','ONEW','PATK','PII','THO','WGO',],
                        'Residential Construction': ['BZH','CCS','CVCO','DHI','GRBK','KBH','LEGH','LEN','LEN-B','LGIH','MDC','MHO','MTH','NVR','PHM','SIC','SKY','TMHC','TOL','TPH',],
                        'Resorts & Casinos': ['BXG','BYD','CNTY','CZR','FLL','GDEN','HGV','LVS','MCRI','MGM','MLCO','MTN','PENN','PLYA','RRR','VAC','WYNN',],
                        'Restaurants': ['ARKR','ARMK','BBQ','BH-A','BJRI','BLMN','CAKE','CBRL','CHUY','CMG','CNNE','DENN','DIN','DNKN','DPZ','DRI','EAT','FAT','FRGI','GRIL','GTIM','JACK','KRUS','LOCO','MCD','MYT','NATH','NDLS','PBPB','PLAY','PZZA','RAVE','RICK','RRGB','RUTH','SBUX','SHAK','STKS','TACO','TAST','TXRH','WEN','WING','YUM','YUMC',],
                        'Specialty Retail': ['AAP','AZO','BBBY','BBY','BGFV','BLNK','BWMX','CONN','CTIB','DKS','ELA','EYE','FIVE','FLWS','GME','GPC','HIBB','HOME','HZO','KAR','KIRK','KSPN','LE','LIVE','MIK','MUSA','ODP','ORLY','REAL','RH','SBH','SFIX','TA','TCS','TSCO','ULTA','WINA','WSM','ZAGG',],
                        'Textile Manufacturing': ['AIN','CRWS','DXYN','UFI',],
                        'Travel Services': ['BKNG','CCL','EXPE','LIND','MKGI','MMYT','NCLH','RCL','TCOM','TOUR','TRIP','TZOO','YTRA',],
                        'Beverages—Brewers': ['SAM','TAP',],
                        'Beverages—Non-Alcoholic': ['CELH','COKE','FIZZ','KDP','KO','MNST','NBEV','PEP','PRMW','REED','WTER',],
                        'Beverages—Wineries & Distilleries': ['BF-A','BF-B','EAST','STZ','WVVI',],
                        'Confectioners': ['HSY','MDLZ','RMCF','TR',],
                        'Discount Stores': ['BIG','BJ','COST','DG','DLTR','OLLI','PSMT','TGT','WMT',],
                        'Education & Training Services': ['AACG','AFYA','APEI','ARCE','ASPU','ATGE','CHGG','CLEU','EDTK','GHC','GPX','HLG','HMHC','LAUR','LINC','LOPE','LRN','METX','PRDO','REDU','STRA','TEDU','TWOU','UTI','VSTA','VTRU','WAFU','ZVO',],
                        'Farm Products': ['ADM','AGFS','ALCO','AQB','AVO','BG','CALM','CRESY','FDP','LMNR','PME','SANW','TSN','VFF','VITL',],
                        'Food Distribution': ['ANDE','CHEF','CORE','HFFG','PFGC','SPTN','SYY','UNFI','USFD','WILC',],
                        'Grocery Stores': ['ACI','CASY','GO','IFMK','IMKTA','KR','NGVC','SFM','VLGEA','WMK',],
                        'Household & Personal Products': ['CHD','CL','CLX','COTY','DOGZ','EL','ELF','EPC','HELE','IPAR','KMB','MTEX','NATR','NUS','NWL','PG','REV','SPB','SUMR','TANH','UG','USNA',],
                        'Packaged Foods': ['BGS','BRBR','BRID','BYND','CAG','CENT','CENTA','CLXT','CPB','CVGW','CYAN','DAR','DTEA','FAMI','FARM','FLO','FREE','FRPT','GIS','HAIN','HLF','HRL','INGR','JBSS','JJSF','JVA','K','KHC','LANC','LFVN','LNDC','LW','LWAY','MGPI','MKC','NAII','NUZE','PETZ','PLIN','POST','PPC','RELV','RIBT','SAFM','SENEA','SENEB','SJM','SMPL','STKL','THS','TWNK',],
                        'Tobacco': ['MO','PM','TPB','UVV','VGR',],
                        'Oil & Gas Drilling': ['HP','NBR','PTEN','RIG',],
                        'Oil & Gas E&P': ['APA','AR','AXAS','BCEI','BRY','CDEV','CLMT','CLR','CNX','COG','COP','CRC','CRK','CXO','DMLP','DVN','EOG','EPM','EPSN','EQT','ESTE','FANG','FLMN','GDP','HES','HPK','KOS','MCEP','MCF','MGY','MNRL','MRO','MTDR','MUR','NEXT','OVV','OXY','PDCE','PE','PNRG','PVAC','PXD','RRC','SM','SNDE','SWN','TALO','TELL','TGA','TRCH','USEG','WLL','WPX','WTI','XEC',],
                        'Oil & Gas Equipment & Services': ['AROC','BKR','BOOM','CCLP','CHX','CKH','DNOW','DRQ','DWSN','EXTN','FI','FTI','GEOS','GIFI','HAL','HLX','KLXE','LBRT','MARPS','MRC','MTRX','NCSM','NESR','NEX','NOV','NR','OII','OIS','PFIE','PUMP','RCON','RES','RNET','SLB','SLCA','SND','SOI','TDW','TH','TUSK','VTOL','WHD','WTTR',],
                        'Oil & Gas Integrated': ['AE','CVX','NFG','TOT','XOM',],
                        'Oil & Gas Midstream': ['ALTM','AM','BKEP','BROG','DHT','DSSI','ETRN','FRO','GLNG','GMLP','GPP','KMI','LNG','LPG','MMLP','NBLX','OKE','OMP','OSG','RTLR','STNG','TRGP','TRMD','USWS','VNOM','WMB',],
                        'Oil & Gas Refining & Marketing': ['AMTX','CLNE','CVI','DK','HFC','INT','MPC','PARR','PBF','PEIX','PSX','REGI','REX','VLO','VTNR','VVV',],
                        'Thermal Coal': ['ARCH','ARLP','BTU','CEIX','HNRG','NC',],
                        'Uranium': ['UEC','UUUU',],
                        'Asset Management': ['AMG','AMK','AMP','APAM','APO','ARES','BCOR','BEN','BLK','BSIG','CCAP','CG','CNS','CPTA','CSWC','DHIL','EV','FHI','GROW','HCAP','HLNE','HNNA','HRZN','ICMB','IVZ','KKR','LGHL','NEWT','NMFC','NTRS','PHCF','PUYI','PZN','SAMG','SCU','SEIC','SFE','STEP','STT','SWKH','TROW','VCTR','VRTS','WDR','WETF',],
                        'Banks—Diversified': ['BAC','C','EWBC','JPM','NTB','WFC',],
                        'Banks—Regional': ['ABCB','ABTX','ACBI','ACNB','ALRS','ALTA','AMAL','AMNB','AMRB','AMTB','AMTBB','AROW','ASB','ASRV','ATLO','AUB','AUBN','AX','BANC','BANF','BANR','BCBP','BCML','BCOW','BDGE','BFC','BFIN','BFST','BHB','BHLB','BKSC','BKU','BLX','BMRC','BMTC','BOCH','BOH','BOKF','BOTJ','BPFH','BPOP','BPRN','BRKL','BSBK','BSRR','BSVN','BUSE','BWB','BWFG','BXS','BY','BYFC','CAC','CADE','CALB','CARV','CASH','CATC','CATY','CBAN','CBFV','CBMB','CBNK','CBSH','CBTX','CBU','CCB','CCBG','CCNE','CFB','CFBI','CFBK','CFFI','CFFN','CFG','CFR','CHCO','CHMG','CIT','CIVB','CIZN','CLBK','CLDB','CMA','CNBKA','CNNB','CNOB','COFS','COLB','CPF','CSTR','CTBI','CUBI','CVBF','CVCY','CVLY','CWBC','CZNC','CZWI','DCOM','EBC','EBMT','EBSB','EBTC','EFSC','EGBN','EMCF','EQBK','ESBK','ESQ','ESSA','ESXB','EVBN','FBC','FBIZ','FBK','FBMS','FBNC','FBP','FBSS','FCAP','FCBC','FCBP','FCCO','FCCY','FCF','FCNCA','FDBC','FFBC','FFBW','FFIC','FFIN','FFNW','FFWM','FGBI','FHB','FHN','FIBK','FISI','FITB','FLIC','FMAO','FMBH','FMBI','FMNB','FNB','FNCB','FNLC','FNWB','FRAF','FRBA','FRBK','FRC','FRME','FSBW','FSEA','FSFG','FULT','FUNC','FUSB','FVCB','FXNC','GABC','GBCI','GCBC','GFED','GGAL','GLBZ','GNTY','GSBC','GWB','HAFC','HBAN','HBCP','HBMD','HBNC','HBT','HFBL','HFWA','HIFS','HMNF','HMST','HOMB','HONE','HOPE','HTBI','HTBK','HTH','HTLF','HVBC','HWBK','HWC','IBCP','IBOC','IBTX','ICBK','INBK','INDB','IROQ','ISBC','ISTR','KEY','KFFB','KRNY','LARK','LBAI','LBC','LCNB','LEVL','LKFN','LMST','LOB','LSBK','MBCN','MBIN','MBWM','MCB','MCBC','MCBS','MFNC','MGYR','MLVF','MNSB','MOFG','MPB','MRBK','MSBI','MSVB','MTB','MVBF','MYFW','NBHC','NBN','NBTB','NCBS','NFBK','NKSH','NRIM','NWBI','NWFL','NYCB','OBNK','OCFC','OFED','OFG','ONB','OPBK','OPHC','OPOF','ORRF','OSBC','OVBC','OVLY','OZK','PACW','PB','PBCT','PBFS','PBHC','PBIP','PCB','PCSB','PDLB','PEBK','PEBO','PFBC','PFBI','PFC','PFHD','PFIS','PFS','PGC','PKBK','PLBC','PMBC','PNBK','PNC','PNFP','PPBI','PRK','PROV','PTRS','PVBC','PWOD','QCRH','RBB','RBCAA','RBKB','RBNC','RF','RIVE','RMBI','RNDB','RNST','RRBI','RVSB','SAL','SASR','SBCF','SBFG','SBNY','SBSI','SBT','SFBC','SFBS','SFNC','SFST','SHBI','SI','SIVB','SLCT','SMBC','SMBK','SMMF','SNV','SONA','SPFI','SRCE','SSB','SSBI','STBA','STL','STND','STXB','SVBI','SYBT','TBBK','TBK','TBNK','TCBI','TCBK','TCF','TCFC','TFC','TFSL','THFF','TMP','TOWN','TRMK','TRST','TSBK','TSC','UBCP','UBFO','UBOH','UBSI','UCBI','UMBF','UMPQ','UNB','UNTY','USB','UVSP','VBFC','VBTX','VLY','WABC','WAFD','WAL','WASH','WBS','WNEB','WSBC','WSBF','WSFS','WTBA','WTFC','WVFC','ZION',],
                        'Capital Markets': ['AC','AMRK','ATIF','BGCP','COWN','DFIN','EVR','FOCS','FRHC','FUTU','GBL','GHL','GS','HGBL','HLI','HUSN','IBKR','JRJC','LAZ','LPLA','MARA','MC','MFH','MKTX','MS','NHLD','OPY','PIPR','PJT','RJF','SCHW','SF','SIEB','SNEX','TIGR','TW','VIRT','WHG','XP',],
                        'Credit Services': ['ADS','AGM','AIHS','ALLY','ATLC','AXP','CACC','COF','CPSS','CURO','DFS','ENVA','EZPW','FCFS','GDOT','HX','LC','LMFA','LX','LYL','MA','MFIN','MGI','MRLN','NAVI','NICK','NNI','OMF','OPRT','PRAA','PT','PYPL','QIWI','RM','SC','SGOC','SLM','SNFCA','SYF','V','WRLD','WU',],
                        'Financial Conglomerates': ['JEF','RILY','VOYA',],
                        'Financial Data & Stock Exchanges': ['CBOE','CME','FDS','ICE','MCO','MORN','MSCI','NDAQ','SPGI','VALU',],
                        'Insurance Brokers': ['AJG','AON','BRO','BRP','CRD-A','CRVL','EHTH','ERIE','FANH','GOCO','HUIZ','MMC','WLTW',],
                        'Insurance—Diversified': ['ACGL','AIG','ANAT','ATH','BRK-A','BRK-B','EQH','ESGR','GSHD','HIG','IGIC','ORI','PFG','WTRE',],
                        'Insurance—Life': ['AAME','AEL','AFL','BHF','CIA','CNO','FFG','GL','GNW','GWGH','IHC','LNC','MET','NWLI','PRI','PRU','UNM','VERY',],
                        'Insurance—Property & Casualty': ['AFG','ALL','ARGO','AXS','CB','CINF','CNA','CNFR','DGICA','FNHC','GBLI','HALL','HCI','HMN','HRTG','KINS','KMPR','KNSL','L','LMND','MCY','MKL','NGHC','NMIH','NODK','NSEC','PGR','PIH','PLMR','PRA','PTVCA','PTVCB','RLI','ROOT','SAFT','SG','SIGI','STC','STFC','THG','TRV','UFCS','UIHC','UNAM','UVE','WRB','WTM','Y',],
                        'Insurance—Reinsurance': ['GLRE','MHLD','OXBR','RE','RGA','RNR','TPRE',],
                        'Insurance—Specialty': ['AGO','AIZ','AMBC','AMSF','EIG','FAF','FNF','ICCH','ITIC','JRVR','MBI','MTG','PROS','RDN','TIG','TIPT','TRUP',],
                        'Mortgage Finance': ['ASPS','ATAX','COOP','ECPG','EFC','ESNT','MMAC','PFSI','RKT','TREE','WD',],
                        'Shell Companies': ['AACQ','ACAM','ACEV','AGBA','ALAC','AMCI','AMHC','ANDA','APXT','ARYA','BCTG','BLSA','BRLI','BRPA','CGRO','CHPM','CIIC','CRSA','DFHT','DFPH','ERES','ESSC','ETAC','EXPC','FIII','FSDC','FSRV','GHIV','GNRS','GRCY','GRNV','GRSV','GXGX','HCAC','HEC','HLXA','HSAQ','HYAC','LACQ','LATN','LCA','LFAC','LIVK','LOAC','LPRO','LSAC','MCAC','MCMJ','MLAC','MNCL','NBAC','NHIC','NOVS','NPA','OPES','PSAC','PTAC','RACA','ROCH','SAMA','SMMC','SRAC','SSPK','TDAC','THBR','THCA','THCB','TOTA','TZAC','VMAC','ZGYH',],
                        'Biotechnology': ['ABEO','ABIO','ABUS','ACAD','ACER','ACET','ACHV','ACIU','ACOR','ACRS','ACST','ADAP','ADIL','ADMA','ADPT','ADTX','ADVM','ADXN','ADXS','AEZS','AFMD','AGEN','AGIO','AGLE','AGTC','AIKI','AKBA','AKRO','AKTX','AKUS','ALBO','ALDX','ALEC','ALGS','ALKS','ALLK','ALLO','ALNA','ALNY','ALPN','ALRN','ALT','ALVR','ALXN','ALXO','AMRN','AMTI','ANAB','ANCN','ANIK','ANNX','ANPC','APLS','APLT','APM','APOP','APRE','APTO','APTX','APVO','AQST','ARAV','ARCT','ARDS','ARDX','ARGX','ARNA','ARPO','ARQT','ARVN','ARWR','ASLN','ASMB','ASND','ATHA','ATHE','ATHX','ATOS','ATRA','ATXI','AUPH','AUTL','AVEO','AVIR','AVRO','AVXL','AXLA','AXSM','AYLA','AZRX','BBI','BBIO','BCDA','BCEL','BCLI','BCRX','BCYC','BDSI','BDTX','BEAM','BFRA','BGNE','BHVN','BIVI','BLCM','BLI','BLPH','BLRX','BLU','BLUE','BMRN','BNTC','BNTX','BPMC','BPTH','BTAI','BVXV','BXRX','BYSI','CABA','CALA','CAPR','CARA','CASI','CATB','CBAY','CBIO','CBLI','CBMG','CBPO','CCCC','CCXI','CDAK','CDMO','CDTX','CDXC','CDXS','CERC','CERE','CERS','CFRX','CGEN','CGIX','CHMA','CHRS','CKPT','CLBS','CLDX','CLGN','CLLS','CLRB','CLSD','CLSN','CLVS','CMPI','CMRX','CNCE','CNSP','CNST','COCP','COGT','CORT','CPRX','CRBP','CRDF','CRIS','CRMD','CRNX','CRSP','CRTX','CRVS','CSBR','CTIC','CTMX','CTXR','CUE','CVAC','CVM','CWBR','CYAD','CYCC','CYCN','CYTK','DARE','DBVT','DCPH','DFFN','DMAC','DNLI','DRNA','DTIL','DVAX','DYAI','DYN','EARS','EDIT','EDSA','EIDX','EIGR','ELOX','ENLV','ENOB','ENTA','ENTX','EPIX','EPZM','EQ','ERYP','ESPR','ETNB','ETON','ETTX','EVFM','EVGN','EVLO','EXEL','EYEG','EYEN','FATE','FBIO','FBRX','FENC','FGEN','FHTX','FIXX','FMTX','FOLD','FPRX','FREQ','FRLN','FULC','FUSN','FWP','GALT','GBIO','GBT','GERN','GLMD','GLPG','GLTO','GLYC','GMAB','GMDA','GNCA','GNFT','GNPX','GOSS','GOVX','GRAY','GRTS','GRTX','GTHX','HALO','HARP','HCM','HEPA','HGEN','HOOK','HOTH','HRMY','HRTX','HSTO','HTBX','IBIO','ICCC','ICPT','IDRA','IDYA','IFRX','IGMS','IMAB','IMGN','IMMP','IMNM','IMRA','IMRN','IMTX','IMUX','IMV','IMVT','INBX','INCY','INFI','INMB','INO','INSM','INVA','INZY','IONS','IOVA','IPHA','ISEE','ITCI','ITOS','ITRM','JAGX','JAZZ','JNCE','KALA','KALV','KDMN','KLDO','KNSA','KOD','KPTI','KRON','KROS','KRTX','KRYS','KTOV','KTRA','KURA','KYMR','KZIA','KZR','LEGN','LGND','LIFE','LJPC','LMNL','LOGC','LPCN','LPTX','LQDA','LRMR','LTRN','LUMO','LXRX','LYRA','MACK','MBIO','MBRX','MCRB','MDGL','MDNA','MDWD','MEIP','MESO','MGEN','MGNX','MGTA','MGTX','MIRM','MIST','MITO','MLND','MNKD','MNOV','MNPR','MOR','MORF','MREO','MRKR','MRNA','MRNS','MRSN','MRTX','MRUS','MTCR','MTEM','MTP','NBIX','NBRV','NBSE','NCNA','NERV','NGM','NK','NKTR','NKTX','NMTR','NOVN','NRBO','NRIX','NSTG','NTLA','NVAX','NVIV','NVUS','NXTC','NYMX','OBSV','OCGN','OCUL','OCX','ODT','OMER','ONCS','ONCT','ONCY','ONTX','OPNT','ORGS','ORIC','ORMP','ORPH','ORTX','OSMT','OTIC','OTLK','OVID','OYST','PAND','PASG','PBLA','PBYI','PCVX','PDLI','PDSB','PGEN','PHAS','PHAT','PHIO','PIRS','PLRX','PMVP','PRAX','PRLD','PROG','PRQR','PRTA','PRTK','PRVB','PRVL','PSTI','PSTV','PSTX','PTCT','PTE','PTGX','PTI','PULM','QLGN','QURE','RAPT','RARE','RCKT','RCUS','REGN','REPL','RETA','RFL','RGLS','RGNX','RIGL','RLAY','RNA','RPRX','RPTX','RUBY','RVMD','RVNC','RYTM','SAGE','SAVA','SBBP','SCPH','SEEL','SELB','SESN','SGEN','SGMO','SIGA','SIOX','SLGL','SLN','SLRX','SLS','SMMT','SNCA','SNDX','SNGX','SNSS','SONN','SPPI','SPRB','SPRO','SRNE','SRPT','SRRA','SRRK','STOK','STRO','STSA','STTK','SURF','SVA','SVRA','SWTX','SYBX','SYRS','TARA','TBIO','TBPH','TCON','TCRR','TECH','TENX','TGTX','TLC','TLSA','TNXP','TPTX','TRIL','TRVI','TRVN','TSHA','TTNP','TYME','UBX','URGN','UROV','UTHR','VBIV','VBLT','VCEL','VCNX','VCYT','VERU','VIE','VIR','VKTX','VNDA','VRCA','VRNA','VRTX','VSTM','VTGN','VTVT','VXRT','VYGR','VYNE','WINT','XBIO','XBIT','XCUR','XENE','XERS','XFOR','XLRN','XNCR','XOMA','XTLB','YMAB','ZEAL','ZGNX','ZIOP','ZLAB','ZNTL','ZSAN',],
                        'Diagnostics & Research': ['A','AKU','ANIX','ARA','AWH','AXDX','BASI','BEAT','BIOC','BMRA','BNGO','BNR','BWAY','CDNA','CELC','CEMI','CHEK','CNTG','CODX','CRL','CSTL','DGX','DHR','DMTK','DRIO','DXCM','ENZ','EXAS','FLDM','FLGT','GENE','GH','GTH','HSKA','HTGM','ICLR','IDXG','IDXX','ILMN','IQV','LH','LNTH','MEDP','MOTS','MTD','MYGN','NDRA','NEO','NEOG','NRC','NTRA','NVTA','ONVO','OPGN','OPK','OXFD','PACB','PKI','PMD','PRAH','PRPO','PSNL','QDEL','QGEN','QTNT','RDNT','RNLX','SLNO','SRDX','STIM','SYNH','TMO','TRIB','TTOO','TWST','VIVO','VNRX','WAT','XGN',],
                        'Drug Manufacturers—General': ['ABBV','AMGN','AZN','BIIB','BMY','GILD','GRFS','GWPH','HZNP','JNJ','LLY','MRK','NVS','PFE','SNY',],
                        'Drug Manufacturers—Specialty & Generic': ['ACRX','ADMP','ADMS','AERI','AGRX','ALIM','AMPH','AMRX','AMYT','ANIP','APHA','ASRT','ATNX','AVDL','CALT','CGC','COLL','CPIX','CRON','CTLT','DRRX','EBS','EGRX','ELAN','ENDP','EOLS','EVOK','FLXN','GHSI','HAPP','HROW','HUGE','IRWD','KIN','KMDA','LCI','NEOS','NEPT','NLTX','OGI','OPTN','ORGO','PAHC','PCRX','PETQ','PLXP','PPD','PRFX','PRGO','PRPH','RDHL','RDUS','REPH','RLMD','RMTI','SCYX','SLDB','SNDL','SNOA','SUPN','SXTC','TCDA','THTX','TLGT','TLRY','TXMD','TYHT','ZTS','ZYNE',],
                        'Health Information Services': ['ACCD','CERN','CHNG','CPSI','CVET','EVH','GDRX','HCAT','HMSY','HQY','HSTM','ICAD','INOV','KERN','MDRX','MTBC','NH','NXGN','OMCL','ONEM','OPRX','PGNY','PHR','PINC','RCM','SDGR','SLP','STRM','SY','TDOC','TRHC','TXG','VEEV','WORX','ZCMD',],
                        'Healthcare Plans': ['ANTM','CI','CNC','CVS','GTS','HUM','MGLN','MOH','UNH',],
                        'Medical Care Facilities': ['ACHC','ADUS','AIH','AMED','AMEH','AMN','AVCO','BKD','CHE','CMPS','CYH','DVA','EHC','ENSG','FVE','HCA','HCSG','HNGR','IMAC','JYNT','LHCG','MD','NHC','OPCH','OSH','OTRK','PNTG','PRSC','SEM','SGRY','THC','TVTY','UHS','USPH',],
                        'Medical Devices': ['ABMD','ABT','AEMD','AFIB','AHCO','AHPI','ALGN','APEN','APYX','ARAY','ATEC','AVGR','AVNS','AXGN','AXNX','AZYO','BIO','BIOL','BRKR','BSGM','BSX','CFMS','CHFS','CLPT','CNMD','CRY','CSII','CTSO','CUTR','DCTH','DRAD','DYNT','EAR','EDAP','ELMD','ESTA','EW','EYES','FONR','GMED','GNMK','HJLI','HSDT','IART','INGN','INMD','INSP','IRIX','IRMD','ITGR','ITMR','IVC','KIDS','LIVN','LNSR','LUNG','MDGS','MDT','MDXG','MSON','NAOV','NARI','NNOX','NTUS','NUVA','NVCN','NVRO','OBLN','OFIX','OM','PAVM','PEN','PODD','PROF','QTRX','RCEL','RWLK','SDC','SIBN','SIEN','SILK','SINT','SOLY','SPNE','SRGA','SRTS','SSKN','SWAV','SYK','TCMD','TELA','THMO','TMDI','TMDX','TNDM','VAPO','VERO','VIVE','VMD','VRAY','VREX','XAIR','XENT','ZBH','ZYXI',],
                        'Medical Distribution': ['ABC','CAH','GEC','HSIC','MCK','OMI','PBH','PDCO',],
                        'Medical Instruments & Supplies': ['AKER','ANGO','ATRC','ATRI','ATRS','BAX','BDX','BLFS','CMD','COO','ECOR','EKSO','GKOS','HAE','HBIO','HOLX','HRC','ICUI','IIN','INFU','IRTC','ISRG','KRMD','LMAT','LMNX','MASI','MBOT','MLSS','MMSI','NEPH','NURO','NVCR','NVST','OSUR','PDEX','PLSE','POAI','RGEN','RMD','RVP','STAA','STE','STXS','TFX','UTMD','VAR','WST','XRAY',],
                        'Pharmaceutical Retailers': ['BIMI','CJJD','GNLN','MEDS','PETS','RAD','WBA','YI',],
                        'Aerospace & Defense': ['AAXN','AIR','AJRD','ASTC','ATRO','AVAV','BA','BWXT','CODA','CUB','DCO','EH','ESLT','HEI','HEI-A','HII','HXL','ISSC','IVAC','KAMN','KTOS','LHX','LMT','MOG-A','MRCY','NOC','NPK','PKE','POWW','RADA','RGR','RTX','SPCE','SPR','SWBI','TATT','TDG','TGI','TXT','VEC','VSEC','VTSI','WWD',],
                        'Airlines': ['AAL','ALGT','ALK','CPA','DAL','HA','JBLU','LUV','MESA','RYAAY','SAVE','SKYW','UAL',],
                        'Airports & Air Services': ['AAWW','MIC','OMAB',],
                        'Building Products & Equipment': ['AAON','APOG','APT','ASPN','AWI','AZEK','BECN','BLDR','BMCH','CARR','CNR','CSL','CSTE','DOOR','FRTA','GMS','IBP','JELD','LPX','MAS','NX','OC','PGTI','PPIH','ROCK','SSD','TGLS','TREX','WMS',],
                        'Business Equipment & Supplies': ['ACCO','AVY','CATM','EBF','HNI','KNL','PBI','SCS','VRTV',],
                        'Conglomerates': ['IEP','MATW','NNBR','OBCI','SEB','STCN','TRC',],
                        'Consulting Services': ['BAH','CRAI','EFX','EXPO','FC','FCN','FORR','GRNQ','HURN','ICFI','INFO','NLSN','RGP','TRU','VRSK',],
                        'Electrical Equipment & Parts': ['AEIS','APWC','AYI','AZZ','BDC','BE','BMI','CBAT','EAF','ENR','ENS','FCEL','FLUX','HOLI','HUBB','IPWR','KE','LTBR','NVT','OESX','OPTT','PLPC','PLUG','POLA','POWL','PPSI','RFIL','VRT','WIRE',],
                        'Engineering & Construction': ['ACM','AEGN','AGX','AMRC','APG','ATCX','BBCP','BLD','DRTT','DY','EME','ENG','FIX','FLR','GLDD','GVA','IEA','IESC','J','JCI','KBR','LMB','MTZ','MYRG','NVEE','PRIM','PWR','RCMT','ROAD','STRL','TPC','TTEK','WLDN',],
                        'Farm & Heavy Construction Machinery': ['AGCO','ALG','ARTW','ASTE','CAT','CMCO','DE','GENC','HY','LNN','MNTX','MTW','NAV','OSK','PCAR','REVG','SHYF','TEX','WNC',],
                        'Industrial Distribution': ['AIT','DXPE','EVI','FAST','FBM','GWW','HBP','HDS','HWCC','LAWS','MSM','PKOH','SITE','SYX','TITN','TRNS','WCC','WSO',],
                        'Infrastructure Operations': ['ACA',],
                        'Integrated Freight & Logistics': ['AIRT','ATSG','CHRW','CYRX','ECHO','EXPD','FDX','FWRD','HUBG','JBHT','LSTR','RLGT','SINO','UPS','XPO',],
                        'Marine Shipping': ['ASC','CMRE','CPLP','CTRM','EDRY','EGLE','ESEA','GASS','GNK','GOGL','GRIN','INSW','KEX','MATX','NAT','NMCI','PANL','PSHG','PXS','SALT','SB','SBLK','SFL','SHIP','TOPS',],
                        'Metal Fabrication': ['ATI','CRS','HAYN','HIHO','IIIN','MEC','MLI','NWPX','PRLB','RYI','SGBX','VMI','WOR',],
                        'Pollution & Treatment Controls': ['ADES','AQUA','BHTG','CECE','CLIR','CLWT','ERII','FSS','FTEK','LIQT','NEWA',],
                        'Railroads': ['CSX','FSTR','GBX','KSU','NSC','RAIL','TRN','UNP','WAB',],
                        'Rental & Leasing Services': ['AL','ALTG','CAI','CAR','FPAY','GATX','GFN','HEES','HRI','HYRE','MGRC','NSCO','R','RCII','TGH','TRTN','UHAL','URI','WLFC','WSC',],
                        'Security & Protection Services': ['ADT','ALLE','APDN','ARLO','BCO','BKYI','BRC','CIX','DGLY','MAGS','MG','MSA','NL','NSSC','NXTD','REZI','SPCB','VRME','VRRM','VVNT',],
                        'Specialty Business Services': ['ABM','ACTG','ALJJ','BV','CASS','CBZ','CLCT','CPRT','CTAS','DLHC','GPN','IAA','KODK','MMS','OMEX','PAE','PAYS','PFMT','PFSW','PRGX','QUAD','SGRP','SP','SRT','TISI','UNF','VVI','WHLM',],
                        'Specialty Industrial Machinery': ['AIMC','AME','AMSC','AOS','ARNC','ATKR','B','BLDP','BWEN','CFX','CIR','CMI','CPST','CR','CSWI','CVV','CW','DCI','DOV','EMR','EPAC','ETN','FELE','FLOW','FLS','GE','GGG','GHM','GNRC','GRC','GTEC','GTES','GTLS','HI','HLIO','HON','HSC','HURC','HWM','IEX','IR','ITT','ITW','JBT','KAI','KRNT','LDL','LII','LXFR','MIDD','MMM','MWA','NDSN','NPO','OFLX','OTIS','PH','PNR','PSN','RAVN','RBC','ROK','ROP','RXN','SPXC','SXI','TAYD','THR','TNC','TPIC','TRS','TT','TWIN','ULBI','WBT','WTS','XONE','XYL',],
                        'Staffing & Employment Services': ['ADP','ASGN','BBSI','BGSF','CCRN','DHX','HHR','HQI','HSII','HSON','IPDN','JOBS','KELYA','KELYB','KFRC','KFY','MAN','MHH','NSP','PAYX','PIXY','RHI','STAF','TBI','TNET','UPWK',],
                        'Tools & Accessories': ['EML','GFF','KMT','LECO','PFIN','ROLL','SNA','SWK','TBLT','TKR','TTC',],
                        'Trucking': ['ARCB','CVLG','DSKE','HTLD','KNX','MRTN','ODFL','PATI','PTSI','SAIA','SNDR','ULH','USAK','USX','WERN','YRCW',],
                        'Waste Management': ['AQMS','CCNC','CLH','CVA','CWST','ECOL','HCCI','JAN','PESI','QRHC','RSG','SMED','SRCL','WM',],
                        'REIT—Diversified': ['AAT','AFIN','AHH','ALEX','CLNC','CLNY','CLPR','CORR','EPRT','ESRT','GOOD','LXP','MDRR','OLP','PINE','PSB','SAFE','SRC','STAR','STOR','UE','VER','VICI','WPC',],
                        'REIT—Healthcare Facilities': ['CHCT','CTRE','DHC','DOC','GEO','GMRE','HR','HTA','LTC','MPW','NHI','OHI','PEAK','SBRA','UHT','VTR','WELL',],
                        'REIT—Hotel & Motel': ['APLE','CLDT','CPLG','DRH','FCPT','HST','HT','INN','PEB','PK','RHP','RLJ','SHO','SOHO','SVC','XHR',],
                        'REIT—Industrial': ['COLD','CUBE','DRE','EGP','EXR','FR','IIPR','ILPT','LAND','LSI','MNR','NSA','PLD','PLYM','PSA','QTS','REXR','SELF','STAG','TRNO',],
                        'REIT—Mortgage': ['ABR','ACRE','AGNC','AJX','ANH','ARI','ARR','BRMK','BXMT','CHMI','CIM','CMO','DX','EARN','GPMT','IVR','KREF','LADR','LOAN','MFA','NLY','NRZ','NYMT','ORC','PMT','RC','RWT','STWD','TRMT','TRTX','TWO','WMC',],
                        'REIT—Office': ['ARE','BDN','BXP','CIO','CLI','CMCT','COR','CUZ','CXP','DEA','DEI','DLR','EQC','FSP','GNL','HIW','HPP','JBGS','KRC','OFC','OPI','PDM','PGRE','SLG','VNO','WRE',],
                        'REIT—Residential': ['ACC','AIV','AMH','APTS','AVB','BRG','BRT','CPT','ELS','EQR','ESS','INVH','IRET','IRT','MAA','NXRT','RESI','SNR','SUI','UDR','UMH',],
                        'REIT—Retail': ['ADC','AKR','ALX','BFS','BPYU','BRX','EPR','FRT','GTY','KIM','KRG','MAC','NNN','O','REG','ROIC','RPAI','RPT','RVI','SITC','SKT','SPG','SRG','TCO','UBA','WHLR','WRI','WSR',],
                        'REIT—Specialty': ['AMT','CCI','CONE','CTT','CXW','EQIX','FPI','GLPI','HASI','IRM','LAMR','OUT','PCH','RYN','SBAC','UNIT',],
                        'Real Estate Services': ['BPY','CBRE','CIGI','CSGP','CWK','DUO','EXPI','FRPH','FSV','FTHM','GYRO','IRCP','JLL','KW','LMRK','MAYS','MMI','NMRK','OBAS','QK','RDFN','RLGY','RMAX','RMR','TCI',],
                        'Real Estate—Development': ['ARL','CTO','FOR','GRIF','HCDI','HGSH','MLP',],
                        'Real Estate—Diversified': ['CHCI','HHC','JOE','STRS',],
                        'Communication Equipment': ['ACIA','ADTN','AUDC','AVNW','BOSC','BOXL','CAMP','CASA','CIEN','CLFD','CLRO','CMBM','CMTL','COMM','CRNT','CSCO','DGII','DZSI','ERIC','EXFO','EXTR','FEIM','GILT','HLIT','HPE','INFN','INSG','ITI','ITRN','JCS','JNPR','KN','KVHI','LITE','LTRX','MAXR','MSI','NTGR','OCC','PCTI','PI','PLT','PWFL','SATS','SILC','SONM','SWIR','SYTA','TCCO','TESS','UI','UTSI','VCRA','VIAV','VISL','VSAT','ZBRA',],
                        'Computer Hardware': ['ALOT','ANET','CAN','CRSR','DAKT','DDD','DELL','EBON','HPQ','INVE','KTCC','LOGI','MICT','NNDM','NTAP','OSS','PSTG','QMCO','SCKT','SMCI','SSYS','STX','TACT','VJET','WDC',],
                        'Consumer Electronics': ['AAPL','GPRO','HBB','HEAR','IRBT','KOSS','MWK','SNE','SONO','UEIC','VIOT','VOXX','VUZI',],
                        'Electronic Components': ['AMOT','APH','BELFA','BELFB','BHE','CPSH','CTS','DAIO','DSWL','ELTK','FLEX','FN','GLW','IEC','IMTE','JBL','KOPN','LFUS','LPTH','LYTS','MEI','NEON','NSYS','OSIS','PLXS','REFR','RELL','ROG','SANM','SGMA','SMTX','TEL','TTMI','VICR',],
                        'Electronics & Computer Distribution': ['AEY','ARW','AVT','CNXN','SCSC','TAIT','WSTG',],
                        'Information Technology Services': ['ACN','ALYA','AMRH','AVCT','BR','CACI','CCRC','CD','CDW','CLGX','CLPS','CNDT','CSPI','CTG','CTSH','CXDO','DMRC','DNB','DXC','EPAM','EXLS','FIS','FISV','FLT','FORTY','G','GDS','GDYN','GLG','HCKT','IBM','IMXI','INOD','IT','JKHY','LDOS','NCR','NSIT','PRFT','PRSP','PRTH','RAMP','RSSS','SABR','SAIC','SGLB','SNX','SWCH','SYKE','TDC','TTEC','UIS','USIO','VNET','VRTU','XRX',],
                        'Scientific & Technical Instruments': ['BNSO','CGNX','COHR','CYBE','ELSE','ESE','FARO','FIT','FLIR','FTV','GNSS','GRMN','IIVI','ISNS','ITRI','KEYS','LUNA','MIND','MKSI','MLAB','MTSC','MVIS','NOVT','PRCP','SMIT','ST','TDY','TRMB','VNT','VPG','WATT','WRAP',],
                        'Semiconductor Equipment & Materials': ['ACLS','ACMR','AEHR','AMAT','AMBA','ASML','ASYS','ATOM','AXTI','BRKS','CAMT','CCMP','COHU','ENTG','ICHR','IPGP','KLAC','KLIC','LRCX','NVMI','OLED','PLAB','RBCN','TER','UCTT','VECO','XPER',],
                        'Semiconductors': ['AAOI','ADI','ALGM','AMD','AMKR','AOSL','AVGO','CEVA','CREE','CRUS','DIOD','DSPG','EMKR','FORM','GSIT','HIMX','IMOS','INTC','IPHI','LASR','LEDS','LSCC','MCHP','MOSY','MPWR','MRAM','MRVL','MTSI','MU','MXIM','MXL','NPTN','NVDA','NVEC','NXPI','OIIM','ON','ONTO','POWI','PXLW','QCOM','QRVO','QUIK','RESN','RMBS','SGH','SIMO','SITM','SLAB','SMTC','SWKS','SYNA','TSEM','TSM','TXN','VSH','WISA','XLNX',],
                        'Software—Application': ['ABST','ADSK','AEYE','AGMH','AGYS','ALRM','AMST','AMSWA','ANSS','ANY','API','APPF','APPS','ASUR','AVLR','AVYA','AWRE','AYX','AZPN','BCOV','BIGC','BILL','BLKB','BNFT','BRQS','BSQR','BSY','BTBT','CALX','CDAY','CDK','CDNS','CLDR','COUP','CPAH','CREX','CRM','CRNC','CSOD','CTXS','CVLT','DBD','DCT','DDOG','DOCU','DOMO','DSGX','DT','DUOT','EB','EBIX','ECOM','EGAN','EGHT','EGOV','EIGI','ENV','ESTC','EVBG','EVOL','FICO','FROG','FSLY','FTFT','GLOB','GSUM','GTYH','GVP','GWRE','HUBS','IBEX','IDEX','IDN','IMMR','INPX','INS','INTU','INTZ','JAMF','JFU','JG','KBNT','KC','LPSN','LYFT','MANH','MANT','MCFE','MDLA','MGIC','MITK','MNDO','MODN','MOGO','MRIN','MSTR','MTC','MTLS','MYSZ','NATI','NCNO','NICE','NOW','NTWK','NUAN','OLB','OSPN','OTEX','PAR','PAYC','PBTS','PCTY','PCYG','PD','PDFS','PEGA','PHUN','PLUS','PRGS','PRO','PS','PTC','QADA','QADB','QTWO','QUMU','RDVT','RIOT','RMNI','RNG','RP','RPD','SEAC','SHOP','SHSP','SMAR','SMSI','SNCR','SPNS','SPRT','SPT','SREV','SSNC','SSNT','SSTI','STMP','STNE','SVMK','TEAM','TNAV','TSRI','TTD','TYL','UBER','UPLD','VERB','VERX','WDAY','WK','WORK','WTRH','XELA','ZEN','ZI',],
                        'Software—Infrastructure': ['ACIW','ADBE','AKAM','ALLT','ALTR','APPN','ATEN','BAND','BKI','BL','BLIN','BOX','CETX','CHKP','CLSK','CRWD','CSGS','CYBR','CYRN','DBX','DOX','DTSS','EEFT','EPAY','EVOP','EVTC','FEYE','FFIV','FIVN','FTNT','GDDY','GSKY','IIIV','JCOM','LLNW','MDB','MIME','MSFT','NET','NETE','NEWR','NLOK','NTCT','NTNX','OKTA','OPRA','ORCL','PANW','PFPT','PING','PLAN','QLYS','RDWR','REKR','RPAY','RXT','SAIL','SCWX','SFET','SNPS','SPLK','SPSC','SQ','SWI','SYNC','TAOP','TCX','TENB','TLND','UEPS','USAT','VERI','VHC','VMW','VRNS','VRNT','VRSN','WEX','WIX','YEXT','ZIXI','ZS','ZUO',],
                        'Solar': ['ARRY','BEEM','CSIQ','ENPH','FSLR','MAXN','NOVA','PECK','RUN','SEDG','SPI','SPWR','SUNW','VVPR',],
                        'Utilities—Diversified': ['AES','ALE','AVA','BKH','D','ETR','EXC','FE','MGEE','NWE','OEG','OTTR','PEG','SJI','SRE','UTL',],
                        'Utilities—Independent Power Producers': ['AT','NRG','VST',],
                        'Utilities—Regulated Electric': ['AEE','AEP','AGR','CMS','DTE','DUK','ED','EIX','ES','EVRG','GNE','HE','IDA','LNT','NEE','OGE','PCG','PNM','PNW','POR','PPL','SO','SPKE','WEC','XEL',],
                        'Utilities—Regulated Gas': ['ATO','BIPC','CNP','CPK','NFE','NI','NJR','NWN','OGS','RGCO','SR','SWX','UGI',],
                        'Utilities—Regulated Water': ['ARTNA','AWK','AWR','CDZI','CWCO','CWT','GWRS','MSEX','PCYO','PICO','SJW','WTRG','YORW',],
                        'Utilities—Renewable': ['AY','CREG','CWEN','CWEN-A','ORA',],}

# group_desc_dist
group_desc_dict = {'All': f"All unique tickers/symbols included in this app",
                   'Basic Materials': f"Companies engaged in the discovery, development, and processing of raw materials, which are used across a broad range of sectors and industries.",
                   'Communication Services': f"A broad range of companies that sell phone and internet services via traditional landline, broadband, or wireless.",
                   'Consumer Cyclical': f"A category of stocks that rely heavily on the business cycle and economic conditions.\n\nCompanies in the consumer discretionary sector sell goods and services that are considered non-essential, such as appliances, cars, and entertainment.",
                   'Consumer Defensive': f"A category of corporations whose sales and earnings remain relatively stable during both economic upturns and downturns.\n\nFor example, companies that manufacture food, beverages, household and personal products, packaging, or tobacco. Also includes companies that provide services such as education and training services. Defensive companies tend to make products or services that are essential to consumers.\n\nCompanies that produce and sell items considered essential for everyday use.",
                   'Energy': f"Companies focused on the exploration, production, and marketing of oil, gas, and renewable resources around the world.",
                   'Financial Services': f"Companies that offer services including loans, savings, insurance, payment services, and money management for individuals and firms.",
                   'Healthcare': f"A broad range of companies that sell medical products and services.",
                   'Industrials': f"Companies that produce machinery, equipment, and supplies that are used in construction and manufacturing, as well as providing related services.\n\nThese companies are closely tied to the economy, and their business volume often falls sharply during recessions, though each industrial subsector often performs differently.",
                   'Technology': f"Businesses that sell goods and services in electronics, software, computers, artificial intelligence, and other industries related to information technology (IT).",
                   'Utilities': f"Companies that provide electricity, natural gas, water, sewage, and other services to homes and businesses.",
                   'Real Estate': f"Companies that allow individual investors to buy shares in real estate portfolios that receive income from a variety of properties.",
                   'Dividend Stocks (11/2020)': f"Dividend Stocks (11/2020)",
                   'Growth Stocks (11/2020)': f"Growth Stocks (11/2020)",
                   'COVID-19': f"Vaccines: 'ALT','MRNA','INO','GILD','JNJ','PFE','AZN','ARCT'<br/><br/>COVID-19 testing: 'QDEL','ABT','HOLX','DGX'<br/><br/>Cruises: 'RCL','CCL','NCLH'<br/><br/>Pet food: 'CHWY'<br/><br/>Game: 'GME'",
                   'Cyber Security': f"One of the largest recent <a href='https://en.wikipedia.org/wiki/2020_United_States_federal_government_data_breach'>hacks</a>:<br/>On 12/14/2020, the news that SWI was used by Russia to back the U.S. governments went public.<br/>SWI tumbled and other cyber security firms soared because of the heightened need for years to come.<br/><br/>CRWD, CYBR, FEYE, PANW, ZS ... all jumped big within 2 weeks.",
                   '5G': f"5G wireless networks",
                   'Innovation': "https://ark-invest.com/",
                   'ETF': f"Exchange-traded fund (ETF) is a basket of securities that trade on an exchange. Unlike mutual funds (which only trade once a day after the market closes), ETF is just like a stock and share prices fluctuate all day as the ETF is bought and sold.\n\nExchange-traded note (ETN) is a basket of unsecured debt securities that track an underlying index of securities and trade on a major exchange like a stock.\n\nDifference: Investing ETF is investing in a fund that holds the asset it tracks. That asset may be stocks, bonds, gold or other commodities, or futures contracts. In contrast, ETN is more like a bond. It's an unsecured debt note issued by an institution. If the underwriter (usually a bank) were to go bankrupt, the investor would risk a total default.",
                   'ETF database': f"https://nasdaqtrader.com/",
                   'Major Market Indexes': f"https://www.investing.com/indices/major-indices",
                   'Non-US World Market Indexes': f"FTSE (Financial Times Stock Exchange) 100 Index is a share index of the 100 companies listed on the London Stock Exchange with the highest market capitalisation.",
                   'DOW 30': f"Dow Jones Industrial Average 30 Components",
                   'NASDAQ 100': f"A stock market index made up of 103 equity securities issued by 100 of the largest non-financial companies listed on the Nasdaq stock market.\n\nThe complete index, NASDAQ Composite (COMP), has 2,667 securities as of February 2020.\n\nBecause the index is weighted by market capitalization, the index is rather top-heavy. In fact, the top 10 stocks in the Nasdaq Composite account for one-third of the index’s performance.",
                   'S&P 500': f"A stock market index that measures the stock performance of 500 large companies listed on stock exchanges in the United States.\n\nIndex funds that track the S&P 500 have been recommended as investments by Warren Buffett, Burton Malkiel, and John C. Bogle for investors with long time horizons.",
                   'NASDAQ Composite': f"https://en.wikipedia.org/wiki/NASDAQ_Composite",
                   'Russell 1000': f"The Russell 1000 Index, a subset of the Russell 3000 Index, represents the 1000 top companies by market capitalization in the United States.\n\nThe Russell 1000 index comprises approximately 92% of the total market capitalization of all listed stocks in the U.S. equity market and is considered a bellwether index for large-cap investing.\n\nNote: Russell 3000 = Russell 1000 (large cap) + Russell 2000 (small cap)",
                   'Russell 2000': f"The Russell 2000 Index, a subset of the Russell 3000 Index, includes ~2,000 smallest-cap American companies in the Russell 3000 Index.",
                   'Russell 3000': f"The Russell 3000 Index, a market-capitalization-weighted equity index maintained by FTSE Russell, provides exposure to the entire U.S. stock market and represents about 98% of all U.S incorporated equity securities.\n\nRussell 3000 = Russell 1000 (larger cap) + Russell 2000 (smaller cap).",
                   'Equity database': f"https://nasdaqtrader.com/",
                   'Volatility': f"<a href='https://www.investopedia.com/articles/active-trading/070213/tracking-volatility-how-vix-calculated.asp'>https://www.investopedia.com/articles/active-trading/070213/tracking-volatility-how-vix-calculated.asp</a>",
                   'Treasury Yield': f"<a href='https://www.treasury.gov/resource-center/data-chart-center/interest-rates/Pages/TextView.aspx?data=yield'>https://www.treasury.gov/resource-center/data-chart-center/interest-rates/Pages/TextView.aspx?data=yield</a>",
                   'OTC Market': f"Over-the-counter Market",
                   'Others': f"Others"}

def ticker_preprocessing():
    global ticker_group_dict
    global subgroup_group_dict
    global ticker_subgroup_dict

    # make sure ticker_group_dict has everything
    for group in subgroup_group_dict.keys():
        for subgroup in subgroup_group_dict[group]:
            for ticker in ticker_subgroup_dict[subgroup]:
                if not ticker in ticker_group_dict[group]:
                    ticker_group_dict[group].append(ticker)

    # make the ticker elements unique and sorted in ticker_group_dict
    for group in ticker_group_dict.keys():
        ticker_group_dict[group] = sorted(list(set(ticker_group_dict[group])))

    ticker_group_dict['All'] = sorted(list(set([item for sublist in ticker_group_dict.values() for item in sublist])))

    # make sure subgroup_group_dict is complete
    for group in ticker_group_dict.keys():
        if not group in subgroup_group_dict.keys():
            subgroup_group_dict[group] = []

    subgroup_group_dict['All'] = sorted(list(set([item for sublist in subgroup_group_dict.values() for item in sublist])))

    for group in subgroup_group_dict.keys():
        subgroup_group_dict[group] = sorted(subgroup_group_dict[group])
        subgroup_group_dict[group].insert(0, 'All')

ticker_preprocessing()

###########################################################################################

class Ticker(object):
    def __init__(self, ticker=None, ticker_data_dict=None, last_date=None, keep_up_to_date=False):
        """
        if keep_up_to_date = True ==> try to download the lastest data so it's as new as today
        """
        if ticker is None:
            if ticker_data_dict is None:
                raise ValueError('error')
            else:
                self.ticker_data_dict = ticker_data_dict
                self.ticker = ticker_data_dict['ticker']
        else:
            if ticker_data_dict is None:
                from ._data import get_ticker_data_dict
                self.ticker = ticker
                self.ticker_data_dict = get_ticker_data_dict(ticker=self.ticker, last_date=last_date, keep_up_to_date=keep_up_to_date, download_today_data=True)
            else:
                self.ticker_data_dict = ticker_data_dict
                self.ticker = ticker_data_dict['ticker']

    @property
    def nasdaq_listed(self):
        df = nasdaqlisted_df[ nasdaqlisted_df['ticker'] == self.ticker ]
        n_len = len(df)
        if n_len == 0:
            return False
        elif n_len == 1:
            return True
        else:
            raise ValueError(f'self.ticker = {self.ticker}, n_len should not be >1')

    @property
    def nasdaq_security_name(self):
        if self.nasdaq_listed:
            sn = nasdaqlisted_df[ nasdaqlisted_df['ticker'] == self.ticker ]['Security Name'].iloc[0]
            return sn
        else:
            raise ValueError("this question should be asked for NASDAQ-listed ticker only")

    @property
    def nasdaq_market_category(self):
        if self.nasdaq_listed:
            mc = nasdaqlisted_df[ nasdaqlisted_df['ticker'] == self.ticker ]['Market Category'].iloc[0]
            mc_dict = {'Q': 'NASDAQ Global Select MarketSM', 'G': 'NASDAQ Global MarketSM', 'S': 'NASDAQ Capital Market'}
            return mc_dict[mc]
        else:
            raise ValueError("this question should be asked for NASDAQ-listed ticker only")

    @property
    def nasdaq_financial_status(self):
        if self.nasdaq_listed:
            fs = nasdaqlisted_df[ nasdaqlisted_df['ticker'] == self.ticker ]['Financial Status'].iloc[0]
            fs_dict = {'D': 'Deficient: Issuer Failed to Meet NASDAQ Continued Listing Requirements',
                       'E': 'Delinquent: Issuer Missed Regulatory Filing Deadline',
                       'Q': 'Bankrupt: Issuer Has Filed for Bankruptcy',
                       'N': 'Normal', # NOT Deficient, Delinquent, or Bankrupt.',
                       'G': 'Deficient and Bankrupt',
                       'H': 'Deficient and Delinquent',
                       'J': 'Delinquent and Bankrupt',
                       'K': 'Deficient, Delinquent, and Bankrupt',}
            return fs_dict[fs]
        else:
            raise ValueError("this question should be asked for NASDAQ-listed ticker only")

    @property
    def nasdaq_etf(self):
        if self.nasdaq_listed:
            etf = nasdaqlisted_df[ nasdaqlisted_df['ticker'] == self.ticker ]['ETF'].iloc[0]
            if etf == 'Y':
                return True
            elif etf == 'N':
                return False
            else:
                raise ValueError('unexpected ETF answer')
        else:
            raise ValueError("this question should be asked for NASDAQ-listed ticker only")

    @property
    def non_nasdaq_listed(self):
        df = otherlisted_df[ otherlisted_df['ticker'] == self.ticker ]
        n_len = len(df)
        if n_len == 0:
            return False
        elif n_len == 1:
            return True
        else:
            raise ValueError(f'self.ticker = {self.ticker}, n_len should not be >1')

    @property
    def non_nasdaq_security_name(self):
        if self.non_nasdaq_listed:
            sn = otherlisted_df[ otherlisted_df['ticker'] == self.ticker ]['Security Name'].iloc[0]
            return sn
        else:
            raise ValueError("this question should be asked for non-NASDAQ-listed ticker only")

    @property
    def non_nasdaq_exchange(self):
        if self.non_nasdaq_listed:
            ex = otherlisted_df[ otherlisted_df['ticker'] == self.ticker ]['Exchange'].iloc[0]
            ex_dict = {'A': 'NYSE MKT',
                       'N': 'New York Stock Exchange (NYSE)',
                       'P': 'NYSE ARCA',
                       'Z': 'BATS Global Markets (BATS)',
                       'V': 'Investors\' Exchange, LLC (IEXG)'}
            return ex_dict[ex]
        else:
            raise ValueError("this question should be asked for non-NASDAQ-listed ticker only")

    @property
    def non_nasdaq_etf(self):
        if self.non_nasdaq_listed:
            etf = otherlisted_df[ otherlisted_df['ticker'] == self.ticker ]['ETF'].iloc[0]
            if etf == 'Y':
                return True
            elif etf == 'N':
                return False
            else:
                raise ValueError('unexpected ETF answer')
        else:
            raise ValueError("this question should be asked for non-NASDAQ-listed ticker only")

    @property
    def is_etf(self):
        if (self.ticker in ticker_group_dict['ETF']) or (self.ticker in ticker_group_dict['ETF database']):
            return True
        else:
            return False
        
    @property
    def in_dow30(self):
        if self.ticker in ticker_group_dict['DOW 30']:
            return True
        else:
            return False

    @property
    def in_nasdaq100(self):
        if self.ticker in ticker_group_dict['NASDAQ 100']:
            return True
        else:
            return False

    @property
    def in_sandp500(self):
        if self.ticker in ticker_group_dict['S&P 500']:
            return True
        else:
            return False

    @property
    def in_russell1000(self):
        if self.ticker in ticker_group_dict['Russell 1000']:
            return True
        else:
            return False

    @property
    def in_russell2000(self):
        if self.ticker in ticker_group_dict['Russell 2000']:
            return True
        else:
            return False

    @property
    def in_russell3000(self):
        if self.ticker in ticker_group_dict['Russell 3000']:
            return True
        else:
            return False

    @property
    def in_nasdaq_composite(self):
        if self.ticker in ticker_group_dict['NASDAQ Composite']:
            return True
        else:
            return False       

    @property
    def symbol(self):
        if 'symbol' in self.ticker_info.keys():
            return self.ticker_info['symbol']
        else:
            return None

    @property
    def name(self):
        if self.longName is not None:
            return self.longName
        elif self.shortName is not None:
            return self.shortName
        else:
            return None

    @property
    def shortName(self):
        if 'shortName' in self.ticker_info.keys():
            return self.ticker_info['shortName']
        else:
            return None

    @property
    def longName(self):
        if 'longName' in self.ticker_info.keys():
            return self.ticker_info['longName']
        else:
            return None

    @property
    def longBusinessSummary(self):
        if 'longBusinessSummary' in self.ticker_info.keys():
            return self.ticker_info['longBusinessSummary']
        else:
            return None

    @property
    def logo(self):
        if 'logo' in self.ticker_info.keys():
            return self.ticker_info['logo']
        else:
            return None

    @property
    def options(self):
        return self.ticker_data_dict['options']

    def option_chain(self, expiration_date: str = None):
        if 'option_chain_dict' in self.ticker_data_dict.keys():
            return self.ticker_data_dict['option_chain_dict'][expiration_date]
        else:
            return None

    @property
    def recommendations(self):
        if self.ticker_data_dict['recommendations'] is not None:
            return self.ticker_data_dict['recommendations'].reset_index(level=0)
        else:
            return None

    @property
    def ticker_info(self):
        return self.ticker_data_dict['info']

    @property
    def ticker_history(self):
        return self.ticker_data_dict['history']

    @property
    def last_date(self):
        return self.ticker_history['Date'].iloc[-1]

    @property
    def last_date_dayname(self):
        return day_name[self.last_date.weekday()]
        
    @property
    def last_close_price(self):
        return self.ticker_history['Close'].iloc[-1]

    def nearest_actual_date(self, target_date):
        idx = self.ticker_history['Date'].searchsorted(target_date)
        return self.ticker_history['Date'].iloc[idx]

    def close_price_on_date(self, target_date):
        max_idx = len(self.ticker_history) - 1
        idx = min( self.ticker_history['Date'].searchsorted(target_date), max_idx ) # if the date is beyond all available dates, idx could be max_idx+1
        #df = self.ticker_history[self.ticker_history['Date'] == target_date]
        #if len(df) != 1:
        #    raise ValueError('not exactly 1 match here')
        return float(self.ticker_history['Close'].iloc[idx]), self.ticker_history['Date'].iloc[idx]

    def key_value(self, this_key):
        if this_key is not None:
            if self.ticker_info is not None:
                if this_key in self.ticker_info.keys():
                    if self.ticker_info[this_key] is not None:
                        return round(self.ticker_info[this_key],7)
        return None

    @property
    def price_target(self):
        if 'price_target' in self.ticker_data_dict.keys():
            return self.ticker_data_dict['price_target']
        else:
            return None

    @property
    def price_target_upside_pct(self):
        if self.price_target is None:
            return None
        else:
            return 100 * (self.price_target - self.last_close_price) / self.last_close_price

    @property
    def prob_price_target_upside(self):
        if self.price_target_upside_pct is not None: 
            return sigmoid(self.price_target_upside_pct/100)
        return None

    @property
    def last_1yr_dividends_pct(self):
        if self.pay_dividends:
            if 'trailingAnnualDividendYield' in self.ticker_info.keys() and self.ticker_info['trailingAnnualDividendYield'] is not None:
                return self.ticker_info['trailingAnnualDividendYield'] * 100
            else:
                dividends_df = self.ticker_data_dict['dividends'].reset_index(level=0)
                dividends_df['Date'] = pd.to_datetime(dividends_df['Date'], format='%Y-%m-%d', utc=True)
                last_1yr_dividends_df = dividends_df[ dividends_df['Date'] > (datetime.now(tz=timezone.utc) - timedelta(days=365.25)) ]
                date_close_df = self.ticker_data_dict['history'][['Date','Close']]
                dividends_info_df = pd.DataFrame(columns=['date','dividends','yield_pct'])
                for idx, row in last_1yr_dividends_df.iterrows():
                    try:
                        close_price_on_this_date = float(date_close_df[date_close_df.Date == row['Date']].Close)
                        dividends_yield_percent = 100*row['Dividends']/close_price_on_this_date
                    except:
                        dividends_yield_percent = 0
                    dividends_info_df = dividends_info_df.append({'date': row['Date'].date(), 'dividends': row['Dividends'], 'yield_pct': dividends_yield_percent}, ignore_index = True)
                #print(dividends_info_df)
                if len(dividends_info_df) > 0:
                    return dividends_info_df['yield_pct'].sum()
        return 0

    @property
    def pay_dividends(self):
        if 'dividends' in self.ticker_data_dict.keys():
            dividends_df = self.ticker_data_dict['dividends'].reset_index(level=0)
            if len(dividends_df) > 0:
                return True
        return False

    @property
    def EV_to_EBITDA(self):
        """
        Enterprise value / EBITDA (earnings before interest, taxes, depreciation, and amortization.)
        The lower the better
        """
        return self.key_value('enterpriseToEbitda')

    @property
    def forwardPE(self):
        """
        Price-to-earnings ratio = Current market price per share / forwardEps
        """
        return self.key_value('forwardPE')

    @property
    def trailingPE(self):
        """
        Price-to-earnings ratio = Current market price per share / trailingEps
        """
        return self.key_value('trailingPE')

    @property
    def PEG_ratio(self):
        """
        forward PE / EPS growth (5 year)
        """
        return self.key_value('pegRatio')

    @property
    def Eps_growth_rate(self):
        """
        Yahoo! Finance, uses a five-year expected growth rate to calculate the PEG ratio.
        https://www.investopedia.com/terms/p/pegratio.asp
        https://www.nasdaq.com/market-activity/stocks/aapl/price-earnings-peg-ratios
        """
        if self.PEG_ratio is not None and self.forwardPE is not None:
            if self.PEG_ratio != 0:
                return round(self.forwardPE / self.PEG_ratio, 7)
        return None

    @property
    def forwardEps(self):
        """
        Earning per share
        """
        return self.key_value('forwardEps')

    @property
    def trailingEps(self):
        return self.key_value('trailingEps')

    @property
    def Eps_change_pct(self):
        if self.forwardEps is not None and self.trailingEps is not None:
            EPS_change_pct = 100*(self.forwardEps - self.trailingEps)/abs(self.trailingEps)
            return EPS_change_pct
        return None

    @property
    def prob_Eps_change_pct(self):
        if self.Eps_change_pct is not None:
            return sigmoid(self.Eps_change_pct/100)
        return None

    @property
    def RSI(self):
        from ._indicator import momentum_indicator
        return momentum_indicator().RSI(close_price = self.ticker_history['Close'])
