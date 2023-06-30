import backtrader as bt
import talib

class PivitPoint(bt.Indicator):
    lines = ('signal', 'stop_signal',)
    params = dict(
        use_fib = 0,
        data_src = 0 ,

    )

    def __init__(self):
        # Pivot Point levels
        self.pp = pp = bt.indicators.PivotPoint(self.data, open=True, _autoplot=False) # 
        pp.plotinfo.plot = False  # deactivate plotting    

        # Pivot Point levels
        self.fib_pp = fib_pp = bt.indicators.FibonacciPivotPoint(self.data, open=True, _autoplot=False) # 
        fib_pp.plotinfo.plot = False  # deactivate plotting

        # self.p = self.pp()
        self.s1 = self.pp.s1()
        self.s2 = self.pp.s2()
        self.r1 = self.pp.r1()
        self.r2 = self.pp.r2()

        

    def pivot_buy(self):
        pivot_buy1 = (self.params.data_src[0] > self.s1[0]) and \
                     (self.params.data_src[-1] < self.s1[0]) and \
                     (self.params.data_src[-2] >= self.s1[0]) and \
                     (self.params.data_src[-3] >= self.s1[0]) and \
                     (self.params.data_src[-1] < self.params.data_src[0])
        
        pivot_buy2 = (self.params.data_src[0] > self.s2[0]) and \
                     (self.params.data_src[-1] < self.s2[0]) and \
                     (self.params.data_src[-2] >= self.s2[0])
        pivot_buy = (pivot_buy1 or pivot_buy2)
        return pivot_buy    
        
    def pivot_sell(self):
        pivot_sell1 = ((self.params.data_src[0] < self.r1[0]) and
                       (self.params.data_src[-1] > self.r1[0]) and
                       (self.params.data_src[-2] <= self.r1[0]) and 
                       (self.params.data_src[-3] <= self.r1[0]))
        pivot_sell2 = ((self.params.data_src[0] < self.r2[0]) and
                       (self.params.data_src[-1] > self.r2[0]) and 
                       (self.params.data_src[-2] <= self.r2[0]))  
        pivot_sell = (pivot_sell1 or pivot_sell2)      
        return pivot_sell       
    
    def pivot_stop_buy(self):
        return ((self.params.data_src[0] < self.r1[0]) and
                (self.params.data_src[-1] > self.r1[0]) and
                (self.params.data_src[-2] > self.r1[0]))        
    
    def pivot_stop_sell(self):
         return ((self.params.data_src[0] > self.s1[0]) and
                (self.params.data_src[-1] < self.s1[0]) and
                (self.params.data_src[-2] < self.s1[0]))