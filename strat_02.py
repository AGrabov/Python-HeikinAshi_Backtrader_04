# strat_01.py

from collections import deque, defaultdict
import backtrader as bt
import numpy as np

from ccxtbt import CCXTStore

from indicators.heikin_patterns_01 import HeikinPatterns
from indicators.movavs import MovAverages
from indicators.linear_regress1 import LinearRegress
from indicators.ta_patterns_02 import TaPatterns

class HeikinAshiStrategy(bt.Strategy):    
    params = {
        'fast_ema': 6,                # GMT # Best parameters found by GA: [6, 20, 16, 8, 54, 9, 18, 13, 3, 29, 10, 10, 76, 16, 1]
        'slow_ema': 20,
        'hma_length': 16,
        'atr_period': 8,
        'atr_threshold': 50,
        'dmi_length': 9,        
        'dmi_threshold': 18,
        'cmo_period': 13,
        'cmo_threshold': 3,
        'volume_factor_perc': 25,  # Volume must be 2 times the average volume
        'ta_threshold': 10,
        'mfi_period': 10,
        'mfi_level': 65,
        'mfi_smooth': 7,
        'sl_percent': 5,  
        'kama_period': 8, 
        'dma_period': 26, 
        'dma_gainlimit': 20,
        'dma_hperiod': 8,
        'fast_ad': 3,
        'slow_ad': 10, 
        'fastk_period': 5,
        'fastd_period': 3,
        'mama_fastlimit': 5,
        'mama_slowlimit': 5,
        'num_past_trades': 10,
        'bb_period': 21,
        'bb_up': 21, 
        'bb_dn': 21,        
        'stoch_treshold': 0,
        'ult_period1': 5,
        'ult_period2': 10,
        'ult_period3': 25,
        'lineregre_period': 15     
        
                
    }
    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.data.datetime[0]
        if isinstance(dt, float):
            dt = bt.num2date(dt)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.values = []        
        self.current_position_size = 0
        self.long_position = False
        self.long_entry_price = 0
        self.short_entry_price = 0
        self.entry_price = 0
        self.order = None
        self.in_position = 0
        self.kelly_coef = 0
        # self.lines.movav = 0
        self.pp = []
        # self.pp = defaultdict(list)
        self.past_trades = deque(maxlen=self.params.num_past_trades)  # Store the past trades
        self.multi_df = True

        # HeikinAshi
        self.ha = bt.indicators.HeikinAshi(self.data0)
        self.ha.plotlines.ha_high._plotskip=True 
        self.ha.plotlines.ha_low._plotskip=True
        self.ha.plotlines.ha_open._plotskip=True
        self.ha.plotlines.ha_close._plotskip=True
        
        self.ha_green = (self.ha.lines.ha_close > self.ha.lines.ha_open)
        self.ha_red = (self.ha.lines.ha_close < self.ha.lines.ha_open)

        # Heikin Ashi Patterns
        self.patterns = HeikinPatterns(self.data0, plot=False)
        # self.patterns.plotlines.signal._plotskip=True
        self.patterns.plotlines.stop_signal._plotskip=True

        self.pattern_buy1 = (self.patterns.lines.signal == 1)
        self.pattern_sell1 = (self.patterns.lines.signal == -1)
        self.pattern_stopBuy1 = (self.patterns.lines.stop_signal == 1)
        self.pattern_stopSell1 = (self.patterns.lines.stop_signal == -1)

        # TA-lib Patterns
        self.ta_patterns = TaPatterns(self.data0, 
                                      threshold=self.params.ta_threshold*100, 
                                      plot=False)

        # Moving averages
        self.movav = MovAverages(self.data0.close, 
                                 fast_ema=self.params.fast_ema, 
                                 slow_ema=self.params.slow_ema, 
                                 hma_length=self.params.hma_length,
                                 kama_period= self.params.kama_period,
                                 dma_period= self.params.dma_period,
                                 dma_gainlimit= self.params.dma_gainlimit,
                                 dma_hperiod= self.params.dma_hperiod, plot=False
                                 )
        # self.movav.plotlines.signal._plotskip=True
        # self.movav.plotlines.stop_signal._plotskip=True
        self.mas_buy = (self.movav.lines.signal == 1)
        self.mas_sell = (self.movav.lines.signal == -1)
        self.mas_stop_buy = (self.movav.lines.stop_signal == 1)
        self.mas_stop_sell = (self.movav.lines.stop_signal == -1)

        

        # # Hull movav Oscillator
        self.hmo = bt.indicators.HullMovingAverageOscillator(self.data0.close, period=self.params.hma_length, plot=False)
        self.hmo_buy1 = (self.hmo.hma > 0.0)
        self.hmo_sell1 = (self.hmo.hma < 0.0)

        # Dicson Moving Average Oscillator
        self.dma_osc = bt.indicators.DMAOscillator(self.data0.close,
                                                    period=self.params.dma_period,
                                                    gainlimit =self.params.dma_gainlimit,
                                                    hperiod = self.params.dma_hperiod, 
                                                    plot=False
                                                    )
        self.dma_osc_buy = (self.dma_osc > 0.0)
        self.dma_osc_sell = (self.dma_osc < 0.0)        

        # KAMA Oscillator
        self.kama_osc = bt.indicators.KAMAOsc(self.data0.close,
                                            period=self.params.kama_period,
                                            fast=5,
                                            slow=15, plot=False)
        
        self.kama_osc_buy1 = (self.kama_osc > 0.0)
        self.kama_osc_sell1 = (self.kama_osc < 0.0)        
               

        self.simple_ma = bt.talib.SMA(self.data0.close, timeperiod=50)
        # self.sma_cross = bt.indicators.CrossOver(self.data0.close, self.simple_ma)
        # self.sma_buy = (self.sma_cross > 0)

        # MAVP
        periods =np.array([2,3,3,2], dtype=float)
        self.mavp = bt.talib.MAVP(price=self.data0, periods=periods, minperiod=2, maxperiod=25)
        

        # MAMA

        self.mama = bt.talib.MAMA(self.data0.close, 
                                  fastlimit=(self.params.mama_fastlimit/10), 
                                  slowlimit=(self.params.mama_slowlimit/100),
                                  )
        self.mama_cross = bt.indicators.CrossOver(self.mama.mama, self.mama.fama)
        self.mama_buy = (self.mama_cross > 0)
        self.mama_sell = (self.mama_cross < 0)

        # Keltner Channels
        # self.kch = bt.talib.KeltnerChannel(self.data0, timeperiod=self.params.kch_period, nbdevup=self.params.kch_up, nbdevdn=self.params.kch_dn, plot=False)
        # self.lr = LinearRegress(self.ha, timeperiod=self.params.lineregre_period).lines.lr_signal

        # Bollinger Bands
        # self.b_bands = bt.talib.BBANDS(self.ha.lines.ha_close,
        #                                timeperiod=self.params.bb_period,
        #                                nbdevup=(self.params.bb_up/10),
        #                                nbdevdn=(self.params.bb_dn/10),
        #                                matype=0)
        # self.bb_up = self.b_bands.lines.upperband
        # self.bb_dn = self.b_bands.lines.lowerband
        # self.bb_mid = self.b_bands.lines.middleband

        # Chaikin A/D Oscillator
        self.ad_osc = bt.talib.ADOSC(self.data0.high, self.data0.low, 
                                     self.data0.close, self.data0.volume, 
                                     fastperiod=self.params.fast_ad,
                                    slowperiod=self.params.slow_ad, plot=False)        
        
        self.ad_osc_buy1 = (self.ad_osc > 0.0)
        self.ad_osc_sell1 = (self.ad_osc < 0.0)
        
        # Stochastic oscillator
        self.stoch = bt.talib.STOCHF(self.data0.high, 
                                    self.data0.low, 
                                    self.data0.close, 
                                    fastk_period=self.params.fastk_period, 
                                    fastd_period=self.params.fastd_period, 
                                    # fastd_matype=self.params.fastd_matype,
                                    plot=False
                                    )
        self.stoch_k = self.stoch.lines.fastk
        self.stoch_d = self.stoch.lines.fastd
        

        self.stoch_buy1 = (self.stoch_k > self.stoch_d) #bt.And((self.stoch_k > self.stoch_d),
                                #  (self.stoch_k < 20),
                                #  (self.stoch_d < 20))
                                 
        self.stoch_sell1 = (self.stoch_k < self.stoch_d) # bt.And((self.stoch_k < self.stoch_d),
                                #   (self.stoch_k > 80),
                                #   (self.stoch_d > 80))

        # Aroon Oscillator
        # self.aroon = bt.talib.AROONOSC(self.data0.high, 
        #                                 self.data0.low,                                    
        #                                 timeperiod=self.params.ult_period1,)
        # self.aroon_buy1 = (self.aroon > 0)
        # self.aroon_sell1 = (self.aroon < 0)

        # CMO
        self.cmo = bt.talib.CMO(self.data0, timeperiod=self.params.cmo_period, plot=False)
        self.cmo_buy = self.cmo.real > (self.params.cmo_threshold)
        self.cmo_sell = self.cmo.real < -(self.params.cmo_threshold)


        # ATR 
        self.atr = bt.talib.NATR(self.data0.high, 
                                 self.data0.low, 
                                 self.data0.close, 
                                 timeperiod=self.params.atr_period, 
                                 plotyhlines=[0.5, 1.0, 1.5], 
                                 plot=False)
        # self.atr = bt.talib.NATR(self.ha.lines.ha_high, self.ha.lines.ha_low, self.ha.lines.ha_close, 
        #                          timeperiod=self.params.atr_period, plotyhlines=[0.5, 1.0, 1.5])
        self.high_volatility = (self.atr.real  >  (self.params.atr_threshold / 100)) 
        

        # ADX
        self.dmi = bt.indicators.DirectionalMovementIndex(self.data0, period=self.params.dmi_length,  plot=False)
        # self.adx = bt.talib.ADX(self.data0.high, self.data0.low, self.data0.close, 
        #                         timeperiod=self.params.dmi_length, plot=False) 
        self.adx = bt.talib.ADXR(self.data0.high, 
                                 self.data0.low, 
                                 self.data0.close, 
                                 timeperiod=self.params.dmi_length,  
                                 plot=False)      
        # self.adx_signal = bt.And((self.dmi.DIplus > self.dmi.DIminus),(self.adx.real > self.params.dmi_threshold))
        self.adx_buy = bt.And((self.dmi.DIplus > self.dmi.DIminus), (self.adx.real > self.params.dmi_threshold))
        self.adx_sell = bt.And((self.dmi.DIplus < self.dmi.DIminus), (self.adx.real > self.params.dmi_threshold))


        # Volume filter
        self.volume_averages = (bt.indicators.SMA(self.data0.volume, 
                                                  period=self.params.slow_ema, 
                                                  plot=False) * 
                                (self.params.volume_factor_perc / 10))
        self.volume_filter = (self.data0.volume > self.volume_averages)
        

        # MFI
        # self.mfi = bt.talib.MFI(self.data0.high, self.data0.low, self.data0.close, self.data0.volume,
        #                         timeperiod=self.params.mfi_period)
        self.mfi = bt.talib.MFI(self.ha.lines.ha_high, 
                                self.ha.lines.ha_low, 
                                self.ha.lines.ha_close, 
                                self.data0.volume,
                                timeperiod=self.params.mfi_period)
        # self.mfi.plotlines.real._plotskip=True
        self.mfi.plotinfo.plothlines = [self.params.mfi_level]
        self.mfi_smoothed = bt.indicators.ExponentialMovingAverage(self.mfi, period=self.params.mfi_smooth)
        self.mfi_smoothed.plotinfo.plotname = 'MFI smoothed'
        self.mfi_smoothed.plotlines.ema._plotskip=True

        self.mfi = self.mfi.real # self.mfi_smoothed.lines.ema # 
        self.mfi_cross = bt.ind.CrossOver(self.mfi, self.params.mfi_level, plot=False)

        self.mfi_buy = bt.Or((self.mfi_cross == 1), (self.mfi > self.params.mfi_level))
        self.mfi_sell = bt.Or((self.mfi_cross == -1), (self.mfi < self.params.mfi_level))

        # self.close_smoothed = bt.indicators.ExpSmoothing(self.ha.lines.ha_close, period=self.params.mfi_smooth, alpha=0.1)

        
        
        
        
        # Pivot Point levels
        self.pp = pp = bt.indicators.PivotPoint(self.data1, open=True, _autoplot=False) # 
        pp.plotinfo.plot = False  # deactivate plotting    

        # self.p = self.pp()
        self.s1 = self.pp.s1()
        self.s2 = self.pp.s2()
        self.r1 = self.pp.r1()
        self.r2 = self.pp.r2()

        self.order = None        
        self.entry_price = None
        

    def pivot_buy(self):
        pivot_buy1 = (self.ha.lines.ha_close[0] > self.s1[0]) and \
                     (self.ha.lines.ha_close[-1] < self.s1[0]) and \
                     (self.ha.lines.ha_close[-2] >= self.s1[0]) and \
                     (self.ha.lines.ha_close[-3] >= self.s1[0]) and \
                     (self.ha.lines.ha_close[-1] < self.ha.lines.ha_close[0])
        
        pivot_buy2 = (self.ha.lines.ha_close[0] > self.s2[0]) and \
                     (self.ha.lines.ha_close[-1] < self.s2[0]) and \
                     (self.ha.lines.ha_close[-2] >= self.s2[0])
        pivot_buy = (pivot_buy1 or pivot_buy2)
        return pivot_buy    
        
    def pivot_sell(self):
        pivot_sell1 = ((self.ha.lines.ha_close[0] < self.r1[0]) and
                       (self.ha.lines.ha_close[-1] > self.r1[0]) and
                       (self.ha.lines.ha_close[-2] <= self.r1[0]) and 
                       (self.ha.lines.ha_close[-3] <= self.r1[0]))
        pivot_sell2 = ((self.ha.lines.ha_close[0] < self.r2[0]) and
                       (self.ha.lines.ha_close[-1] > self.r2[0]) and 
                       (self.ha.lines.ha_close[-2] <= self.r2[0]))  
        pivot_sell = (pivot_sell1 or pivot_sell2)      
        return pivot_sell       
    
    def pivot_stop_buy(self):
        return ((self.ha.lines.ha_close[0] < self.r1[0]) and
                (self.ha.lines.ha_close[-1] > self.r1[0]) and
                (self.ha.lines.ha_close[-2] > self.r1[0]))        
    
    def pivot_stop_sell(self):
        return ((self.ha.lines.ha_close[0] > self.s1[0]) and
                (self.ha.lines.ha_close[-1] < self.s1[0]) and
                (self.ha.lines.ha_close[-2] < self.s1[0]))      
  
    def adx_growing(self):
        return (self.adx.real[-1] < self.adx.real[0]) and \
                (self.adx.real[-2] <= self.adx.real[-1]) #and \
                # (self.adx.real[-3] >= self.adx.real[-2])
    
   
    def pattern_buy(self):
        condition1 = self.pattern_buy1[0]
        condition2 = self.ta_patterns.signal_buy()        
        pattern_buy = (condition1) # or condition2)
        return pattern_buy

    def pattern_sell(self):
        condition1 = self.pattern_sell1[0]
        condition2 = self.ta_patterns.signal_sell()        
        pattern_sell = (condition1) # or condition2)
        return pattern_sell
    
    def pattern_stop_buy(self):
        condition1 = self.pattern_stopBuy1[0]
        condition2 = self.ta_patterns.signal_stop_buy()        
        pattern_stop_buy = (condition1) # or condition2)
        return pattern_stop_buy

    def pattern_stop_sell(self):
        condition1 = self.pattern_stopSell1[0]
        condition2 = self.ta_patterns.signal_stop_sell()              
        pattern_stop_sell = (condition1) # or condition2)
        return pattern_stop_sell
    
    def check_buy_condition(self):        
        condition1 = (self.mas_buy[0] or self.pivot_buy() or self.mama_buy[0]) #or self.pattern_buy())
        condition2 = (self.cmo_buy[0] or self.adx_buy[0]) and self.mfi_buy[0] and self.dma_osc_buy[0]
        condition3 = self.high_volatility[0] and (self.ad_osc_buy1[0] or self.volume_filter[0]) and self.hmo_buy1[0] #   # 
        condition4 = (self.stoch_buy1[0] or self.stoch_buy1[-1])
        check_buy_condition = (condition1 and condition2 and condition3 and condition4)
        return check_buy_condition

    def check_sell_condition(self):        
        condition1 = (self.mas_sell[0] or self.pivot_sell() or self.mama_sell[0]) # or self.pattern_sell())
        condition2 = (self.cmo_sell[0] or self.adx_sell[0]) and self.mfi_sell[0] and self.dma_osc_sell[0]
        condition3 = self.high_volatility[0] and (self.ad_osc_sell1[0] or self.volume_filter[0]) and self.hmo_sell1[0]
        condition4 = (self.stoch_sell1[0] or self.stoch_sell1[-1])
        check_sell_condition = (condition1 and condition2 and condition3 and condition4)
        return check_sell_condition

    def check_stop_buy_condition(self):        
        condition1 = (self.pattern_stopBuy1[0] or self.pattern_sell1[0] or self.mas_stop_buy[0] or self.mama_sell[0]) #  or self.pivot_stop_buy())
        condition2 = self.mfi_sell[0] and (self.ad_osc_sell1[0] or self.volume_filter[0])
        condition3 = ((self.dmi.DIminus[-1] < self.dmi.DIminus[0]) and self.adx_growing()) or \
                      (self.stoch_sell1[0] or self.stoch_sell1[-1])
        check_stop_buy_condition = (condition1 and condition2 and condition3) or self.pivot_sell()
        return check_stop_buy_condition 
                                  
                

    def check_stop_sell_condition(self):
        condition1 = (self.pattern_stopSell1[0] or self.pattern_buy1[0] or self.mas_stop_sell[0] or self.mama_buy[0]) #  or self.pivot_stop_sell())
        condition2 = self.mfi_buy[0] and (self.ad_osc_sell1[0] or self.volume_filter[0])
        condition3 = ((self.dmi.DIplus[0] > self.dmi.DIplus[-1]) and self.adx_growing()) or \
                      (self.stoch_buy1[0] or self.stoch_buy1[-1])
        check_stop_sell_condition = (condition1 and condition2 and condition3) or self.pivot_buy()
        return check_stop_sell_condition
        

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:            
            # Order has been submitted/accepted - no action required
            self.order = order
            return

        # Check if an order has been completed
        if order.status in [order.Completed]:
            if order.isbuy():                
                self.current_position_size += order.executed.size
                self.long_position = True
                self.long_entry_price = order.executed.price
                # self.log(f"BUY EXECUTED, Price: {order.executed.price:.4f}, Cost: {order.executed.value:.2f}, Comm {order.executed.comm:.2f}")

            else:                
                self.current_position_size -= order.executed.size
                self.long_position = False
                self.short_entry_price = order.executed.price
                # self.log(f"SELL EXECUTED, Price: {order.executed.price:.4f}, Cost: {order.executed.value:.2f}, Comm {order.executed.comm:.2f}")


            if not self.position:  # if position is closed
                closed_size = self.current_position_size
                self.current_position_size = 0
                # self.in_position = False
                if self.long_position:
                    profit_loss = (self.short_entry_price - order.executed.price) * closed_size
                    self.log(f"Closed SHORT position, Price: {order.executed.price:.4f},\t ----- PnL = {profit_loss:.2f} $") 
                    print("-" * 50) 
                    print()                  
                else:  # short position
                    profit_loss = (order.executed.price - self.long_entry_price) * closed_size
                    self.log(f"Closed LONG position, Price: {order.executed.price:.4f},\t ----- PnL = {profit_loss:.2f} $")
                    print("-" * 50)
                    print()
                
                self.past_trades.append(profit_loss)
            # else:
            #     self.in_position = True
            self.order = None

        elif order.status in [order.Canceled, order.Rejected]:
            self.log('Order Canceled/Rejected')            

        elif order.status in [order.Margin]:
            self.log('Order Margin')   
            
        # Reset
        self.order = None

    def next(self): 
         
        # if self.r1[-1] != self.r1[0]:          
        #     print(f"{bt.num2date(self.data.datetime[0])}, Close: {self.ha.lines.ha_close[0]:.4f} ====,       R2: {self.r2[0]:.4f},   R1: {self.r1[0]:.4f},    P: {self.pp[0]:.4f},    S1: {self.s1[0]:.4f},    S2: {self.s2[0]:.4f}")
       
        price = self.data0[0]
        if price == 0:           
            return
            
        self.in_position = self.broker.getposition(self.data).size 

        # Calculate win_rate and win_loss_ratio
        wins = [trade for trade in self.past_trades if trade > 0]  # Wins are trades with positive profit
        losses = [trade for trade in self.past_trades if trade < 0]  # Losses are trades with negative profit

        average_win = sum(wins) / len(wins) if wins else 0.0
        average_loss = abs(sum(losses)) / abs(len(losses)) if losses else 0.0
        win_rate = len(wins) / len(self.past_trades) if self.past_trades else 0.0
        win_loss_ratio1 = average_win / average_loss if average_loss != 0 else 1.0
        # win_rate = len(wins) / len(self.past_trades) if self.past_trades else 0.0
        # win_loss_ratio2 = abs(sum(wins)) / abs(sum(losses)) if losses else float('inf')
        win_loss_ratio = win_loss_ratio1 #+ win_loss_ratio2) / 2

        # Calculate the size for the trade using the Kelly Criterion
        if len(self.past_trades) == self.params.num_past_trades:                   
            kelly_coef = (win_rate - ((1 - win_rate) / win_loss_ratio)) if win_loss_ratio != 0.0 else 0.5
        else:
            kelly_coef = 0.5
        if kelly_coef < 0:
            kelly_coef = 0.0             
        
        if self.in_position == 0 and \
            (self.check_buy_condition() or self.check_sell_condition()):            
            
            if self.check_buy_condition():
                price = self.data0.high[0]  
                cash = self.broker.getvalue()                         
                free_money = self.broker.getcash() * 0.5 #(0.3 + (0.3 * kelly_coef))

                size = self.broker.getcommissioninfo(self.data).getsize(price=price, cash=free_money) #* (kelly_coef)
                self.order = self.buy(size=size, exectype=bt.Order.Market)                               
                print("-" * 50)                
                print(f"{bt.num2date(self.data.datetime[0])}\t ---- LONG ---- size = {size:.2f} at price = {price:.4f} //// ----- Value: {cash:.2f} $")                
                # print(f"win rate: {win_rate:.2f}, win loss ratio: {win_loss_ratio:.2f},\t Kelly coef: {kelly_coef:.2f}  ----- Cash: {cash:.2f} $")
                print()


            elif self.check_sell_condition():
                price = self.data0.low[0]  
                cash = self.broker.getvalue()           
                free_money = self.broker.getcash() * 0.5 #(0.3 + (0.3 * kelly_coef))
                size = self.broker.getcommissioninfo(self.data).getsize(price=price, cash=free_money) #* (kelly_coef)          
                self.order = self.sell(size=size, exectype=bt.Order.Market)                                      
                print("-" * 50)
                print(f"{bt.num2date(self.data.datetime[0])}\t ---- SHORT ---- size = {size:.2f} at price = {price:.4f} //// ----- Value: {cash:.2f} $")                
                # print(f"win rate: {win_rate:.2f}, win\loss ratio: {win_loss_ratio:.2f},\t Kelly coef: {kelly_coef:.2f}  ----- Cash: {cash:.2f} $")
                print()
                
        elif ((self.in_position > 0) and (self.check_sell_condition() or self.check_stop_buy_condition())):            
            self.order = self.close()
            cash = self.broker.getcash()
            print(f"{bt.num2date(self.data.datetime[0])}          ---- LONG ---- STOP       \t //// CASH: {cash:.2f} $") 
        elif ((self.in_position < 0) and (self.check_buy_condition() or self.check_stop_sell_condition())):            
            self.order = self.close()  
            cash = self.broker.getcash()
            print(f"{bt.num2date(self.data.datetime[0])}         ---- SHORT ---- STOP       \t //// CASH: {cash:.2f} $")                       
               

        current_price = self.data[0]
        sl_value = self.params.sl_percent / 100
        if (self.in_position > 0) and  ((self.long_entry_price * (1 - sl_value)) > current_price):
            self.order = self.close()

        elif (self.in_position < 0) and  ((self.short_entry_price * (1 + sl_value)) < current_price):
            self.order = self.close()            
                        
            # print("-" * 50)
            # self.log('DrawDown: %.2f' % self.stats.drawdown.drawdown[-1])
            # self.log('MaxDrawDown: %.2f' % self.stats.drawdown.maxdrawdown[-1])            

        self.in_position = 0    

        self.values.append(self.broker.getvalue())