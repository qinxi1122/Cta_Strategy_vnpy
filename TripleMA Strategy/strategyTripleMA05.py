# encoding: UTF-8

""""
基于三均线的交易策略，适合用在RB88 5分钟线上。
策略逻辑：
1. 信号：MA10，MA20金叉死叉
2. 过滤：MA120；
        MA10，MA120多头、空头排列(对比其的MA5）
3. 出场：分级跟随止损
        固定止损
4. 开盘5分钟时间段过滤
5. 日内平仓
6. 观察周期，策略周期分开

"""

from __future__ import division
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate, BarGenerator, ArrayManager
from datetime import datetime

########################################################################
class TripleMAStrategy05(CtaTemplate):
    """基于三均线的交易策略"""
    className = 'TripleMAStrategy05'
    author = 'Y.Raul'

    # 策略参数
    initDays = 10  # 初始化数据所用的天数
    windowCheck = True #交易窗口开关
    openWindowSize = 5 #开盘观察窗口，单位分钟
    closeWindowSize = 10 #收盘平仓窗口，单位分钟
    minDiff = 1 #最小变动单位

    # 策略变量
    # 仓位设置
    stepPos = 1  # 每次交易的数量
    maxPos = 4  # 仓位上限
    addPosRatio = 3

    # 均线设置
    maWindow1 = 10
    maWindow2 = 20
    maWindow3 = 120
    maWindow4 = 5
    atrWindow =  30 # ATR窗口数
    
    # 分级出场设置
    trailingStart1 = 50
    trailingStart2 = 80
    exitOnTrailingStop1 = 30  # Trailing Stop 距离
    exitOnTrailingStop2 = 20  # Trailing Stop 距离
    exitOnLossStop = 5 # Loss Stop 距离

    # 价格相关变量
    intraTradeHigh = 0  # 持仓期内的最高点
    intraTradeLow = 0  # 持仓期内的最低点
    longExit = 0  # 多头止损
    shortExit = 0  # 空头止损
    longEntry = 0  # 多头开仓
    shortEntry = 0
    avgEntryPrice = 0
    
    # 指标相关变量
    # ma次新值
    ma10 = 0
    ma20 = 0
    ma30 = 0
    # ma最新值
    ma11 = 0
    ma21 = 0
    ma31 = 0
    atrValue = 0  # ATR指标数值

    orderList = []  # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'maWindow1',
                 'maWindow2',
                 'maWindow3',
                 'maWindow4',
                 'initDays',
                 'addPos',
                 'stepPos',
                 'maxPos',
                 'exitOnTrailingStop',
                 'exitOnLossStop'
                 ]

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'ma10',
               'ma11',
               'ma20',
               'ma21',
               'ma30',
               'ma31',
               'atrValue',
               'avgEntryPrice'
               ]
    # 同步列表
    syncList = ['pos']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(TripleMAStrategy05, self).__init__(ctaEngine, setting)
        self.entryPriceList = []
        self.bm = BarGenerator(self.onBar, 5, self.onFiveBar)
        self.am = ArrayManager(size= 150)

        self.backTesting = True
        # 策略信号
        self.buySig = False
        self.shortSig = False
        self.sellSig = False
        self.coverSig = False

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)

        if self.backTesting:
            # 载入历史数据，并采用回放计算的方式初始化策略数值
            self.writeCtaLog(u"回测模式，载入历史数据，并采用回放计算的方式初始化策略数值")
            initData = self.loadBar(self.initDays)
            for bar in initData:
                self.onBar(bar)
        else:
            # self.trading = True
            self.inited =True
            self.writeCtaLog(u"实盘模式")
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.curDateTime = tick.datetime
        # 计算交易时间和平仓时间
        if self.windowCheck == True:
            self.__timeWindow(tick.datetime)
        else:
            self.tradeWindow = True

        self.bm.updateTick(tick)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 回测数据传送的bar.datetime，为bar的开始时间

        self.curDateTime = bar.datetime
        # 计算交易时间和平仓时间
        if self.windowCheck == True:
            self.__timeWindow(bar.datetime)
        else:
            self.tradeWindow = True
            
        self.bm.updateBar(bar)

        if self.pos == 0:
            self.intraTradeLow = bar.low
            self.intraTradeHigh = bar.high
        else:
            self.intraTradeHigh = max(bar.high, self.intraTradeHigh)
            self.intraTradeLow = min(bar.low, self.intraTradeLow)

        print "-----"*10
        print "@onBar"
        print "bar.datetime: {0}; pos: {1} ".format(bar.datetime,self.pos)
        print "buySig: {0}; shortSig: {1}".format(self.buySig, self.shortSig)
        print "sellSig: {0}; coverSig: {1}".format(self.sellSig, self.coverSig)
        print "intraTradeHigh: {0}".format(self.intraTradeHigh)
        print "intraTradeLow: {0}".format(self.intraTradeLow)

        #检查交易信号
        if self.buySig:
            
            self.longEntry = max(self.longEntry, bar.close)
            self.buy(self.longEntry, self.stepPos, True)

            # self.LossStopPrice = round(self.longEntry * (100.0 - self.exitOnLossStop) / 100)
            self.entryPriceList.append(self.longEntry)
            self.avgEntryPrice = sum(self.entryPriceList) / len(self.entryPriceList)
            self.LossStopPrice = round(self.avgEntryPrice * (100.0 + self.exitOnLossStop) / 100)

            self.intraTradeHigh = max(bar.high, self.avgEntryPrice)
            self.intraTradeLow = min(bar.low, self.avgEntryPrice)

            # 记录log
            log = "\n Trading: {0}\n".format(self.trading) + \
                  "{0} Buy : longEntry: {1};\n".format(bar.datetime, self.longEntry) + \
                  " ma10:{0}; ma11:{1}; ma20:{2}; ma21:{3}; ma30:{4};ma31:{5}\n".format(self.ma10, self.ma11, self.ma20,
                                                                                        self.ma21, self.ma30,
                                                                                        self.ma31) + \
                  "ma1_ma5:{0}; ma3_ma5:{1}\n".format(self.ma1_ma5, self.ma3_ma5)
                  # "LossStopPrice:{0}\n".format(self.LossStopPrice)
            self.writeCtaLog(log)

            self.buySig = False
            return

        if self.shortSig:

            self.shortEntry = min(self.shortEntry, bar.close)
            self.short(self.shortEntry, self.stepPos, True)

            # self.LossStopPrice = round(self.shortEntry * (100.0 + self.exitOnLossStop) / 100)
            self.entryPriceList.append(self.shortEntry)
            self.avgEntryPrice = sum(self.entryPriceList) / len(self.entryPriceList)
            self.LossStopPrice = round(self.avgEntryPrice * (100.0 + self.exitOnLossStop) / 100)

            self.intraTradeHigh = max(bar.high, self.avgEntryPrice)
            self.intraTradeLow = min(bar.low, self.avgEntryPrice)

            # 记录log
            log = "\n Trading: {0}\n".format(self.trading) + \
                  "{0} Short : shortEntry: {1};\n".format(bar.datetime, self.shortEntry) + \
                  " ma10:{0}; ma11:{1}; ma20:{2}; ma21:{3}; ma30:{4};ma31:{5}\n".format(self.ma10, self.ma11,
                                                                                        self.ma20, self.ma21,
                                                                                        self.ma30, self.ma31) + \
                  "ma1_ma5:{0}; ma3_ma5:{1}\n".format(self.ma1_ma5, self.ma3_ma5)
                  # "LossStopPrice:{0}\n".format(self.LossStopPrice)
            self.writeCtaLog(log)

            self.shortSig = False
            return
        
        if self.sellSig:
            
            self.longExit = min(bar.close, self.longExit)
            self.sell(self.longExit, abs(self.pos), True)

            # 记录log
            # log = "\n{0} Sell(Trailing Stop) : longExit: {1};\n".format(bar.datetime, self.longExit) + \
            #       "intraTradeHigh:{0}; atrValue:{1}; \n".format(self.intraTradeHigh, self.atrValue) + \
            #       "LongExit:{0}\n".format(self.longExit)
            # self.writeCtaLog(log)

            self.entryPriceList = []
            self.sellSig = False
            return
        
        if self.coverSig:
            
            self.shortExit = max(bar.close, self.shortExit)
            self.cover(self.shortExit, abs(self.pos), True)

            # 记录log
            # log = "\n{0} Cover(Trailing Stop) : bar.close: {1};\n".format(bar.datetime, bar.close) + \
            #       "intraTradeLow:{0}; atrValue:{1};\n".format(self.intraTradeLow, self.atrValue) + \
            #       "shortExit:{0}\n".format(self.shortExit)
            # self.writeCtaLog(log)

            self.entryPriceList = []
            self.coverSig = False
            return
            


    # ----------------------------------------------------------------------
    def onFiveBar(self, bar):
        """收到5分钟K线"""

        print "-----"*10
        print "@onFiveBar"
        print "bar.datetime: ", bar.datetime
        print "ma11: %f, ma10 %f" %(self.ma11, self.ma10)
        print "ma21: %f, ma20 %f" %(self.ma21, self.ma20)
        print "ma31: %f, ma30 %f" %(self.ma31, self.ma30)


        # 保存K线数据
        self.am.updateBar(bar)
        print "bar count: ", self.am.count
        print "am.inited: ", self.am.inited
        if not self.am.inited:
            return

        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        # 等于策略信号的生存期只有5分钟
        self.cancelAll()

        import talib

        # 计算指标数值
        ma3Array = self.am.sma(self.maWindow3, True)
        self.ma30 = round(ma3Array[-2])
        self.ma31 = round(ma3Array[-1])
        self.ma3_ma5 = round(talib.SMA(ma3Array, self.maWindow4)[-1])

        ma1Array = self.am.sma(self.maWindow1, True)
        self.ma10 = round(ma1Array[-2])
        self.ma11 = round(ma1Array[-1])
        self.ma1_ma5 = talib.SMA(ma1Array, self.maWindow4)[-1]

        ma2Array = self.am.sma(self.maWindow2, True)
        self.ma20 = round(ma2Array[-2])
        self.ma21 = round(ma2Array[-1])

        self.atrValue = round(self.am.atr(self.atrWindow))

        # 当前为空仓
        if self.pos == 0 :

            self.intraTradeHigh = bar.high
            self.intraTradeLow = bar.low
            self.avgEntryPrice = 0
            self.entryPriceList = []

            if self.tradeWindow:
                # 开多, bar.close > MA120,MA10 > MA120,MA10 上穿MA20，MA10、MA120向上
                if bar.close > self.ma31 and self.ma11 > self.ma31 \
                        and self.ma10 < self.ma20 and self.ma11 > self.ma21\
                        and self.ma31 > self.ma3_ma5 and self.ma11 > self.ma1_ma5:

                    self.buySig = True
                    self.longEntry = bar.close

                # 开空, bar.close < MA120,MA10 < MA120,MA10 下穿MA20, MA10,MA120向下
                elif bar.close < self.ma31 and self.ma11 < self.ma31 \
                        and self.ma10 > self.ma20 and self.ma11 < self.ma21\
                        and self.ma31 < self.ma3_ma5 and self.ma11 < self.ma1_ma5:

                    self.shortSig = True
                    self.shortEntry = bar.close
        if self.pos != 0:
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.intraTradeLow = min(self.intraTradeLow, bar.low)

            if self.tradeWindow:
                if self.pos > 0:
                    # 二级止赢判断 盈利80跳
                    if self.intraTradeHigh >= self.avgEntryPrice + self.trailingStart2 * self.minDiff:
                        # 回撤20跳
                        if (bar.close <= self.intraTradeHigh - self.exitOnTrailingStop2 * self.minDiff):
                                self.longExit = self.intraTradeHigh - self.exitOnTrailingStop2 * self.minDiff
                                self.sellSig = True
                                if bar.close < self.longExit:
                                    self.longExit = bar.close
                                # 记录log
                                log = "\n{0} Sell(Trailing Stop2)\n".format(bar.datetime) + \
                                    'bar.close: {0}; bar.low: {1}; longExit: {2}'.format(bar.close,bar.low, self.longExit)+ \
                                    'intraTradeHigh: {0}; avgEntryPrice: {1}; bar.open: {2}'.format(self.intraTradeHigh,self.avgEntryPrice, bar.open)
                                self.writeCtaLog(log)
                    # 一级止赢判断，盈利50跳
                    elif self.intraTradeHigh >= self.avgEntryPrice + self.trailingStart1 * self.minDiff:
                            # 回撤20跳
                            if (bar.close <= self.intraTradeHigh - self.exitOnTrailingStop1 * self.minDiff):
                                self.longExit = self.intraTradeHigh - self.exitOnTrailingStop1 * self.minDiff
                                self.sellSig = True
                                if bar.close < self.longExit:
                                    self.longExit = bar.close
                                # 记录log
                                log = "\n{0} Sell(Trailing Stop1)\n".format(bar.datetime) + \
                                      'bar.close: {0}; bar.low: {1}; longExit: {2}'.format(bar.close, bar.low,
                                                                                           self.longExit)+ \
                                      'intraTradeHigh: {0}; avgEntryPrice: {1}; bar.open: {2}'.format(self.intraTradeHigh,self.avgEntryPrice, bar.open)
                                self.writeCtaLog(log)
                    # 止损，回撤20跳
                    elif (bar.close <= self.avgEntryPrice - self.exitOnLossStop * self.minDiff):
                        self.longExit = self.avgEntryPrice - self.exitOnLossStop * self.minDiff
                        self.sellSig = True
                        if bar.close < self.longExit:
                            self.longExit = bar.close
                        # 记录log
                        log = "\n{0} Sell(Loss Stop)\n".format(bar.datetime) + \
                              'bar.close: {0}; bar.low: {1}; longExit: {2}'.format(bar.close, bar.low,
                                                                                   self.longExit)+ \
                              'intraTradeHigh: {0}; avgEntryPrice: {1}; bar.open: {2}'.format(self.intraTradeHigh,
                                                                                              self.avgEntryPrice,
                                                                                              bar.open)
                        self.writeCtaLog(log)

            elif self.pos < 0:
                # 二级止赢判断 盈利80跳
                if self.intraTradeLow <= self.avgEntryPrice - self.trailingStart2 * self.minDiff:
                    # 回撤20跳
                    if (bar.close >= self.intraTradeLow + self.exitOnTrailingStop2 * self.minDiff):
                        self.shortExit = self.intraTradeLow + self.exitOnTrailingStop2 * self.minDiff
                        self.coverSig = True
                        if bar.close > self.shortExit:
                            self.shortExit = bar.close
                        # 记录log
                        log = "\n{0} Cover(Trailing Stop1)\n".format(bar.datetime) + \
                              'bar.close: {0}; bar.low: {1}; shortExit: {2}'.format(bar.close, bar.low,
                                                                                   self.shortExit)+ \
                              'intraTradeLow: {0}; avgEntryPrice: {1}; bar.open: {2}'.format(self.intraTradeLow,
                                                                                              self.avgEntryPrice,
                                                                                              bar.open)
                        self.writeCtaLog(log)
                # 一级止赢判断，盈利50跳
                elif self.intraTradeLow <= self.avgEntryPrice - self.trailingStart1 * self.minDiff:
                        # 回撤20跳
                    if (bar.close >= self.intraTradeLow + self.exitOnTrailingStop1 * self.minDiff):
                        self.shortExit = self.intraTradeLow + self.exitOnTrailingStop1 * self.minDiff
                        self.coverSig = True
                        if bar.close > self.shortExit:
                            self.shortExit = bar.close
                        # 记录log
                        log = "\n{0} Cover(Trailing Stop2)\n".format(bar.datetime) + \
                              'bar.close: {0}; bar.low: {1}; shortExit: {2}'.format(bar.close, bar.low,
                                                                                   self.shortExit)+ \
                              'intraTradeLow: {0}; avgEntryPrice: {1}; bar.open: {2}'.format(self.intraTradeLow,
                                                                                             self.avgEntryPrice,
                                                                                             bar.open)
                        self.writeCtaLog(log)
                # 止损，回撤20跳
                elif (bar.close >= self.avgEntryPrice + self.exitOnLossStop * self.minDiff):
                    self.shortExit = self.avgEntryPrice + self.exitOnLossStop * self.minDiff
                    self.coverSig = True
                    if bar.close > self.shortExit:
                        self.shortExit = bar.close
                    # 记录log
                    log = "\n{0} Cover(Loss Stop)\n".format(bar.datetime) + \
                          'bar.close: {0}; bar.low: {1}; shortExit: {2}'.format(bar.close, bar.low,
                                                                                self.shortExit)+ \
                          'intraTradeLow: {0}; avgEntryPrice: {1}; bar.open: {2}'.format(self.intraTradeLow,
                                                                                         self.avgEntryPrice,
                                                                                         bar.open)
                    self.writeCtaLog(log)



                # # 加仓
                # if self.addPos and (self.maxPos - abs(self.pos) > 0):
                #     # print self.pos, (self.maxPos - abs(self.pos) )
                #     # print self.entryPriceList
                #
                #     lastEntryPrice = self.entryPriceList[-1]
                #     # 固定百分比加仓
                #     addPosOnPips= round(lastEntryPrice* self.addPosRatio/100)
                #
                #     self.writeCtaLog(u'\n 加仓判断:{0}，当前仓位:{1}'.format(bar.datetime, self.pos))
                #     # 加多仓
                #     if self.pos > 0 \
                #             and bar.close >= (lastEntryPrice + addPosOnPips* self.minDiff):
                #
                #         self.buySig = True
                #         self.longEntry = bar.close
                #
                #         # 记录log
                #         self.writeCtaLog(u'\n {0},加仓多单{1}手,价格:{2}'.format(bar.datetime, self.stepPos, self.longEntry))
                #
                #         return
                #
                #     # 加空仓
                #     if self.pos < 0 \
                #             and bar.close <= (lastEntryPrice + addPosOnPips*self.minDiff):
                #
                #         self.shortSig = True
                #         self.shortEntry = bar.close
                #         # 记录log
                #         self.writeCtaLog(u'{0},加仓空单{1}手,价格:{2}'.format(bar.datetime, self.stepPos, self.shortEntry))

        # 执行收盘前平仓检查
        # self.__dailyCloseCheck(bar)
        # 发出状态更新事件
        self.putEvent()

        # ----------------------------------------------------------------------

    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        log = u'\n OnOrder()更新，orderID:{0},{1},totalVol:{2},tradedVol:{3},offset:{4},price:{5},direction:{6},status:{7},orderTime: {7}'\
                         .format(order.orderID, order.vtSymbol, order.totalVolume,order.tradedVolume,
                                 order.offset, order.price, order.direction, order.status, order.orderTime)
        # self.writeCtaLog(log)
        self.putEvent()
    # ----------------------------------------------------------------------
    def onTrade(self, trade):

        log = u'\n OnTrade()更新，orderID:{0},{1},Vol:{2},price:{3},direction:{4},tradeTime:{5}' \
            .format(trade.orderID, trade.vtSymbol, trade.volume,trade.price, trade.direction,trade.tradeTime)
        # self.writeCtaLog(log)
        # 发出状态更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        log = u'\n OnStopOrder()停止单更新，stopOrderID:{0},Vol:{1},price:{2},direction:{3},status:{4}' \
            .format(so.stopOrderID, so.volume,so.price, so.direction,so.status)
        # self.writeCtaLog(log)

    def __timeWindow(self, dt):
        """交易与平仓窗口"""

        # 螺纹钢交易窗口 避开早盘和夜盘的前5分钟，防止隔夜跳空。
        # 日内平仓窗口
        self.closeWindow = False
        # 交易窗口
        self.tradeWindow = False
        # 开盘窗口
        self.openWindow = False

        # 开市期头5分钟波动较大
        if (dt.hour == 9 or dt.hour == 21) and dt.minute < self.openWindowSize:
            self.openWindow = False
            return

        # 日盘
        if dt.hour == 9 and dt.minute >= 0:
            self.tradeWindow = True
            return

        if dt.hour == 10:
            if dt.minute <= 15 or dt.minute >= 30:
                self.tradeWindow = True
                return

        if dt.hour == 11 and dt.minute <= 30:
            self.tradeWindow = True
            return

        if dt.hour == 13 and dt.minute >= 30:
            self.tradeWindow = True
            return

        if dt.hour == 14:

            if dt.minute < 60 - self.closeWindowSize:
                self.tradeWindow = True
                return
            else:
                self.closeWindow = True
                return

        # 夜盘

        if dt.hour == 21 and dt.minute >= 0:
            self.tradeWindow = True
            return

        if dt.hour == 22 and dt.minute < 60 - self.closeWindowSize:
            self.tradeWindow = True
            return
        else:
            self.closeWindow = True
            return

    def __dailyCloseCheck(self, bar):
        """每天收盘前检查，如果是亏损单，则平掉"""

        if self.pos == 0 :
            return False

        if not self.closeWindow:
            return False

        # 撤销未成交的订单
        self.cancelAll()
        log = u'{0},收盘前{1}分钟，撤单及平仓'.format(bar.datetime,self.closeWindowSize)
        self.writeCtaLog(log)
        self.avgEntryPrice = (sum(self.entryPriceList)) / len(self.entryPriceList)
        # 记录log
        log = "\n{0} __dailyCloseCheck : bar.close: {1};\n".format(bar.datetime, bar.close) + \
              "avgPrice:{0}\n".format(self.avgEntryPrice)+\
            "pos:{0}\n".format(self.pos)

        self.writeCtaLog(log)

        # 强制平仓
        if self.pos > 0 and bar.close < self.avgEntryPrice:
            self.writeCtaLog(u'强制日内平亏损多仓')

            # 降低两个滑点
            self.sell(bar.close-2*self.minDiff, abs(self.pos),True )
            # 记录log
            log = "\n{0} Sell(Force) : bar.close: {1};\n".format(bar.datetime, bar.close) + \
                  "entryPrice:{0}\n".format(bar.close - 2 * self.minDiff)
            self.writeCtaLog(log)

            return True

        if self.pos < 0 and bar.close > self.avgEntryPrice:
            self.writeCtaLog(u'强制日内平亏损空仓')

            self.cover(bar.close+2*self.minDiff, abs(self.pos),True )
            # 记录log
            log = "\n{0} Cover(Force) : bar.close: {1};\n".format(bar.datetime, bar.close) + \
                  "forcePrice:{0}\n".format(bar.close - 2 * self.minDiff)
            self.writeCtaLog(log)
            return True

        return True

if __name__ == '__main__':
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
    from strategyTripleMA05 import TripleMAStrategy05

    #  使用策略类中的默认参数，则参数配置字典留空
    d = {

    }
    # 初始化策略
    engine.initStrategy(TripleMAStrategy05, d)
    # 运行回测
    engine.runBacktesting()  # 运行回测
    engine.showBacktestingResult()
    engine.showDailyResult()
    d = engine.calculateBacktestingResult()

    import logging
    logger = logging.getLogger("backtest")
    fh = logging.FileHandler('./backtest.log')
    logger.setLevel(logging.INFO)
    logger.addHandler(fh)

    for log in engine.logList:
        logger.info(log)

    result = d['resultList']
    for trade in result:
        dic = trade.__dict__
        logger.info("entryDate: {0}; entryPrice: {1}".format(dic['entryDt'], dic['entryPrice']))
        logger.info("exitDate: {0}; exitPrice: {1}".format(dic['exitDt'], dic['exitPrice']))
        logger.info("pnl:{0}".format(dic['pnl']))