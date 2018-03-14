# encoding: UTF-8

""""
基于布林带的交易策略
观察周期：1min
策略周期：5min
策略逻辑：
1. 信号：突破上轨、下轨
2. 过滤：均线多头、空头排列
3. 出场：分级止盈；固定止损
"""

from __future__ import division

import talib
import numpy as np

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate, BarGenerator, ArrayManager
from vnpy.trader.vtConstant import *


########################################################################
class BollingerBotStrategy01(CtaTemplate):
    """基于布林通道的交易策略"""
    className = 'BollingerBotStrategy01'
    author = 'Y.Raul'

    # 策略参数
    bollWindow = 28         # 通道窗口数
    entryDevUp = 4          # 开仓偏差
    entryDevDown = 3.2
    # exitDev = 1.2           # 平仓偏差
    # trailingPrcnt = 0.4
    # 移动止损百分比
    maWindow = 10           # 过滤用均线窗口
    initDays = 10           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量

    # 策略变量    
    bollMid = 0                         # 布林带中轨
    bollStd = 0                         # 布林带宽度
    entryUp = 0                         # 开仓上轨
    # exitUp = 0                          # 平仓上轨
    entryDown = 0                       #开仓下轨
    # exitDown = 0                        #平仓下轨

    dispacedLen = 0                        #均线平移长度
    maFilter = 0                        # 均线过滤
    maFilter1 = 0                       # 上一期均线                   

    # 分级出场设置
    trailingStart1 = 20
    trailingStart2 = 30
    exitOnTrailingStop1 = 5  # Trailing Stop 距离
    exitOnTrailingStop2 = 10  # Trailing Stop 距离
    exitOnLossStop = 20  # Loss Stop 距离

    # 价格相关变量
    intraTradeHigh = 0  # 持仓期内的最高点
    intraTradeLow = 0  # 持仓期内的最低点
    avgEntryPrice = 0
    minDiff = 1
    trailingExit = 0  #
    stopExit = 0  # 空头止损
    # longEntry = 0  # 多头开仓
    # shortEntry = 0

    # 信号相关变量
    buySig = False
    shortSig = False
    sellSig = False
    coverSig = False
    # entrusted = False #是否已有委托

    orderList = []                      # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'bollWindow',
                 'entryDevUp',
                 'entryDevDown',
                 'trailingStart1',
                 'trailingStart2',
                 'exitOnTrailingStop1',
                 'exitOnTrailingStop2',
                 'maWindow',
                 'initDays',
                 'fixedSize']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'buySig',
               'shortSig',
               'sellSig',
               'coverSig',
               'entryUp',
               'entryDown',
               'trailingExit',
               'stopExit',
               'intraTradeHigh',
               'intraTradeLow',
               'avgEntryPrice']
    
    # 同步列表
    syncList = ['pos',
                'intraTradeHigh']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(BollingerBotStrategy01, self).__init__(ctaEngine, setting)
        
        self.bm = BarGenerator(self.onBar, 5, self.onFiveBar)
        self.am = ArrayManager(30)
        self.orderList = []
        self.entryPriceList = []
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
        """收到Bar推送（必须由用户继承实现）"""
        # 观察周期1 Min,根据信号进行交易
        # 回测数据传送的bar.datetime，为bar的开始时间
        self.bm.updateBar(bar)
        if not self.trading:
            return


        self.date = bar.date
        self.time = bar.time
        # 检查交易信号
        if self.buySig:
            res = self.buy(bar.close, self.fixedSize, True)
            self.orderList.extend([x.split('.')[1] for x in res])
            # self.orderList.extend(res.split('.')[1])

            # self.entryPriceList.append(self.longEntry)
            # self.avgEntryPrice = sum(self.entryPriceList) / len(self.entryPriceList)
            # self.LossStopPrice = round(self.avgEntryPrice * (100.0 + self.exitOnLossStop) / 100)

            # self.intraTradeHigh = max(bar.high, self.avgEntryPrice)
            # self.intraTradeLow = min(bar.low, self.avgEntryPrice)
            log = "-----" * 10 + "\n@onBar\n" + \
                  "bar.datetime: {0}; pos: {1} \n".format(bar.datetime, self.pos) + \
                  "buySig: {0}; shortSig: {1}\n".format(self.buySig, self.shortSig) + \
                  "sellSig: {0}; coverSig: {1}\n".format(self.sellSig, self.coverSig) + \
                  "intraTradeHigh: {0}\n".format(self.intraTradeHigh) + \
                  "intraTradeLow: {0}\n".format(self.intraTradeLow)
            self.writeCtaLog(log)
            # 记录log
            log = "\n Trading: {0}\n".format(self.trading) + \
                  "{0} Buy : longEntry: {1};\n".format(bar.datetime, bar.close) + \
                  " entryUp:{0}; maFilter:{1}; maFilter1:{2}; \n".format(self.entryUp, self.maFilter, self.maFilter1)
            self.writeCtaLog(log)
            self.buySig = False
            # return

        if self.shortSig:
            self.res = self.short(bar.close, self.fixedSize, True)
            self.orderList.extend([x.split('.')[1] for x in self.res])
            # self.orderList.extend(res.split('.')[1])

            # self.LossStopPrice = round(self.shortEntry * (100.0 + self.exitOnLossStop) / 100)
            # self.entryPriceList.append(self.shortEntry)
            # self.avgEntryPrice = sum(self.entryPriceList) / len(self.entryPriceList)
            # self.LossStopPrice = round(self.avgEntryPrice * (100.0 + self.exitOnLossStop) / 100)
            #
            # self.intraTradeHigh = max(bar.high, self.avgEntryPrice)
            # self.intraTradeLow = min(bar.low, self.avgEntryPrice)
            log = "-----" * 10 + "\n@onBar\n" + \
                  "bar.datetime: {0}; pos: {1} \n".format(bar.datetime, self.pos) + \
                  "buySig: {0}; shortSig: {1}\n".format(self.buySig, self.shortSig) + \
                  "sellSig: {0}; coverSig: {1}\n".format(self.sellSig, self.coverSig) + \
                  "intraTradeHigh: {0}\n".format(self.intraTradeHigh) + \
                  "intraTradeLow: {0}\n".format(self.intraTradeLow)
            self.writeCtaLog(log)
            # 记录log
            log = "\n Trading: {0}\n".format(self.trading) + \
                  "{0} Short : shortEntry: {1};\n".format(bar.datetime, bar.close) + \
                  " entryDown:{0}; maFilter:{1}; maFilter1:{2}; \n".format(self.entryDown, self.maFilter, self.maFilter1)
            self.writeCtaLog(log)

            self.shortSig = False
            # return

        if self.sellSig:
            if bar.close > self.stopExit:
                price = self.trailingExit
            else:
                price = bar.close
            res = self.sell(price, abs(self.pos), True)
            # self.orderList.extend(res)
            log = "-----" * 10 + "\n@onBar\n" + \
                  "bar.datetime: {0}; pos: {1} \n".format(bar.datetime, self.pos) + \
                  "buySig: {0}; shortSig: {1}\n".format(self.buySig, self.shortSig) + \
                  "sellSig: {0}; coverSig: {1}\n".format(self.sellSig, self.coverSig) + \
                  "intraTradeHigh: {0}\n".format(self.intraTradeHigh) + \
                  "intraTradeLow: {0}\n".format(self.intraTradeLow)
            self.writeCtaLog(log)
            # 记录log
            log = "\n Trading: {0}\n".format(self.trading) + \
                  "{0} Sell : {1};\n".format(bar.datetime, bar.close) + \
                  " price:{0}; stopExit: {1}\n".format(price,self.stopExit)
            self.writeCtaLog(log)

            # self.entryPriceList = []
            # self.avgEntryPrice = 0
            # self.stopExit = 0
            self.sellSig = False
            # return

        if self.coverSig:
            if bar.close < self.stopExit:
                price = self.trailingExit
            else:
                price = bar.close
            res = self.cover(price, abs(self.pos), True)
            # self.orderList.extend(res)
            log = "-----" * 10 + "\n@onBar\n" + \
                  "bar.datetime: {0}; pos: {1} \n".format(bar.datetime, self.pos) + \
                  "buySig: {0}; shortSig: {1}\n".format(self.buySig, self.shortSig) + \
                  "sellSig: {0}; coverSig: {1}\n".format(self.sellSig, self.coverSig) + \
                  "intraTradeHigh: {0}\n".format(self.intraTradeHigh) + \
                  "intraTradeLow: {0}\n".format(self.intraTradeLow)
            self.writeCtaLog(log)
            # 记录log
            log = "\n Trading: {0}\n".format(self.trading) + \
                  "{0} Cover : {1};\n".format(bar.datetime, bar.close) + \
                  " price:{0}; stopExit: {1}\n".format(price,self.stopExit)
            self.writeCtaLog(log)

            # self.entryPriceList = []
            # self.avgEntryPrice = 0
            # self.stopExit = 0
            self.coverSig = False
            # return
        self.putEvent()
    #----------------------------------------------------------------------
    def onFiveBar(self, bar):
        """收到5分钟K线"""
        # 策略周期5Min,生成交易信号
        # 保存K线数据
        if not self.trading:
            return
        self.am.updateBar(bar)

        if not self.am.inited:
            return        

        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        self.cancelAll()
    
        # 计算指标数值
        self.bollMid = self.am.sma(self.bollWindow,True)[-1 * (self.dispacedLen + 1)]
        self.bollStd = self.am.std(self.bollWindow)
        self.entryUp = round(self.bollMid + self.bollStd * self.entryDevUp)
        self.entryDown = round(self.bollMid - self.bollStd * self.entryDevDown)
        maArray = self.am.sma(self.maWindow, True)
        self.maFilter = round(maArray[-1])
        self.maFilter1 = round(maArray[-2])
        
        # 判断是否要进行交易
        # 当前无仓位
        if self.pos == 0:
            self.intraTradeHigh = bar.high
            self.intraTradeLow = bar.low
            self.entryPriceList = []
            self.orderList =[]
            self.avgEntryPrice = 0

            if bar.close > self.maFilter and self.maFilter > self.maFilter1:
                # 均线多头过滤
                if bar.close >= self.entryUp:
                    # 上轨突破
                    self.buySig = True


            if bar.close < self.maFilter and self.maFilter < self.maFilter1:
                # 均线空头过滤
                if bar.close <= self.entryDown:
                    # 下轨突破
                    self.shortSig = True

            log = "-----" * 10 + "\n@onFiveBar\n" + \
                  "bar.datetime: {0}; pos: {1} ; close: {2}\n".format(bar.datetime, self.pos,bar.close) + \
                  "buySig: {0}; shortSig: {1}\n".format(self.buySig, self.shortSig) + \
                  "intraTradeHigh: {0}\n".format(self.intraTradeHigh) + \
                  "intraTradeLow: {0}\n".format(self.intraTradeLow)
            self.writeCtaLog(log)

        # 当前有仓位
        else:
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.intraTradeLow = min(self.intraTradeLow, bar.low)

            if self.pos > 0:
                # self.stopExit = self.avgEntryPrice - self.exitOnLossStop * self.minDiff #固定止损价位

                if self.intraTradeHigh >= self.avgEntryPrice + self.trailingStart2 * self.minDiff:
                    # 二级止赢判断 盈利80跳
                    if (bar.close <= self.intraTradeHigh - self.exitOnTrailingStop2 * self.minDiff):
                        # 回撤20跳
                            self.trailingExit = self.intraTradeHigh - self.exitOnTrailingStop2 * self.minDiff
                            self.sellSig = True
                            # if bar.close < self.longExit:
                            #     self.longExit = bar.close
                            # 记录log
                            # log = "\n{0} Sell(Trailing Stop2)\n".format(bar.datetime) + \
                            #     'bar.close: {0}; bar.low: {1}; longExit: {2}'.format(bar.close,bar.low, self.longExit)+ \
                            #     'intraTradeHigh: {0}; avgEntryPrice: {1}; bar.open: {2}'.format(self.intraTradeHigh,self.avgEntryPrice, bar.open)
                            # self.writeCtaLog(log)

                elif self.intraTradeHigh >= self.avgEntryPrice + self.trailingStart1 * self.minDiff:
                    # 一级止赢判断，盈利50跳
                        if (bar.close <= self.intraTradeHigh - self.exitOnTrailingStop1 * self.minDiff):
                            # 回撤20跳
                            self.trailingExit = self.intraTradeHigh - self.exitOnTrailingStop1 * self.minDiff
                            self.sellSig = True
                            # if bar.close < self.longExit:
                            #     self.longExit = bar.close
                            # 记录log
                            # log = "\n{0} Sell(Trailing Stop1)\n".format(bar.datetime) + \
                            #       'bar.close: {0}; bar.low: {1}; longExit: {2}'.format(bar.close, bar.low,
                            #                                                            self.longExit)+ \
                            #       'intraTradeHigh: {0}; avgEntryPrice: {1}; bar.open: {2}'.format(self.intraTradeHigh,self.avgEntryPrice, bar.open)
                            # self.writeCtaLog(log)
                elif self.stopExit != 0:
                        if (bar.close <= self.stopExit):
                    # 固定止损，回撤20跳
                            self.sellSig = True
                log = "-----" * 10 + "\n@onFiveBar\n" + \
                      "bar.datetime: {0}; pos: {1} ; close:{2}\n".format(bar.datetime, self.pos, bar.close) + \
                      "sellSig: {0}; coverSig: {1}\n".format(self.sellSig, self.coverSig) + \
                      "intraTradeHigh: {0}\n".format(self.intraTradeHigh) + \
                      "intraTradeLow: {0}\n".format(self.intraTradeLow) + \
                      "trailingStart1: {0}\n".format(self.avgEntryPrice + self.trailingStart1 * self.minDiff) + \
                      "trailingStart2: {0}\n".format(self.avgEntryPrice + self.trailingStart2 * self.minDiff) + \
                      "avgEntryPrice: {0}\n".format(self.avgEntryPrice) + \
                      "trailingStop: {0}\n".format(self.trailingExit) + \
                      "stopExit: {0}\n".format(self.stopExit)

                self.writeCtaLog(log)
                    # if bar.close < self.longExit:
                    #     self.longExit = bar.close
                    # 记录log
                    # log = "\n{0} Sell(Loss Stop)\n".format(bar.datetime) + \
                    #       'bar.close: {0}; bar.low: {1}; longExit: {2}'.format(bar.close, bar.low,
                    #                                                            self.longExit)+ \
                    #       'intraTradeHigh: {0}; avgEntryPrice: {1}; bar.open: {2}'.format(self.intraTradeHigh,
                    #                                                                       self.avgEntryPrice,
                    #                                                                       bar.open)
                    # self.writeCtaLog(log)

            elif self.pos < 0:
                # self.stopExit = self.avgEntryPrice + self.exitOnLossStop * self.minDiff #固定止损价
                if self.intraTradeLow <= self.avgEntryPrice - self.trailingStart2 * self.minDiff:
                    # 二级止赢判断 盈利80跳
                    if (bar.close >= self.intraTradeLow + self.exitOnTrailingStop2 * self.minDiff):
                        # 回撤20跳
                        self.trailingExit = self.intraTradeLow + self.exitOnTrailingStop2 * self.minDiff
                        self.coverSig = True
                        # if bar.close > self.shortExit:
                        #     self.shortExit = bar.close
                        # 记录log
                        # log = "\n{0} Cover(Trailing Stop1)\n".format(bar.datetime) + \
                        #       'bar.close: {0}; bar.low: {1}; shortExit: {2}'.format(bar.close, bar.low,
                        #                                                            self.shortExit)+ \
                        #       'intraTradeLow: {0}; avgEntryPrice: {1}; bar.open: {2}'.format(self.intraTradeLow,
                        #                                                                       self.avgEntryPrice,
                        #                                                                       bar.open)
                        # self.writeCtaLog(log)

                elif self.intraTradeLow <= self.avgEntryPrice - self.trailingStart1 * self.minDiff:
                    # 一级止赢判断，盈利50跳
                    if (bar.close >= self.intraTradeLow + self.exitOnTrailingStop1 * self.minDiff):
                        # 回撤20跳
                        self.trailingExit = self.intraTradeLow + self.exitOnTrailingStop1 * self.minDiff
                        self.coverSig = True
                        # if bar.close > self.shortExit:
                        #     self.shortExit = bar.close
                        # 记录log
                        # log = "\n{0} Cover(Trailing Stop2)\n".format(bar.datetime) + \
                        #       'bar.close: {0}; bar.low: {1}; shortExit: {2}'.format(bar.close, bar.low,
                        #                                                            self.shortExit)+ \
                        #       'intraTradeLow: {0}; avgEntryPrice: {1}; bar.open: {2}'.format(self.intraTradeLow,
                        #                                                                      self.avgEntryPrice,
                        #                                                                      bar.open)
                        # self.writeCtaLog(log)
                elif self.stopExit != 0:
                        if (bar.close >= self.stopExit):
                    # 固定止损，回撤20跳
                    # self.shortExit = self.avgEntryPrice + self.exitOnLossStop * self.minDiff
                            self.coverSig = True
                    # if bar.close > self.shortExit:
                    #     self.shortExit = bar.close
                    # 记录log
                    # log = "\n{0} Cover(Loss Stop)\n".format(bar.datetime) + \
                    #       'bar.close: {0}; bar.low: {1}; shortExit: {2}'.format(bar.close, bar.low,
                    #                                                             self.shortExit)+ \
                    #       'intraTradeLow: {0}; avgEntryPrice: {1}; bar.open: {2}'.format(self.intraTradeLow,
                    #                                                                      self.avgEntryPrice,
                    #                                                                      bar.open)
                    # self.writeCtaLog(log)

                log = "-----" * 10 + "\n@onFiveBar\n" + \
                      "bar.datetime: {0}; pos: {1} ; close:{2}\n".format(bar.datetime, self.pos, bar.close) + \
                      "sellSig: {0}; coverSig: {1}\n".format(self.sellSig, self.coverSig) + \
                      "intraTradeHigh: {0}\n".format(self.intraTradeHigh) + \
                      "intraTradeLow: {0}\n".format(self.intraTradeLow) + \
                      "trailingStart1: {0}\n".format(self.avgEntryPrice - self.trailingStart1 * self.minDiff)+\
                      "trailingStart2: {0}\n".format(self.avgEntryPrice - self.trailingStart2 * self.minDiff)+\
                      "avgEntryPrice: {0}\n".format(self.avgEntryPrice)+\
                      "trailingStop: {0}\n".format(self.trailingExit)+\
                      "stopExit: {0}\n".format(self.stopExit)

                self.writeCtaLog(log)
        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # CTA引擎中涉及到的交易方向类型
        # CTAORDER_BUY = u'买开'
        # CTAORDER_SELL = u'卖平'
        # CTAORDER_SHORT = u'卖开'
        # CTAORDER_COVER = u'买平'
        log = "-----" * 10 + "\n@onOrder\n" + \
              "orderTime: {0}; pos: {1} \n".format(order.orderTime, order.totalVolume) + \
              u"status {0}; vtOrderID: {1}\n".format(order.status, order.vtOrderID)
        self.writeCtaLog(log)

        # 对于开仓，记录相关价格
        # if order.vtOrderID in self.orderList:
        if order.direction == DIRECTION_LONG and order.offset == OFFSET_OPEN:
            if order.totalVolume == order.tradedVolume:
                # 更新入场价列表，更新平均入场价
                self.entryPriceList.append(order.price)
                self.avgEntryPrice = sum(self.entryPriceList) / len(self.entryPriceList)
                self.stopExit = self.avgEntryPrice - self.exitOnLossStop * self.minDiff  # 固定止损价
                    # self.orderList.remove(order.vtOrderID)

        elif order.direction == DIRECTION_SHORT and order.offset == OFFSET_OPEN:
            # 更新入场价列表，更新平均入场价
            if order.totalVolume == order.tradedVolume:
                # 更新入场价列表，更新平均入场价
                self.entryPriceList.append(order.price)
                self.avgEntryPrice = sum(self.entryPriceList) / len(self.entryPriceList)
                self.stopExit = self.avgEntryPrice + self.exitOnLossStop * self.minDiff  # 固定止损价
                # self.orderList.remove(order.vtOrderID)

        self.putEvent()

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        # print so.__dict__
        self.putEvent()

if __name__ == "__main__":
    from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine, OptimizationSetting, MINUTE_DB_NAME
    dbName = MINUTE_DB_NAME
    symbol = 'rb88'
    # 创建回测引擎对象
    engine = BacktestingEngine()
    # 设置回测使用的数据
    engine.setBacktestingMode(engine.BAR_MODE)  # 设置引擎的回测模式为K线
    engine.setDatabase(dbName, symbol)  # 设置使用的历史数据库
    engine.setStartDate('20130101',10)  # 设置回测用的数据起始日期
    engine.setEndDate('20171231')
    # 配置回测引擎参数
    engine.setSlippage(0)  # 设置滑点为股指1跳
    engine.setRate(1.1 / 10000)  # 设置手续费万1.1
    engine.setSize(10)  # 设置股指合约大小
    engine.setPriceTick(1)  # 设置股指最小价格变动
    engine.setCapital(10000)  # 设置回测本金

    # 从当前目录加载策略类代码
    from strategyBollingerBot01 import BollingerBotStrategy01

    #  使用策略类中的默认参数，则参数配置字典留空
    d = {}
    # 初始化策略
    engine.initStrategy(BollingerBotStrategy01, d)
    # 运行回测
    engine.runBacktesting()  # 运行回测
    # engine.showBacktestingResult()
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

    # logger2 = logging.getLogger("result")
    # fh2 = logging.FileHandler('./{0}_result.log'.format(engine.strategy.className))
    # logger2.setLevel(logging.INFO)
    # logger2.addHandler(fh2)

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
        # logger2.info("entryDate: {0}; entryPrice: {1}".format(dic['entryDt'], dic['entryPrice']))
        # logger2.info("exitDate: {0}; exitPrice: {1}".format(dic['exitDt'], dic['exitPrice']))
        # logger2.info("volume:{0}".format(dic['volume']))
        # logger2.info("pnl:{0}".format(dic['pnl']))
    import pandas as pd
    data = {'entryDate': entryDate, 'entryPrice': entryPrice, 'exitDate':exitDate, 'exitPrice':exitPrice, 'volume':volume, 'pnl':pnl}
    df = pd.DataFrame(data)
    df.to_csv('./{0}_result.csv'.format(engine.strategy.className), index=False)