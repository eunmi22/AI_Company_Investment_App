"""Stock chart pure unit tests: all synthetic, no internet or API key required.

Run: python -m unittest -v test_stock_chart.py
"""
import unittest
from datetime import datetime

import pandas as pd

from stock_chart import (PERIODS, prepare_stock_history, select_stock_period,
                         summarize_stock_period, make_stock_figure, ohlc_valid_mask)


class StockChartTest(unittest.TestCase):
    def setUp(self):
        # The latest observation is deliberately in the past, testing the last-trading-day anchor.
        dates = pd.bdate_range('2025-01-02', periods=150)
        self.source = pd.DataFrame({
            '날짜': dates,
            '시가': [1000 + i * 10 for i in range(150)],
            '고가': [1010 + i * 10 for i in range(150)],
            '저가': [990 + i * 10 for i in range(150)],
            '종가': [1005 + i * 10 for i in range(150)],
            '등락률(%)': [1.0] * 150,
            '거래량': [100] * 149 + [1000],
            '시가총액': [1_000_000] * 150,
            '출처': ['단위 테스트용 가상 자료'] * 150,
        })
        self.history = prepare_stock_history(self.source)

    def test_moving_averages_exact_windows(self):
        self.assertTrue(pd.isna(self.history.loc[3, 'SMA5']))
        self.assertEqual(self.history.loc[4, 'SMA5'], self.history.loc[:4, '종가'].mean())
        self.assertTrue(pd.isna(self.history.loc[18, 'SMA20']))
        self.assertEqual(self.history.loc[19, 'SMA20'], self.history.loc[:19, '종가'].mean())
        self.assertTrue(pd.isna(self.history.loc[59, 'SMA120']))
        self.assertAlmostEqual(self.history.loc[149, 'SMA120'], self.history.loc[30:149, '종가'].mean())

    def test_periods_use_actual_latest_data_date(self):
        a = select_stock_period(self.history, '1개월')
        b = select_stock_period(self.history, '3개월')
        c = select_stock_period(self.history, '전체')
        self.assertEqual(a['날짜'].iloc[-1], self.history['날짜'].iloc[-1])
        self.assertTrue(1 < len(a) < len(b) < len(c))
        self.assertTrue(a['날짜'].min() >= self.history['날짜'].max() - pd.DateOffset(months=1))
        self.assertFalse((c['날짜'] > self.history['날짜'].max()).any())
        self.assertEqual(len(c), 150)

    def test_invalid_period_rejected(self):
        with self.assertRaises(ValueError):
            select_stock_period(self.history, '10년')

    def test_period_percent_from_real_close(self):
        s = select_stock_period(self.history, '1개월')
        m = summarize_stock_period(self.history, s)
        self.assertAlmostEqual(m['선택기간수익률(%)'],
                               (s.iloc[-1]['종가']/s.iloc[0]['종가']-1)*100)
        self.assertEqual(m['기간최고가'], s['고가'].max())
        self.assertEqual(m['기간최저가'], s['저가'].min())
        self.assertEqual(m['최근거래량'], 1000)
        self.assertEqual(m['시가총액'], 1_000_000)
        self.assertEqual(m['거래일수'], len(s))

    def test_ohlc_validity(self):
        bad = self.history.tail(3).copy()
        bad.loc[bad.index[0], '고가'] = 1  # high smaller than low
        mask = ohlc_valid_mask(bad)
        self.assertEqual(mask.sum(), 2)

    def test_chart_no_future_x_and_volume_nonnegative(self):
        s = select_stock_period(self.history, '3개월')
        fig = make_stock_figure(s, '캔들', (5, 20, 60))
        self.assertEqual(fig.layout.xaxis.type, 'category')
        self.assertEqual(fig.layout.xaxis2.type, 'category')
        self.assertLessEqual(float(fig.layout.xaxis.range[1]), len(s))
        self.assertEqual(float(fig.layout.yaxis2.range[0]), 0)
        self.assertGreater(float(fig.layout.yaxis2.range[1]), 0)
        self.assertEqual(fig.layout.xaxis.rangeslider.visible, False)
        self.assertTrue(any(t.type == 'candlestick' for t in fig.data))
        # Plotly X-axis contains actual trading-date strings only.
        last = s['날짜'].iloc[-1].strftime('%Y-%m-%d')
        self.assertEqual(str(fig.data[0].x[-1]), last)

    def test_line_chart_and_sma(self):
        s = select_stock_period(self.history, '1개월')
        fig = make_stock_figure(s, '종가선', (20,))
        self.assertFalse(any(t.type == 'candlestick' for t in fig.data))
        self.assertTrue(any(t.name == '20일 이동평균' for t in fig.data))
        self.assertEqual(sum(t.type == 'bar' for t in fig.data), 1)

    def test_invalid_ohlc_falls_back_to_line(self):
        s = self.history.tail(3).copy()
        s['고가'] = pd.NA
        fig = make_stock_figure(s, '캔들', ())
        self.assertFalse(any(t.type == 'candlestick' for t in fig.data))
        self.assertTrue(any(t.name == '종가' for t in fig.data))

    def test_short_history_keeps_missing_sma(self):
        s = prepare_stock_history(self.source.head(4))
        self.assertTrue(s['SMA5'].isna().all())
        fig = make_stock_figure(s, '캔들', (5, 20, 60, 120))
        self.assertEqual(len(fig.data), 2)  # candles + volume only

    def test_malformed_volume_not_drawn_negative(self):
        altered = self.source.tail(3).copy()
        altered.loc[altered.index[1], '거래량'] = -9999
        s = prepare_stock_history(altered)
        fig = make_stock_figure(s, '캔들', ())
        self.assertTrue(pd.isna(fig.data[-1].y[1]))
        self.assertEqual(fig.layout.yaxis2.range[0], 0)

    def test_duplicate_dates_and_input_unchanged(self):
        src = pd.concat([self.source, self.source.tail(1)], ignore_index=True)
        prepared = prepare_stock_history(src)
        self.assertEqual(len(prepared), 150)
        self.assertNotIn('SMA5', src.columns)

    def test_empty_input(self):
        h = prepare_stock_history(pd.DataFrame())
        self.assertTrue(h.empty)
        self.assertTrue(select_stock_period(h).empty)
        self.assertEqual(summarize_stock_period(h, h), {})
        with self.assertRaises(ValueError):
            make_stock_figure(h)

    def test_stale_data_does_not_claim_live(self):
        s = select_stock_period(self.history, '1년')
        self.assertLess(s['날짜'].max(), pd.Timestamp('2026-01-01'))
        self.assertEqual(s['날짜'].max(), self.history['날짜'].max())


if __name__ == '__main__':
    unittest.main()
