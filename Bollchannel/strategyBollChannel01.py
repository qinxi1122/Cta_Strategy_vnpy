# encoding: UTF-8

""""
基于布林带的交易策略
观察周期：1min
策略周期：5min
策略逻辑：
1. 信号：突破上轨、下轨
2. 过滤：CCI
3. 出场：ATR跟随
"""

from __future__ import division

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import *
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate, 
                                                     BarGenerator, 
                                                     ArrayManager)


########################################################################
class BollChannelStrategy01(CtaTemplate):
    """基于布林通道的交易策略"""
    className = 'BollChannelStrategy01'
    author = 'Y.Raul'

    # 策略参数
    bollWindow = 18                     # 布林通道窗口数
    bollDev = 5                       # 布林通道的偏差
    cciWindow = 10                      # CCI窗口数
    atrWindow = 30                      # ATR窗口数
    slMultiplier = 5                 # 计算止损距离的乘数
    initDays = 10                       # 初始化数据所用的天数
    fixedSize = 1                       # 每次交易的数量

    # 策略变量
    bollUp = 0                          # 布林通道上轨
    bollDown = 0                        # 布林通道下轨
    cciValue = 0                        # CCI指标数值
    atrValue = 0                        # ATR指标数值
    filterTime = True                  #是否过滤9点开盘后头五分钟，15点收盘前五分钟

    intraTradeHigh = 0                  # 持仓期内的最高点
    intraTradeLow = 0                   # 持仓期内的最低点
    longStop = 0                        # 多头止损
    shortStop = 0                       # 空头止损
    avgEntryPrice = 0                   #平均入场价
    avgExitPrice = 0                    #平均出场价
    buySig = False
    shortSig = False
    exitOnLossStop = 2
    miniDiff = 1

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'bollWindow',
                 'bollDev',
                 'cciWindow',
                 'atrWindow',
                 'slMultiplier',
                 'initDays',
                 'fixedSize']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'bollUp',
               'bollDown',
               'cciValue',
               'atrValue',
               'intraTradeHigh',
               'intraTradeLow',
               'longStop',
               'shortStop']  
    
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos',
                'intraTradeHigh',
                'intraTradeLow']    

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(BollChannelStrategy01, self).__init__(ctaEngine, setting)
        
        self.bm = BarGenerator(self.onBar, 15, self.on5minBar)        # 创建K线合成器对象
        self.am = ArrayManager()
        self.entryPriceList = []
        self.orderList = []
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
        self.bm.updateTick(tick)

    #----------------------------------------------------------------------
    def onBar(self, bar):

        self.bm.updateBar(bar)
        if not self.trading:
            # 记录log
            log = "-----" * 10 + "\n@onBar\n" + \
                    "trading: {0}\n".format(self.trading)+\
                  "bar.datetime: {0}; pos: {1} \n".format(bar.datetime, self.pos) + \
                  "buySig: {0}; shortSig: {1}\n".format(self.buySig, self.shortSig)
            self.writeCtaLog(log)
            print log
            self.buySig = False
            self.shortSig = False
            return

        # 检查开仓信号
        if self.buySig:
            res = self.buy(self.bollUp, self.fixedSize)
            self.orderList.extend(res)

            # 记录log
            log = "-----" * 10 + "\n@onBar\n" + \
                  "bar.datetime: {0}; pos: {1} \n".format(bar.datetime, self.pos) + \
                  "buySig: {0}; shortSig: {1}\n".format(self.buySig, self.shortSig)
            self.writeCtaLog(log)

            log = "\n Trading: {0}\n".format(self.trading) + \
                  "{0} Buy : bar.close: {1};\n".format(bar.datetime, bar.close) + \
                  " entryUp:{0}; cci:{1};\n".format(self.bollUp, self.cciValue)
            self.writeCtaLog(log)
            self.buySig = False
            print log

        if self.shortSig:
            res = self.short(self.bollDown, self.fixedSize)
            self.orderList.extend(res)

            # 记录log
            log = "-----" * 10 + "\n@onBar\n" + \
                  "bar.datetime: {0}; pos: {1} \n".format(bar.datetime, self.pos) + \
                  "buySig: {0}; shortSig: {1}\n".format(self.buySig, self.shortSig)
            self.writeCtaLog(log)

            log = "\n Trading: {0}\n".format(self.trading) + \
                  "{0} Short : bar.close: {1};\n".format(bar.datetime, bar.close) + \
                  " entryDown:{0}; cci:{1};\n".format(self.bollDown, self.cciValue)
            self.writeCtaLog(log)
            self.shortSig = False
            print log

        self.putEvent()
    #----------------------------------------------------------------------
    def on5minBar(self, bar):
        """收到X分钟K线"""
        # 全撤之前发出的委托
        self.cancelAll()
    
        # 保存K线数据
        am = self.am
        
        am.updateBar(bar)
        
        if not am.inited:
            return
        
        # 计算指标数值
        self.bollUp, self.bollDown = am.boll(self.bollWindow, self.bollDev)
        self.cciValue = am.cci(self.cciWindow)

        atrArray = am.atr(self.atrWindow, array=True)
        self.atrValue = atrArray[-1]
        self.atrMa = atrArray[-self.atrWindow:].mean()
        # 判断是否要进行交易

        # 当前无仓位，发送开仓委托，限价单
        if self.pos == 0:
            self.intraTradeHigh = bar.high
            self.intraTradeLow = bar.low
            self.entryPriceList = []
            self.orderList = []
            self.avgEntryPrice = []
            import datetime
            timeWindow = True
            if self.filterTime:
                timeWindow = bar.datetime.time() > datetime.time(9) and bar.datetime.time()< datetime.time(14,55)

            if timeWindow:
                if self.cciValue > 0 and self.atrValue > self.atrMa:
                # if self.cciValue > 0 :
                    self.buySig = True

                elif self.cciValue < 0 and self.atrValue < self.atrMa:
                # elif self.cciValue < 0:
                    self.shortSig = True

            # 记录log
            log = "-----" * 10 + "\n@on5minBar\n" + \
                "timeWidow: {0}\n".format(timeWindow) +\
                "bar.datetime: {0}; pos: {1} ; close: {2}\n".format(bar.datetime, self.pos, bar.close) + \
                "buySig: {0}; shortSig: {1}\n".format(self.buySig, self.shortSig) + \
                "intraTradeHigh: {0}\n".format(self.intraTradeHigh) + \
                "intraTradeLow: {0}\n".format(self.intraTradeLow)
            self.writeCtaLog(log)
            print log

        # 当前有仓位，以本地停止单止损
        # 持有多头仓位
        elif self.pos > 0:
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.intraTradeLow = bar.low
            self.longStop = self.intraTradeHigh - self.atrValue * self.slMultiplier

            # if bar.close < self.stopExit:
                # 固定止损
                # self.sell(bar.close, abs(self.pos), True)
            # else:
            #     跟随止损
                # self.sell(self.longStop, abs(self.pos), True)
            self.sell(self.longStop, abs(self.pos), True)

            # 记录log
            log = "-----" * 10 + "\n@on5minBar\n" + \
                  "bar.datetime: {0}; pos: {1} ; close: {2}\n".format(bar.datetime, self.pos, bar.close) + \
                  "intraTradeHigh: {0}\n".format(self.intraTradeHigh) + \
                  "intraTradeLow: {0}\n".format(self.intraTradeLow)
            "avgEntryPrice: {0}\n".format(self.avgEntryPrice) + \
            "longStop: {0}\n".format(self.longStop) + \
            "stopExit:{0}\n".format(self.stopExit)

            self.writeCtaLog(log)
            print log
    
        # 持有空头仓位
        elif self.pos < 0:
            self.intraTradeHigh = bar.high
            self.intraTradeLow = min(self.intraTradeLow, bar.low)
            self.shortStop = self.intraTradeLow + self.atrValue * self.slMultiplier
            
            # if bar.close > self.stopExit:
            #     固定止损
                # self.cover(bar.close, abs(self.pos), True)
            # else:
                # 跟随止损
                # self.cover(self.shortStop, abs(self.pos), True)
            self.cover(self.shortStop, abs(self.pos), True)

            # 记录log
            log = "-----" * 10 + "\n@on5minBar\n" + \
                  "bar.datetime: {0}; pos: {1} ; close: {2}\n".format(bar.datetime, self.pos, bar.close) + \
                  "intraTradeHigh: {0}\n".format(self.intraTradeHigh) + \
                  "intraTradeLow: {0}\n".format(self.intraTradeLow) +\
                  "avgEntryPrice: {0}\n".format(self.avgEntryPrice) + \
                  "shortStop: {0}\n".format(self.longStop) + \
                  "stopExit:{0}\n".format(self.stopExit)
            self.writeCtaLog(log)
            print log
            # 同步数据到数据库
        self.saveSyncData()
            # 发出状态更新事件
        self.putEvent()
    #----------------------------------------------------------------------
    def onOrder(self, order):
        '''
        处理order更新
        :param order:
        :return:
        '''
        # 记录log
        log = "-----" * 10 + "\n@onOrder\n" + \
              "orderTime: {0}; pos: {1} \n".format(order.orderTime, order.totalVolume) + \
              u"status {0}; vtOrderID: {1}\n".format(order.status, order.vtOrderID)+ \
              u"direction:{0}\n".format(order.direction)
        self.writeCtaLog(log)
        print log

        # 对于开仓，记录相关价格
        if order.direction == DIRECTION_LONG and order.offset == OFFSET_OPEN:
            if order.totalVolume == order.tradedVolume:
                # 更新入场价列表，更新平均入场价
                self.entryPriceList.append(order.price)
                self.avgEntryPrice = sum(self.entryPriceList) / len(self.entryPriceList)
                self.stopExit = round(self.avgEntryPrice * (100 - self.exitOnLossStop)/100)  # 固定止损价

        elif order.direction == DIRECTION_SHORT and order.offset == OFFSET_OPEN:
            # 更新入场价列表，更新平均入场价
            if order.totalVolume == order.tradedVolume:
                # 更新入场价列表，更新平均入场价
                self.entryPriceList.append(order.price)
                self.avgEntryPrice = sum(self.entryPriceList) / len(self.entryPriceList)
                self.stopExit = round(self.avgEntryPrice * (1 + self.exitOnLossStop)/100) # 固定止损价

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

    # 从当前目录加载策略类代码
    from strategyBollChannel01 import BollChannelStrategy01

    #  使用策略类中的默认参数，则参数配置字典留空
    d = {}
    # 初始化策略
    engine.initStrategy(BollChannelStrategy01, d)
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