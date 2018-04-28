# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     mySignals
   Author :       yesheng
   date：          2018/4/28
-------------------------------------------------
"""
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaSignal,
                                                     BarGenerator,
                                                     ArrayManager)

class RsiSignal(CtaSignal):
    """RSI信号"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(RsiSignal, self).__init__()

        self.rsiWindow = 14
        self.rsiLevel = 20
        self.rsiLong = 50 + self.rsiLevel
        self.rsiShort = 50 - self.rsiLevel

        self.bg = BarGenerator(self.onBar)
        self.am = ArrayManager()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """Tick更新"""
        self.bg.updateTick(tick)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """K线更新"""
        self.am.updateBar(bar)

        if not self.am.inited:
            self.setSignalPos(0)

        self.rsiValue = self.am.rsi(self.rsiWindow)

        if self.rsiValue >= self.rsiLong:
            self.setSignalPos(1)
        elif self.rsiValue <= self.rsiShort:
            self.setSignalPos(-1)
        else:
            self.setSignalPos(0)


########################################################################
class CciSignal(CtaSignal):
    """CCI信号"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(CciSignal, self).__init__()

        self.cciWindow = 10
        self.cciLevel = 20
        self.cciLong = self.cciLevel
        self.cciShort = -self.cciLevel
        self.cciValue = 0.0
        self.bg = BarGenerator(self.onBar, 15, self.on15Bar)
        self.am = ArrayManager()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """Tick更新"""
        self.bg.updateTick(tick)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """K线更新"""
        self.bg.updateBar(bar)

    def on15Bar(self, bar):

        self.am.updateBar(bar)
        print bar.datetime
        print "@cciSignal"
        print "cci inited: ", self.am.inited

        if not self.am.inited:
            self.setSignalPos(0)
            return

        self.cciValue = self.am.cci(self.cciWindow)

        print "cciValue: ", self.cciValue

        if self.cciValue >= self.cciLong:
            self.setSignalPos(1)
        elif self.cciValue <= self.cciShort:
            self.setSignalPos(-1)
        else:
            self.setSignalPos(0)

########################################################################
class MaSignal(CtaSignal):
    """双均线信号"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(MaSignal, self).__init__()

        self.fastWindow = 5
        self.slowWindow = 20

        self.bg = BarGenerator(self.onBar, 5, self.onFiveBar)
        self.am = ArrayManager()

        # ----------------------------------------------------------------------

    def onTick(self, tick):
        """Tick更新"""
        self.bg.updateTick(tick)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """K线更新"""
        self.bg.updateBar(bar)

    # ----------------------------------------------------------------------
    def onFiveBar(self, bar):
        """5分钟K线更新"""
        self.am.updateBar(bar)

        if not self.am.inited:
            self.setSignalPos(0)

        fastMa = self.am.sma(self.fastWindow)
        slowMa = self.am.sma(self.slowWindow)

        if fastMa > slowMa:
            self.setSignalPos(1)
        elif fastMa < slowMa:
            self.setSignalPos(-1)
        else:
            self.setSignalPos(0)


########################################################################
class BollSignal(CtaSignal):
    """布林带信号"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(BollSignal, self).__init__()

        self.bollWindow = 18
        self.bollDev = 5
        # self.bollUp, self.bollDown = 0.0,0.0
        self.bg = BarGenerator(self.onBar, 15, self.on15Bar)
        self.am = ArrayManager()

        # ----------------------------------------------------------------------

    def onTick(self, tick):
        """Tick更新"""
        self.bg.updateTick(tick)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """K线更新"""
        self.bg.updateBar(bar)

    # ----------------------------------------------------------------------
    def on15Bar(self, bar):
        """15分钟K线更新"""
        self.am.updateBar(bar)

        if not self.am.inited:
            self.setSignalPos(0)
        bollUp, bollDown = self.am.boll(self.bollWindow, self.bollDev)

        if bar.close >= bollUp:
            self.setSignalPos(1)
        elif bar.close <= bollDown:
            self.setSignalPos(-1)
        else:
            self.setSignalPos(0)
        # 记录log
        # log = "-----" * 10 + "\n@BollSignal\n" + \
        #       "bar.datetime: {0}\n".format(bar.datetime) + \
        #       "bollUp: {0}; SignalPos: {1}\n".format(bollUp, self.signalPos)
        # self.writeCtaLog(log)


########################################################################
class AtrSignal(CtaSignal):
    """Atr信号"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(AtrSignal, self).__init__()
        self.atrWindow = 30
        self.bg = BarGenerator(self.onBar, 15, self.on15Bar)
        self.am = ArrayManager()
        self.atrValue = 0.0
        # ----------------------------------------------------------------------

    def onTick(self, tick):
        """Tick更新"""
        self.bg.updateTick(tick)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """K线更新"""
        self.bg.updateBar(bar)

    # ----------------------------------------------------------------------
    def on15Bar(self, bar):
        """15分钟K线更新"""
        self.am.updateBar(bar)

        print bar.datetime
        print "@atrSignal"
        print "atr inited: ", self.am.inited

        if not self.am.inited:
            self.setSignalPos(0)
            return

        atrArray = self.am.atr(self.atrWindow, array=True)
        self.atrValue = atrArray[-1]
        atrMa = atrArray[-self.atrWindow:].mean()

        print "atrValue: ", self.atrValue

        # 趋势增强
        if self.atrValue > atrMa:
            self.setSignalPos(1)
        else:
            self.setSignalPos(0)


########################################################################
class TrailingStopSignal(CtaSignal):
    """跟随出场信号"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(TrailingStopSignal, self).__init__()
        self.slMultiplier = 5
        self.bg = BarGenerator(self.onBar, 15, self.on15Bar)
        self.signalPos = 100

        # 当前持仓
        self.holdPos = 0
        # 当前atr值
        self.atrValue = 0.0
        self.intraTradeHigh = 0.0
        self.intraTradeLow = 0.0
        self.longStop = 0.0
        self.shortStop = 0.0
        self.stopExit = 0.0

        # ------------------ ----------------------------------------------------

    def onTick(self, tick):
        """Tick更新"""
        self.bg.updateTick(tick)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """K线更新"""
        self.bg.updateBar(bar)
        # print "@onBar"

    # ----------------------------------------------------------------------
    def on15Bar(self, bar):
        # print "@on15Bar"
        if self.holdPos > 0:
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.longStop = self.intraTradeHigh - self.atrValue * self.slMultiplier

            # print bar.datetime
            # print "atrValue: ", self.atrValue
            # print "holdPos: ", self.holdPos
            # print "longStop: ",self.longStop
            # print "close: ", bar.close

            if self.longStop > bar.close:
                self.setSignalPos(0)
                # print "tailingPos: ", self.getSignalPos()

        elif self.holdPos < 0:
            self.intraTradeLow = min(self.intraTradeLow, bar.low)
            self.shortStop = self.intraTradeLow + self.atrValue * self.slMultiplier

            # print bar.datetime
            # print "atrValue: ", self.atrValue
            # print "holdPos: ", self.holdPos
            # print "shortStop: ",self.shortStop
            # print "close: ", bar.close

            if self.shortStop < bar.close:
                self.setSignalPos(0)

        elif self.holdPos == 0:
            # 空仓时返回100
            self.setSignalPos(100)