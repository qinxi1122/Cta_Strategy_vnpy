# encoding: UTF-8

"""
一个多信号组合策略，基于的信号包括：
RSI（1分钟）：大于70为多头、低于30为空头
CCI（1分钟）：大于10为多头、低于-10为空头
MA（5分钟）：快速大于慢速为多头、低于慢速为空头
"""

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import *
from vnpy.trader.app.ctaStrategy.ctaTemplate import (TargetPosTemplate, 
                                                     CtaSignal,
                                                     BarGenerator, 
                                                     ArrayManager)


########################################################################
class RsiSignal(CtaSignal):
    """RSI信号"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(RsiSignal, self).__init__()
        
        self.rsiWindow = 14
        self.rsiLevel = 20
        self.rsiLong = 50 + self.rsiLevel
        self.rsiShort = 50 - self.rsiLevel
        
        self.bg = BarGenerator(self.onBar)
        self.am = ArrayManager()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """Tick更新"""
        self.bg.updateTick(tick)
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """K线更新"""
        self.am.updateBar(bar)
        
        if not self.am.inited:
            self.setSignalPos(0)
            
        rsiValue = self.am.rsi(self.rsiWindow)
        
        if rsiValue >= self.rsiLong:
            self.setSignalPos(1)
        elif rsiValue <= self.rsiShort:
            self.setSignalPos(-1)
        else:
            self.setSignalPos(0)
########################################################################
class CciSignal(CtaSignal):
    """CCI信号"""

    #----------------------------------------------------------------------
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
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """Tick更新"""
        self.bg.updateTick(tick)
        
    #----------------------------------------------------------------------
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

        # # 记录log
        # log = "-----" * 10 + "\n@CciSignal\n" + \
        #       "bar.datetime: {0}\n".format(bar.datetime) + \
        #       "cciValue: {0}; SignalPos: {1}\n".format(cciValue, self.signalPos)
        # self.writeCtaLog(log)

########################################################################
class MaSignal(CtaSignal):
    """双均线信号"""
    
    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(MaSignal, self).__init__()
        
        self.fastWindow = 5
        self.slowWindow = 20
        
        self.bg = BarGenerator(self.onBar, 5, self.onFiveBar)
        self.am = ArrayManager()        
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """Tick更新"""
        self.bg.updateTick(tick)
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """K线更新"""
        self.bg.updateBar(bar)
    
    #----------------------------------------------------------------------
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
    """出场信号"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(TrailingStopSignal, self).__init__()
        # self.atrWindow = 30
        self.slMultiplier = 5
        self.bg = BarGenerator(self.onBar,15, self.on15Bar)
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
    def on15Bar(self,bar):
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

########################################################################
class MultiSignalStrategy(TargetPosTemplate):
    """跨时间周期交易策略"""
    className = 'MultiSignalStrategy'
    author = 'Y.Raul'

    # 策略参数
    initDays = 10           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量

    # 策略变量
    signalPos = {}          # 信号仓位
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'signalPos',
               'targetPos']

    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(MultiSignalStrategy, self).__init__(ctaEngine, setting)

        self.cciSignal = CciSignal()
        self.trailingStopSignal = TrailingStopSignal()
        self.bollSignal = BollSignal()
        self.atrSignal = AtrSignal()

        self.signalPos = {
            "cci": 0,
            "atr": 0,
            "bool": 0
        }

        self.entryPriceList = []
        self.avgEntryPrice = 0.0
        # self.exitOnLossStop = 2

        self.bg = BarGenerator(self.onBar, 15, self.on15Bar)
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        super(MultiSignalStrategy, self).onTick(tick)
        
        self.atrSignal.onTick(tick)
        self.cciSignal.onTick(tick)
        self.bollSignal.onTick(tick)

        if self.pos:
            self.trailingStopSignal.onTick(tick)


    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        super(MultiSignalStrategy, self).onBar(bar)
        
        self.atrSignal.onBar(bar)
        self.cciSignal.onBar(bar)
        self.bollSignal.onBar(bar)

        self.trailingStopSignal.atrValue = self.atrSignal.atrValue
        # self.trailingStopSignal.atrValue = 5
        self.trailingStopSignal.onBar(bar)


        self.bg.updateBar(bar)


    def on15Bar(self, bar):
        """
        策略周期15min
        :param bar:
        :return:
        """

        self.signalPos['atr'] = self.atrSignal.getSignalPos()
        self.signalPos['cci'] = self.cciSignal.getSignalPos()
        self.signalPos['boll'] = self.bollSignal.getSignalPos()

        # 记录log
        log = "-----" * 10 + "\n@on15Bar\n" + \
              "bar.datetime: {0}\n".format(bar.datetime) + \
              "cci: {0}; atr: {1}; trailing: {2}\n".format(self.signalPos['cci'], self.signalPos['atr'],self.trailingStopSignal.signalPos) +\
              "pos: {0}\n".format(self.pos)+\
            "cciValue: {0}, atrValue: {1}\n".format(self.cciSignal.cciValue,self.atrSignal.atrValue)
        self.writeCtaLog(log)

        self.caculatePos(bar)

        # 重置信号
        # self.cciSignal = CciSignal()
        # self.trailingStopSignal = TrailingStopSignal()
        # self.bollSignal = BollSignal()
        # self.atrSignal = AtrSignal()
        #
        # # 记录log
        # log = '[Zeros]\n' + \
        #       "cci: {0}; atr: {1}; trailing: {2}\n".format(self.cciSignal.getSignalPos(), self.atrSignal.getSignalPos(),
        #                                                    self.trailingStopSignal.signalPos) + \
        #       "pos: {0}\n".format(self.pos)
        # self.writeCtaLog(log)


    def caculatePos(self, bar):
        """
        计算仓位
        """
        # 记录log
        log = "-----" * 10 + "\n@caculatePos\n" + \
              "bar.datetime: {0}\n".format(bar.datetime) + \
              "cci: {0}; atr: {1}; trailing: {2}\n".format(self.signalPos['cci'], self.signalPos['atr'],self.trailingStopSignal.signalPos) +\
              "pos: {0}\n".format(self.pos)
        self.writeCtaLog(log)
        # 开仓
        if self.pos == 0 and self.signalPos['atr'] == 1:
            if (self.signalPos['cci'] == 1):

                # 记录log
                log = '\n [Buy]\n'
                self.writeCtaLog(log)

                self.setTargetPos(self.fixedSize)
            if  (self.signalPos['cci'] == -1):
                # 记录log
                log = '\n [Short]\n'
                self.writeCtaLog(log)
                self.setTargetPos(-1 * self.fixedSize)
        # 平仓
        if self.pos != 0 and self.trailingStopSignal.getSignalPos() == 0:

            # 记录log
            log = "-----" * 10 + "\n@trailingStop\n" + \
              "bar.datetime: {0}\n".format(bar.datetime) + \
              "atr: {0}; intraHigh: {1}; intraLow: {2}\n".format(self.trailingStopSignal.atrValue, self.trailingStopSignal.intraTradeHigh,
                                                           self.trailingStopSignal.intraTradeLow) + \
              "holdpos: {0}\n".format(self.trailingStopSignal.holdPos) +\
                "longStop: {0}; shortStop: {1}\n".format(self.trailingStopSignal.longStop,self.trailingStopSignal.shortStop) +\
              "close: {0}\n".format(bar.close) +\
                "tailingStop: {0}\n".format(self.trailingStopSignal.getSignalPos())
            self.writeCtaLog(log)

            if self.pos > 0:
                # 记录log
                log = '\n [Sell]\n'
                self.writeCtaLog(log)

            elif self.pos < 0:
                # 记录log
                log = '\n [Cover]\n'
                self.writeCtaLog(log)
            # 重置信号
            # self.atrSignal.setSignalPos(0)
            # self.cciSignal.setSignalPos(0)
            # self.bollSignal.setSignalPos(0)
            self.atrSignal=AtrSignal()
            self.cciSignal=CciSignal()
            self.bollSignal=BollSignal()

            # 设置策略仓位
            self.setTargetPos(0)

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        super(MultiSignalStrategy, self).onOrder(order)
        # 对于开仓，记录相关价格
        if order.direction == DIRECTION_LONG and order.offset == OFFSET_OPEN:
            if order.totalVolume == order.tradedVolume:
                # self.trailingStopSignal.holdPos = self.pos
                # 更新入场价列表，更新平均入场价
                self.entryPriceList.append(order.price)
                self.avgEntryPrice = sum(self.entryPriceList) / len(self.entryPriceList)
                self.trailingStopSignal.intraTradeHigh = self.avgEntryPrice
                # self.trailingStopSignal.stopExit = round(self.avgEntryPrice * (100 - self.exitOnLossStop) / 100)  # 固定止损价

        elif order.direction == DIRECTION_SHORT and order.offset == OFFSET_OPEN:
            # 更新入场价列表，更新平均入场价
            if order.totalVolume == order.tradedVolume:
                # self.trailingStopSignal.holdPos = self.pos
                # 更新入场价列表，更新平均入场价
                self.entryPriceList.append(order.price)
                self.avgEntryPrice = sum(self.entryPriceList) / len(self.entryPriceList)
                self.trailingStopSignal.intraTradeLow = self.avgEntryPrice
                # self.trailingStopSignal.stopExit = round(self.avgEntryPrice * (1 + self.exitOnLossStop) / 100)  # 固定止损价

        self.trailingStopSignal.holdPos = self.pos
        self.putEvent()
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass

if __name__ == "__main__":
    from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine, OptimizationSetting, MINUTE_DB_NAME
    dbName = MINUTE_DB_NAME
    symbol = 'rb88'
    # 创建回测引擎对象
    engine = BacktestingEngine()
    # 设置回测使用的数据
    engine.setBacktestingMode(engine.BAR_MODE)  # 设置引擎的回测模式为K线
    engine.setDatabase(dbName, symbol)  # 设置使用的历史数据库
    engine.setStartDate('20130101',1)  # 设置回测用的数据起始日期
    engine.setEndDate('20171231')
    # 配置回测引擎参数
    engine.setSlippage(2)  # 设置滑点为股指1跳
    engine.setRate(1.1 / 10000)  # 设置手续费万1.1
    engine.setSize(10)  # 设置股指合约大小
    engine.setPriceTick(1)  # 设置股指最小价格变动
    engine.setCapital(10000)  # 设置回测本金

    #  使用策略类中的默认参数，则参数配置字典留空
    d = {}
    # 初始化策略
    engine.initStrategy(MultiSignalStrategy, d)
    # 运行回测
    engine.runBacktesting()  # 运行回测
    engine.showBacktestingResult()
    # engine.showDailyResult()
    d = engine.calculateBacktestingResult()

    # 记录Log
    import logging
    logger = logging.getLogger("backtest")
    fh = logging.FileHandler('./{0}_backtest.log'.format(engine.strategy.className))
    logger.setLevel(logging.INFO)
    logger.addHandler(fh)

    for log in engine.logList:
        logger.info(log)
    result = d['resultList']
    entryDate = []
    entryPrice = []
    exitDate = []
    exitPrice = []
    volume = []
    pnl = []
    for trade in result:
        dic = trade.__dict__
        entryDate.append(dic['entryDt'])
        entryPrice.append(dic['entryPrice'])
        exitDate.append(dic['exitDt'])
        exitPrice.append(dic['exitPrice'])
        volume.append(dic['volume'])
        pnl.append(dic['pnl'])

    import pandas as pd
    data = {'entryDate': entryDate, 'entryPrice': entryPrice, 'exitDate':exitDate, 'exitPrice':exitPrice, 'volume':volume, 'pnl':pnl}
    df = pd.DataFrame(data)
    df['ratio'] = (df['exitPrice'] - df['entryPrice'])/df['entryPrice'] * df['volume'] * 100
    df.to_csv('./{0}_result.csv'.format(engine.strategy.className), index=False)