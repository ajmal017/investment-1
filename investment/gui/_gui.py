# -*- coding: utf-8 -*-

#  Author: Investment Prediction Enthusiast <investment.ml.prediction@gmail.com>
#
#  License: LGPL-3.0

import sys

import matplotlib
#print(matplotlib.rcsetup.interactive_bk)
#print(matplotlib.rcsetup.non_interactive_bk)
#print(matplotlib.rcsetup.all_backends)

# non_interactive_bk, for example: AGG (http://antigrain.com/) backend is for writing to file, not for rendering in a window. Thus, it's a headless framework.
if matplotlib.get_backend() not in matplotlib.rcsetup.non_interactive_bk: 
    matplotlib.use('Qt5Agg') # backend

import PySide2
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile
from urllib.parse import urlparse

from PySide2.QtWidgets import QApplication
from PySide2.QtWidgets import QMainWindow, QWidget, QAction
from PySide2.QtWidgets import QGridLayout
from PySide2.QtWidgets import QComboBox, QCheckBox, QCompleter
from PySide2.QtWidgets import QTextEdit, QLineEdit, QTextBrowser
from PySide2.QtWidgets import QCalendarWidget
from PySide2.QtWidgets import QPushButton, QLabel, QProgressBar
from PySide2.QtWidgets import QDialog, QToolBar
from PySide2.QtGui import QFontDatabase, QTextDocument
from PySide2 import QtCore
from PySide2.QtCore import Qt, QThread, Signal, QUrl, QSortFilterProxyModel

import copy

import pathlib
from os.path import join

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
import matplotlib.pyplot as plt

from datetime import date, datetime, timedelta, timezone

from ..data import Ticker, get_ticker_data_dict, get_formatted_ticker_data, momentum_indicator, volume_indicator, moving_average, ticker_group_dict, subgroup_group_dict, ticker_subgroup_dict, group_desc_dict, global_data_root_dir, nasdaqlisted_df, otherlisted_df

import numpy as np
import pandas as pd

from matplotlib.widgets import Cursor

import time

import random

StyleSheet = '''
#ProgressBar {
    text-align: center;
    border-radius: 5px;
    border: 1px solid #009688;
}
#ProgressBar::chunk {
    background-color: #009688;
}
'''

App_name = "Investment"

# https://stackoverflow.com/questions/35894171/redirect-qdebug-output-to-file-with-pyqt5
def qt_message_handler(mode, context, message):
    if mode == QtCore.QtInfoMsg:
        mode = 'INFO'
    elif mode == QtCore.QtWarningMsg:
        mode = 'WARNING'
    elif mode == QtCore.QtCriticalMsg:
        mode = 'CRITICAL'
    elif mode == QtCore.QtFatalMsg:
        mode = 'FATAL'
    else:
        mode = 'DEBUG'
    #print('>>> qt_message_handler: line: %d, func: %s(), file: %s' % (context.line, context.function, context.file))
    #print('>>>   %s: %s\n' % (mode, message))

#QtCore.qInstallMessageHandler(qt_message_handler)
#QtCore.qDebug('<<qDebug init>>')

from matplotlib.dates import num2date
from matplotlib.ticker import Formatter
# https://matplotlib.org/gallery/ticks_and_spines/date_index_formatter.html
class DateFormatter(Formatter):
    def __init__(self, dates):
        self.dates = dates

    def __call__(self, x, pos=0):
        ind = int(np.round(x))
        if ind >= len(self.dates) or ind < 0:
            return None
        #print(f"x = {x}, ind = {ind}")#" date = {num2date(self.dates[ind]).strftime(self.fmt)}")
        np_datetime64 = self.dates[ind]
        return np.datetime_as_string(np_datetime64, unit='M') # if unit='D' -> '2020-12-30'
        #return num2date(self.dates[ind]).strftime(self.fmt)

# https://stackoverflow.com/questions/4827207/how-do-i-filter-the-pyqt-qcombobox-items-based-on-the-text-input
class ExtendedComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMaxVisibleItems(50)
        #self.setFocusPolicy(Qt.StrongFocus)
        self.setEditable(True)

        # add a filter model to filter matching items
        self.pFilterModel = QSortFilterProxyModel(self)
        self.pFilterModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.pFilterModel.setSourceModel(self.model())

        # add a completer, which uses the filter model
        self.completer = QCompleter(self.pFilterModel, self)
        # always show all (filtered) completions
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCompleter(self.completer)

        # connect signals
        self.lineEdit().textEdited.connect(self.pFilterModel.setFilterFixedString)
        self.completer.activated.connect(self.on_completer_activated)

    # on selection of an item from the completer, select the corresponding item from combobox 
    def on_completer_activated(self, text):
        #print(f"debugging - completer activated: [{text}]")
        if text:
            index = self.findText(text)
            self.setCurrentIndex(index)
            self.activated[str].emit(self.itemText(index))

    # not sure if this function is ever called
    # on model change, update the models of the filter and completer as well 
    #def setModel(self, model):
    #    print(f"debugging - model change. model = {model}")
    #    super().setModel(model)
    #    self.pFilterModel.setSourceModel(model)
    #    self.completer.setModel(self.pFilterModel)

    # not sure if this function is ever called
    # on model column change, update the model column of the filter and completer as well
    #def setModelColumn(self, column):
    #    print(f"debugging - model col change. model col = {column}")
    #    self.completer.setCompletionColumn(column)
    #    self.pFilterModel.setFilterKeyColumn(column)
    #    super().setModelColumn(column)  



# references: 
# https://matplotlib.org/api/widgets_api.html
# https://matplotlib.org/3.3.0/gallery/misc/cursor_demo.html
# https://matplotlib.org/users/event_handling.html
class SnappingCursor(Cursor):
    def __init__(self, plotline=None, actual_x_data=None, x_index=None, y_data=None, name=None, UI=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if plotline is None:
            self.x, self.y = x_index, y_data
            self.actual_x_data = actual_x_data
            self.use_x_index = True
        else:
            self.x, self.y = plotline.get_data()
            self.actual_x_data = None
            self.use_x_index = False
        dy = (self.y.max() - self.y.min()) / self.y.size
        self.y_grad = np.gradient(self.y, dy, edge_order=2)
        self._last_index = None
        self.name = name
        self.UI = UI

    def onmove(self, event):
        if event.inaxes:
            if type(event.xdata) == np.float64:

                if self.use_x_index:
                    index = min(np.searchsorted(self.x, event.xdata), len(self.x)-1)
                else:
                    x_datetime = datetime(1970,1,1,tzinfo=timezone.utc) + timedelta(days=event.xdata)
                    index = min(np.searchsorted(self.x, pd.to_datetime(x_datetime, utc=True)), len(self.x)-1) # np.datetime64() is used to be congruent with self.x
                    
                if index == self._last_index:
                    return  # still on the same data point. Nothing to do.

                self._last_index = index
                event.xdata = self.x[index]
                event.ydata = self.y[index]
                event.ydata_grad = self.y_grad[index]

                if self.use_x_index:
                    text_str = f"{pd.to_datetime(self.actual_x_data[index], utc=True).date()}, {event.ydata:.2f}, slope={event.ydata_grad:.2f}"
                else:
                    text_str = f"{pd.to_datetime(event.xdata, utc=True).date()}, {event.ydata:.2f}, slope={event.ydata_grad:.2f}"

                if self.name == 'ticker_canvas_cursor':
                    self.UI.ticker_canvas_coord_label.setText(text_str)
                if self.name == 'index_canvas_cursor':
                    self.UI.index_canvas_coord_label.setText(text_str)

            super().onmove(event)


# reference: https://matplotlib.org/faq/usage_faq.html
class canvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=6.0, height=3.0, dpi=72, UI=None, tight_layout=True, *args, **kwargs):
        self.figure = plt.figure(figsize=(width, height), dpi=dpi, tight_layout=tight_layout, *args, **kwargs)
        self.axes = self.figure.add_subplot(111)
        self.axes.tick_params(axis='both', which='major', labelsize=10.0)
        self.axes.tick_params(axis='both', which='minor', labelsize=8.0)
        super().__init__(self.figure)
        self.dragging = False
        self._UI = UI

    def button_pressed(self, event):
        if event.inaxes:
            if type(event.xdata) == np.float64:
                self.dragging = True
                self.original_x_datetime = datetime(1970,1,1,tzinfo=timezone.utc) + timedelta(days=event.xdata)
                self.original_time_last_date = self._UI.control.time_last_date
                self.time_diff = timedelta(0)

    def button_released(self, event):
        self.dragging = False
        self._UI.control.time_last_date = self.original_time_last_date - self.time_diff
        self._UI.control._ticker_lastdate_dialog_any_button_clicked()

    def onmove(self, event):
        if event.inaxes:
            if self.dragging:
                if type(event.xdata) == np.float64:
                    self.time_diff = datetime(1970,1,1,tzinfo=timezone.utc) + timedelta(days=event.xdata) - self.original_x_datetime
                    #self._UI.control.time_last_date = self.original_time_last_date - self.time_diff
                    #self._UI.control._ticker_lastdate_dialog_any_button_clicked()

class ticker_selection(ExtendedComboBox):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.setFixedWidth(parent.app_window.width*0.12)
        self.reset()
    
    def reset(self):
        self.clear()
        self.addItem("-- Select or enter a ticker --")
        self.setFocusPolicy(Qt.ClickFocus)


class group_selection(QComboBox):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.setFixedWidth(parent.app_window.width*0.12)
        self.reset()

    def reset(self):
        self.addItem("-- Select a sector or ticker group --")
        self.groups = list(ticker_group_dict.keys())
        for group in self.groups:
            self.addItem(group)


class subgroup_selection(QComboBox):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.setFixedWidth(parent.app_window.width*0.12)
        self.reset()

    def reset(self):
        self.clear()
        self.addItem("-- Select an industry or ticker subgroup --")


class index_selection(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self.clear()
        self.addItem("-- Select an index --")


class ticker_timeframe_selection(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self.clear()
        self.addItem("-- Select a ticker canvas time frame --")


class ticker_lastdate_pushbutton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self.setText("Select a last date on the timeline")
        self.setEnabled(False)


class ticker_download_latest_data_from_yfinance_pushbutton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self.setText("Download latest data from the Internet")
        self.setEnabled(False)

            
class ticker_lastdate_calendar(QCalendarWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSelectedDate(date.today())
        self.currentPageChanged.connect(self._current_page_changed)
    def _current_page_changed(self, year, month):
        self.setCurrentPage(year, month)


class ticker_lastdate_calendar_dialog(QDialog):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.setWindowTitle("Select a last date on the timeline")
        self.ticker_lastdate_calendar_use_last_available_date_button = QPushButton('Use the last available date in the data')
        self.ticker_lastdate_calendar = ticker_lastdate_calendar()
        self.ticker_lastdate_calendar_dialog_ok_button = QPushButton('Done')
        self.layout = QGridLayout()
        self.layout.addWidget(self.ticker_lastdate_calendar_use_last_available_date_button, 0, 0)
        self.layout.addWidget(self.ticker_lastdate_calendar, 1, 0)
        self.layout.addWidget(self.ticker_lastdate_calendar_dialog_ok_button, 2, 0)
        self.setLayout(self.layout)


class message_dialog(QDialog):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.setWindowTitle("Message Box")
        self.textinfo = textinfo()
        self.textinfo_ok_button = QPushButton('Ok')
        self.layout = QGridLayout()
        self.layout.addWidget(self.textinfo, 0, 0)
        self.layout.addWidget(self.textinfo_ok_button, 1, 0)
        self.setLayout(self.layout)


class index_canvas_options(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self.clear()
        self.addItem("-- Select an index canvas option --")


class textinfo(QTextBrowser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.setAcceptRichText(True)
        self.setOpenExternalLinks(True)
        #self.setCurrentFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))


from ..__about__ import (
    __version__,
    __license__,
)

class about_dialog(QDialog):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.setWindowTitle(f"About {App_name}")
        self.aboutText = QLabel(parent=self)
        self.aboutText.setTextFormat(Qt.RichText)
        self.aboutText.setText(f"This App provides an UI to help with investment.<br/><br/>Version: {__version__}<br/>License: {__license__}<br/>PyPI: <a href=\"https://pypi.org/project/investment/\">https://pypi.org/project/investment/</a>")
        self.aboutText.setOpenExternalLinks(True)
        self.close_button = QPushButton('Close', parent=self)
        self.layout = QGridLayout()
        self.layout.addWidget(self.aboutText, 0, 0)
        self.layout.addWidget(self.close_button, 1, 0)
        self.setLayout(self.layout)
        self.close_button.clicked.connect(self._close_button_clicked)

    def _close_button_clicked(self):
        self.hide()


class preferences_dialog(QDialog):
    def __init__(self, parent=None, force_redownload_yfinance_data = None, download_today_data = None, data_root_dir = None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.setWindowTitle("Preference Settings")
        self.checkbox_force_redownload_yfinance_data = QCheckBox("When viewing an individual ticker's history data, do not use any existing cache but download latest data from the Internet ?", parent=self)
        self.checkbox_download_today_data = QCheckBox("When downloading latest data from the Internet, include today's data (which may be incomplete if market still opens) ?", parent=self)
        self.checkbox_overlap_fear_green_index_data = QCheckBox("Overlap the ticker plot on top of CNN's Fear && Greed Index", parent=self)
        self.label_data_root_dir = QLabel(parent=self)
        self.data_root_dir = data_root_dir
        self.label_data_root_dir.setText(f"Directory to store cache data: <span style=\"color:blue\">{data_root_dir}</span>")
        self.label_data_root_dir.setTextFormat(Qt.RichText)
        self.force_redownload_yfinance_data = force_redownload_yfinance_data
        self.download_today_data = download_today_data
        self.checkbox_force_redownload_yfinance_data.setChecked(self.force_redownload_yfinance_data)            
        self.checkbox_force_redownload_yfinance_data.stateChanged.connect(self._checkbox_force_redownload_yfinance_data_state_changed)
        self.checkbox_download_today_data.setChecked(self.download_today_data)
        self.checkbox_overlap_fear_green_index_data.setChecked(True)
        self.checkbox_download_today_data.stateChanged.connect(self._checkbox_download_today_data_state_changed)
        self.close_button = QPushButton('Close', parent=self)
        self.layout = QGridLayout()
        self.layout.addWidget(self.checkbox_force_redownload_yfinance_data, 0, 0)
        self.layout.addWidget(self.checkbox_download_today_data, 1, 0)
        self.layout.addWidget(self.checkbox_overlap_fear_green_index_data, 2, 0)
        self.layout.addWidget(self.label_data_root_dir, 3, 0)
        self.layout.addWidget(self.close_button, 4, 0)
        self.setLayout(self.layout)
        self.close_button.clicked.connect(self._close_button_clicked)

    def _checkbox_force_redownload_yfinance_data_state_changed(self):
        self.force_redownload_yfinance_data = self.checkbox_force_redownload_yfinance_data.isChecked()

    def _checkbox_download_today_data_state_changed(self):
        self.download_today_data = self.checkbox_download_today_data.isChecked()

    def _close_button_clicked(self):
        self.hide()


# reference: https://pythonpyqt.com/pyqt-progressbar/
class ticker_download_thread(QThread):
    _signal = Signal(int, str)
    def __init__(self, app_window=None, smart_redownload=None, tickers_to_download=[], ascending=True):
        super().__init__()
        self.app_window = app_window
        self.smart_redownload = smart_redownload
        self.tickers_to_download = tickers_to_download
        self.ascending = ascending

    def run(self):
        if self.ascending:
            tickers_to_download = self.tickers_to_download
        else:
            tickers_to_download = self.tickers_to_download[::-1]
        for idx, ticker in enumerate(tickers_to_download):
            try:
                #time.sleep(0.001)
                get_ticker_data_dict(ticker = ticker, force_redownload = True, smart_redownload = self.smart_redownload, download_today_data = self.app_window.app_menu.preferences_dialog.download_today_data, data_root_dir = self.app_window.app_menu.preferences_dialog.data_root_dir, auto_retry = True)
            except:
                print(f"Warning: Unable to download this ticker = {ticker}")
            self._signal.emit(idx+1, ticker)


class ticker_analyze_for_dividends_thread(QThread):
    _signal = Signal(pd.DataFrame)
    def __init__(self, app_window=None, tickers_to_analyze=[]):
        super().__init__()
        self.app_window = app_window
        self.tickers_to_analyze = tickers_to_analyze
    def run(self):
        df = pd.DataFrame(columns=['ticker','recent 1-year dividends (%)'])
        #tickers = ticker_group_dict['All']
        #tickers = ['MSM', 'T', 'LUMN', 'CAT']
        #tickers = ['HCHC', 'SPRT', 'NLOK', 'QRTEA', 'QRTEB', 'LORL', 'AIV', 'FF', 'VRS', 'IRCP', 'DHT', 'AM', 'OMP', 'FRO', 'ICMB', 'TRTX', 'BXG', 'CLWT', 'PATI', 'IVR', 'OMF', 'MFA', 'CSWC', 'ORC', 'IEP', 'VHC', 'MSM', 'ARI', 'NGVC', 'NHTC', 'RC', 'ACRE', 'GEO', 'CIM', 'NLY', 'EARN', 'STWD', 'EQC', 'MNDO', 'BKEP', 'RTLR', 'TLYS', 'TRMD', 'AFIN', 'DMLP', 'ANH', 'CHMI', 'NAT', 'HRZN', 'SSNT', 'OKE', 'AGNC', 'DX', 'EFC', 'ABR', 'HVT', 'OLP', 'CCAP', 'SFL', 'NBLX', 'MARPS', 'ETRN', 'GNL', 'SNDR', 'CMO', 'KREF', 'BXMT', 'CPLP', 'NEWT', 'MNRL', 'HT', 'BPY', 'EV', 'BPYU', 'ITIC', 'NCMI', 'GMLP', 'NMFC', 'APAM', 'TWO', 'XLE', 'AJX', 'PMT', 'AMRK', 'ARR', 'PKE', 'LOAN', 'BGS', 'WMB', 'MAC', 'HIHO', 'GOOD', 'VNO', 'GPP', 'BRG', 'AROC', 'PLYM', 'OPI', 'CNA', 'UNIT', 'FCAU', 'BRMK', 'VGR', 'HP', 'SBRA', 'BLX', 'SFE', 'UVV', 'MO', 'SOHO', 'HCAP', 'RGR', 'OHI', 'SPKE', 'CLNY', 'WDR', 'FHI', 'LMRK', 'NYMT', 'ISSC', 'APTS', 'SNR', 'DHIL', 'WSBF', 'FLMN', 'TOT', 'SYX', 'BRT', 'XOM', 'AMSF', 'FFG', 'CRWS', 'PK', 'PZN', 'QIWI', 'CIO', 'NPK', 'BKE', 'SRC', 'NRZ', 'CPLG', 'NVEC', 'WSR', 'LADR', 'KMI', 'NYCB', 'NHI', 'IIIN', 'GMRE', 'NAVI', 'SKT', 'NWBI', 'FSP', 'ATAX', 'NTB', 'BDN', 'ALX', 'HRB', 'CTO', 'T', ]
        for ticker in self.tickers_to_analyze:
            df = df.append({'ticker': ticker, 'recent 1-year dividends (%)': round(Ticker(ticker).last_1yr_dividends_pct,2)}, ignore_index=True)
        df = df.sort_values(by=['recent 1-year dividends (%)'], ascending=False)
        df = df[ df['recent 1-year dividends (%)'] > 0 ].reset_index().drop(['index'],axis=1)
        self._signal.emit(df)


class dialog_with_textbrowser(QDialog):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.app_window = parent
        self.resize(self.app_window.width*0.3, self.app_window.height*0.5)
        self.textbox = QTextBrowser(parent=self)
        self.layout = QGridLayout()
        self.layout.addWidget(self.textbox, 0, 0)
        self.setLayout(self.layout)
        self.textbox.setReadOnly(True)
        self.textbox.setAcceptRichText(True)
        self.textbox.setOpenExternalLinks(True)

class fed_funds_rate_dialog(dialog_with_textbrowser):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.setWindowTitle("Federal Funds Rate")
        self.textbox.setHtml("<a href='https://www.investopedia.com/terms/f/federalfundsrate.asp#citation-7'>Explanation</a><br/><br/><a href='https://www.federalreserve.gov/monetarypolicy/openmarket.htm'>FOMC's target federal funds rate or range, change (basis points) and level</a>")

class options_dialog(dialog_with_textbrowser):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.setWindowTitle("Options")
        self.textbox.setHtml("https://www.investopedia.com/terms/o/openinterest.asp<br/>https://www.investopedia.com/articles/optioninvestor/10/sell-puts-benefit-any-market.asp<br/><a href='https://www.investopedia.com/terms/o/option.asp'>https://www.investopedia.com/terms/o/option.asp</a><br/><br/><a href='https://www.investopedia.com/articles/active-trading/040915/guide-option-trading-strategies-beginners.asp'>https://www.investopedia.com/articles/active-trading/040915/guide-option-trading-strategies-beginners.asp</a><br/>Options are derivatives/contracts (1 contract = 100 shares) that give the holder/bearer the right (but not the obligation) to buy (call option) or sell (put option) an amount of underlying asset at a set price (strike price) on or before the contract expiration date.<br/><br/>Call option is like a non-refundable down-payment for a future purchase, while put option is like insurance policy limiting downside risk.<br/><br/>Use case:<br/>1. buy calls: hedge against stock price going up.<br/>2. buy puts: hedge against stock price going down.<br/><Br/>https://www.fidelity.com/learning-center/investment-products/options/options-learning-path")

class screener_dialog(dialog_with_textbrowser):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.setWindowTitle("Screener")
        self.textbox.setHtml("<a href='https://finance.yahoo.com/options/highest-open-interest/'>Highest open interest</a><br/><br/><a href='https://www.sectorspdr.com/sectorspdr/tools/correlation-tracker/multiple-securities'>Correlation tracker</a><br/><br/><a href='https://www.marketwatch.com/story/this-year-end-stock-selling-strategy-offsets-capital-gains-taxes-and-sidesteps-the-wash-sale-rule-2020-12-04'>tax-loss selling</a>")
        
class download_data_dialog(QDialog):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.setWindowTitle("Download data and store as cache")
        self.main_label = QLabel(parent=self)
        self.group_selection_label = QLabel(parent=self)
        self.group_selection_label.setText('Ticker group(s) to download:')
        #
        self.dow30_checkbox = QCheckBox('DOW 30', parent=self)
        self.nasdaq100_checkbox = QCheckBox('NASDAQ 100', parent=self)
        self.sandp500_checkbox = QCheckBox('S&&P 500', parent=self)
        self.comp_checkbox = QCheckBox('NASDAQ Composite', parent=self)
        self.russell1k_checkbox = QCheckBox('Russell 1000', parent=self)
        self.russell2k_checkbox = QCheckBox('Russell 2000', parent=self)
        self.russell3k_checkbox = QCheckBox('Russell 3000', parent=self)
        self.etf_db_checkbox = QCheckBox('ETF database', parent=self)
        self.equity_db_checkbox = QCheckBox('Equity database', parent=self)
        #self.etf_db_checkbox.setEnabled(False)
        #self.equity_db_checkbox.setEnabled(False)
        #
        self.dow30_checkbox.setChecked(True)
        self.nasdaq100_checkbox.setChecked(True)
        self.sandp500_checkbox.setChecked(True)
        #
        self.dow30_checkbox.stateChanged.connect(self._update_download_selection)
        self.nasdaq100_checkbox.stateChanged.connect(self._update_download_selection)
        self.sandp500_checkbox.stateChanged.connect(self._update_download_selection)
        self.comp_checkbox.stateChanged.connect(self._update_download_selection)
        self.russell1k_checkbox.stateChanged.connect(self._update_download_selection)
        self.russell2k_checkbox.stateChanged.connect(self._update_download_selection)
        self.russell3k_checkbox.stateChanged.connect(self._update_download_selection)
        self.etf_db_checkbox.stateChanged.connect(self._update_download_selection)
        self.equity_db_checkbox.stateChanged.connect(self._update_download_selection)
        #
        self.options_label = QLabel('Option:', parent=self)
        self.checkbox_smart_redownload = QCheckBox('Do not re-download if exsting data are already up-to-date (as of -7d ~ now).', parent=self)
        self.checkbox_smart_redownload.stateChanged.connect(self._checkbox_smart_redownload_state_changed)
        self.download_progressbar = QProgressBar(parent=self, objectName="ProgressBar")
        self.download_button = QPushButton(parent=self)
        self.close_button = QPushButton(parent=self)
        self.layout = QGridLayout()
        self.layout.addWidget(self.main_label, 0, 0)
        self.layout.addWidget(self.group_selection_label, 1, 0)
        self.layout.addWidget(self.dow30_checkbox, 2, 0)
        self.layout.addWidget(self.nasdaq100_checkbox, 3, 0)
        self.layout.addWidget(self.sandp500_checkbox, 4, 0)
        self.layout.addWidget(self.comp_checkbox, 5, 0)
        self.layout.addWidget(self.russell1k_checkbox, 6, 0)
        self.layout.addWidget(self.russell2k_checkbox, 7, 0)
        self.layout.addWidget(self.russell3k_checkbox, 8, 0)
        self.layout.addWidget(self.etf_db_checkbox, 9, 0)
        self.layout.addWidget(self.equity_db_checkbox, 10, 0)
        self.layout.addWidget(self.options_label, 11, 0)
        self.layout.addWidget(self.checkbox_smart_redownload, 12, 0)
        self.layout.addWidget(self.download_progressbar, 13, 0)
        self.layout.addWidget(self.download_button, 14, 0)
        self.layout.addWidget(self.close_button, 15, 0)
        self.setLayout(self.layout)
        self.download_button.clicked.connect(self._download_button_clicked)
        self.close_button.clicked.connect(self._close_button_clicked)
        self.app_window = parent
        self._update_download_selection()
        #self._reset()

    def _update_download_selection(self):
        self.tickers_to_download = []
        if self.dow30_checkbox.isChecked():
            self.tickers_to_download += ticker_group_dict['DOW 30']
        if self.nasdaq100_checkbox.isChecked():
            self.tickers_to_download += ticker_group_dict['NASDAQ 100']
        if self.sandp500_checkbox.isChecked():
            self.tickers_to_download += ticker_group_dict['S&P 500']
        if self.russell1k_checkbox.isChecked():
            self.tickers_to_download += ticker_group_dict['Russell 1000']
        if self.russell2k_checkbox.isChecked():
            self.tickers_to_download += ticker_group_dict['Russell 2000']
        if self.russell3k_checkbox.isChecked():
            self.tickers_to_download += ticker_group_dict['Russell 3000']
        if self.comp_checkbox.isChecked():
            self.tickers_to_download += ticker_group_dict['NASDAQ Composite']
        if self.etf_db_checkbox.isChecked():
            self.tickers_to_download += ticker_group_dict['ETF database']
        if self.equity_db_checkbox.isChecked():
            self.tickers_to_download += ticker_group_dict['Equity database']
        self.tickers_to_download = sorted(list(set(self.tickers_to_download)))
        self.n_tickers = len(self.tickers_to_download)
        self.main_label.setText(f"Ready to download the latest data of [{self.n_tickers}] tickers and store as cache?\nNote: the data may take lots of space and the process may take hours.")
        if self.n_tickers > 0:
            self._reset()

    def _checkbox_smart_redownload_state_changed(self):
        self.smart_redownload = self.checkbox_smart_redownload.isChecked()

    def _reset(self):
        self.checkbox_smart_redownload.setChecked(True)
        self.smart_redownload = True
        self.download_progressbar.setMinimum(0)
        if self.n_tickers>0:
            self.download_progressbar.setMaximum(self.n_tickers)
        self.download_progressbar.setValue(0)
        self.download_button.setText('Yes, please download')
        self.close_button.setText('No, please skip this optional process')
        self.download_button.setEnabled(True)
        self.close_button.setEnabled(True)
        self.download_button.setDefault(True)
        self.checkbox_smart_redownload.setEnabled(True)

    def _close_button_clicked(self):
        self._reset()
        self.hide()

    def _download_button_clicked(self):
        if self.n_tickers > 0:
            #
            self.checkbox_smart_redownload.setEnabled(False)
            self.download_button.setEnabled(False)
            self.close_button.setEnabled(False)
            #
            self.download_button.setDefault(False)
            self.download_button.repaint()
            self.close_button.repaint()
            # the reason to use this ticker_thread() is because in MacOS, there is an update problem in PyQt5
            # specifically, if there is any 'external' function call, like get_ticker_data_dict(), or even time.sleep(), after 'self.download_progressbar.setValue(idx)' in the _download_this_ticker() function
            # then the download_progressbar update won't show.
            # it is like we need to remove any external function call in self.download_progressbar.setValue(idx) in the signal.connect(), in MacOS
            # to see the effect, try to uncomment the # time.sleep(0.003) statement below; you will see how unsmooth it is.
            self.thread1=ticker_download_thread(app_window=self.app_window, smart_redownload=self.smart_redownload, tickers_to_download=self.tickers_to_download, ascending=True)
            self.thread1._signal.connect(self._download_this_ticker)
            self.thread1.start()

    def _download_this_ticker(self, idx: int = None, ticker: str = None):
        self.download_progressbar.setValue(idx)
        #time.sleep(0.003)
        if idx == self.n_tickers:
            self.close_button.setText('Download completed. Return to App')
            #
            #self.checkbox_smart_redownload.setEnabled(True)
            #self.download_button.setEnabled(True)
            self.close_button.setEnabled(True)
            #
            self.download_button.setDefault(False)
            self.close_button.setDefault(True)
            self.download_button.repaint()
            self.close_button.repaint() # to cope with a bug in PyQt5


class high_dividends_dialog(QDialog):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.app_window = parent
        self.resize(self.app_window.width*0.2, self.app_window.height*0.8)
        self.label = QLabel('Ticker group(s) to analyze for dividends:', parent=self)
        #
        self.dow30_checkbox = QCheckBox('DOW 30', parent=self)
        self.nasdaq100_checkbox = QCheckBox('NASDAQ 100', parent=self)
        self.sandp500_checkbox = QCheckBox('S&&P 500', parent=self)
        self.russell1k_checkbox = QCheckBox('Russell 1000', parent=self)
        self.russell2k_checkbox = QCheckBox('Russell 2000', parent=self)
        self.russell3k_checkbox = QCheckBox('Russell 3000', parent=self)
        self.comp_checkbox = QCheckBox('NASDAQ Composite', parent=self)
        self.etf_db_checkbox = QCheckBox('ETF database', parent=self)
        self.equity_db_checkbox = QCheckBox('Equity database', parent=self)
        #
        self.dow30_checkbox.setChecked(True)
        self.nasdaq100_checkbox.setChecked(False)
        self.sandp500_checkbox.setChecked(False)
        #
        self.dow30_checkbox.stateChanged.connect(self._update_checkbox_selection)
        self.nasdaq100_checkbox.stateChanged.connect(self._update_checkbox_selection)
        self.sandp500_checkbox.stateChanged.connect(self._update_checkbox_selection)
        self.russell1k_checkbox.stateChanged.connect(self._update_checkbox_selection)
        self.russell2k_checkbox.stateChanged.connect(self._update_checkbox_selection)
        self.russell3k_checkbox.stateChanged.connect(self._update_checkbox_selection)
        self.comp_checkbox.stateChanged.connect(self._update_checkbox_selection)
        self.etf_db_checkbox.stateChanged.connect(self._update_checkbox_selection)
        self.equity_db_checkbox.stateChanged.connect(self._update_checkbox_selection)
        #self.etf_db_checkbox.setEnabled(False)
        #self.equity_db_checkbox.setEnabled(False)
        #
        self.exec_pushbutton = QPushButton('Analyze', parent=self)
        self.exec_pushbutton.clicked.connect(self._analyze_button_clicked)
        #
        self.text_browser = QTextBrowser(parent=self)
        # layout
        self.layout = QGridLayout()
        self.layout.addWidget(self.label, 0, 0)
        self.layout.addWidget(self.dow30_checkbox, 1, 0)
        self.layout.addWidget(self.nasdaq100_checkbox, 2, 0)
        self.layout.addWidget(self.sandp500_checkbox, 3, 0)
        self.layout.addWidget(self.russell1k_checkbox, 5, 0)
        self.layout.addWidget(self.russell2k_checkbox, 6, 0)
        self.layout.addWidget(self.russell3k_checkbox, 7, 0)
        self.layout.addWidget(self.comp_checkbox, 4, 0)
        self.layout.addWidget(self.etf_db_checkbox, 8, 0)
        self.layout.addWidget(self.equity_db_checkbox, 9, 0)
        self.layout.addWidget(self.exec_pushbutton, 10, 0)
        self.layout.addWidget(self.text_browser, 11, 0)
        self.setLayout(self.layout)
        self._update_checkbox_selection()

    def _update_checkbox_selection(self):
        self.tickers_to_analyze = []
        if self.dow30_checkbox.isChecked():
            self.tickers_to_analyze += ticker_group_dict['DOW 30']
        if self.nasdaq100_checkbox.isChecked():
            self.tickers_to_analyze += ticker_group_dict['NASDAQ 100']
        if self.sandp500_checkbox.isChecked():
            self.tickers_to_analyze += ticker_group_dict['S&P 500']
        if self.russell1k_checkbox.isChecked():
            self.tickers_to_analyze += ticker_group_dict['Russell 1000']
        if self.russell2k_checkbox.isChecked():
            self.tickers_to_analyze += ticker_group_dict['Russell 2000']
        if self.russell3k_checkbox.isChecked():
            self.tickers_to_analyze += ticker_group_dict['Russell 3000']
        if self.comp_checkbox.isChecked():
            self.tickers_to_analyze += ticker_group_dict['NASDAQ Composite']
        if self.etf_db_checkbox.isChecked():
            self.tickers_to_analyze += ticker_group_dict['ETF database']
        if self.equity_db_checkbox.isChecked():
            self.tickers_to_analyze += ticker_group_dict['Equity database']
        self.tickers_to_analyze = sorted(list(set(self.tickers_to_analyze)))
        self.n_tickers = len(self.tickers_to_analyze)
        self.exec_pushbutton.setText(f"Analyze {self.n_tickers} tickers for dividends")

    def _analyze_button_clicked(self):
        if self.n_tickers > 0:
            #self.text_browser.clearHistory()
            self.exec_pushbutton.setEnabled(False)
            self.exec_pushbutton.repaint()
            #
            self.thread=ticker_analyze_for_dividends_thread(app_window=self.app_window, tickers_to_analyze=self.tickers_to_analyze)
            self.thread._signal.connect(self._analyze_completed)
            self.thread.start()

    def _analyze_completed(self, df: pd.DataFrame):
        self.text_browser.setHtml(df.to_html(index=False))
        self.text_browser.repaint()
        self.exec_pushbutton.setEnabled(True)
        self.exec_pushbutton.repaint()


class ticker_db_dialog(QDialog):
    def __init__(self, parent=None, etf=True, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.app_window = parent
        self.resize(self.app_window.width*0.4, self.app_window.height*0.6)
        self.search_label = QLabel('Search:', parent=self)
        self.search_lineedit = QLineEdit(parent=self)
        self.search_lineedit.returnPressed.connect(self._search_lineedit_return_pressed)
        self.search_backward_checkbox = QCheckBox('Backward', parent=self)
        self.search_case_sensitive_checkbox = QCheckBox('Case Sensitive', parent=self)
        self.text_browser = QTextBrowser(parent=self)
        if etf:
            df1 = nasdaqlisted_df[ nasdaqlisted_df['ETF'] == 'Y' ][['ticker', 'Security Name']]
            df2 = otherlisted_df[ otherlisted_df['ETF'] == 'Y' ][['ticker', 'Security Name', 'Exchange']]
        else:
            df1 = nasdaqlisted_df[ nasdaqlisted_df['ETF'] == 'N' ][['ticker', 'Security Name']]
            df2 = otherlisted_df[ otherlisted_df['ETF'] == 'N' ][['ticker', 'Security Name', 'Exchange']]            
        df1['Exchange'] = 'Nasdaq'
        df2['Exchange'] = df2['Exchange'].map({'A': 'NYSE MKT',
                                               'N': 'New York Stock Exchange (NYSE)',
                                               'P': 'NYSE ARCA',
                                               'Z': 'BATS Global Markets (BATS)',
                                               'V': 'Investors\' Exchange, LLC (IEXG)'})
        df = pd.concat([df1, df2],axis=0)[['ticker', 'Security Name', 'Exchange']].reset_index().drop(['index'],axis=1) # axis=0 (1): row (column)
        self.text_browser.setHtml(df.to_html(index=True))
        # layout
        self.layout = QGridLayout()
        self.layout.addWidget(self.search_label, 0, 0)
        self.layout.addWidget(self.search_lineedit, 0, 1)
        self.layout.addWidget(self.search_backward_checkbox, 0, 2)
        self.layout.addWidget(self.search_case_sensitive_checkbox, 0, 3)
        self.layout.addWidget(self.text_browser, 1, 0, 1, 4)
        self.setLayout(self.layout)

    def _search_lineedit_return_pressed(self):
        search_str = self.search_lineedit.text()
        flag = QTextDocument.FindFlags()
        if self.search_backward_checkbox.isChecked():
            flag = flag | QTextDocument.FindBackward
        if self.search_case_sensitive_checkbox.isChecked():
            flag = flag | QTextDocument.FindCaseSensitively
        self.text_browser.find(search_str, flag)


class research_dialog(QDialog):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.app_window = parent
        self.home_url_str = "https://google.com"
        self.home_qurl = QUrl.fromUserInput(self.home_url_str)
        self.home_url_str = self.home_qurl.toString()
        # lineedit
        self.web_url_lineedit = web_url(parent=self, url_str = self.home_url_str)
        # webview
        self.webview = web_view(parent=self, qurl = self.home_qurl)
        self.web_url_lineedit.returnPressed.connect(self.web_url_entered)
        self.webview.page().urlChanged.connect(self.webview_url_changed)
        self.webview.page().titleChanged.connect(self.setWindowTitle)
        # toolbar
        self.toolBar = QToolBar(parent=self)
        #
        self.backButton = QPushButton(parent=self)
        self.backButton.setText("Back")
        self.backButton.setAutoDefault(False)
        self.backButton.clicked.connect(self.webview.back)
        self.toolBar.addWidget(self.backButton)
        #
        self.forwardButton = QPushButton(parent=self)
        self.forwardButton.setText("Forward")
        self.forwardButton.setAutoDefault(False)
        self.forwardButton.clicked.connect(self.webview.forward)
        self.toolBar.addWidget(self.forwardButton)
        #
        self.reloadButton = QPushButton(parent=self)
        self.reloadButton.setText("Reload")
        self.reloadButton.setAutoDefault(False)
        self.reloadButton.clicked.connect(self.webview.reload)
        self.toolBar.addWidget(self.reloadButton)
        #
        self.website1Button = QPushButton(parent=self)
        self.website1Button.setText(self.webview.ref_website1)
        self.website1Button.setAutoDefault(False)
        self.website1Button.clicked.connect(self.webview.reload_website1)
        self.toolBar.addWidget(self.website1Button)
        #
        self.website2Button = QPushButton(parent=self)
        self.website2Button.setText(self.webview.ref_website2)
        self.website2Button.setAutoDefault(False)
        self.website2Button.clicked.connect(self.webview.reload_website2)
        self.toolBar.addWidget(self.website2Button)
        #
        self.website3Button = QPushButton(parent=self)
        self.website3Button.setText(self.webview.ref_website3)
        self.website3Button.setAutoDefault(False)
        self.website3Button.clicked.connect(self.webview.reload_website3)
        self.toolBar.addWidget(self.website3Button)
        # layout
        self.layout = QGridLayout()
        self.layout.addWidget(self.web_url_lineedit, 0, 0)
        self.layout.addWidget(self.toolBar, 1, 0)
        self.layout.addWidget(self.webview, 2, 0)
        self.setLayout(self.layout)

    def web_url_entered(self):
        url_entered = self.web_url_lineedit.text()
        qurl_entered = QUrl.fromUserInput(url_entered)
        if qurl_entered.isValid():
            self.webview.load(qurl_entered)

    def webview_url_changed(self, qurl):
        self.web_url_lineedit.setText(qurl.toString())


class web_url(QLineEdit):
    def __init__(self, url_str="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(False)
        self.setText(url_str)


# https://myprogrammingnotes.com/suppress-js-error-output-qtwebengine.html
class web_engine_page(QWebEnginePage):
    def __init__(self, profile, parent):
        super().__init__(profile, parent) # parent=None
    def javaScriptConsoleMessage(self, *args, **kwargs):
        pass
    

# reference: https://doc.qt.io/qtforpython/examples/tabbedbrowser.html
class web_view(QWebEngineView):
    def __init__(self, parent, qurl):
        super().__init__()
        # references
        #self.page().profile().cachePath()
        #self.page().profile().cookieStore()
        #self.page().profile().persistentStoragePath()
        #self.page().profile().clearAllVisitedLinks()
        #self.page().profile().clearHttpCache()
        #self.page().profile().cookieStore().deleteAllCookies()
        self.web_engine_profile = QWebEngineProfile()
        #print(self.web_engine_profile.isOffTheRecord())
        #print(self.web_engine_profile.persistentStoragePath())
        self.web_engine_page = web_engine_page(profile=self.web_engine_profile, parent=self)
        #print(self.web_engine_page.profile().isOffTheRecord())
        self.setPage(self.web_engine_page)
        if not self.page().profile().isOffTheRecord():
            raise ValueError("the profile should be off-the-record.")
        self.setUrl(qurl)
        self.ref_website1 = "Investopedia"
        self.ref_website2 = "Nasdaq"
        self.ref_website3 = "Yahoo Finance"
        #self.ref_website4 = "Finviz"
    def reload_website1(self):
        self.load(QUrl.fromUserInput("https://investopedia.com"))
    def reload_website2(self):
        self.load(QUrl.fromUserInput("https://www.nasdaq.com/"))
    def reload_website3(self):
        self.load(QUrl.fromUserInput("https://finance.yahoo.com/"))


class app_menu(object):
    def __init__(self, app_window=None):
        self.app_window = app_window
        self._default_preference_settings()
        self.about_dialog = about_dialog(parent=self.app_window)
        self.preferences_dialog = preferences_dialog(parent=self.app_window, force_redownload_yfinance_data=self.force_redownload_yfinance_data, download_today_data=self.download_today_data, data_root_dir=self.data_root_dir)
        self.download_data_dialog = download_data_dialog(parent=self.app_window)
        self.research_dialog = research_dialog(parent=self.app_window)
        self.high_dividends_dialog = high_dividends_dialog(parent=self.app_window)
        self.etf_db_dialog = ticker_db_dialog(parent=self.app_window, etf=True)
        self.equity_db_dialog = ticker_db_dialog(parent=self.app_window, etf=False)
        self.fed_funds_rate_dialog = fed_funds_rate_dialog(parent=self.app_window)
        self.options_dialog = options_dialog(parent=self.app_window)
        self.screener_dialog = screener_dialog(parent=self.app_window)
        # about
        aboutAct = QAction('&About', parent=self.app_window)
        aboutAct.setShortcut('Ctrl+A')
        aboutAct.setStatusTip('About this app')
        aboutAct.triggered.connect(self.about_dialog.exec)
        # preferences
        prefAct = QAction('&Preferences...', parent=self.app_window)
        prefAct.setShortcut('Ctrl+,')
        prefAct.setStatusTip('Preference settings')
        prefAct.triggered.connect(self.preferences_dialog.exec)
        # download data
        download_Act = QAction('&Download data as cache', parent=self.app_window)
        download_Act.setShortcut('Ctrl+D')
        download_Act.setStatusTip('Download the latest data of tickers and store as cache')
        download_Act.triggered.connect(self.download_data_dialog.exec)        
        # exit
        exitAct = QAction('&Exit', parent=self.app_window)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.setStatusTip('Exit app')
        exitAct.triggered.connect(self.app_window.app.quit)
        # menubar
        self.app_window.menubar = self.app_window.menuBar()
        self.app_window.menubar.setNativeMenuBar(False)
        # 1. appMenu
        self.app_window.AppMenu = self.app_window.menubar.addMenu('&App')
        self.app_window.AppMenu.addAction(aboutAct)
        self.app_window.AppMenu.addAction(prefAct)
        self.app_window.AppMenu.addAction(download_Act)
        self.app_window.AppMenu.addAction(exitAct)
        # view
        webAct = QAction('&Useful websites', parent=self.app_window)
        webAct.triggered.connect(self.research_dialog.exec)
        #
        high_dividendsAct = QAction('&High-dividend investments', parent=self.app_window)
        high_dividendsAct.triggered.connect(self.high_dividends_dialog.exec)
        #
        etf_db_Act = QAction('&ETF database', parent=self.app_window)
        etf_db_Act.triggered.connect(self.etf_db_dialog.exec)
        #
        equity_db_Act = QAction('&Equity database', parent=self.app_window)
        equity_db_Act.triggered.connect(self.equity_db_dialog.exec)
        #
        fed_funds_rate_Act = QAction('&Federal funds rate', parent=self.app_window)
        fed_funds_rate_Act.setShortcut('Ctrl+F')
        fed_funds_rate_Act.triggered.connect(self.fed_funds_rate_dialog.exec)
        #
        options_trading_Act = QAction('&Options trading', parent=self.app_window)
        options_trading_Act.setShortcut('Ctrl+O')
        options_trading_Act.triggered.connect(self.options_dialog.exec)
        #
        screener_Act = QAction('&Screener', parent=self.app_window)
        screener_Act.setShortcut('Ctrl+S')
        screener_Act.triggered.connect(self.screener_dialog.exec)
        # 2. researchMenu
        self.app_window.ResearchMenu = self.app_window.menubar.addMenu('&Research')
        self.app_window.ResearchMenu.addAction(webAct)
        self.app_window.ResearchMenu.addAction(high_dividendsAct)
        self.app_window.ResearchMenu.addAction(etf_db_Act)
        self.app_window.ResearchMenu.addAction(equity_db_Act)
        self.app_window.ResearchMenu.addAction(fed_funds_rate_Act)
        self.app_window.ResearchMenu.addAction(options_trading_Act)
        self.app_window.ResearchMenu.addAction(screener_Act)
        # 3. additional menu
        if self.add_additional_menu():
            self.build_additional_menu()

    def _default_preference_settings(self):
        self.force_redownload_yfinance_data = False
        self.download_today_data = True
        self.data_root_dir = global_data_root_dir

    def add_additional_menu(self):
        return False

    def build_additional_menu(self):
        pass


class app_window(QMainWindow):
    def __init__(self, app=None, appmenu=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app

        # screen
        screen = self.app.primaryScreen()
        dpi = 72/screen.devicePixelRatio()
        self.width = screen.availableGeometry().width() * 0.96
        self.height = screen.availableGeometry().height() * 0.75
            
        # central widget
        self.UI = UI(parent=self, app_window=self, dpi=dpi)
        self.setCentralWidget(self.UI)
        # others
        self.setWindowTitle(f"{App_name}")
        self.resize(self.width, self.height)
        #self.setGeometry(300, 300, 300, 200)

        # menuBar
        if appmenu is None:
            self.app_menu = app_menu(app_window=self)
        else:
            self.app_menu = appmenu(app_window=self)


class UI(QWidget):
    def __init__(self, app_window=None, dpi=72, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #
        self.app_window = app_window

        self.group_selection = group_selection(parent=self)
        self.subgroup_selection = subgroup_selection(parent=self)

        self.ticker_selection = ticker_selection(parent=self)
        self.ticker_textinfo = textinfo(parent=self)
        self.ticker_textinfo.setFixedHeight(self.app_window.height*0.55)

        self.index_selection = index_selection(parent=self)
        self.index_textinfo = textinfo(parent=self)
        self.index_textinfo.setFixedHeight(self.app_window.height*0.55)

        self.ticker_timeframe_selection = ticker_timeframe_selection(parent=self)
        self.ticker_lastdate_pushbutton = ticker_lastdate_pushbutton(parent=self)
        self.ticker_download_latest_data_from_yfinance_pushbutton = ticker_download_latest_data_from_yfinance_pushbutton(parent=self)
        self.ticker_canvas_coord_label = QLabel(text='', parent=self)
        self.ticker_lastdate_calendar_dialog = ticker_lastdate_calendar_dialog(parent=self)
        self.ticker_canvas = canvas(parent=self, dpi=dpi, UI=self)
        self.index_canvas_options = index_canvas_options(parent=self)
        self.index_canvas_coord_label = QLabel(text='', parent=self)
        self.index_canvas = canvas(parent=self, dpi=dpi, UI=self)

        self.message_dialog = message_dialog(parent=self)

        # the layout
        self.layout = QGridLayout()
        self.layout.addWidget(self.group_selection,    0, 0, 1, 1)
        self.layout.addWidget(self.subgroup_selection, 0, 1, 1, 1)
        self.layout.addWidget(self.ticker_selection,   0, 2, 1, 1)
        self.layout.addWidget(self.ticker_textinfo,    1, 0, 2, 3, Qt.AlignTop)
        self.layout.addWidget(self.index_selection,    3, 0, 1, 1)
        self.layout.addWidget(self.index_textinfo,     4, 0, 2, 3, Qt.AlignTop)
        self.layout.addWidget(self.ticker_timeframe_selection, 0, 3)
        self.layout.addWidget(self.ticker_lastdate_pushbutton, 0, 4)
        self.layout.addWidget(self.ticker_download_latest_data_from_yfinance_pushbutton, 0, 5)
        self.layout.addWidget(self.ticker_canvas_coord_label, 0, 6)
        self.layout.addWidget(self.ticker_canvas, 1, 3, 2, 4)
        self.layout.addWidget(self.index_canvas_options,     3, 3)
        self.layout.addWidget(self.index_canvas_coord_label, 3, 4)
        self.layout.addWidget(self.index_canvas,  4, 3, 2, 4)
        self.setLayout(self.layout)

        # control
        self.control = UI_control(UI = self)


class UI_control(object):

    def __init__(self, UI):
        super().__init__()
        self._UI = UI
        # connect signals
        self._UI.group_selection.currentIndexChanged.connect(self._group_selection_change)
        self._UI.subgroup_selection.currentIndexChanged.connect(self._subgroup_selection_change)
        self._UI.ticker_selection.currentIndexChanged.connect(self._ticker_selection_change)
        self._UI.ticker_timeframe_selection.currentIndexChanged.connect(self._ticker_timeframe_selection_change)
        self._UI.ticker_lastdate_pushbutton.clicked.connect(self._ticker_lastdate_pushbutton_clicked)
        self._UI.ticker_lastdate_calendar_dialog.ticker_lastdate_calendar_use_last_available_date_button.clicked.connect(self._ticker_lastdate_dialog_use_last_available_date_button_clicked)
        self._UI.ticker_lastdate_calendar_dialog.ticker_lastdate_calendar_dialog_ok_button.clicked.connect(self._ticker_lastdate_dialog_ok_button_clicked)
        self._UI.ticker_download_latest_data_from_yfinance_pushbutton.clicked.connect(self._ticker_download_latest_data_from_yfinance)
        self._UI.message_dialog.textinfo_ok_button.clicked.connect(self._message_dialog_textinfo_ok_button_clicked)
        self._UI.index_selection.currentIndexChanged.connect(self._index_selection_change)
        self._UI.index_canvas_options.currentIndexChanged.connect(self._index_canvas_options_change)
        self.timeframe_text = None
        self.ticker_data_dict_in_effect = None
        self._ticker_selected = False
        self.selected_ticker = None
        self.ticker_canvas_cursor = None
        self.index_canvas_cursor = None
        self.timeframe_dict = {"1 week": 1/52, "2 weeks": 1/26, "1 month": 1/12, "2 months": 1/6, "3 months": 1/4, "6 months": 1/2, "1 year": 1.0, "2 years": 2.0, "5 years": 5.0, "10 years": 10.0, "15 years": 15.0, "20 years": 20.0, "30 years": 30.0, "All time": float('inf')}
        self.time_last_date = pd.to_datetime(date.today(), utc=True)
        self.timeframe_selection_index = list(self.timeframe_dict).index('1 year') + 1
        self.index_options_selection_index = 1
        self.index_selection_index = 2
        self._group_selected = None
        self._index_selected = None
        self._UI.group_selection.setCurrentIndex(1) # 'All'
        #self._group_selection_change(1) # 'All'

    def _index_selection_change(self, index: int = None):
        if index > 0:
            self.index_selection_index = index
            # index canvas selection
            self._UI.index_canvas_options.reset()
            #
            self._index_selected = self._UI.index_selection.itemText(index)
            if self._index_selected == 'PVI and NVI':
                #self._UI.index_textinfo.setText(f"PVI (Positive Volume Index) reflects high-volume days and thus the crowd's feelings: When PVI_EMA9 is above (or below) PVI_EMA255, the crowd is optimistic (or turning pessimistic).\n\nNVI (Negative Volume Index) reflects low-volume days and thus what the non-crowd (e.g., 'smart money') may be doing: When NVI_EMA9 is above (or below) NVI_EMA255, the non-crowd (e.g., 'smart money') may be buying (or selling).")
                self._UI.index_textinfo.setHtml(f"<body style=\"font-family:Courier New;\"><b>PVI</b> (Positive Volume Index) reflects high-volume days and thus the crowd's feelings: When PVI_EMA9 is above (or below) PVI_EMA255, the crowd (the retail investors) is optimistic (or turning pessimistic).<br/><br/><b>NVI</b> (Negative Volume Index) reflects low-volume days and thus what the non-crowd (e.g., 'smart money', namely, institutional investors) may be doing: When NVI_EMA9 is above (or below) NVI_EMA255, the non-crowd (e.g., 'smart money') may be buying (or selling).</body>")
                self._UI.index_canvas_options.addItem("PVI")
                self._UI.index_canvas_options.addItem("NVI")
                self.index_options_selection_index = 1
                self._UI.index_canvas_options.setCurrentIndex(self.index_options_selection_index)
            elif self._index_selected == 'RSI':
                self._UI.index_textinfo.setHtml(f"<body style=\"font-family:Courier New;\"><b>RSI</b> (Relative Strength Index) reflects a possible oversold (RSI &lt; 30) or overbought (RSI &gt; 70) condition.<br/><br/><a href='https://www.investopedia.com/terms/r/rsi.asp'>https://www.investopedia.com/terms/r/rsi.asp</a></body>")
                self._UI.index_canvas_options.addItem("RSI14")
                self.index_options_selection_index = 1
                self._UI.index_canvas_options.setCurrentIndex(self.index_options_selection_index)
            elif self._index_selected == 'MACD':
                self._UI.index_textinfo.setHtml(f"<body style=\"font-family:Courier New;\"><b>MACD</b> (Moving Average Convergence Divergence) is a lagging momentum indicator. When <b><span style='color:blue'>MACD</span></b> crosses <b>above</b> (or below) its 9-day EMA <b><span style='color:orange'>signal</span></b> line, it's a <b>buy</b> (or sell).<br/><br/>Common interpretations: crossovers, divergences, and rapid rises/falls.<br/><br/><a href='https://www.investopedia.com/terms/m/macd.asp'>https://www.investopedia.com/terms/m/macd.asp</a></body>")
                self._UI.index_canvas_options.addItem("MACD: EMA12 vs. EMA26")
                self.index_options_selection_index = 1
                self._UI.index_canvas_options.setCurrentIndex(self.index_options_selection_index)
            elif self._index_selected == 'OBV':
                self._UI.index_textinfo.setHtml(f"<body style=\"font-family:Courier New;\"><b>OBV</b> (On-Balance Volume) is a leading (as opposed to lagging) momentum indicator to predict changes in stock price.<br/><br/>The author viewed OBV as \"a spring being wound tightly.\" and believed that when volume increases sharply (<b>positive OBV slope</b>) without a significant change in the stock's price (<b>relatively flat price slope</b>), the price will eventually jump upward or fall downward.<br/><br/><a href='https://www.investopedia.com/terms/o/onbalancevolume.asp'>https://www.investopedia.com/terms/o/onbalancevolume.asp</a><br/><br/><a href='https://www.investopedia.com/articles/active-trading/021115/uncover-market-sentiment-onbalance-volume-obv.asp'>https://www.investopedia.com/articles/active-trading/021115/uncover-market-sentiment-onbalance-volume-obv.asp</a></body>")
                self._UI.index_canvas_options.addItem("OBV")
                self.index_options_selection_index = 1
                self._UI.index_canvas_options.setCurrentIndex(self.index_options_selection_index)
            elif self._index_selected == 'Heat':
                self._UI.index_textinfo.setHtml(f"<body style=\"font-family:Courier New;\">Market heat, defined as <b>standardized score of price*volume</b>, reflecting how hot the symbol was or how much active attention was drawn to the symbol at that moment.</body>")
                self._UI.index_canvas_options.addItem("Heat")
                self.index_options_selection_index = 1
                self._UI.index_canvas_options.setCurrentIndex(self.index_options_selection_index)
            elif self._index_selected == 'Supply & Demand':
                self._UI.index_textinfo.setHtml(f"<body style=\"font-family:Courier New;\">Support and demand (related support/resistance, inflation point).</body>")
                self._UI.index_canvas_options.addItem("Supply & Demand")
                self.index_options_selection_index = 1
                self._UI.index_canvas_options.setCurrentIndex(self.index_options_selection_index) 

            self._calc_index()
            self._draw_index_canvas()

    def _group_selection_change(self, index: int = None):
        if index > 0:
            self._group_selected = self._UI.group_selection.itemText(index)
            # subgroup selection
            self._UI.subgroup_selection.reset()
            for subgroup in subgroup_group_dict[self._group_selected]:
                self._UI.subgroup_selection.addItem(subgroup)
            self._UI.subgroup_selection.setCurrentIndex(1) # The item of index=1 is 'All'
            # ticker selection
            self._UI.ticker_selection.reset()
            for ticker in ticker_group_dict[self._group_selected]:
                self._UI.ticker_selection.addItem(ticker)
            # ticker texinfo
            self._UI.ticker_textinfo.setText(group_desc_dict[self._group_selected])
            # group_or_subgroup_selection_change
            self._group_or_subgroup_selection_change()

    def _subgroup_selection_change(self, index: int = None):
        if index > 0:
            subgroup_selected = self._UI.subgroup_selection.itemText(index)
            # ticker selection
            self._UI.ticker_selection.reset()
            if index == 1: # 'All'
                for ticker in ticker_group_dict[self._group_selected]:
                    self._UI.ticker_selection.addItem(ticker)
                # ticker texinfo
                self._UI.ticker_textinfo.setText(group_desc_dict[self._group_selected])
            else:
                for ticker in ticker_subgroup_dict[subgroup_selected]:
                    self._UI.ticker_selection.addItem(ticker)
                # ticker texinfo
                self._UI.ticker_textinfo.setText(group_desc_dict[self._group_selected] + f"\n\nSubgroup: [{subgroup_selected}]")

    def _group_or_subgroup_selection_change(self):
        # ticker frame selection
        self._UI.ticker_timeframe_selection.reset()
        # ticker canvas
        self._UI.ticker_canvas.axes.clear()
        self._UI.ticker_canvas.draw()
        self._UI.ticker_canvas_coord_label.clear()
        # index canvas
        self._UI.index_canvas.axes.clear()
        self._UI.index_canvas.draw()
        self._UI.index_canvas_coord_label.clear()
        # index selection
        self._UI.index_selection.reset()
        # index textinfo
        self._UI.index_textinfo.clear()
        # index canvas selection
        self._UI.index_canvas_options.reset()
        # ticker lastdate and redownload pushbuttons
        self._UI.ticker_lastdate_pushbutton.reset()
        self._UI.ticker_download_latest_data_from_yfinance_pushbutton.reset()
        # others
        self._ticker_selected = False

    def _ticker_selection_change(self, index: int = None):
        if index > 0:
            self.selected_ticker = self._UI.ticker_selection.itemText(index).upper()
            if self.selected_ticker not in ticker_group_dict['All']:
                print(f"Info: unrecognized ticker was entered: [{self.selected_ticker}]")

            self.ticker_data_dict_original = get_ticker_data_dict(ticker = self.selected_ticker, 
                                                                  force_redownload = self._UI.app_window.app_menu.preferences_dialog.force_redownload_yfinance_data, 
                                                                  download_today_data = self._UI.app_window.app_menu.preferences_dialog.download_today_data, 
                                                                  data_root_dir=self._UI.app_window.app_menu.preferences_dialog.data_root_dir)
            self.ticker_data_dict_in_effect = copy.deepcopy(self.ticker_data_dict_original)
            self._calc_index()

            self._UI.ticker_textinfo.setHtml(get_formatted_ticker_data(self.ticker_data_dict_in_effect, use_html=True))

            self._UI.ticker_timeframe_selection.reset()
            for timeframe in self.timeframe_dict.keys():
                self._UI.ticker_timeframe_selection.addItem(timeframe)

            self.time_last_date = self.ticker_data_dict_in_effect['history']['Date'].iloc[-1]
            self._UI.ticker_lastdate_calendar_dialog.ticker_lastdate_calendar.setMaximumDate(self.time_last_date)
            self._UI.ticker_lastdate_calendar_dialog.ticker_lastdate_calendar.setSelectedDate(self.time_last_date)
            self._UI.ticker_lastdate_pushbutton.setText(f"Last Date: {str(self.time_last_date.date())}")
            self._UI.ticker_timeframe_selection.setCurrentIndex(self.timeframe_selection_index) # this changes self.ticker_data_dict_in_effect

            self._UI.ticker_canvas_coord_label.clear()
            self._UI.index_canvas_coord_label.clear()
            self._draw_ticker_canvas()
            self._draw_index_canvas()

            self._UI.index_selection.reset()
            self._UI.index_selection.addItem("PVI and NVI")
            self._UI.index_selection.addItem("RSI")
            self._UI.index_selection.addItem("MACD")
            self._UI.index_selection.addItem("OBV")
            self._UI.index_selection.addItem("Heat")
            self._UI.index_selection.addItem("Supply & Demand")
            self._UI.index_selection.setCurrentIndex(self.index_selection_index)

            self._UI.ticker_lastdate_pushbutton.setEnabled(True)
            self._UI.ticker_download_latest_data_from_yfinance_pushbutton.setEnabled(True)

            self._ticker_selected = True

    def _draw_ticker_canvas(self):
        canvas = self._UI.ticker_canvas
        canvas.axes.clear()
        # to skip non-existent dates on the plot
        # x = self.ticker_data_dict_in_effect['history']['Date']
        dates = self.ticker_data_dict_in_effect['history']['Date'].values
        formatter = DateFormatter(dates)
        canvas.axes.xaxis.set_major_formatter(formatter)
        x = np.arange(len(dates))
        # volume bar
        volumes = self.ticker_data_dict_in_effect['history']['Volume'].values
        if volumes[0] is not None:
            close = self.ticker_data_dict_in_effect['history']['Close']
            scale_factor = (max(close.values) * 0.40) / max(volumes)
            volumes = volumes * scale_factor
            close_prev = self.ticker_data_dict_in_effect['history']['Close'].shift(1)
            close_increase = (close >= close_prev).values
            volume_color = ['#86cbc5' if chg else '#f69f9d' for chg in close_increase]
            canvas.axes.bar(x, volumes, color=volume_color)
        #
        #ticker_plotline, = canvas.axes.plot(x, self.ticker_data_dict_in_effect['history']['Close'], color='tab:blue',                    linewidth=1)
        canvas.axes.plot(x, self.ticker_data_dict_in_effect['history']['Close_EMA255'],             color='#9ed5f7', linestyle="dashed", linewidth=1)
        canvas.axes.plot(x, self.ticker_data_dict_in_effect['history']['Close_EMA9'],               color='#9ed5f7',                     linewidth=1)
        canvas.axes.plot(x, self.ticker_data_dict_in_effect['history']['Close'],                    color='tab:blue',                    linewidth=1)
        canvas.axes.set_xlabel('Date', fontsize=10.0)
        canvas.axes.set_ylabel('Close Price (EMA9, 255)', fontsize=10.0)
        #
        canvas.figure.autofmt_xdate()
        ticker_plotline = None
        actual_x_data = dates
        x_index = x
        y_data = self.ticker_data_dict_in_effect['history']['Close'].values
        #################################################
        self.ticker_canvas_cursor = SnappingCursor(plotline=ticker_plotline, actual_x_data=actual_x_data, x_index=x_index, y_data=y_data, ax=canvas.axes, useblit=True, color='black', linestyle='dashed', linewidth=1, name='ticker_canvas_cursor', UI=self._UI)
        canvas.mpl_connect('motion_notify_event',  self.ticker_canvas_cursor.onmove) # mpl = matplotlib
        #################################################
        canvas.mpl_connect('button_press_event',   canvas.button_pressed)
        canvas.mpl_connect('button_release_event', canvas.button_released)
        canvas.mpl_connect('motion_notify_event',  canvas.onmove)
        #################################################
        canvas.draw()

    def _draw_index_canvas(self):
        actual_x_data = None
        x_index = None
        y_data = None

        canvas = self._UI.index_canvas
        canvas.axes.clear()
        canvas.axes.set_xlabel('Date', fontsize=10.0)
        #################################################
        if self._index_selected is None:
            canvas.axes.set_ylabel('Index to be selected', fontsize=10.0)
            canvas.draw()
            return

        elif self._index_selected == 'PVI and NVI':
            canvas.axes.set_ylabel('PVI (green) and NVI (orange) (EMA9, 255)', fontsize=10.0)
            if all(v is None for v in self.ticker_data_dict_in_effect['history']['PVI_EMA9']):
                canvas.draw()
                return
            # to skip non-existent dates on the plot
            dates = self.ticker_data_dict_in_effect['history']['Date'].values
            formatter = DateFormatter(dates)
            canvas.axes.xaxis.set_major_formatter(formatter)
            x = np.arange(len(dates))
            #
            #index_plotline_PVI, = canvas.axes.plot(x, self.ticker_data_dict_in_effect['history']['PVI'], color='tab:green',    linewidth=1.0)
            #index_plotline_NVI, = canvas.axes.plot(x, self.ticker_data_dict_in_effect['history']['NVI'], color='tab:orange',   linewidth=1.0)
            canvas.axes.plot(x, self.ticker_data_dict_in_effect['history']['PVI_EMA255'], color='#baf1b2', linestyle="dashed", linewidth=1.0)
            canvas.axes.plot(x, self.ticker_data_dict_in_effect['history']['NVI_EMA255'], color='#efb663', linestyle="dashed", linewidth=1.0)
            canvas.axes.plot(x, self.ticker_data_dict_in_effect['history']['PVI_EMA9'],   color='#baf1b2',                     linewidth=1.0)
            canvas.axes.plot(x, self.ticker_data_dict_in_effect['history']['NVI_EMA9'],   color='#efb663',                     linewidth=1.0)
            canvas.axes.plot(x, self.ticker_data_dict_in_effect['history']['PVI'], color='tab:green',    linewidth=1.0)
            canvas.axes.plot(x, self.ticker_data_dict_in_effect['history']['NVI'], color='tab:orange',   linewidth=1.0)
            #################################################
            canvas.figure.autofmt_xdate()
            if self.index_options_selection_index == 1:
                #index_plotline = index_plotline_PVI
                index_plotline = None
                actual_x_data = dates
                x_index = x
                y_data = self.ticker_data_dict_in_effect['history']['PVI'].values
            elif self.index_options_selection_index == 2:
                #index_plotline = index_plotline_NVI
                index_plotline = None
                actual_x_data = dates
                x_index = x
                y_data = self.ticker_data_dict_in_effect['history']['NVI'].values
            else:
                raise ValueError("index options selection index not within range")

        elif self._index_selected == 'RSI':
            # to skip non-existent dates on the plot
            dates = self.ticker_data_dict_in_effect['history']['Date'].values
            formatter = DateFormatter(dates)
            canvas.axes.xaxis.set_major_formatter(formatter)
            x = np.arange(len(dates))
            #
            n_ticks = len(x)
            y70 = np.empty(n_ticks); y70.fill(70)
            y30 = np.empty(n_ticks); y30.fill(30)
            canvas.axes.set_ylabel('RSI14', fontsize=10.0)
            canvas.axes.set_ylim(0, 100)
            y = self.ticker_data_dict_in_effect['history']['RSI14']
            canvas.axes.plot(x, y30, '--', color='black', linewidth=0.5)
            canvas.axes.plot(x, y70, '--', color='black', linewidth=0.5)
            canvas.axes.fill_between(x, y30, y70, where=(y30<y70), color='tab:blue',  alpha=0.05, interpolate=True)
            canvas.axes.fill_between(x, y,   y70, where=(y>y70),   color='tab:green', alpha=0.3,  interpolate=True)
            canvas.axes.fill_between(x, y,   y30, where=(y<y30),   color='tab:red',   alpha=0.3,  interpolate=True)
            #index_plotline, = canvas.axes.plot(x, y, color='tab:blue', linewidth=1)
            canvas.axes.plot(x, y, color='tab:blue', linewidth=1)
            #
            canvas.figure.autofmt_xdate()
            index_plotline = None
            actual_x_data = dates
            x_index = x
            y_data = y.values

        elif self._index_selected == 'MACD':
            # https://stackoverflow.com/questions/43029895/python-matlabplot-with-datetime-numpy-array-how-to-skip-days-in-plot
            # to skip non-existent dates on the plot
            dates = self.ticker_data_dict_in_effect['history']['Date'].values
            formatter = DateFormatter(dates)
            canvas.axes.xaxis.set_major_formatter(formatter)
            x = np.arange(len(dates))
            #
            canvas.axes.set_ylabel('MACD', fontsize=10.0)
            MACD_macd = self.ticker_data_dict_in_effect['history']['MACD_macd']
            MACD_signal = self.ticker_data_dict_in_effect['history']['MACD_signal']
            MACD_histogram = self.ticker_data_dict_in_effect['history']['MACD_histogram']
            # The ternary operator has the same syntax:
            # [(token if emoticon_re.search(token) else token.lower()) for token in tokens]
            color_cross_above_and_increase = '#26A69A'
            color_cross_above_and_decrease = '#B2DFDB'
            color_cross_below_and_increase = '#FFCDD2'
            color_cross_below_and_decrease = '#EF5350'
            MACD_increase = (MACD_histogram > MACD_histogram.shift(1)).values
            MACD_hist_color = [((color_cross_above_and_increase if MACD_increase[idx] else color_cross_above_and_decrease) if cross>=0 else (color_cross_below_and_increase if MACD_increase[idx] else color_cross_below_and_decrease)) for idx, cross in enumerate(MACD_histogram)]
            # 
            n_ticks = len(x)
            y0 = np.empty(n_ticks); y0.fill(0)
            canvas.axes.plot(x, y0, '--', color='black', linewidth=0.5)
            #
            canvas.axes.bar(x, MACD_histogram, color=MACD_hist_color)
            canvas.axes.plot(x, MACD_macd, color='tab:blue', linewidth=1)
            canvas.axes.plot(x, MACD_signal, color='tab:orange', linewidth=1)
            #
            canvas.figure.autofmt_xdate()
            index_plotline = None
            actual_x_data = dates
            x_index = x
            y_data = MACD_macd.values

        elif self._index_selected == 'OBV':
            # to skip non-existent dates on the plot
            dates = self.ticker_data_dict_in_effect['history']['Date'].values
            formatter = DateFormatter(dates)
            canvas.axes.xaxis.set_major_formatter(formatter)
            x = np.arange(len(dates))
            canvas.axes.set_ylabel('On-Balance Volume (EMA9, EMA255)', fontsize=10.0)
            obv = self.ticker_data_dict_in_effect['history']['OBV']
            obv_255 = self.ticker_data_dict_in_effect['history']['OBV_EMA255']
            obv_9 = self.ticker_data_dict_in_effect['history']['OBV_EMA9']
            color_obv = '#3A6CA8'
            canvas.axes.plot(x, obv_255, color='#9ed5f7', linestyle="dashed", linewidth=1)
            canvas.axes.plot(x, obv_9,   color='#9ed5f7',                     linewidth=1)
            canvas.axes.plot(x, obv,     color=color_obv, linewidth=1)
            #
            canvas.figure.autofmt_xdate()
            index_plotline = None
            actual_x_data = dates
            x_index = x
            y_data = obv.values

        elif self._index_selected == 'Heat':
            # to skip non-existent dates on the plot
            dates = self.ticker_data_dict_in_effect['history']['Date'].values
            formatter = DateFormatter(dates)
            canvas.axes.xaxis.set_major_formatter(formatter)
            x = np.arange(len(dates))
            #
            n_ticks = len(x)
            y0 = np.empty(n_ticks); y0.fill(0)
            canvas.axes.plot(x, y0, '--', color='#0e6b0e', linewidth=0.5)
            #
            canvas.axes.set_ylabel('Standardized Price * Volume (EMA9, EMA255)', fontsize=10.0)
            Z_price_vol = self.ticker_data_dict_in_effect['history']['Z_price_vol']
            Z_price_vol_EMA9 = self.ticker_data_dict_in_effect['history']['Z_price_vol_EMA9']
            Z_price_vol_EMA255 = self.ticker_data_dict_in_effect['history']['Z_price_vol_EMA255']
            color_Z_price_vol = '#3A6CA8'
            canvas.axes.plot(x, Z_price_vol_EMA255, color='#9ed5f7', linestyle="dashed", linewidth=1)
            canvas.axes.plot(x, Z_price_vol_EMA9,   color='tab:red',                     linewidth=1)
            canvas.axes.plot(x, Z_price_vol,        color=color_Z_price_vol,             linewidth=1)
            #
            canvas.figure.autofmt_xdate()
            index_plotline = None
            actual_x_data = dates
            x_index = x
            y_data = Z_price_vol.values

        elif self._index_selected == 'Supply & Demand':
            # to skip non-existent dates on the plot
            dates = self.ticker_data_dict_in_effect['history']['Date'].values
            formatter = DateFormatter(dates)
            canvas.axes.xaxis.set_major_formatter(formatter)
            x = np.arange(len(dates))
            #
            n_ticks = len(x)
            y0 = np.empty(n_ticks); y0.fill(0)
            canvas.axes.plot(x, y0, '--', color='#0e6b0e', linewidth=0.5)
            #
            canvas.axes.set_ylabel('Standardized Price * Volume (EMA9, EMA255)', fontsize=10.0)
            Z_price_vol = self.ticker_data_dict_in_effect['history']['Z_price_vol']
            Z_price_vol_EMA9 = self.ticker_data_dict_in_effect['history']['Z_price_vol_EMA9']
            Z_price_vol_EMA255 = self.ticker_data_dict_in_effect['history']['Z_price_vol_EMA255']
            color_Z_price_vol = '#3A6CA8'
            canvas.axes.plot(x, Z_price_vol_EMA255, color='#9ed5f7', linestyle="dashed", linewidth=1)
            canvas.axes.plot(x, Z_price_vol_EMA9,   color='tab:red',                     linewidth=1)
            canvas.axes.plot(x, Z_price_vol,        color=color_Z_price_vol,             linewidth=1)
            #
            canvas.figure.autofmt_xdate()
            index_plotline = None
            actual_x_data = dates
            x_index = x
            y_data = Z_price_vol.values

        else:
            raise ValueError(f"Unexpected self._index_selected = [{self._index_selected}]")

        #################################################
        self.index_canvas_cursor = SnappingCursor(plotline=index_plotline, actual_x_data=actual_x_data, x_index=x_index, y_data=y_data, ax=canvas.axes, useblit=True, color='black', linestyle='dashed', linewidth=1, name='index_canvas_cursor', UI=self._UI)
        canvas.mpl_connect('motion_notify_event', self.index_canvas_cursor.onmove)
        #################################################
        canvas.draw()

    def _index_canvas_options_change(self, index: int = None):
        if index > 0:
            self.index_options_text = self._UI.index_canvas_options.itemText(index)
            self.index_options_selection_index = index
            self._draw_index_canvas() 

    def _ticker_timeframe_selection_change(self, index: int = None):
        if index > 0:
            self.timeframe_text = self._UI.ticker_timeframe_selection.itemText(index)
            self.timeframe_selection_index = index

            if self.timeframe_text in self.timeframe_dict.keys():
                history_df = self.ticker_data_dict_original['history'].copy()
                if self.timeframe_text == "All time":
                    time_first_date = history_df['Date'].iloc[0]
                else:
                    time_first_date = self.time_last_date - timedelta(days=365.25*self.timeframe_dict[self.timeframe_text])
                history_df = history_df[(time_first_date<=history_df['Date']) & (history_df['Date']<=self.time_last_date)].copy()
                if len(history_df) == 0:
                    self._UI.message_dialog.textinfo.setText(f"No data available within the specified date range: {str(time_first_date.date())} ~ {str(self.time_last_date.date())}")
                    self._UI.message_dialog.exec()
                    return
                self.ticker_data_dict_in_effect['history'] = history_df

            self._calc_index()
            self._draw_ticker_canvas()
            self._draw_index_canvas()

    def _calc_index(self):
        history_df = self.ticker_data_dict_in_effect['history']
        history_all_df = self.ticker_data_dict_original['history']
        ######################
        # positive volume index and negative volume index
        history_all_df['PVI'], history_all_df['NVI'], history_all_df['PVI_EMA9'], history_all_df['NVI_EMA9'], history_all_df['PVI_EMA255'], history_all_df['NVI_EMA255'] = volume_indicator(short_periods=9, long_periods=255).PVI_NVI(history_all_df['Close'], history_all_df['Volume'])
        history_df[['PVI','NVI','PVI_EMA9','NVI_EMA9','PVI_EMA255','NVI_EMA255']] = history_all_df[history_all_df['Date'].isin(history_df['Date'])][['PVI','NVI','PVI_EMA9','NVI_EMA9','PVI_EMA255','NVI_EMA255']]
        PVI_max = max(history_df[['PVI','PVI_EMA9','PVI_EMA255']].max())
        PVI_min = min(history_df[['PVI','PVI_EMA9','PVI_EMA255']].min())
        NVI_max = max(history_df[['NVI','NVI_EMA9','NVI_EMA255']].max())
        NVI_min = min(history_df[['NVI','NVI_EMA9','NVI_EMA255']].min())
        # this is to keep PVI indexes between 0 and 1000
        history_df[['PVI','PVI_EMA9','PVI_EMA255']] = (history_df[['PVI','PVI_EMA9','PVI_EMA255']] - PVI_min) / (PVI_max - PVI_min) * 1000
        # this is to keep NVI indexes between 0 and 1000
        history_df[['NVI','NVI_EMA9','NVI_EMA255']] = (history_df[['NVI','NVI_EMA9','NVI_EMA255']] - NVI_min) / (NVI_max - NVI_min) * 1000
        ######################
        history_all_df['RSI14'] = momentum_indicator().RSI(close_price=history_all_df['Close'], RSI_periods=14)
        history_df['RSI14'] = history_all_df[history_all_df['Date'].isin(history_df['Date'])]['RSI14']
        ######################
        history_all_df['MACD_macd'], history_all_df['MACD_signal'], history_all_df['MACD_histogram'] = momentum_indicator().MACD(close_price=history_all_df['Close'], fast_period=12, slow_period=26, signal_period=9)
        history_df[['MACD_macd','MACD_signal','MACD_histogram']] = history_all_df[history_all_df['Date'].isin(history_df['Date'])][['MACD_macd','MACD_signal','MACD_histogram']]
        ######################
        history_all_df['OBV'] = momentum_indicator().OBV(close_price=history_all_df['Close'], volume=history_all_df['Volume'])
        history_all_df['OBV_EMA9'] = moving_average(periods=9).exponential(history_all_df['OBV'])
        history_all_df['OBV_EMA255'] = moving_average(periods=255).exponential(history_all_df['OBV'])
        history_df[['OBV', 'OBV_EMA9', 'OBV_EMA255']] = history_all_df[history_all_df['Date'].isin(history_df['Date'])][['OBV', 'OBV_EMA9', 'OBV_EMA255']]
        ######################
        history_all_df['Z_price_vol'] = momentum_indicator().Z_price_vol(close_price=history_all_df['Close'], volume=history_all_df['Volume'])
        history_all_df['Z_price_vol_EMA9'] = moving_average(periods=9).exponential(history_all_df['Z_price_vol'])
        history_all_df['Z_price_vol_EMA255'] = moving_average(periods=255).exponential(history_all_df['Z_price_vol'])
        history_df[['Z_price_vol','Z_price_vol_EMA9','Z_price_vol_EMA255']] = history_all_df[history_all_df['Date'].isin(history_df['Date'])][['Z_price_vol','Z_price_vol_EMA9','Z_price_vol_EMA255']]  
        ######################
        history_all_df['Close_EMA9'], history_all_df['Close_EMA255'] = moving_average(periods=9).exponential(history_all_df['Close']), moving_average(periods=255).exponential(history_all_df['Close'])
        history_df[['Close_EMA9', 'Close_EMA255']] = history_all_df[history_all_df['Date'].isin(history_df['Date'])][['Close_EMA9', 'Close_EMA255']]
        ######################
        self.ticker_data_dict_in_effect['history'] = history_df

    def _ticker_lastdate_pushbutton_clicked(self):
        if self._ticker_selected:
            self._UI.ticker_lastdate_calendar_dialog.exec() # using .exec() instead of .show() to ensure that the dialog stays on the top

    def _ticker_download_latest_data_from_yfinance(self):
        if self._ticker_selected:
            self.ticker_data_dict_original = get_ticker_data_dict(ticker = self.selected_ticker, force_redownload = True, download_today_data=self._UI.app_window.app_menu.preferences_dialog.download_today_data, data_root_dir=self._UI.app_window.app_menu.preferences_dialog.data_root_dir)
            self._ticker_lastdate_dialog_use_last_available_date_button_clicked()
            self.ticker_data_dict_in_effect['info'] = copy.deepcopy(self.ticker_data_dict_original['info'])
            self._UI.ticker_textinfo.setHtml(get_formatted_ticker_data(self.ticker_data_dict_in_effect, use_html=True))
            self._UI.repaint() # to cope with a bug in PyQt5

    def _ticker_lastdate_dialog_use_last_available_date_button_clicked(self):
        self.time_last_date = self.ticker_data_dict_original['history']['Date'].iloc[-1]
        self._UI.ticker_lastdate_calendar_dialog.ticker_lastdate_calendar.setMaximumDate(self.time_last_date)
        self._UI.ticker_lastdate_calendar_dialog.ticker_lastdate_calendar.setSelectedDate(self.time_last_date)
        self._ticker_lastdate_dialog_any_button_clicked()

    def _ticker_lastdate_dialog_ok_button_clicked(self):
        self.time_last_date = pd.to_datetime(self._UI.ticker_lastdate_calendar_dialog.ticker_lastdate_calendar.selectedDate().toPython(), utc=True)
        self._ticker_lastdate_dialog_any_button_clicked()

    def _ticker_lastdate_dialog_any_button_clicked(self):
        if self._UI.ticker_lastdate_calendar_dialog.isVisible():
            self._UI.ticker_lastdate_calendar_dialog.hide()
        self._UI.ticker_lastdate_pushbutton.setText(f"Last Date: {str(self.time_last_date.date())}")
        self._ticker_timeframe_selection_change(self.timeframe_selection_index)

    def _message_dialog_textinfo_ok_button_clicked(self):
        self._UI.message_dialog.hide()


def main(appmenu=None):
    app = QApplication(sys.argv)
    app.setStyleSheet(StyleSheet)
    window = app_window(app=app, appmenu=appmenu)
    window.show()
    app.exec_()


def test():
    return
    for ticker in random.sample(ticker_group_dict['All'], len(ticker_group_dict['All'])):
        print("\n<-------------------------------------------------------------------------------------------")
        print(get_formatted_ticker_data(get_ticker_data_dict(ticker=ticker, force_redownload=False, download_today_data=True, auto_retry=True)))
        print("------------------------------------------------------------------------------------------->\n")
