# optimizer_01.py

import datetime
import multiprocessing
from multiprocessing import Pool
from deap import base, creator, tools, algorithms
import random
import numpy as np
from data_feed.data_feed import BinanceFuturesData
from strat_02 import HeikinAshiStrategy
import backtrader as bt
import pickle


def run_backtest(fast_ema, slow_ema, hma_length, atr_period, atr_threshold, dmi_length, dmi_threshold,
                cmo_period, cmo_threshold, volume_factor_perc, ta_threshold, mfi_period, mfi_level, mfi_smooth,
                sl_percent, kama_period, dma_period, dma_gainlimit, dma_hperiod, fast_ad, slow_ad, 
                fastk_period, fastd_period, mama_fastlimit, mama_slowlimit,
                fetched_data, start_date, end_date, bt_timeframe, compression):
    cerebro = bt.Cerebro(quicknotify=True)    

    cerebro.addobserver(bt.observers.DrawDown, plot=False)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')

    data = BinanceFuturesData(
        dataname=fetched_data,
        fromdate=start_date,
        todate=end_date,
        timeframe=bt_timeframe,
        compression=compression,
    )    

    # Add the data to the backtrader instance
    cerebro.adddata(data)

    # Add resampling    
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
       

    cerebro.addstrategy(
        HeikinAshiStrategy,
        fast_ema=fast_ema,
        slow_ema=slow_ema,
        hma_length=hma_length,
        atr_period=atr_period,
        atr_threshold=atr_threshold,
        dmi_length=dmi_length,        
        dmi_threshold=dmi_threshold,
        cmo_period=cmo_period,
        cmo_threshold=cmo_threshold,
        volume_factor_perc=volume_factor_perc,
        ta_threshold=ta_threshold,
        mfi_period=mfi_period,
        mfi_level=mfi_level,
        mfi_smooth=mfi_smooth,
        sl_percent=sl_percent,
        kama_period=kama_period,
        dma_period=dma_period,
        dma_gainlimit=dma_gainlimit,
        dma_hperiod=dma_hperiod,
        fast_ad=fast_ad,
        slow_ad=slow_ad,
        fastk_period=fastk_period,
        fastd_period=fastd_period,
        mama_fastlimit=mama_fastlimit,
        mama_slowlimit=mama_slowlimit,

    )
        
    results = cerebro.run(runonce=False)
    final_value = cerebro.broker.getvalue()

    print(final_value, results)

    return final_value, results  # return both final_value and results


# Set the ranges for the parameters to optimize
fast_ema_range = range(2, 11)
slow_ema_range = range(5, 25)
hma_length_range = range(4, 30)
atr_period_range = range(1, 30)
atr_threshold_range = range(10, 200)
dmi_length_range = range(2, 20)
dmi_threshold_range = range(5, 75)
cmo_period_range = range(2, 25)
cmo_threshold_range = range(0, 100)
volume_factor_perc_range = range(10, 70)
ta_threshold_range = range(0, 10)
mfi_period_range = range(2, 25)
mfi_level_range = range(0, 100)
mfi_smooth_range = range(1, 15)
sl_percent_range = range(0, 10)
kama_period_range = range(3, 50)
dma_period_range = range(3, 35)
dma_gainlimit_range = range(5, 100)
dma_hperiod_range = range(2, 30)
fast_ad_range = range(2, 20)
slow_ad_range = range(5, 50)
fastk_period_range = range(2, 30)
fastd_period_range = range(2, 30)
mama_fastlimit_range = range(1, 9)
mama_slowlimit_range = range(1, 9)



def evaluate(params, fetched_data, start_date, end_date, bt_timeframe, compression):
    assert len(params) == 25, "params should have exactly 25 elements"
    final_value, results = run_backtest(*params, fetched_data, start_date, end_date, bt_timeframe, compression
                                        )  # capture both final_value and results
    drawdown = results[0].analyzers.drawdown.get_analysis()['max']['drawdown']  # get maximum drawdown
    sqn = results[0].analyzers.sqn.get_analysis()['sqn']  # get sqn    
    net_profit = results[0].analyzers.returns.get_analysis()['rtot']
    trade_analysis = results[0].analyzers.trade_analyzer.get_analysis()
    
    if 'total' in trade_analysis and 'total' in trade_analysis['total']:
        total_trades = trade_analysis.total.total
        if  'won' in trade_analysis and 'total' in trade_analysis['won']:        
            won_total = trade_analysis.won.total

        else:        
            won_total = 0
    else:
        total_trades = 0
        won_total = 0    

    print(final_value, drawdown, sqn, total_trades, won_total, net_profit)
    return final_value, drawdown, sqn, total_trades, won_total, net_profit  # return profit, drawdown, sqn, won_total, net_profit


# Genetic Algorithm
creator.create("FitnessMax", base.Fitness, weights=(1.0, -0.9, 0.9, 0.5, 0.8, 0.4)) # 6 objectives: maximize profit, minimize drawdown, maximize sqn, 
                                                                                    # maximize total_trades, maximize won_total, maximize net_profit
creator.create("Individual", list, fitness=creator.FitnessMax)

toolbox = base.Toolbox()

toolbox.register("attr_fast_ema", lambda: int(random.randint(2, 11)))
toolbox.register("attr_slow_ema", lambda: int(random.randint(5, 25)))
toolbox.register("attr_hma_length", lambda: int(random.randint(4, 30)))
toolbox.register("attr_atr_period", lambda: int(random.randint(1, 30)))
toolbox.register("attr_atr_threshold", lambda: int(round(random.uniform(50, 200))))
toolbox.register("attr_dmi_length", lambda: int(random.randint(2, 20)))
toolbox.register("attr_dmi_threshold", lambda: int(random.randint(5, 75)))
toolbox.register("attr_cmo_period", lambda: int(random.randint(2, 25)))
toolbox.register("attr_cmo_threshold", lambda: int(random.randint(0, 100)))
toolbox.register("attr_volume_factor_perc", lambda: int(random.randint(10, 70)))
toolbox.register("attr_ta_threshold", lambda: int(random.randint(0, 10)))
toolbox.register("attr_mfi_period", lambda: int(random.randint(2, 25)))
toolbox.register("attr_mfi_level", lambda: int(random.randint(0, 100)))
toolbox.register("attr_mfi_smooth", lambda: int(random.randint(1, 15)))
toolbox.register("attr_sl_percent", lambda: int(random.randint(0, 10)))
toolbox.register("attr_kama_period", lambda: int(random.randint(3, 50)))
toolbox.register("attr_dma_period", lambda: int(random.randint(3, 35)))
toolbox.register("attr_dma_gainlimit", lambda: int(random.randint(5, 100)))
toolbox.register("attr_dma_hperiod", lambda: int(random.randint(2, 30)))
toolbox.register("attr_fast_ad", lambda: int(random.randint(2, 20)))
toolbox.register("attr_slow_ad", lambda: int(random.randint(5, 50)))
toolbox.register("attr_fastk_period", lambda: int(random.randint(2, 30)))
toolbox.register("attr_fastd_period", lambda: int(random.randint(2, 30)))
toolbox.register("attr_mama_fastlimit", lambda: int(random.randint(1, 9)))
toolbox.register("attr_mama_slowlimit", lambda: int(random.randint(1, 9)))

toolbox.register("attr_int", random.randint, 1, 100)  # generates random integers between 1 and 100

toolbox.register("individual", tools.initCycle, creator.Individual, (
                toolbox.attr_fast_ema, toolbox.attr_slow_ema, toolbox.attr_hma_length,
                toolbox.attr_atr_period, toolbox.attr_atr_threshold, toolbox.attr_dmi_length,
                toolbox.attr_dmi_threshold, toolbox.attr_cmo_period, toolbox.attr_cmo_threshold,
                toolbox.attr_volume_factor_perc, toolbox.attr_ta_threshold, toolbox.attr_mfi_period, 
                toolbox.attr_mfi_level, toolbox.attr_mfi_smooth, toolbox.attr_sl_percent, 
                toolbox.attr_kama_period, toolbox.attr_dma_period, toolbox.attr_dma_gainlimit, 
                toolbox.attr_dma_hperiod, toolbox.attr_fast_ad, toolbox.attr_slow_ad, toolbox.attr_fastk_period,
                toolbox.attr_fastd_period, toolbox.attr_mama_fastlimit, toolbox.attr_mama_slowlimit)
        , n=1)

attr_ranges = [fast_ema_range, slow_ema_range, hma_length_range, atr_period_range, atr_threshold_range,
              dmi_length_range, dmi_threshold_range, cmo_period_range, cmo_threshold_range, volume_factor_perc_range,
                ta_threshold_range, mfi_period_range, mfi_level_range, mfi_smooth_range, sl_percent_range, 
                kama_period_range, dma_period_range, dma_gainlimit_range, dma_hperiod_range, fast_ad_range, slow_ad_range,
                fastk_period_range, fastd_period_range, mama_fastlimit_range, mama_slowlimit_range]


def custom_mutate(individual, indpb):
    for i in range(len(individual)):
        if random.random() < indpb:
            individual[i] = random.choice(attr_ranges[i])  # Choose a random value from the range of the current attribute
    return individual,

toolbox.register("population", tools.initRepeat, list, toolbox.individual)  # creates the population
toolbox.register("mate", tools.cxTwoPoint)
toolbox.register("mutate", custom_mutate, indpb=0.2)
toolbox.register("select", tools.selNSGA2)  # use NSGA-II selection for multi-objective optimization
toolbox.register("evaluate", evaluate)


def main(symbol, start_date, end_date, bt_timeframe, compression, fetched_data):
    random.seed(42)
    np.random.seed(42)
    multiprocessing.set_start_method("spawn")

    toolbox.register("evaluate", evaluate, fetched_data=fetched_data, start_date=start_date, end_date=end_date,
                     bt_timeframe=bt_timeframe, compression=compression)

    # Use a multiprocessing Pool for the map function
    pool = Pool()
    toolbox.register("map", pool.map)

    pop = toolbox.population(n=55)
    hof = tools.HallOfFame(35)
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("min", np.min)
    stats.register("max", np.max)

    try:
        pop, logbook = algorithms.eaSimple(pop, toolbox, cxpb=0.5, mutpb=0.2, ngen=40, 
                                            stats=stats, halloffame=hof, verbose=True)
        
        # Save best individuals and their fitness to a file
        best_individuals = [(ind, ind.fitness.values) for ind in hof]
        with open('best_individuals.pkl', 'wb') as f:
            pickle.dump(best_individuals, f)

        print("Best parameters found by GA:", hof[0])
        return hof[0]
    
    
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        print(traceback.format_exc())

    finally:
        # Make sure to close the pool when you're done with it
        pool.close()
        pool.join()

    if len(hof) > 0:
        best_params = hof[0]
    else:
        # handle the case when the list is empty, e.g., set a default value or raise an error
        best_params = None
   

    print("Best parameters found by GA:", best_params)

    return best_params

