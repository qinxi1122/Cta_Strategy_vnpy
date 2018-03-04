# encoding: UTF-8

# 首先写系统内置模块
import sys
from datetime import datetime, timedelta, date
from time import sleep

# 其次，导入vnpy的基础模块
import sys
sys.path.append('..')
from vtConstant import EMPTY_STRING, EMPTY_INT, DIRECTION_LONG, DIRECTION_SHORT, OFFSET_OPEN, STATUS_CANCELLED,EMPTY_FLOAT

# 然后是自己编写的模块
from ctaTemplate import *
from ctaBase import *
from ctaLineBar import *
from ctaPolicy import *
from ctaPosition import *


class Strategy_TripleMa(CtaTemplate):
    """螺纹钢、5分钟级别、三均线策略
    策略：
    10，20，120均线，120均线做多空过滤
    MA120之上
        MA10 上穿 MA20，金叉，做多
        MA10 下穿 MA20，死叉，平多
    MA120之下
        MA10 下穿 MA20，死叉，做空
        MA10 上穿 MA20，金叉，平空
    更新记录
    v0.1 初始版本，带有1分钟后撤单逻辑
    v0.2 优化开仓条件
    v0.3 优化平仓
    v0.4 海龟加仓法
    v0.5 趋势网格（去除海龟加仓）

    """
    className = 'Strategy_TripleMa'
    author = u'李来佳'

    # 策略在外部设置的参数
    inputSS = 1                # 参数SS，下单，范围是1~100，步长为1，默认=1，
    minDiff = 1                # 商品的最小交易单位
    atrLength = 20             # 平均波动周期 ATR Length
    maxPos = 4
    gridHeight = 10            # 网格高度

#----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting=None):
        """Constructor"""
        super(Strategy_TripleMa, self).__init__(ctaEngine, setting)

        # 增加监控参数项目
        self.paramList.append('inputSS')
        self.paramList.append('minDiff')

        # 增加监控变量项目
        self.varList.append('pos')              # 仓位
        self.varList.append('entrust')          # 是否正在委托

        self.curDateTime = None                 # 当前Tick时间
        self.curTick = None                     # 最新的tick
        self.lastOrderTime = None               # 上一次委托时间
        self.cancelSeconds = 60                 # 撤单时间(秒)

        # 定义日内的交易窗口
        self.openWindow = False                 # 开市窗口
        self.tradeWindow = False                # 交易窗口
        self.closeWindow = False                # 收市平仓窗口

        self.inited = False                     # 是否完成了策略初始化
        self.backtesting = False                # 是否回测
        self.lineM5 = None                      # 5分钟K线

        # 创建一个策略规则
        self.policy = CtaPolicy()
        self.atr = 10                           # 平均波动
        self.policy.addPos = True               # 是否激活加仓策略
        self.policy.addPosOnPips = 1            # 加仓策略1，固定点数（动态ATR）

        self.highPriceInLong = EMPTY_FLOAT      # 成交后，最高价格
        self.lowPriceInShort = EMPTY_FLOAT      # 成交后，最低价格

        # 增加仓位管理模块
        self.position = CtaPosition(self)
        self.position.maxPos = self.maxPos

        # 网格列表,首次开仓后，必须有两个值，一个开仓价，一个是平仓价。
        # 当最高价超出最后一个值>n个网格时,自动添加item
        self.gridPrices = []
        self.gridOpened = False     # 这里demo，简单的只做一次
        self.gridStopPrice = EMPTY_FLOAT
        self.gridWinPrice = EMPTY_FLOAT

        if setting:
            # 根据配置文件更新参数
            self.setParam(setting)

            # 创建的M5 K线
            lineM5Setting = {}
            lineM5Setting['name'] = u'M5'                   # k线名称
            lineM5Setting['barTimeInterval'] = 60*5         # K线的Bar时长

            lineM5Setting['inputMa1Len'] = 10               # 第1条均线
            lineM5Setting['inputMa2Len'] = 20               # 第2条均线
            lineM5Setting['inputMa3Len'] = 120              # 第3条均线
            lineM5Setting['inputAtr1Len'] = self.atrLength  # ATR
            lineM5Setting['inputPreLen'] = 10               # 前高/前低
            lineM5Setting['minDiff'] = self.minDiff
            lineM5Setting['shortSymbol'] = self.shortSymbol
            self.lineM5 = CtaLineBar(self, self.onBarM5, lineM5Setting)

        self.onInit()

    #----------------------------------------------------------------------
    def onInit(self, force = False):
        """初始化 """
        if force:
            self.writeCtaLog(u'策略强制初始化')
            self.inited = False
            self.trading = False                        # 控制是否启动交易
        else:
            self.writeCtaLog(u'策略初始化')
            if self.inited:
                self.writeCtaLog(u'已经初始化过，不再执行')
                return

        self.pos = EMPTY_INT                 # 初始化持仓
        self.entrust = EMPTY_INT             # 初始化委托状态

        if not self.backtesting:
            # 这里需要加载前置数据哦。
            self.inited = True                   # 更新初始化标识
            self.trading = True                  # 启动交易

        self.putEvent()
        self.writeCtaLog(u'策略初始化完成')

    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'启动')

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.uncompletedOrders.clear()
        self.pos = EMPTY_INT
        self.entrust = EMPTY_INT

        self.writeCtaLog(u'停止' )
        self.putEvent()

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """交易更新"""
        self.writeCtaLog(u'{0},OnTrade(),当前持仓：{1} '.format(self.curDateTime, self.position.pos))


    def clearGrid(self):
        """"清空网格数据"""
        if self.pos != 0:
            return
        self.gridPrices = []
        self.gridOpened = False
        self.gridStopPrice = EMPTY_FLOAT
        self.gridWinPrice = EMPTY_FLOAT

    def buildGrid(self):
        if self.pos == self.inputSS:
            # 首次开仓，添加基准价格和上一级网格价格
            self.gridPrices.append(self.policy.entryPrice)
            self.gridPrices.append(self.policy.entryPrice+self.gridHeight)
        elif self.pos == 0 - self.inputSS:
            # 首次开仓，添加基准价格和上一级网格价格
            self.gridPrices.append(self.policy.entryPrice)
            self.gridPrices.append(self.policy.entryPrice - self.gridHeight)

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """报单更新"""
        self.writeCtaLog(u'OnOrder()报单更新，orderID:{0},{1},totalVol:{2},tradedVol:{3},offset:{4},price:{5},direction:{6},status:{7}'
                         .format(order.orderID, order.vtSymbol, order.totalVolume,order.tradedVolume,
                                 order.offset, order.price, order.direction, order.status))

        # 委托单主键，vnpy使用 "gateway.orderid" 的组合
        orderkey = order.gatewayName+u'.'+order.orderID

        if orderkey in self.uncompletedOrders:
            if order.totalVolume == order.tradedVolume:
                # 开仓，平仓委托单全部成交
                # 平空仓完成(cover)
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_LONG and order.offset != OFFSET_OPEN:
                    self.writeCtaLog(u'平空仓完成，原仓位:{0}'.format(self.pos))
                    self.position.closePos(direction=DIRECTION_LONG, vol=order.tradedVolume)
                    self.writeCtaLog(u'新仓位:{0}'.format(self.pos))
                    self.clearGrid()

                # 平多仓完成(sell)
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_SHORT and order.offset != OFFSET_OPEN:
                    self.writeCtaLog(u'平多仓完成，原仓位:{0}'.format(self.pos))
                    self.position.closePos(direction=DIRECTION_SHORT, vol=order.tradedVolume)
                    self.writeCtaLog(u'新仓位:{0}'.format(self.pos))
                    self.clearGrid()

                # 开多仓完成
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_LONG and order.offset == OFFSET_OPEN:
                    self.writeCtaLog(u'开多仓完成，原仓位:{0}'.format(self.pos))
                    self.position.openPos(direction=DIRECTION_LONG, vol=order.tradedVolume, price=order.price)
                    self.writeCtaLog(u'新仓位:{0}'.format(self.pos))
                    self.buildGrid()

                # 开空仓完成
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_SHORT and order.offset == OFFSET_OPEN:
                    # 更新仓位
                    self.writeCtaLog(u'开空仓完成，原仓位:{0}'.format(self.pos))
                    self.position.openPos(direction=DIRECTION_SHORT, vol=order.tradedVolume, price=order.price)
                    self.writeCtaLog(u'新仓位:{0}'.format(self.pos))
                    self.buildGrid()

                del self.uncompletedOrders[orderkey]

                if len(self.uncompletedOrders) == 0:
                    self.entrust = 0
                    self.lastOrderTime = None

                if self.position.pos == 0:
                    self.highPriceInLong = EMPTY_FLOAT
                    self.lowPriceInShort = EMPTY_FLOAT
                    self.policy.entryPrice = EMPTY_FLOAT

            elif order.tradedVolume > 0 and not order.totalVolume == order.tradedVolume and order.offset != OFFSET_OPEN:
                # 平仓委托单部分成交
                pass

            elif order.offset == OFFSET_OPEN and order.status == STATUS_CANCELLED:
                # 开仓委托单被撤销
                self.entrust = 0
                pass

            else:
                self.writeCtaLog(u'OnOrder()委托单返回，total:{0},traded:{1}'
                                 .format(order.totalVolume, order.tradedVolume,))

        self.putEvent()         # 更新监控事件

    # ----------------------------------------------------------------------
    def onStopOrder(self, orderRef):
        """停止单更新"""
        self.writeCtaLog(u'{0},停止单触发，orderRef:{1}'.format(self.curDateTime, orderRef))
        pass

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """行情更新
        :type tick: object
        """
        self.curTick = tick

        if (tick.datetime.hour >= 3 and tick.datetime.hour <= 8) or (tick.datetime.hour >= 16 and tick.datetime.hour <= 20):
            self.writeCtaLog(u'休市/集合竞价排名时数据不处理')
            return

        # 更新策略执行的时间（用于回测时记录发生的时间）
        self.curDateTime = tick.datetime

        # 2、计算交易时间和平仓时间
        self.__timeWindow(tick)

        # 推送Tick到lineM5
        self.lineM5.onTick(tick)

        # 首先检查是否是实盘运行还是数据预处理阶段
        if not (self.inited and len(self.lineM5.lineMa3) > 0):
            return

        # 持有多仓/空仓时，更新最高价和最低价
        if self.position.pos > 0:
            if tick.lastPrice > self.highPriceInLong:
                self.highPriceInLong = tick.lastPrice

        if self.position.pos < 0:
            if tick.lastPrice < self.lowPriceInShort:
                self.lowPriceInShort = tick.lastPrice

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """分钟K线数据更新（仅用于回测时，从策略外部调用)"""

        # 更新策略执行的时间（用于回测时记录发生的时间）
        # 回测数据传送的bar.datetime，为bar的开始时间，所以，到达策略时，当前时间为bar的结束时间
        self.curDateTime = bar.datetime + timedelta(seconds=self.lineM5.barTimeInterval)

        # 2、计算交易时间和平仓时间
        self.__timeWindow(bar.datetime)

        # 推送tick到15分钟K线
        self.lineM5.addBar(bar)

        # 4、交易逻辑
        # 首先检查是否是实盘运行还是数据预处理阶段
        if not self.inited:
            if len(self.lineM5.lineBar) > 120 + 5:
                self.inited = True
            else:
                return

    def onBarM5(self, bar):
        """  分钟K线数据更新，实盘时，由self.lineM5的回调"""

        # 调用lineM5的显示bar内容
        self.writeCtaLog(self.lineM5.displayLastBar())

        # 未初始化完成
        if not self.inited:
            if len(self.lineM5.lineBar) > 120 + 5:
                self.inited = True
            else:
                return

        # 更新ATR
        if self.lineM5.lineAtr1[-1] > 2:
            self.atr = max(self.lineM5.lineAtr1[-1], 5)
            # 2倍的ATR作为跟随止损
            self.policy.exitOnLastRtnPips = int((self.atr*2) / self.minDiff) + 1

        # 更新最高价/最低价
        if self.backtesting:
            # 持有多仓/空仓时，更新最高价和最低价
            if self.position.pos > 0:
                if bar.high > self.highPriceInLong:
                    self.highPriceInLong = bar.high

                    # 增加一个上网格
                    if self.highPriceInLong - self.gridPrices[-1] > self.gridHeight*1.5:
                        self.gridPrices.append(self.gridPrices[-1]+self.gridHeight)

            if self.position.pos < 0:
                if bar.low < self.lowPriceInShort:
                    self.lowPriceInShort = bar.low

                    # 增加一个下网格
                    if self.lowPriceInShort - self.gridPrices[-1] < (0 - self.gridHeight * 1.5):
                        self.gridPrices.append(self.gridPrices[-1] - self.gridHeight)

        # 执行撤单逻辑
        self.__cancelLogic(dt=self.curDateTime)

        if len(self.lineM5.lineMa3) > 5:
            ma5_Ma120 = ta.MA(numpy.array(self.lineM5.lineMa3, dtype=float), 5)[-1]
        else:
            ma5_Ma120 = self.lineM5.lineMa3[-1]

        ma5_Ma10 = ta.MA(numpy.array(self.lineM5.lineMa1, dtype=float), 5)[-1]

        # 如果未持仓，检查是否符合开仓逻辑
        if self.position.pos == 0:
            # MA10 上穿MA20， MA10 > MA120， bar.close > MA120, MA(MA120)< MA120
            if self.lineM5.lineMa1[-2] < self.lineM5.lineMa2[-2] \
                    and self.lineM5.lineMa1[-1] > self.lineM5.lineMa2[-1] \
                    and self.lineM5.lineMa1[-1] > self.lineM5.lineMa3[-1] \
                    and bar.close > self.lineM5.lineMa3[-1] \
                    and ma5_Ma120 < self.lineM5.lineMa3[-1] \
                    and self.lineM5.lineMa1[-1] > ma5_Ma10:

                self.writeCtaLog(u'{0},开仓多单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                orderid = self.buy(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                if orderid:
                    # 更新下单时间（为了定时撤单）
                    self.lastOrderTime = self.curDateTime
                    # 更新开仓价格
                    self.policy.entryPrice = bar.close
                    # 设置前低为止损价
                    self.policy.exitOnStopPrice = self.lineM5.preLow[-1]
                return

            # MA10 下穿MA20， MA10 < MA120， bar.close < MA120, MA(MA120) > MA120
            if self.lineM5.lineMa1[-2] > self.lineM5.lineMa2[-2] \
                    and self.lineM5.lineMa1[-1] < self.lineM5.lineMa2[-1] \
                    and self.lineM5.lineMa1[-1] < self.lineM5.lineMa3[-1] \
                    and bar.close < self.lineM5.lineMa3[-1] \
                    and ma5_Ma120 > self.lineM5.lineMa3[-1] \
                    and self.lineM5.lineMa1[-1] < ma5_Ma10:

                self.writeCtaLog(u'{0},开仓空单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                orderid = self.short(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                if orderid:
                    # 更新下单时间（为了定时撤单）
                    self.lastOrderTime = self.curDateTime
                    # 更新开仓价格
                    self.policy.entryPrice = bar.close
                    # 更新最低价
                    self.lowPriceInShort = bar.close
                    # 设置前高为止损价
                    self.policy.exitOnStopPrice = self.lineM5.preHigh[-1]
                return

        # 持仓，检查是否满足平仓条件
        else:
            # MA10下穿MA20，多单离场
            if self.lineM5.lineMa1[-1] < self.lineM5.lineMa2[-1] \
                    and self.position.pos > 0 and self.entrust != -1:
                self.writeCtaLog(u'{0},平仓多单{1}手,价格:{2}'.format(bar.datetime, abs(self.position.pos), bar.close))
                orderid = self.sell(price=bar.close, volume=abs(self.position.pos), orderTime=self.curDateTime)
                if orderid:
                    # 更新下单时间（为了定时撤单）
                    self.lastOrderTime = self.curDateTime
                return

            # MA10上穿MA20，空离场
            if self.lineM5.lineMa1[-1] > self.lineM5.lineMa2[-1] \
                    and self.position.pos < 0 and self.entrust != 1:
                self.writeCtaLog(u'{0},平仓空单{1}手,价格:{2}'.format(bar.datetime, abs(self.position.pos), bar.close))
                orderid = self.cover(price=bar.close, volume=abs(self.position.pos), orderTime=self.curDateTime)
                if orderid:
                    # 更新下单时间（为了定时撤单）
                    self.lastOrderTime = self.curDateTime
                return

            # policy 跟随止损
            if self.policy.exitOnLastRtnPips > 0:
                if self.position.pos > 0 and self.entrust != 1 \
                        and bar.close < (self.highPriceInLong - self.policy.exitOnLastRtnPips * self.minDiff):
                    self.writeCtaLog(u'{0},跟随止损，平仓多单{1}手,价格:{2}'.format(bar.datetime, abs(self.position.pos), bar.close))
                    orderid = self.sell(price=bar.close, volume=abs(self.position.pos), orderTime=self.curDateTime)
                    if orderid:
                        # 更新下单时间（为了定时撤单）
                        self.lastOrderTime = self.curDateTime
                    return

                if self.position.pos < 0 and self.entrust != -1 \
                            and bar.close > (self.lowPriceInShort + self.policy.exitOnLastRtnPips * self.minDiff):
                    self.writeCtaLog(u'{0},跟随止损，平仓空单{1}手,价格:{2}'.format(bar.datetime, abs(self.position.pos), bar.close))
                    orderid = self.cover(price=bar.close, volume=abs(self.position.pos), orderTime=self.curDateTime)
                    if orderid:
                        # 更新下单时间（为了定时撤单）
                        self.lastOrderTime = self.curDateTime
                    return

            # 固定止损
            if self.policy.exitOnStopPrice > 0:
                if self.position.pos > 0 and self.entrust != 1 \
                        and bar.close < self.policy.exitOnStopPrice:
                    self.writeCtaLog(u'{0},固定止损，平仓多单{1}手,价格:{2}'.format(bar.datetime, abs(self.position.pos), bar.close))
                    orderid = self.sell(price=bar.close, volume=abs(self.position.pos), orderTime=self.curDateTime)
                    if orderid:
                        # 更新下单时间（为了定时撤单）
                        self.lastOrderTime = self.curDateTime
                    return

                if self.position.pos < 0 and self.entrust != -1 \
                        and bar.close > self.policy.exitOnStopPrice:
                    self.writeCtaLog(u'{0},固定止损，平仓空单{1}手,价格:{2}'.format(bar.datetime, abs(self.position.pos), bar.close))
                    orderid = self.cover(price=bar.close, volume=abs(self.position.pos), orderTime=self.curDateTime)
                    if orderid:
                        # 更新下单时间（为了定时撤单）
                        self.lastOrderTime = self.curDateTime
                    return

            if len(self.gridPrices) > 1:
                # 满足网格多单加仓：在开仓价以上；均线上升；下穿网格线
                if self.position.pos == self.inputSS and self.entrust != 1 \
                        and bar.close < self.gridPrices[-1] and bar.close > self.policy.entryPrice \
                        and self.highPriceInLong > self.gridPrices[-1]  \
                        and ma5_Ma120 < self.lineM5.lineMa3[-1]:

                    self.writeCtaLog(u'{0},加仓网格多单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                    orderid = self.buy(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                    if orderid:
                        # 更新下单时间（为了定时撤单）
                        self.lastOrderTime = self.curDateTime
                        # 更新网格的止盈止损价格
                        self.gridStopPrice = self.gridPrices[-1] - self.gridHeight
                        self.gridWinPrice = self.gridPrices[-1] + self.gridHeight
                    return

                # 满足网格空单加仓，在开仓价以上；均线下升；上穿网格线
                if self.position.pos ==(0-self.inputSS) and self.entrust != -1 \
                        and bar.close > self.gridPrices[-1] and bar.close < self.policy.entryPrice \
                        and self.lowPriceInShort < self.gridPrices[-1] \
                        and ma5_Ma120 > self.lineM5.lineMa3[-1]:

                    self.writeCtaLog(u'{0},加仓网格空单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                    orderid = self.short(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                    if orderid:
                        # 更新下单时间（为了定时撤单）
                        self.lastOrderTime = self.curDateTime
                        # 更新网格的止盈止损价格
                        self.gridStopPrice = self.gridPrices[-1] + self.gridHeight
                        self.gridWinPrice = self.gridPrices[-1] - self.gridHeight
                    return

                # 固定止盈多单
                if self.position.pos > 1 and bar.close >= self.gridWinPrice and self.entrust != -1:
                    self.writeCtaLog(u'{0},固定止盈网格单，平仓多单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                    orderid = self.sell(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                    if orderid:
                        # 更新下单时间（为了定时撤单）
                        self.lastOrderTime = self.curDateTime
                    return

                # 固定止盈空单
                if self.position.pos < -1 and bar.close <= self.gridWinPrice and self.entrust != 1:
                    self.writeCtaLog(u'{0},固定止盈网格单，平仓空单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                    orderid = self.cover(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                    if orderid:
                        # 更新下单时间（为了定时撤单）
                        self.lastOrderTime = self.curDateTime
                    return

                # 固定止损多单
                if self.position.pos > 1 and bar.close < self.gridStopPrice and self.entrust != -1:
                    self.writeCtaLog(u'{0},固定止损网格单，平仓多单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                    orderid = self.sell(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                    if orderid:
                        # 更新下单时间（为了定时撤单）
                        self.lastOrderTime = self.curDateTime
                    return

                # 固定止损空单
                if self.position.pos < -1 and bar.close > self.gridStopPrice and self.entrust != 1:
                    self.writeCtaLog(u'{0},固定止损网格单，平仓空单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                    orderid = self.cover(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                    if orderid:
                        # 更新下单时间（为了定时撤单）
                        self.lastOrderTime = self.curDateTime
                    return

        # 执行收盘前平仓检查
        self.__dailyCloseCheck(bar)
    # ----------------------------------------------------------------------
    def __cancelLogic(self, dt, force=False):
        "撤单逻辑"""
        if len(self.uncompletedOrders) < 1:
            return

        if not self.lastOrderTime:
            self.writeCtaLog(u'异常，上一交易时间为None')
            return

        # 平仓检查时间比开开仓时间需要短一倍
        if (self.position.pos >= 0 and self.entrust == 1) \
                or (self.position.pos <= 0 and self.entrust == -1):
            i = 1
        else:
            i = 1  # 原来是2，暂时取消

        canceled = False

        if ((dt - self.lastOrderTime).seconds > self.cancelSeconds / i ) \
                or force:  # 超过设置的时间还未成交

            for order in self.uncompletedOrders.keys():
                self.writeCtaLog(u'{0}超时{1}秒未成交，取消委托单：{2}'.format(dt, (dt - self.lastOrderTime).seconds, order))

                self.cancelOrder(str(order))

                canceled = True
                if self.uncompletedOrders[order]['OFFSET'] == OFFSET_OPEN:
                    self.lineM5.lineBar[-2].tradeStatus = CTAORDER_OPEN_FAIL
                else:
                    self.lineM5.lineBar[-2].tradeStatus = CTAORDER_CLOSE_FAIL

            # 取消未完成的订单
            self.uncompletedOrders.clear()

            if canceled:
                self.entrust = 0
                self.policy.entryPrice = 0
            else:
                self.writeCtaLog(u'异常：没有撤单')

    def __dailyCloseCheck(self, bar):
        """每天收盘前检查，如果是亏损单，则平掉"""

        if self.position.pos == 0 and self.entrust == 0:
            return False

        if bar.time not in ['14:45:00','14:50:00','14:55:00','22:45:00','22:50:00','22:55:00']:
            return False

        # 撤销未成交的订单
        if len(self.uncompletedOrders) > 0:
            for order in self.uncompletedOrders.keys():
                self.writeCtaLog(u'{0},收盘前15分钟，仍未成交，取消委托单：{1}'.format(bar.datetime,order))
                self.cancelOrder(str(order))

            self.uncompletedOrders.clear()

        self.entrust = 0

        # 强制平仓
        if self.position.pos > 0 and bar.close < self.policy.entryPrice + self.atr:
            self.writeCtaLog(u'强制日内平亏损多仓')
            # 降低两个滑点
            orderid = self.sell(price=bar.close-2*self.minDiff, volume=self.inputSS, orderTime=self.curDateTime)
            if orderid:
                # 更新下单时间
                self.lastOrderTime = self.curDateTime
            return True

        if self.position.pos < 0 and bar.close > self.policy.entryPrice - self.atr:
            self.writeCtaLog(u'强制日内平亏损空仓')

            orderid = self.cover(price=bar.close+2*self.minDiff, volume=self.inputSS, orderTime=self.curDateTime)
            if orderid:
                # 更新下单时间（为了定时撤单）
                self.lastOrderTime = self.curDateTime
            return True

        return True

    def __timeWindow(self, dt):
        """交易与平仓窗口"""
        # 交易窗口 避开早盘和夜盘的前5分钟，防止隔夜跳空。

        self.closeWindow = False
        self.tradeWindow = False
        self.openWindow = False

        # 初始化当日的首次交易
        # if (tick.datetime.hour == 9 or tick.datetime.hour == 21) and tick.datetime.minute == 0 and tick.datetime.second ==0:
        #  self.firstTrade = True

        # 开市期，波动较大，用于判断止损止盈，或开仓
        if (dt.hour == 9 or dt.hour == 21) and dt.minute < 2:
            self.openWindow = True

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

            if dt.minute < 59:
                self.tradeWindow = True
                return

            if dt.minute == 59:  # 日盘平仓
                self.closeWindow = True
                return

        # 夜盘

        if dt.hour == 21 and dt.minute >= 0:
            self.tradeWindow = True
            return

        # 上期 贵金属， 次日凌晨2:30
        if self.shortSymbol in NIGHT_MARKET_SQ1:

            if dt.hour == 22 or dt.hour == 23 or dt.hour == 0 or dt.hour == 1:
                self.tradeWindow = True
                return

            if dt.hour == 2:
                if dt.minute < 29:  # 收市前29分钟
                    self.tradeWindow = True
                    return
                if dt.minute == 29:  # 夜盘平仓
                    self.closeWindow = True
                    return
            return

        # 上期 有色金属，黑色金属，沥青 次日01:00
        if self.shortSymbol in NIGHT_MARKET_SQ2:
            if dt.hour == 22 or dt.hour == 23:
                self.tradeWindow = True
                return

            if dt.hour == 0:
                if dt.minute < 59:  # 收市前29分钟
                    self.tradeWindow = True
                    return

                if dt.minute == 59:  # 夜盘平仓
                    self.closeWindow = True
                    return

            return

        # 上期 天然橡胶  23:00
        if self.shortSymbol in NIGHT_MARKET_SQ3:

            if dt.hour == 22:
                if dt.minute < 59:  # 收市前1分钟
                    self.tradeWindow = True
                    return

                if dt.minute == 59:  # 夜盘平仓
                    self.closeWindow = True
                    return

        # 郑商、大连 23:30
        if self.shortSymbol in NIGHT_MARKET_ZZ or self.shortSymbol in NIGHT_MARKET_DL:
            if dt.hour == 22:
                self.tradeWindow = True
                return

            if dt.hour == 23:
                if dt.minute < 29:  # 收市前1分钟
                    self.tradeWindow = True
                    return
                if dt.minute == 29 and dt.second > 30:  # 夜盘平仓
                    self.closeWindow = True
                    return
            return

    #----------------------------------------------------------------------
    def strToTime(self, t, ms):
        """从字符串时间转化为time格式的时间"""
        hh, mm, ss = t.split(':')
        tt = datetime.time(int(hh), int(mm), int(ss), microsecond=ms)
        return tt

     #----------------------------------------------------------------------
    def saveData(self, id):
        """保存过程数据"""
        # 保存K线
        if not self.backtesting:
            return

def testRbByTick():

    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为Tick
    engine.setBacktestingMode(engine.TICK_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20160601')

    # 设置回测用的数据结束日期
    engine.setEndDate('20160930')

    # engine.connectMysql()
    engine.setDatabase(dbName='stockcn', symbol='rb')

    # 设置产品相关参数
    engine.setSlippage(0)  # 1跳（0.1）2跳0.2
    engine.setRate(float(0.0001))  # 万1
    engine.setSize(10)  # 合约大小

    settings = {}
    settings['shortSymbol'] = 'RB'
    settings['name'] = 'ArbRB'
    settings['mode'] = 'tick'
    settings['backtesting'] = True

    # 在引擎中创建策略对象
    engine.initStrategy(Strategy_TripleMa, setting=settings)

    # 使用简单复利模式计算
    engine.usageCompounding = False  # True时，只针对FINAL_MODE有效

    # 启用实时计算净值模式REALTIME_MODE / FINAL_MODE 回测结束时统一计算模式
    engine.calculateMode = engine.REALTIME_MODE
    engine.initCapital = 300000  # 设置期初资金
    engine.percentLimit = 30  # 设置资金使用上限比例(%)
    engine.barTimeInterval = 60*5  # bar的周期秒数，用于csv文件自动减时间
    engine.fixCommission = 10  # 固定交易费用（每次开平仓收费）
    # 开始跑回测
    engine.runBackTestingWithArbTickFile('SHFE','SP RB1610&RB1701')

    # 显示回测结果
    engine.showBacktestingResult()

def testRbByBar():
    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为Tick
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20160101')

    # 设置回测用的数据结束日期
    engine.setEndDate('20161231')

    engine.setDatabase(dbName='stockcn',symbol='rb')

    # 设置产品相关参数
    engine.setSlippage(0)     # 1跳（0.1）2跳0.2
    engine.setRate(float(0.0001))    # 万1
    engine.setSize(10)         # 合约大小

    settings = {}
    settings['shortSymbol'] = 'RB'
    settings['name'] = 'M15RB'
    settings['mode'] = 'bar'
    settings['backtesting'] = True
    settings['percentLimit'] = 30


    # 在引擎中创建策略对象
    engine.initStrategy(Strategy_TripleMa, setting=settings)

    # 使用简单复利模式计算
    engine.usageCompounding = False     # True时，只针对FINAL_MODE有效

    # 启用实时计算净值模式REALTIME_MODE / FINAL_MODE 回测结束时统一计算模式
    engine.calculateMode = engine.REALTIME_MODE
    engine.initCapital = 100000      # 设置期初资金
    engine.percentLimit = 30        # 设置资金使用上限比例(%)
    engine.barTimeInterval = 300    # bar的周期秒数，用于csv文件自动减时间

    # 开始跑回测
    engine.runBackTestingWithBarFile(os.getcwd() + '/cache/RB88_20160101_20161231_M5.csv')

    # 显示回测结果
    engine.showBacktestingResult()


# 从csv文件进行回测
if __name__ == '__main__':
    # 提供直接双击回测的功能
    # 导入PyQt4的包是为了保证matplotlib使用PyQt4而不是PySide，防止初始化出错
    from ctaBacktesting import *
    from setup_logger import setup_logger

    setup_logger(
        filename=u'TestLogs/{0}_{1}.log'.format(Strategy_TripleMa.className, datetime.now().strftime('%m%d_%H%M')),
        debug=False)
    # 回测螺纹
    testRbByBar()




