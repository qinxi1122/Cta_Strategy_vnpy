#coding=utf-8
# author: Y.Raul
# date : 2018-03-03

from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME
from vnpy.trader.app.ctaStrategy.ctaHistoryData import loadRqCsv


if __name__ == '__main__':
    loadRqCsv('rb88_1M_2013_2017.csv', MINUTE_DB_NAME, 'rb88')