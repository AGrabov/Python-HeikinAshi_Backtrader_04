import backtrader as bt


class CustomIndicator(bt.Indicator):
    lines = ('custom_indicator',)

    def __init__(self, pattern, open_price, high_price, low_price, close_price, penetration=None):
        self.pattern = pattern
        self.open = open_price
        self.high = high_price
        self.low = low_price
        self.close = close_price
        self.penetration = penetration
        if self.penetration is not None:
            self.lines.custom_indicator = pattern(open_price, high_price, low_price, close_price, penetration=self.penetration)
        else:
            self.lines.custom_indicator = pattern(open_price, high_price, low_price, close_price)


class TaPatterns(bt.Indicator):
    lines = ('signal',)
    params = (
        ('patterns', [
            (bt.talib.CDLHAMMER, None),
            (bt.talib.CDLTRISTAR, None),
            (bt.talib.CDLTHRUSTING, None),
            (bt.talib.CDLTASUKIGAP, None),
            (bt.talib.CDLTAKURI, None),
            (bt.talib.CDLSTICKSANDWICH, None),
            (bt.talib.CDLSTALLEDPATTERN, None),
            (bt.talib.CDLSPINNINGTOP, None),
            (bt.talib.CDLSHORTLINE, None),
            (bt.talib.CDLSHOOTINGSTAR, None),
            (bt.talib.CDLSEPARATINGLINES, None),
            (bt.talib.CDLRICKSHAWMAN, None),
            (bt.talib.CDLPIERCING, None),
            (bt.talib.CDLONNECK, None),
            (bt.talib.CDLMORNINGSTAR, 0.3),
            (bt.talib.CDLMORNINGDOJISTAR, 0.3),
            (bt.talib.CDLMATHOLD, 0.5),
            (bt.talib.CDLMATCHINGLOW, None),
            (bt.talib.CDLMARUBOZU, None),
            (bt.talib.CDLLONGLINE, None),
            (bt.talib.CDLLONGLEGGEDDOJI, None),
            (bt.talib.CDLLADDERBOTTOM, None),
            (bt.talib.CDLKICKINGBYLENGTH, None),
            (bt.talib.CDLKICKING, None),
            (bt.talib.CDLINVERTEDHAMMER, None),
            (bt.talib.CDLINNECK, None),
            (bt.talib.CDLHOMINGPIGEON, None),
            (bt.talib.CDLHIKKAKEMOD, None),
            (bt.talib.CDLHIKKAKE, None),
            (bt.talib.CDLHIGHWAVE, None),
            (bt.talib.CDLHARAMICROSS, None),
            (bt.talib.CDLHARAMI, None),
            (bt.talib.CDLHANGINGMAN, None),
            (bt.talib.CDLGRAVESTONEDOJI, None),
            (bt.talib.CDLGAPSIDESIDEWHITE, None),
            (bt.talib.CDLGAPSIDESIDEWHITE, None),
            (bt.talib.CDLEVENINGSTAR, 0.3),
            (bt.talib.CDLEVENINGDOJISTAR, 0.3),
            (bt.talib.CDLENGULFING, None),
            (bt.talib.CDLDRAGONFLYDOJI, None),
            (bt.talib.CDLDOJISTAR, None),
            (bt.talib.CDLDOJI, None),
            (bt.talib.CDLDARKCLOUDCOVER, 0.5),
            (bt.talib.CDLCOUNTERATTACK, None),
            (bt.talib.CDLCONCEALBABYSWALL, None),
            (bt.talib.CDLCLOSINGMARUBOZU, None),
            (bt.talib.CDLBREAKAWAY, None),
            (bt.talib.CDLBELTHOLD, None),
            (bt.talib.CDLADVANCEBLOCK, None),
            (bt.talib.CDLABANDONEDBABY, 0.3)
        ]),
        ('pattern_signal', ('ta_patterns_buy', 'ta_patterns_sell')),
        ('use_ha', True),
        ('threshold', 0),
    )

    def __init__(self):
        super().__init__()
        self.ha = bt.indicators.HeikinAshi(self.data)
        self.ha_close = self.ha.lines.ha_close
        self.ha_open = self.ha.lines.ha_open
        self.ha_high = self.ha.lines.ha_high
        self.ha_low = self.ha.lines.ha_low

        self.patterns = []
        for pattern, penetration in self.p.patterns:
            if self.params.use_ha:
                open_price, high_price, low_price, close_price = self.ha_open, self.ha_high, self.ha_low, self.ha_close
            else:
                open_price, high_price, low_price, close_price = self.data.open, self.data.high, self.data.low, self.data.close

            if penetration is not None:
                self.add_pattern(pattern, open_price, high_price, low_price, close_price, penetration)

            else:
                self.add_pattern(pattern, open_price, high_price, low_price, close_price)

        # Initialize signal line to 0
        self.lines.signal = 0

        # Add each pattern's output to the signal line
        for pattern in self.patterns:
            self.lines.signal += pattern.lines.custom_indicator

        print(self.lines.signal)

    def add_pattern(self, pattern, open_price, high_price, low_price, close_price, penetration=None):
        custom_indicator = CustomIndicator(pattern, open_price, high_price, low_price, close_price, penetration)
        self.patterns.append(custom_indicator)

    def ta_patterns_buy(self):
        return self.pattern_signal > self.params.threshold

    def ta_patterns_sell(self):
        return self.pattern_signal < -self.params.threshold
