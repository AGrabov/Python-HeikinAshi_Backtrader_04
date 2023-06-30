# live_trading.py
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


import backtrader as bt
from ccxtbt import CCXTStore
from strat_02 import HeikinAshiStrategy
import api_config
import os
import json
import time
import datetime as dt
from tabulate import tabulate
from trade_list_analyzer import trade_list


# Settings
target_coin = 'GMT'
base_currency = 'USDT'
symbol = target_coin + base_currency
timeframe = bt.TimeFrame.Minutes
compression = 30  # For live trading, you typically want to use smaller timeframes
use_optimization = False
best_params = (
            HeikinAshiStrategy.params.fast_ema,
            HeikinAshiStrategy.params.slow_ema,
            HeikinAshiStrategy.params.hma_length,
            HeikinAshiStrategy.params.atr_period,
            HeikinAshiStrategy.params.atr_threshold,
            HeikinAshiStrategy.params.dmi_length,            
            HeikinAshiStrategy.params.dmi_threshold,
            HeikinAshiStrategy.params.cmo_period,
            HeikinAshiStrategy.params.cmo_threshold,
            HeikinAshiStrategy.params.volume_factor_perc,
            HeikinAshiStrategy.params.ta_threshold,
            HeikinAshiStrategy.params.mfi_period,
            HeikinAshiStrategy.params.mfi_level,
            HeikinAshiStrategy.params.mfi_smooth,
            HeikinAshiStrategy.params.sl_percent,
            HeikinAshiStrategy.params.kama_period,
            HeikinAshiStrategy.params.dma_period,
            HeikinAshiStrategy.params.dma_gainlimit,
            HeikinAshiStrategy.params.dma_hperiod,
            HeikinAshiStrategy.params.fast_ad,
            HeikinAshiStrategy.params.slow_ad,
            HeikinAshiStrategy.params.fastk_period,
            HeikinAshiStrategy.params.fastd_period,
            HeikinAshiStrategy.params.mama_fastlimit,
            HeikinAshiStrategy.params.mama_slowlimit
)  # Retrieve default values from the strategy class


# Create a new backtrader instance
cerebro = bt.Cerebro(quicknotify=True, runonce=False)



# Add the analyzers we are interested in
cerebro.addobserver(bt.observers.DrawDown, plot=False)

cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(trade_list, _name='trade_list')



# absolute dir the script is in
script_dir = os.path.dirname(__file__)
abs_file_path = os.path.join(script_dir, '../params.json')
with open('.\params.json', 'r') as f:
    params = json.load(f)

# Create a CCXTStore and Data Feed
config = {'apiKey': params["binance"]["apikey"],
          'secret': params["binance"]["secret"],
          'enableRateLimit': True,
          'nonce': lambda: str(int(time.time() * 1000)),
          
          }

store = CCXTStore(exchange='binanceusdm', currency=base_currency, config=config, retries=10) #, debug=True) #, sandbox=True)

# store.exchange.setSandboxMode(True)

broker_mapping = {
    'order_types': {
        bt.Order.Market: 'market',
        bt.Order.Limit: 'limit',
        bt.Order.Stop: 'stop-loss', #stop-loss for kraken, stop for bitmex
        bt.Order.StopLimit: 'stop limit'
    },
    'mappings':{
        'closed_order':{
            'key': 'status',
            'value':'closed'
        },
        'canceled_order':{
            'key': 'result',
            'value':1}
    }
}

# broker = store.getbroker(broker_mapping=broker_mapping)
# cerebro.setbroker(broker)
# cerebro.broker.setcommission(leverage=10.0) 

# Set the starting cash and commission
starting_cash = 100
cerebro.broker.setcash(starting_cash)
cerebro.broker.setcommission(
    automargin=True,         
    leverage=10.0, 
    commission=0.0004, 
    commtype=bt.CommInfoBase.COMM_PERC,
    stocklike=True,
)  

hist_start_date = dt.datetime.utcnow() - dt.timedelta(days=30*1)
dataname = (f'{target_coin}/{base_currency}')
# ftech_data = store.getdata(dataname=dataname, name=symbol, from_date=hist_start_date, 
#                      timeframe=bt.TimeFrame.Minutes, compression=15, ohlcv_limit=50000, drop_newest=True)
# ftech_data.plotinfo.plot = False
data = store.getdata(dataname=dataname, name=symbol, from_date=hist_start_date, 
                     timeframe=timeframe, compression=5, ohlcv_limit=50000, drop_newest=True)
data.plotinfo.plot = False
cerebro.adddata(data, name=symbol)
data0 = cerebro.resampledata(data, timeframe=timeframe, compression=compression)

data1 = cerebro.resampledata(data0, timeframe=bt.TimeFrame.Days, compression=1)
data1.plotinfo.plot = False

# Add your strategy
cerebro.addstrategy(
        HeikinAshiStrategy,
        fast_ema=best_params[0],
        slow_ema=best_params[1],
        hma_length=best_params[2],
        atr_period=best_params[3],
        atr_threshold=best_params[4],
        dmi_length=best_params[5],        
        dmi_threshold=best_params[6],
        cmo_period=best_params[7],
        cmo_threshold=best_params[8],
        volume_factor_perc=best_params[9],
        ta_threshold=best_params[10],
        mfi_period=best_params[11],
        mfi_level=best_params[12],
        mfi_smooth=best_params[13],
        sl_percent=best_params[14],
        kama_period=best_params[15],
        dma_period=best_params[16],
        dma_gainlimit=best_params[17],
        dma_hperiod=best_params[18],
        fast_ad=best_params[19],
        slow_ad=best_params[20],
        fastk_period=best_params[21],
        fastd_period=best_params[22],
        mama_fastlimit=best_params[23],
        mama_slowlimit=best_params[24]
)
# Add the data to the backtrader instance
# cerebro.adddata(data0, name=symbol)

# Run the strategy
strat = cerebro.run(quicknotify=True, runonce=False, tradehistory=True)[0]

# Get the trade list
trade_list = strat[0].analyzers.trade_list.get_analysis()
    
# Printing out the results

# Print out the trade list
print (tabulate(trade_list, headers="keys", tablefmt="psql", missingval="?"))
print()
print()

cerebro.plot()
