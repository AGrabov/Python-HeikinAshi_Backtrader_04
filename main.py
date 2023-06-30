# main.py
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


from concurrent import futures
from doctest import debug
import backtrader as bt
from matplotlib.pyplot import plot
from deap import base, creator, tools, algorithms
import datetime as dt
from tabulate import tabulate
from trade_list_analyzer import trade_list
import numpy as np
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import quantstats as qs
import pandas as pd
# import pyfolio as pf
import os
import json
from ccxtbt import CCXTStore, CCXTFeed
import time

from data_feed.data_feed import BinanceFuturesData
from strat_02 import HeikinAshiStrategy
from optimizer_01 import main

import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# Settings
target_coin = 'GMT'
base_currency = 'USDT' # 'BUSD' # 
symbol = target_coin + base_currency
dataname = (f'{target_coin}/{base_currency}')
start_date = dt.datetime.strptime("2023-06-01 00:00:00", "%Y-%m-%d %H:%M:%S")
end_date = dt.datetime.strptime("2023-06-25 00:00:00", "%Y-%m-%d %H:%M:%S")
timeframe =  'Minutes' #   'Hours' #  
compression = 30
use_optimization = False


def convert_to_binance_timeframe(compression, timeframe):

    # Determine the Backtrader timeframe
    if timeframe == 'Minutes':
        bt_timeframe = bt.TimeFrame.Minutes
    elif timeframe == 'Hours':
        if compression not in [1, 2, 3, 4, 6, 8, 12]:
            raise ValueError(
                f'Invalid hourly compression for Binance: {compression}. Supported values are 1, 2, 3, 4, 6, 8, 12.')
        bt_timeframe = bt.TimeFrame.Minutes
        compression *= 60  # Convert hours to minutes
    elif timeframe == 'Days':
        bt_timeframe = bt.TimeFrame.Days
        compression *= 24 * 60  # Convert days to minutes
    elif timeframe == 'Weeks':
        bt_timeframe = bt.TimeFrame.Weeks
        compression *= 7 * 24 * 60  # Convert weeks to minutes
    elif timeframe == 'Months':
        bt_timeframe = bt.TimeFrame.Months
        compression *= 30 * 24 * 60  # Convert months to minutes
    else:
        raise ValueError(f'Invalid timeframe: {timeframe}')

    # Determine the Binance timeframe
    binance_timeframe = str(compression)
    if timeframe == 'Minutes':
        binance_timeframe += 'm'
    elif timeframe == 'Hours':
        binance_timeframe = str(compression // 60) + 'h'  # Binance expects the compression in hours
    elif timeframe == 'Days':
        binance_timeframe += 'd'
    elif timeframe == 'Weeks':
        binance_timeframe += 'w'
    elif timeframe == 'Months':
        binance_timeframe += 'M'

    # Validate Binance timeframe
    valid_binance_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '3h', '4h', '6h', '8h', '12h', '1d', '3d',
                                '1w', '1M']
    if binance_timeframe not in valid_binance_timeframes:
        raise ValueError(f'Invalid Binance timeframe: {binance_timeframe}')

    return bt_timeframe, compression, binance_timeframe


if __name__ == '__main__':

    # Ensure multiprocessing is supported
    multiprocessing.freeze_support()    

    # Convert the specified timeframe to a Binance-compatible timeframe
    bt_timeframe, compression, binance_timeframe = convert_to_binance_timeframe(compression, timeframe)

    # Fetch the data for the specified symbol and time range
    fetched_data = BinanceFuturesData.fetch_data(symbol, start_date, end_date, binance_timeframe)

    if use_optimization:
        # Use the optimizer to find the best parameters for the strategy
        best_params = main(symbol, start_date, end_date, bt_timeframe, compression, fetched_data)
    else:
        # Use the default parameters from the strategy
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
    cerebro = bt.Cerebro(quicknotify=True, tradehistory=True)

    # Add observers
    cerebro.addobserver(bt.observers.DrawDown, plot=False)

    # Add the analyzers we are interested in
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    # cerebro.addanalyzer(bt.analyzers.Calmar, _name='calmar_ratio')
    cerebro.addanalyzer(trade_list, _name='trade_list')
    
    

    # Pass the fetched data to the BinanceFuturesData class
    data = BinanceFuturesData(
        dataname=fetched_data,
        fromdate=start_date,
        todate=end_date,
        timeframe=bt_timeframe,
        compression=compression,
    )

    

    # # absolute dir the script is in
    # script_dir = os.path.dirname(__file__)
    # abs_file_path = os.path.join(script_dir, '../params.json')
    # with open('.\params.json', 'r') as f:
    #     params = json.load(f)

    # # Create a CCXTStore and Data Feed
    # config = {'apiKey': params["binance"]["apikey"],
    #         'secret': params["binance"]["secret"],
    #         'enableRateLimit': True,
    #         'nonce': lambda: str(int(time.time() * 1000)),
    #         'options': { 'defaultType': 'future' },
    #         }    

    # data = CCXTFeed(exchange='binanceusdm',
    #                          dataname=symbol,
    #                          currency=base_currency,                                
    #                          fromdate=start_date,
    #                          todate=end_date,
    #                          timeframe=bt.TimeFrame.Minutes,
    #                          compression=1,
    #                          ohlcv_limit=99999,
    #                          
    #                          retries=5,
    #                          config=config)

    # Add the data to the cerebro
    cerebro.adddata(data, name=dataname)

    # # Add resampling    
    # data1 = cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=60*24)
    data1 = cerebro.resampledata(data, timeframe=bt.TimeFrame.Days, compression=1)
    data1.plotinfo.plot = False

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

    # Add the strategy to the cerebro
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

    # Run the strategy and get the instance
    strat = cerebro.run(quicknotify=True, tradehistory=True, runonce=False)[0]     

    # Plot
    cerebro.plot(style='candlestick', start=start_date, end=end_date)  # 
    
    # Results
    final_value = cerebro.broker.getvalue()
    profit = final_value - starting_cash # Obtain net profit
    profit_percentage = (profit / starting_cash) * 100
    max_drawdown = strat.analyzers.drawdown.get_analysis()['max']['drawdown']
    max_drawdown_len = strat.analyzers.drawdown.get_analysis()['max']['len']     
    sqn = strat.analyzers.sqn.get_analysis()['sqn']
    sqn_trades = strat.analyzers.sqn.get_analysis()['trades']
    net_profit = strat.analyzers.returns.get_analysis()['rtot']
    
    # Trade analysis / PnL
    total_trades = strat.analyzers.trade_analyzer.get_analysis()['total']['total']
    trade_analysis = strat.analyzers.trade_analyzer.get_analysis()    
    total_pnl = trade_analysis.pnl.net.total
    average_pnl = trade_analysis.pnl.net.average

    # Win / Loss
    won_count = trade_analysis.won.total
    won_total_pnl = trade_analysis.won.pnl.total
    won_average_pnl = trade_analysis.won.pnl.average
    won_max_pnl = trade_analysis.won.pnl.max    
    lost_count = trade_analysis.lost.total
    lost_total_pnl = trade_analysis.lost.pnl.total
    lost_average_pnl = trade_analysis.lost.pnl.average
    lost_max_pnl = trade_analysis.lost.pnl.max
    won_trades_perc = (won_count / total_trades) * 100
    lost_trades_perc = (lost_count / total_trades) * 100

    # Long / Short
    long_total_trades = trade_analysis.long.total
    short_total_trades = trade_analysis.short.total
    long_won_trades = trade_analysis.long.won
    long_lost_trades = trade_analysis.long.lost  
    short_won_trades = trade_analysis.short.won
    short_lost_trades = trade_analysis.short.lost

    # Long / Short PnL
    long_total_pnl = trade_analysis.long.pnl.total
    long_avg_pnl = trade_analysis.long.pnl.average    
    short_total_pnl = trade_analysis.short.pnl.total
    short_avg_pnl = trade_analysis.short.pnl.average        
        
    # Get the trade list
    trade_list = strat.analyzers.trade_list.get_analysis()
    
    # Printing out the results

    # Print out the trade list
    print (tabulate(trade_list, headers="keys", tablefmt="psql", missingval="?"))
    print()
    print()

    # Print out the best parameters
    print("Best parameters found by GA:", best_params)
    print()   

    # Print out the statistics
    print("$" * 77)
    print(f"Liquid value of the portfolio: {final_value:.2f} $")  # Liquid value of the portfolio    
    print()
    print(f"Total trades: {total_trades}")
    print(f"SQN: {sqn:.2f}")
    print(f"SQN trades: {sqn_trades}")
    print(f"Net profit: {net_profit:.2f}")
    print(f"Max drawdown: {max_drawdown:.2f}")      
    print()
    print(f"Total PnL: {total_pnl:.2f}, Average PnL: {average_pnl:.2f}")    
    print(f"Profitable trades %: {won_trades_perc:.2f}")
    print()
    print(f"Won Trades: {won_count}: Won PnL(total): {won_total_pnl:.2f}, Won PnL(avg): {won_average_pnl:.2f}, Won PnL(max): {won_max_pnl:.2f}")    
    print(f"Lost Trades: {lost_count}: Lost PnL(total): {lost_total_pnl:.2f}, Lost PnL(avg): {lost_average_pnl:.2f}, Lost PnL(max): {lost_max_pnl:.2f}")    
    print()
    print(f"Long  == Won: {long_won_trades} / {long_total_trades}, Lost: {long_lost_trades} / {long_total_trades}")
    print(f"\t PnL(total): {long_total_pnl:.2f}, PnL(avg): {long_avg_pnl:.2f}")
    print()
    print(f"Short == Won: {short_won_trades} / {short_total_trades}, Lost: {short_lost_trades} / {short_total_trades}")
    print(f"\t PnL(total): {short_total_pnl:.2f}, PnL(avg): {short_avg_pnl:.2f}")   
    print()   
    print("$" * 77)

    # Save the results in a json file

    # Create the directory if it does not exist
    os.makedirs(f'backtests_results_18/{target_coin}', exist_ok=True)

    # Save the results in a json file
    symbol_name = symbol.replace('/', '_')  # Replace '/' with '_'
    filename = f'backtests_results_18/{target_coin}/btest_results_{symbol_name}_{binance_timeframe}.json'

    data = {
        'symbol': symbol,
        'timeframe': binance_timeframe,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'best_params': best_params,
        'profit': round(profit, 2),
        'profit_percentage': round(profit_percentage, 2),
        'max_drawdown': round(max_drawdown, 2),
        'sqn': round(sqn, 2),
        'total_trades': total_trades,        
        'won_total': round(won_count, 2),
        'net_profit': round(net_profit, 2),
        
        

    }

    # Check if the file exists
    if os.path.isfile(filename):
        # If the file exists, open it and load the data
        with open(filename, 'r') as f:
            existing_data = json.load(f)
        print(existing_data)


        # Check if any existing data has the same symbol, timeframe, and date range
        for entry in existing_data:
            if (entry['symbol'] == data['symbol'] and 
                entry['timeframe'] == data['timeframe'] and 
                entry['start_date'] == data['start_date'] and 
                entry['end_date'] == data['end_date']):
                
                # If it does and the new profit is larger, update this entry
                if (entry['profit'] < data['profit']) and (entry['sqn'] < data['sqn']):
                    entry['best_params'] = data['best_params']
                    entry['profit'] = data['profit']                    
                    entry['profit_percentage'] = data['profit_percentage']
                    entry['max_drawdown'] = data['max_drawdown']
                    entry['sqn'] = data['sqn']                    
                    entry['net_profit'] = data['net_profit']
                    entry['total_trades'] = data['total_trades']
                    entry['won_total'] = data['won_total']
                    
                
                # In this case, don't append new data
                break
        else:
            # If no matching entry was found, append the new data
            existing_data.append(data)

        # Write the updated data back to the file
        with open(filename, 'w') as f:
            json.dump(existing_data, f, indent=4)
    else:
        # If the file does not exist, create it with the new data in a list
        with open(filename, 'w') as f:
            json.dump([data], f, indent=4)


