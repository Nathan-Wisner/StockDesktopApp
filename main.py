# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import requests
import finviz
import pandas as pd
import finnhub
import time
import datetime
import wx

pd.set_option('display.max_columns', None)
finnhub_client = finnhub.Client(api_key="c61n84qad3if6r7ls8u0")

earningsCalendar = finnhub_client.earnings_calendar(_from="2021-12-22", to="2021-12-26", symbol="", international=False)


# Gathers key information like financials, price, etc on a stock
class API():
    overview_dict = {}

    # Gets all company info, financials and key metrics of a stock
    def getOverviewData(self, ticker):
        if not ticker in self.overview_dict:
            url = 'https://www.alphavantage.co/query?function=OVERVIEW&symbol=' + ticker + '&apikey=0376WMLPLJK135HF'
            r = requests.get(url)
            self.overview_dict[ticker] = r.json()
            return r.json()
        else:
            return self.overview_dict[ticker]

    # Returns either the columns data or NONE if there was an error
    def getOverviewColumn(self, raw_data, column):
        try:
            value = raw_data[column]
        except Exception:
            value = None
        return value

    # Gets the current price of a given stock
    def getCurrentPrice(self, stock):
        return finnhub_client.quote(stock)['c']

    def getTechnicalIndicators(self, ticker, indicatorName):
        url = 'https://www.alphavantage.co/query?function='+indicatorName+'&symbol=' + ticker + '&interval=weekly&time_period=14&series_type=close&apikey=0376WMLPLJK135HF'
        r = requests.get(url)
        print(url)
        return list(r.json())[1][0][0]

    # Gets a price of a stock at the closing date
    def getPastPrice(self, stock, beginningDate, endDate):
        begin_unixtime = int(time.mktime(beginningDate.timetuple()))
        end_unixtime = int(time.mktime(endDate.timetuple()))
        return finnhub_client.stock_candles(stock, 'D', begin_unixtime, end_unixtime)['c']


# This class is used to get insider trading, insider transaction counts, etc
class Finviz():

    def __init__(self, stockList=None):
        if stockList is None:
            self.stockLists = StockLists()
        else:
            self.stockLists = stockList
        self.insiderDataDict = {}
        self.api = API()
        self.stockDetailsDict = {}
        for stock in self.stockLists.stock_list:
            self.stockDetailsDict[stock] = {}
            for column in self.stockLists.important_columns:
                raw_data = self.api.getOverviewData(stock)
                self.stockDetailsDict[stock][column] = self.api.getOverviewColumn(raw_data, column)
        self.getAllInsider()


    def updateDetailDict(self):
        self.printAllInsider()
        self.getProjectionRoom()

    def getAllInsider(self):
        for stock in self.stockLists.stock_list:
            self.getInsider(stock)
            self.getTransactionCounts(stock)

    def getInsider(self, ticker):
        if not ticker in self.insiderDataDict:
            try:
                data = finviz.get_insider(ticker)
            except Exception:
                data = "Error with insider info"
            self.insiderDataDict[ticker] = data

        return self.insiderDataDict[ticker]

    def printAllInsider(self):
        for stock in self.stockLists.stock_list:
            self.printInsider(stock)

    def getTransactionCounts(self, ticker):
        sell_count = 0
        buy_count = 0
        total_count = 0

        insider_data = self.getInsider(ticker)

        if insider_data == "Error with insider info":
            return 0, 0

        for trade in insider_data:
            tradeType = trade['Transaction']

            if tradeType == "Sale":
                sell_count += 1
            if tradeType == "Buy":
                buy_count += 1
            if tradeType == 'Buy' or tradeType == 'Sale':
                total_count += 1
        if total_count > 0:
            buy_rate = (buy_count / total_count) * 100
            sell_rate = (sell_count / total_count) * 100
            self.stockDetailsDict[ticker]['BuyRate'] = buy_rate
            self.stockDetailsDict[ticker]['SellRate'] = sell_rate
            self.stockDetailsDict[ticker]['Transactions'] = total_count
        else:
            self.stockDetailsDict[ticker]['BuyRate'] = 0
            self.stockDetailsDict[ticker]['SellRate'] = 0
            self.stockDetailsDict[ticker]['Transactions'] = 0
            buy_rate = 0
            sell_rate = 0

        return buy_rate, sell_rate

    def getEarnings(self, ticker):
        earnings = finnhub_client.company_earnings(ticker, limit=1)
        if not earnings[0]['actual'] is None or earnings[0]['estimate'] is None:
            beat = earnings[0]['actual'] - earnings[0]['estimate']
        else:
            beat = "None Reported"
        self.stockDetailsDict[ticker]['Beat'] = beat
        return beat

    def getProjectionRoom(self):
        for stock in self.stockLists.stock_list:
            raw_data = self.api.getOverviewData(stock)
            analyst_price = self.api.getOverviewColumn(raw_data, 'AnalystTargetPrice')
            high_price = self.api.getOverviewColumn(raw_data, '52WeekHigh')
            if analyst_price is None or high_price is None:
                analyst_price = 0
                high_price = 1
            else:
                analyst_price = float(analyst_price)
                high_price = float(high_price)

            if analyst_price == 0 and high_price == 1:
                left_to_move = 0
            else:
                left_to_move = (analyst_price - high_price) / high_price * 100

            self.stockDetailsDict[stock]['LeftToMove'] = left_to_move
            self.getEarnings(stock)

    def printInsider(self, ticker):
        insider_data = self.getTransactionCounts(ticker)
        print(self.stockDetailsDict)


class StockLists:

    def __init__(self):
        self.api = API()
        self.stock_list = ["MSFT", "PI", "AAPL", "FB", "F", "ENVX", "AMD"]
        self.important_columns = ['MarketCapitalization', 'EVToEBITDA', 'PERatio', 'PEGRatio', 'BookValue', 'EPS',
                                  'AnalystTargetPrice', '50DayMovingAverage', '200DayMovingAverage', 'Price']
        self.custom_columns = ['BuyRate', 'SellRate', 'Transactions', 'LeftToMove']
        self.indicators = ['RSI', 'EMA', 'MACD', 'MOM']
        self.stock_earnings_dict = {}
        self.raw_stock_dict = {}

    def getStockListData(self):
        for stock in self.stock_list:
            self.raw_stock_dict[stock] = self.api.getOverviewData(stock)
            self.raw_stock_dict[stock]['Price'] = self.api.getCurrentPrice(stock)
            if self.raw_stock_dict[stock]['Price'] == 0:
                self.raw_stock_dict[stock]['Price'] = 1

        return self.raw_stock_dict

    def getColumns(self):
        for stock in self.stock_list:
            for column in self.raw_stock_dict[stock]:
                print(column)
            print()

    def updateWithFinfiz(self, fin):
        for stock in self.stock_list:
            for column in self.custom_columns:
                if column in fin.stockDetailsDict[stock]:
                    self.raw_stock_dict[stock][column] = fin.stockDetailsDict[stock][column]
                else:
                    self.raw_stock_dict[stock][column] = 'None Available '


    def printAllNeatly(self):
        for stock in self.stock_list:
            print("#########")
            print()
            print(stock)
            print()
            print('########')
            print()
            for column in self.important_columns:
                print(column, ": ", self.raw_stock_dict[stock][column])
            for column in self.custom_columns:
                print(column, ": ", self.raw_stock_dict[stock][column])

    def printStockNeatly(self, stock):
        print("#########")
        print()
        print(stock)
        print()
        print('########')
        print()
        for column in self.important_columns:
            print(column, ": ", self.raw_stock_dict[stock][column])
        for column in self.custom_columns:
            print(column, ": ", self.raw_stock_dict[stock][column])


class MyPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.row_obj_dict = {}
        self.current_folder_path = None

        self.list_ctrl = wx.ListCtrl(
            self, size=(-1, 100), style=wx.LC_REPORT | wx.BORDER_SUNKEN
        )
        self.list_ctrl.InsertColumn(0, "Stock", width=140)
        self.list_ctrl.InsertColumn(1, "Column", width=140)
        self.list_ctrl.InsertColumn(2, "Data", width=200)
        self.list_ctrl.InsertColumn(3, "Analysis", width=200)
        main_sizer.Add(self.list_ctrl, 1,  wx.EXPAND, 5)

        self.SetSizer(main_sizer)
        # Create the list of stocks
        self.stockLists = StockLists()

        # Get the raw data for every stock
        data = self.stockLists.getStockListData()

        # Get insider info for the stock list stocks
        fin = Finviz()
        fin.getProjectionRoom()
        self.stockLists.updateWithFinfiz(fin)

        self.combo = wx.ComboBox(self, choices=self.stockLists.stock_list)
        basicLabel = wx.StaticText(self, -1, "Enter a symbol not in the database:")
        self.basicText = wx.TextCtrl(self, -1, "TSLA", size=(175, -1))
        self.basicText.SetInsertionPoint(0)
        self.btn = wx.Button(self, -1, "Search")

        main_sizer.AddMany([basicLabel, self.basicText, self.btn])
        main_sizer.Add(self.combo, 0 ,wx.ALL , 5)

        self.btn.Bind(wx.EVT_BUTTON, self.OnButtonClicked)
        self.combo.Bind(wx.EVT_COMBOBOX, self.OnCombo)

        index = 0
        analysisScore = 0
        baseScore = 0
        for stock in self.stockLists.stock_list:
            for column in self.stockLists.important_columns:
                self.list_ctrl.InsertItem(index, stock)
                self.list_ctrl.SetItem(index, 1, column)
                if column in self.stockLists.raw_stock_dict[stock]:
                    self.list_ctrl.SetItem(index, 2, str(self.stockLists.raw_stock_dict[stock][column]))
                    analysisScore += self.GetScore(self.GetAnalysis(column, self.stockLists.raw_stock_dict[stock][column], self.stockLists.raw_stock_dict[stock]))
                    baseScore += 1
                    self.list_ctrl.SetItem(index, 3, str(
                        self.GetAnalysis(column, self.stockLists.raw_stock_dict[stock][column],
                                         self.stockLists.raw_stock_dict[stock])))
                else:
                    self.list_ctrl.SetItem(index, 2, 'None Available')
                    self.list_ctrl.SetItem(index, 3, 'None Available')


            for column in self.stockLists.custom_columns:
                self.list_ctrl.InsertItem(index, stock)
                self.list_ctrl.SetItem(index, 1, column)
                self.list_ctrl.SetItem(index, 2, str(self.stockLists.raw_stock_dict[stock][column]))
                analysisScore += self.GetScore(self.GetAnalysis(column, self.stockLists.raw_stock_dict[stock][column],
                                                                self.stockLists.raw_stock_dict[stock]))
                baseScore += 1
                self.list_ctrl.SetItem(index, 3, str(
                    self.GetAnalysis(column, self.stockLists.raw_stock_dict[stock][column],
                                     self.stockLists.raw_stock_dict[stock])))

            self.list_ctrl.InsertItem(index, stock)
            self.list_ctrl.SetItem(index, 1, "Score")
            self.list_ctrl.SetItem(index, 2, str(float(analysisScore/baseScore) * 100))
            self.list_ctrl.SetItem(index, 3, str(self.GetAnalysis("Score", analysisScore/baseScore, baseScore)))

            index = index + 1
            baseScore = 0
            analysisScore = 0
        self.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick, self.list_ctrl)

    def OnCombo(self, event):
        self.list_ctrl.DeleteAllItems()

        stock = str(self.combo.GetValue())
        index = 0
        analysisScore = 0
        baseScore = 0
        for column in self.stockLists.important_columns:
            self.list_ctrl.InsertItem(index, stock)
            self.list_ctrl.SetItem(index, 1, column)
            if column in self.stockLists.raw_stock_dict[stock]:
                self.list_ctrl.SetItem(index, 2, str(self.stockLists.raw_stock_dict[stock][column]))
                analysisScore += self.GetScore(self.GetAnalysis(column, self.stockLists.raw_stock_dict[stock][column],
                                                                self.stockLists.raw_stock_dict[stock]))
                baseScore += 1
                self.list_ctrl.SetItem(index, 3, str(
                    self.GetAnalysis(column, self.stockLists.raw_stock_dict[stock][column],
                                     self.stockLists.raw_stock_dict[stock])))
            else:
                self.list_ctrl.SetItem(index, 2, 'None Available')
                self.list_ctrl.SetItem(index, 3, 'None Available')

        for column in self.stockLists.custom_columns:
            self.list_ctrl.InsertItem(index, stock)
            self.list_ctrl.SetItem(index, 1, column)
            self.list_ctrl.SetItem(index, 2, str(self.stockLists.raw_stock_dict[stock][column]))
            analysisScore += self.GetScore(self.GetAnalysis(column, self.stockLists.raw_stock_dict[stock][column],
                                                            self.stockLists.raw_stock_dict[stock]))
            baseScore += 1
            self.list_ctrl.SetItem(index, 3, str(
                self.GetAnalysis(column, self.stockLists.raw_stock_dict[stock][column],
                                 self.stockLists.raw_stock_dict[stock])))

        self.list_ctrl.InsertItem(index, stock)
        self.list_ctrl.SetItem(index, 1, "Score")
        self.list_ctrl.SetItem(index, 2, str(float(analysisScore / baseScore) * 100))
        self.list_ctrl.SetItem(index, 3, str(self.GetAnalysis("Score", analysisScore / baseScore, baseScore)))

    def OnColClick(self, event):
        self.list_ctrl.SortItems(self.CompareItems)
        pass

    def OnButtonClicked(self, event):
        self.list_ctrl.DeleteAllItems()
        self.stockLists.stock_list = [self.basicText.GetValue()]

        # Get the raw data for every stock
        self.stockLists.getStockListData()

        # Get insider info for the stock list stocks
        fin = Finviz(self.stockLists)
        fin.getProjectionRoom()
        self.stockLists.updateWithFinfiz(fin)

        stock = self.basicText.GetValue()
        index = 0
        analysisScore = 0
        baseScore = 0
        for column in self.stockLists.important_columns:
            self.list_ctrl.InsertItem(index, stock)
            self.list_ctrl.SetItem(index, 1, column)
            if column in self.stockLists.raw_stock_dict[stock]:
                self.list_ctrl.SetItem(index, 2, str(self.stockLists.raw_stock_dict[stock][column]))
                analysisScore += self.GetScore(self.GetAnalysis(column, self.stockLists.raw_stock_dict[stock][column],
                                                                self.stockLists.raw_stock_dict[stock]))
                baseScore += 1
                self.list_ctrl.SetItem(index, 3, str(
                    self.GetAnalysis(column, self.stockLists.raw_stock_dict[stock][column],
                                     self.stockLists.raw_stock_dict[stock])))
            else:
                self.list_ctrl.SetItem(index, 2, 'None Available')
                self.list_ctrl.SetItem(index, 3, 'None Available')

        for column in self.stockLists.custom_columns:
            self.list_ctrl.InsertItem(index, stock)
            self.list_ctrl.SetItem(index, 1, column)
            self.list_ctrl.SetItem(index, 2, str(self.stockLists.raw_stock_dict[stock][column]))
            analysisScore += self.GetScore(self.GetAnalysis(column, self.stockLists.raw_stock_dict[stock][column],
                                                            self.stockLists.raw_stock_dict[stock]))
            baseScore += 1
            self.list_ctrl.SetItem(index, 3, str(
                self.GetAnalysis(column, self.stockLists.raw_stock_dict[stock][column],
                                 self.stockLists.raw_stock_dict[stock])))

        self.list_ctrl.InsertItem(index, stock)
        self.list_ctrl.SetItem(index, 1, "Score")
        self.list_ctrl.SetItem(index, 2, str(float(analysisScore / baseScore) * 100))
        self.list_ctrl.SetItem(index, 3, str(self.GetAnalysis("Score", analysisScore / baseScore, baseScore)))

    def GetScore(self, analysis):
        if analysis == "Good":
            return 2
        elif analysis == "Okay":
            return 1
        elif analysis == "Bad":
            return 0
        else:
            return 1

    def CompareItems(self, item1, item2):
        return item1 - item2

    def GetAnalysis(self, column, data, dict):

        if data == "Not Available" or data is None:
            return "Not Available"
        try:
            data = float(data)
        except ValueError:
            return "Error, not an int"
        if column == "Score":
            if data > 1:
                return "Good, most metrics are either good or okay with maybe a few bad items. Check out if the bull " \
                       "run can continue"
            if data > 0.5:
                return "Okay, there are more bad metrics than good metrics. Is this common? What are the bad metrics?"
            else:
                return "Bad, there are a lot of bad metrics. Is this expected? Is the stock in a downtrun?"

        if column == "PERatio":
            if data < 30:
                return "Good"
            elif data < 50:
                return "Okay"
            else:
                return "Bad"
        if column == "PEGRatio":
            if data > 1:
                return "Okay"
            else:
                return "Bad"
        if column == "BookValue":
            PoB = dict['Price'] / data
            if PoB < 1:
                return "Good"
            elif PoB < 3:
                return "Okay"
            else:
                return "Bad"
        if column == "AnalystTargetPrice":
            price = dict['Price']
            diff = data - price

            if diff > 0:
                return "Good"
            elif diff > -15:
                return "Okay"
            else:
                return "Bad"

        if column == "EPS":
            if data < 5:
                return "Bad"
            elif data < 20:
                return "Okay"
            else:
                return "Good"

        if column == "BuyRate":
            if data > 50:
                return "Good"
            else:
                return "Okay"

        if column == "SellRate":
            if data < 50:
                return "Good"
            else:
                return "Okay"

        if column == "Transactions":
            if data > 10:
                return "Good"
            else:
                return "Okay"
        if column == "LeftToMove":
            if data > 0:
                return "Good"
            elif data > -15:
                return "Okay"
            else:
                return "Bad"

        if column == "50DayMovingAverage":
            price = dict['Price']
            diff = price - data
            diffPercent = diff / price

            if diffPercent > 5:
                return "Good"
            elif diffPercent > 0:
                return "Okay"
            else:
                return "Bad"

        if column == "200DayMovingAverage":
            price = dict['Price']
            diff = price - data
            diffPercent = diff / price

            if diffPercent > 15:
                return "Good"
            elif diffPercent > -5:
                return "Okay"
            else:
                return "Bad"

        if column == "EVToEBITDA":
            if data - 20 > 0:
                return "Good"
            elif data - 30 > 0:
                return "Okay"
            else:
                return "Bad"



class MyFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="Wx Finance")
        self.panel = MyPanel(self)
        self.Show()



if __name__ == "__main__":
    app = wx.App(False)
    frame = MyFrame()
    app.MainLoop()
