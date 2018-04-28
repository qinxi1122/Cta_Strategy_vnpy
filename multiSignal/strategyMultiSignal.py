# encoding: UTF-8
"""
CCI+ATR合成信号策略
1.入场：CCI（15分钟）：大于20为多头、低于-20为空头
       RSI(1分钟）：大于70为多头、低于30为空头
2.过滤：ATR（15分钟）：ATR上穿ATR MA30
3.出场：TrailingStop(15分钟)
用于RB88，策略周期15分钟
"""
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import *
from vnpy.trader.app.ctaStrategy.ctaTemplate import (TargetPosTemplate, CtaSignal,BarGenerator, ArrayManager)
from mySignals.mySignals import *


########################################################################
class MultiSignalStrategy(TargetPosTemplate):
    """CCI+ATR合成信号策略"""
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
        self.atrSignal = AtrSignal()
        self.rsiSignal = RsiSignal()
        self.signalPos = {
            "cci": 0,
            "atr": 0,
            "rsi": 0
        }
        self.entryPriceList = []
        self.avgEntryPrice = 0.0
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
        self.rsiSignal.onTick(tick)

        if self.pos:
            self.trailingStopSignal.onTick(tick)

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        super(MultiSignalStrategy, self).onBar(bar)
        
        self.atrSignal.onBar(bar)
        self.cciSignal.onBar(bar)
        self.rsiSignal.onBar(bar)

        # 更新trailingStop中的ATR值
        self.trailingStopSignal.atrValue = self.atrSignal.atrValue
        self.trailingStopSignal.onBar(bar)

        self.bg.updateBar(bar)


    def on15Bar(self, bar):

        self.signalPos['atr'] = self.atrSignal.getSignalPos()
        self.signalPos['cci'] = self.cciSignal.getSignalPos()
        self.signalPos['rsi'] = self.rsiSignal.getSignalPos()

        # 记录log
        log = "-----" * 10 + "\n@on15Bar\n" + \
              "bar.datetime: {0}\n".format(bar.datetime) + \
              "cci: {0}; atr: {1}; trailing: {2}\n".format(self.signalPos['cci'], self.signalPos['atr'],self.trailingStopSignal.signalPos) +\
              "pos: {0}\n".format(self.pos)+\
            "cciValue: {0}, atrValue: {1}, rsiValue: {2}\n".format(self.cciSignal.cciValue,self.atrSignal.atrValue, self.rsiSignal.rsiValue)
        self.writeCtaLog(log)

        self.caculatePos(bar)

    def caculatePos(self, bar):
        """
        根据信号合成计算仓位
        """
        # 记录log
        log = "-----" * 10 + "\n@caculatePos\n" + \
              "bar.datetime: {0}\n".format(bar.datetime) + \
              "cci: {0}; atr: {1}; trailing: {2}\n".format(self.signalPos['cci'], self.signalPos['atr'],self.trailingStopSignal.signalPos) +\
              "pos: {0}\n".format(self.pos)
        self.writeCtaLog(log)

        # 开仓
        if self.pos == 0 and self.signalPos['atr'] == 1:
            if (self.signalPos['cci'] == 1 and self.signalPos['rsi'] == 1):

                # 记录log
                log = '\n [Buy]\n'
                self.writeCtaLog(log)

                self.setTargetPos(self.fixedSize)
            if  (self.signalPos['cci'] == -1 and self.signalPos['rsi'] == -1):
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
            self.atrSignal=AtrSignal()
            self.cciSignal=CciSignal()
            self.rsiSignal=RsiSignal()

            # 设置策略仓位
            self.setTargetPos(0)

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        super(MultiSignalStrategy, self).onOrder(order)

        if order.direction == DIRECTION_LONG and order.offset == OFFSET_OPEN:
            if order.totalVolume == order.tradedVolume:
                # 更新入场价列表，更新平均入场价
                self.entryPriceList.append(order.price)
                self.avgEntryPrice = sum(self.entryPriceList) / len(self.entryPriceList)
                self.trailingStopSignal.intraTradeHigh = self.avgEntryPrice

        elif order.direction == DIRECTION_SHORT and order.offset == OFFSET_OPEN:
            if order.totalVolume == order.tradedVolume:
                # 更新入场价列表，更新平均入场价
                self.entryPriceList.append(order.price)
                self.avgEntryPrice = sum(self.entryPriceList) / len(self.entryPriceList)
                self.trailingStopSignal.intraTradeLow = self.avgEntryPrice

        # 更新trailingStop中的仓位
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
    engine.setStartDate('20170101',1)  # 设置回测用的数据起始日期
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
    engine.showDailyResult()
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