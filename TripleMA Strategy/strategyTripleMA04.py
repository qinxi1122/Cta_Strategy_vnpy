# encoding: UTF-8

""""
基于三均线的交易策略，适合用在RB88 5分钟线上。
策略逻辑：
1. 信号：MA10，MA20金叉死叉
2. 过滤：MA120；
        MA10，MA120多头、空头排列(对比其的MA5）
3. 出场：ATR跟随止损
        固定止损
4. 开盘5分钟时间段过滤
5. 日内平仓

"""

from __future__ import division
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate, BarGenerator, ArrayManager
from datetime import datetime
import sys
sys.path.append("../")
from myModule.ctaPolicy import CtaPolicy
from myModule.ctaPosition import CtaPosition

########################################################################
class TripleMAStrategy04(CtaTemplate):
    """基于三均线的交易策略"""
    className = 'TripleMAStrategy'
    author = 'Y.Raul'

    # 策略参数
    # 三均线长度设置
    maWindow1 = 10
    maWindow2 = 20
    maWindow3 = 120
    maWindow4 = 5
    slMultiplier = 2  # 计算止损距离的乘数
    atrWindow = 30  # ATR窗口数
    initDays = 1  # 初始化数据所用的天数
    fixedSize = 1  # 每次交易的数量
    maxSize = 4

    openWindowSize = 5 #开盘观察窗口，单位分钟
    closeWindowSize = 10 #收盘平仓窗口，单位分钟
    minDiff = 1 #最小变动单位

    # 策略变量
    atrValue = 0  # ATR指标数值
    stoploss = 1.5
    stopRatio = 3
    addRatio = 5

    intraTradeHigh = 0  # 持仓期内的最高点
    intraTradeLow = 0  # 持仓期内的最低点
    longStop = 0  # 多头止损
    shortStop = 0  # 空头止损

    # ma次新值
    ma10 = 0
    ma20 = 0
    ma30 = 0
    # ma最新值
    ma11 = 0
    ma21 = 0
    ma31 = 0

    longEntry = 0  # 多头开仓
    longExit = 0  # 多头平仓
    shortEntry = 0
    shortExit = 0

    orderList = []  # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'maWindow1',
                 'maWindow2',
                 'maWindow3',
                 'maWindow4'
                 'initDays',
                 'fixedSize',
                 'maxSize']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'ma10',
               'ma11',
               'ma20',
               'ma21']
    # 同步列表
    syncList = ['pos']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(TripleMAStrategy04, self).__init__(ctaEngine, setting)

        self.bm = BarGenerator(self.onBar, 5, self.onFiveBar)

        # 由于maWindow3的长度是120，所以ArrayManager的size要增加至150
        self.am = ArrayManager(size=150)

        # 创建CtaPolicy策略规则实体
        self.policy = CtaPolicy()
        self.policy.exitOnLastRtnPips = self.slMultiplier
        self.policy.addPosOnPips = 0 #加仓间隔
        self.policy.addPos = True #加仓开关

        # 创建仓位管理模块
        self.position = CtaPosition(self)
        self.position.maxPos = self.maxSize #最大仓位
        #

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

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
        self.bm.updateTick(tick)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 更新策略执行的时间（用于回测时记录发生的时间）
        # 回测数据传送的bar.datetime，为bar的结束时间
        self.curDateTime = bar.datetime

        # 计算交易时间和平仓时间
        self.__timeWindow(bar.datetime)
        self.bm.updateBar(bar)

    # ----------------------------------------------------------------------
    def onFiveBar(self, bar):
        """收到5分钟K线"""
        # 保存K线数据
        self.am.updateBar(bar)
        if not self.am.inited:
            return
        print bar.datetime
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        self.cancelAll()

        import talib
        # 计算指标数值
        ma3Array = self.am.sma(self.maWindow3, True)
        self.ma30 = round(ma3Array[-2])
        self.ma31 = round(ma3Array[-1])
        ma3_ma5 = round(talib.SMA(ma3Array, self.maWindow4)[-1])

        ma1Array = self.am.sma(self.maWindow1, True)
        self.ma10 = round(ma1Array[-2])
        self.ma11 = round(ma1Array[-1])
        ma1_ma5 = talib.SMA(ma1Array, self.maWindow4)[-1]

        ma2Array = self.am.sma(self.maWindow2, True)
        self.ma20 = round(ma2Array[-2])
        self.ma21 = round(ma2Array[-1])

        self.atrValue = round(self.am.atr(self.atrWindow))

        # 判断是否要进行交易
        # 当前无仓位，发送OCO开仓委托
        if self.pos == 0 and self.tradeWindow:
            self.intraTradeHigh = bar.high
            self.intraTradeLow = bar.low

            # 开多, bar.close > MA120,MA10 > MA120,MA10 上穿MA20，MA10、MA120向上
            if bar.close > self.ma31 and self.ma11 > self.ma31 \
                    and self.ma10 < self.ma20 and self.ma11 > self.ma21\
                    and self.ma31 > ma3_ma5 and self.ma11 > ma1_ma5:

                self.longEntry = bar.close
                self.buy(self.longEntry, self.fixedSize, True)

                self.policy.entryPrice = self.longEntry
                self.policy.exitOnStopPrice = round(self.policy.entryPrice * (100.0 -self.stopRatio)/100)
                self.position.posList.append(self.policy.entryPrice)
                # 记录log
                log = "\n Trading: {0}\n".format(self.trading)+\
                    "{0} Buy : bar.close: {1};\n".format(bar.datetime, bar.close) + \
                      " ma10:{0}; ma11:{1}; ma20:{2}; ma21:{3}; ma30:{4};ma31:{5}\n".format(self.ma10,self.ma11,self.ma20,self.ma21,self.ma30,self.ma31) + \
                    "ma1_ma5:{0}; ma3_ma5:{1}\n".format(ma1_ma5,ma3_ma5)+\
                    "exitOnStopPrice:{0}\n".format(self.policy.exitOnStopPrice)
                self.writeCtaLog(log)

            # 开空, bar.close < MA120,MA10 < MA120,MA10 下穿MA20, MA10,MA120向下
            elif bar.close < self.ma31 and self.ma11 < self.ma31 \
                    and self.ma10 > self.ma20 and self.ma11 < self.ma21\
                    and self.ma31 < ma3_ma5 and self.ma11 < ma1_ma5:
                self.shortEntry = bar.close

                self.short(self.shortEntry, self.fixedSize, True)


                self.policy.entryPrice = self.shortEntry
                self.policy.exitOnStopPrice = round(self.policy.entryPrice * (100.0  + self.stopRatio)/100)
                self.position.posList.append(self.policy.entryPrice)
                # 记录log
                log = "\n Trading: {0}\n".format(self.trading)+\
                    "{0} Short : bar.close: {1};\n".format(bar.datetime, bar.close) + \
                      " ma10:{0}; ma11:{1}; ma20:{2}; ma21:{3}; ma30:{4};ma31:{5}\n".format(self.ma10, self.ma11,
                                                                                            self.ma20, self.ma21,
                                                                                            self.ma30, self.ma31) + \
                      "ma1_ma5:{0}; ma3_ma5:{1}\n".format(ma1_ma5, ma3_ma5) + \
                      "exitOnStopPrice:{0}\n".format(self.policy.exitOnStopPrice)
                self.writeCtaLog(log)

        else:
            # policy 跟随止损
            if self.policy.exitOnLastRtnPips:
                # 持有多头仓位
                if self.pos > 0 and self.tradeWindow:
                    self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
                    self.intraTradeLow = bar.low
                    self.longStop = round(self.intraTradeHigh - self.atrValue * self.policy.exitOnLastRtnPips)
                    if bar.close < self.longStop:
                        self.sell(bar.close, abs(self.pos), True)

                        # 记录log
                        log = "\n{0} Sell(Trailing Stop) : bar.close: {1};\n".format(bar.datetime, bar.close) + \
                            "intraTradeHigh:{0}; atrValue:{1}; dev: {2}\n".format(self.intraTradeHigh,self.atrValue,self.policy.exitOnLastRtnPips)+\
                              "LongStop:{0}\n".format(self.longStop)
                        self.writeCtaLog(log)
                        self.putEvent()

                        self.position.posList = []
                        return
                # 持有空头仓位
                if self.pos < 0 and self.tradeWindow:
                    self.intraTradeHigh = bar.high
                    self.intraTradeLow = min(self.intraTradeLow, bar.low)
                    self.shortStop = round(self.intraTradeLow + self.atrValue * self.policy.exitOnLastRtnPips)
                    if bar.close > self.shortStop:
                        self.cover(bar.close, abs(self.pos), True)
                        # 记录log
                        log = "\n{0} Cover(Trailing Stop) : bar.close: {1};\n".format(bar.datetime, bar.close) + \
                              "intraTradeLow:{0}; atrValue:{1}; dev: {2}\n".format(self.intraTradeLow, self.atrValue,
                                                                                    self.policy.exitOnLastRtnPips) + \
                              "LongStop:{0}\n".format(self.longStop)
                        self.writeCtaLog(log)
                        self.putEvent()
                        self.position.posList = []
                        return

            # policy 固定止损
            if self.policy.exitOnStopPrice > 0:
                    # 持有多头仓位
                if self.pos > 0 and bar.close < self.policy.exitOnStopPrice:
                    # 记录log
                    log = "\n{0} Sell(Stop Loss) : bar.close: {1};\n".format(bar.datetime, bar.close) + \
                          "exitOnStopPrice:{0}\n".format(self.policy.exitOnStopPrice) + \
                        "Ratio:{0}%\n".format((1 - bar.close/self.policy.exitOnStopPrice)*100)
                    self.writeCtaLog(log)
                    self.sell(bar.close, abs(self.pos), True)
                    self.putEvent()

                    self.position.posList = []
                    return
                    # 持有空头仓位
                if self.pos < 0 and bar.close > self.policy.exitOnStopPrice:
                    # 记录log
                    log = "\n{0} Cover(Stop Loss) : bar.close: {1};\n".format(bar.datetime, bar.close) + \
                          "exitOnStopPrice:{0}\n".format(self.policy.exitOnStopPrice) +\
                    "Ratio:{0}%\n".format((1 - bar.close / self.policy.exitOnStopPrice) * 100)
                    self.writeCtaLog(log)

                    self.cover(bar.close, abs(self.pos), True)
                    self.putEvent()

                    self.position.posList = []
                    return

            # 海龟加仓
            if self.policy.addPos and (self.maxSize - abs(self.pos) > 0):
                # 加仓策略使用特定pip间隔（例如海龟的N）
                # 根据 ATR更新N
                # self.policy.addPosOnPips = int(self.atrValue /(2* self.minDiff))
                # 固定百分比加仓
                self.policy.addPosOnPips = round(self.policy.entryPrice * self.addRatio/100)
                self.writeCtaLog(u'\n 加仓判断:{0}，当前仓位:{1}'.format(bar.datetime, self.pos))
                # 加多仓
                if self.pos > 0 \
                        and bar.close >= self.policy.entryPrice +  self.policy.addPosOnPips * self.minDiff:
                    self.writeCtaLog(u'\n {0},加仓多单{1}手,价格:{2}'.format(bar.datetime, self.fixedSize, bar.close))
                    self.buy(bar.close, self.fixedSize, True)
                    # 更新开仓价格
                    self.policy.entryPrice = bar.close
                    self.position.posList.append(self.policy.entryPrice)
                    self.avgPrice = sum(self.position.posList)/len(self.position.posList)
                    # 更新固定止损价
                    self.policy.exitOnStopPrice = round( self.avgPrice* (100.0 - self.stopRatio) / 100)
                    self.writeCtaLog(u'\n 更新止损价:{0}，最新仓位:{1}'.format(self.policy.exitOnStopPrice,self.pos))

                    return
                # 加空仓
                if self.pos < 0 \
                        and bar.close <= (self.policy.entryPrice + self.policy.addPosOnPips*self.minDiff):
                    self.writeCtaLog(u'{0},加仓空单{1}手,价格:{2}'.format(bar.datetime, self.fixedSize, bar.close))
                    self.short(bar.close, self.fixedSize, True)
                    # 更新开仓价格
                    self.policy.entryPrice = bar.close
                    self.position.posList.append(self.policy.entryPrice)
                    self.avgPrice = (sum(self.position.posList)) / len(self.position.posList)
                    # 更新固定止损价
                    self.policy.exitOnStopPrice = round(self.avgPrice * (100.0 + self.stopRatio) / 100)
                    self.writeCtaLog(u'\n 更新止损价:{0}，最新仓位:{1}'.format(self.policy.exitOnStopPrice, self.pos))
                    return

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
        self.writeCtaLog(log)
        self.putEvent()
    # ----------------------------------------------------------------------
    def onTrade(self, trade):

        log = u'\n OnTrade()更新，orderID:{0},{1},Vol:{2},price:{3},direction:{4},tradeTime:{5}' \
            .format(trade.orderID, trade.vtSymbol, trade.volume,trade.price, trade.direction,trade.tradeTime)
        self.writeCtaLog(log)
        # 发出状态更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        log = u'\n OnStopOrder()停止单更新，stopOrderID:{0},Vol:{1},price:{2},direction:{3},status:{4}' \
            .format(so.stopOrderID, so.volume,so.price, so.direction,so.status)
        self.writeCtaLog(log)

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
        self.avgPrice = (sum(self.position.posList)) / len(self.position.posList)
        # 记录log
        log = "\n{0} __dailyCloseCheck : bar.close: {1};\n".format(bar.datetime, bar.close) + \
              "avgPrice:{0}\n".format(self.avgPrice)+\
            "pos:{0}\n".format(self.pos)

        self.writeCtaLog(log)

        # 强制平仓
        if self.pos > 0 and bar.close < self.avgPrice:
            self.writeCtaLog(u'强制日内平亏损多仓')

            # 降低两个滑点
            self.sell(bar.close-2*self.minDiff, abs(self.pos),True )
            # 记录log
            log = "\n{0} Sell(Force) : bar.close: {1};\n".format(bar.datetime, bar.close) + \
                  "entryPrice:{0}\n".format(bar.close - 2 * self.minDiff)
            self.writeCtaLog(log)

            return True

        if self.pos < 0 and bar.close > self.avgPrice:
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
    engine.setStartDate('20170101',10)  # 设置回测用的数据起始日期
    engine.setEndDate('20171231')
    # 配置回测引擎参数
    engine.setSlippage(0)  # 设置滑点为股指1跳
    engine.setRate(0.3 / 10000)  # 设置手续费万0.3
    engine.setSize(10)  # 设置股指合约大小
    engine.setPriceTick(1)  # 设置股指最小价格变动
    engine.setCapital(100000)  # 设置回测本金

    # 从当前目录加载策略类代码
    from strategyTripleMA04 import TripleMAStrategy04

    #  使用策略类中的默认参数，则参数配置字典留空
    d = {}
    # 初始化策略
    engine.initStrategy(TripleMAStrategy04, d)
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