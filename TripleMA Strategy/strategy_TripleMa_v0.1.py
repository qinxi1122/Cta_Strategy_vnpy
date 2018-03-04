# encoding: UTF-8

# 首先写系统内置模块
import sys
from datetime import datetime, timedelta, date
from time import sleep

# 其次，导入vnpy的基础模块
import sys
sys.path.append('..')
from vtConstant import EMPTY_STRING, EMPTY_INT, DIRECTION_LONG, DIRECTION_SHORT, OFFSET_OPEN, STATUS_CANCELLED

# 然后是自己编写的模块
from ctaTemplate import *
from ctaBase import *
from ctaLineBar import *

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

    """
    className = 'Strategy_TripleMa'
    author = u'李来佳'

    # 策略在外部设置的参数
    inputSS = 1                # 参数SS，下单，范围是1~100，步长为1，默认=1，
    minDiff = 1                # 商品的最小交易单位

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

        if setting:
            # 根据配置文件更新参数
            self.setParam(setting)

            # 创建的M5 K线
            lineM5Setting = {}
            lineM5Setting['name'] = u'M5'            # k线名称
            lineM5Setting['barTimeInterval'] = 60*5  # K线的Bar时长
            lineM5Setting['inputMa1Len'] = 10        # 第1条均线
            lineM5Setting['inputMa2Len'] = 20        # 第2条均线
            lineM5Setting['inputMa3Len'] = 120       # 第3条均线
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
        self.writeCtaLog(u'{0},OnTrade(),当前持仓：{1} '.format(self.curDateTime, self.pos))

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
                    self.writeCtaLog(u'平空仓完成')
                    # 更新仓位
                    self.pos = EMPTY_INT

                # 平多仓完成(sell)
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_SHORT and order.offset != OFFSET_OPEN:
                    self.writeCtaLog(u'平多仓完成')
                    # 更新仓位
                    self.pos = EMPTY_INT

                # 开多仓完成
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_LONG and order.offset == OFFSET_OPEN:
                    self.writeCtaLog(u'开多仓完成')
                    # 更新仓位
                    self.pos = order.tradedVolume

                # 开空仓完成
                if self.uncompletedOrders[orderkey]['DIRECTION'] == DIRECTION_SHORT and order.offset == OFFSET_OPEN:
                    self.writeCtaLog(u'开空仓完成')
                    self.pos = 0 - order.tradedVolume

                del self.uncompletedOrders[orderkey]
                if len(self.uncompletedOrders) == 0:
                    self.entrust = 0

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

        # 执行撤单逻辑
        self.__cancelLogic(dt=self.curDateTime)

        # 如果未持仓，检查是否符合开仓逻辑
        if self.pos == 0:
            # MA10 上穿MA20， MA10 > MA120， bar.close > MA120
            if self.lineM5.lineMa1[-2] < self.lineM5.lineMa2[-2] \
                    and self.lineM5.lineMa1[-1] > self.lineM5.lineMa2[-1] \
                    and self.lineM5.lineMa1[-1] > self.lineM5.lineMa3[-1] \
                    and bar.close > self.lineM5.lineMa3[-1]:

                self.writeCtaLog(u'{0},开仓多单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                orderid = self.buy(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                if orderid:
                    self.lastOrderTime = self.curDateTime
                return

            # MA10 下穿MA20， MA10 < MA120， bar.close < MA120
            if self.lineM5.lineMa1[-2] > self.lineM5.lineMa2[-2] \
                    and self.lineM5.lineMa1[-1] < self.lineM5.lineMa2[-1] \
                    and self.lineM5.lineMa1[-1] < self.lineM5.lineMa3[-1] \
                    and bar.close < self.lineM5.lineMa3[-1]:
                self.writeCtaLog(u'{0},开仓空单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                orderid = self.short(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                if orderid:
                    self.lastOrderTime = self.curDateTime
                return

        # 持仓，检查是否满足平仓条件
        else:
            # MA10下穿MA20，多单离场
            if self.lineM5.lineMa1[-1] < self.lineM5.lineMa2[-1] \
                    and self.pos > 0 and self.entrust != -1:
                self.writeCtaLog(u'{0},平仓多单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                orderid = self.sell(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                if orderid:
                    self.lastOrderTime = self.curDateTime
                return

            # MA10上穿MA20，空离场
            if self.lineM5.lineMa1[-1] > self.lineM5.lineMa2[-1] \
                    and self.pos < 0 and self.entrust != 1:
                self.writeCtaLog(u'{0},平仓空单{1}手,价格:{2}'.format(bar.datetime, self.inputSS, bar.close))
                orderid = self.cover(price=bar.close, volume=self.inputSS, orderTime=self.curDateTime)
                if orderid:
                    self.lastOrderTime = self.curDateTime
                return


    # ----------------------------------------------------------------------
    def __cancelLogic(self, dt, force=False):
        "撤单逻辑"""

        if len(self.uncompletedOrders) < 1:
            return

        if not self.lastOrderTime:
            self.writeCtaLog(u'异常，上一交易时间为None')
            return

        # 平仓检查时间比开开仓时间需要短一倍
        if (self.pos >= 0 and self.entrust == 1) \
                or (self.pos <= 0 and self.entrust == -1):
            i = 1
        else:
            i = 1  # 原来是2，暂时取消

        canceled = False

        if ((dt - self.lastOrderTime).seconds > self.cancelSeconds / i ) or force:  # 超过设置的时间还未成交

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
            else:
                self.writeCtaLog(u'异常：没有撤单')

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
    engine.setStartDate('20160101')

    # 设置回测用的数据结束日期
    engine.setEndDate('20160330')

    # engine.connectMysql()
    engine.setDatabase(dbName='stockcn', symbol='rb')

    # 设置产品相关参数
    engine.setSlippage(0)  # 1跳（0.1）2跳0.2
    engine.setRate(float(0.0001))  # 万1
    engine.setSize(10)  # 合约大小

    settings = {}
    settings['shortSymbol'] = 'RB'
    settings['name'] = 'TripleMa'
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
    engine.runBacktestingWithMysql()

    # 显示回测结果
    engine.showBacktestingResult()

def testRbByBar():
    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为bar
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




