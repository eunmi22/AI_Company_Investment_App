"""주식 분석 차트 전용 기능: pandas 처리와 Plotly 표시를 분리합니다.

실제 시세를 만들어 내지 않습니다. 시각화 기준일은 현재 시각이 아니라 마지막 거래일입니다.
"""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PERIODS = ('1개월', '3개월', '6개월', '1년', '전체')
MA_WINDOWS = (5, 20, 60, 120)
MA_COLORS = {5: '#8577d7', 20: '#e3aa3e', 60: '#35a2a4', 120: '#8b98b4'}
PRICE_COLS = ('시가', '고가', '저가', '종가', '거래량', '등락률(%)', '거래대금', '시가총액')


def prepare_stock_history(prices):
    """중복 날짜 제거/형 변환/지표 계산. 원본 DataFrame을 수정하지 않습니다.

    SMA는 관측된 거래일 개수의 단순평균이며, 데이터가 부족하면 NaN을 유지합니다.
    """
    if prices is None or prices.empty:
        return pd.DataFrame(columns=['날짜', *PRICE_COLS,
                                     *(f'SMA{n}' for n in MA_WINDOWS),
                                     '거래량20일평균', '거래량배율(20일)'])
    if not {'날짜', '종가', '거래량'}.issubset(prices.columns):
        raise ValueError('주가 데이터에는 날짜, 종가, 거래량 열이 필요합니다.')

    df = prices.copy()
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.tz_localize(None).dt.normalize()
    for col in PRICE_COLS:
        if col not in df.columns:
            df[col] = float('nan')
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = (df.dropna(subset=['날짜', '종가'])
          .sort_values('날짜')
          .drop_duplicates(subset=['날짜'], keep='last')
          .reset_index(drop=True))
    # 음수 종가/0원 종가는 유효한 실제 종가로 쓰지 않습니다.
    df = df.loc[df['종가'] > 0].reset_index(drop=True)
    for n in MA_WINDOWS:
        df[f'SMA{n}'] = df['종가'].rolling(window=n, min_periods=n).mean()
    vol = df['거래량'].where(df['거래량'] >= 0)
    df['거래량20일평균'] = vol.rolling(window=20, min_periods=20).mean()
    df['거래량배율(20일)'] = vol.div(df['거래량20일평균'].replace(0, float('nan'))).round(2)
    return df


def select_stock_period(history, period='3개월'):
    """조회된 최신 날짜를 기준으로 표시 기간을 자릅니다(오늘 기준 아님)."""
    if period not in PERIODS:
        raise ValueError(f'기간은 {PERIODS} 중에서 선택하세요.')
    if history is None or history.empty:
        return history.copy() if history is not None else pd.DataFrame()
    latest = pd.Timestamp(history['날짜'].max())
    if period == '전체':
        return history.copy().reset_index(drop=True)
    offsets = {
        '1개월': pd.DateOffset(months=1),
        '3개월': pd.DateOffset(months=3),
        '6개월': pd.DateOffset(months=6),
        '1년': pd.DateOffset(years=1),
    }
    first = latest - offsets[period]
    return history.loc[history['날짜'] >= first].copy().reset_index(drop=True)


def summarize_stock_period(full_history, selected):
    """선택 기간의 주식시세 기초 통계. 보도 내용이나 투자 전망을 포함하지 않습니다."""
    if selected is None or selected.empty:
        return {}
    last = selected.iloc[-1]
    close = pd.to_numeric(selected['종가'], errors='coerce')
    first_close = close.iloc[0]
    latest_close = close.iloc[-1]
    change_percent = (latest_close / first_close - 1) * 100 if len(close) > 1 and first_close > 0 else float('nan')
    previous_close = float('nan')
    if full_history is not None and len(full_history) > 1:
        previous_close = float(full_history.iloc[-2]['종가'])
    delta = latest_close - previous_close if previous_close > 0 else float('nan')
    daily_pct = pd.to_numeric(pd.Series([last.get('등락률(%)')]), errors='coerce').iloc[0]
    if pd.isna(daily_pct) and previous_close > 0:
        daily_pct = delta / previous_close * 100

    # 고가/저가가 정상 OHLC인 날짜만 사용할 수 있도록 조건을 확인합니다.
    high = pd.to_numeric(selected['고가'], errors='coerce')
    low = pd.to_numeric(selected['저가'], errors='coerce')
    valid_hl = ohlc_valid_mask(selected)
    max_high = float(high[valid_hl].max()) if valid_hl.any() else float('nan')
    min_low = float(low[valid_hl].min()) if valid_hl.any() else float('nan')
    max_high_date = selected.loc[valid_hl & (high == max_high), '날짜'].iloc[0] if valid_hl.any() else pd.NaT
    min_low_date = selected.loc[valid_hl & (low == min_low), '날짜'].iloc[0] if valid_hl.any() else pd.NaT
    volumes = pd.to_numeric(selected['거래량'], errors='coerce')
    return {
        '기준일': last['날짜'],
        '최근종가': float(latest_close),
        '전거래일대비': float(delta),
        '최근등락률(%)': float(daily_pct) if pd.notna(daily_pct) else float('nan'),
        '선택기간수익률(%)': float(change_percent),
        '최근거래량': float(volumes.iloc[-1]) if pd.notna(volumes.iloc[-1]) else float('nan'),
        '평균거래량': float(volumes[volumes >= 0].mean()),
        '시가총액': float(last.get('시가총액')) if pd.notna(last.get('시가총액')) else float('nan'),
        '기간최고가': max_high,
        '최고가일': max_high_date,
        '기간최저가': min_low,
        '최저가일': min_low_date,
        '거래일수': int(len(selected)),
        '출처': str(last.get('출처', '확인 필요')),
    }


def ohlc_valid_mask(df):
    """실제 캔들로 표시할 수 있는 시가/고가/저가/종가 검증."""
    if df is None or df.empty:
        return pd.Series([], dtype=bool)
    opn, high, low, close = [pd.to_numeric(df[k], errors='coerce') for k in ('시가', '고가', '저가', '종가')]
    return (opn.notna() & high.notna() & low.notna() & close.notna()
            & (opn > 0) & (high > 0) & (low > 0) & (close > 0)
            & (high >= low) & (high >= opn) & (high >= close)
            & (low <= opn) & (low <= close))


def make_stock_figure(selected, chart_type='캔들', moving_averages=(5, 20, 60)):
    """캔들/종가 + 이동평균선 + 거래량을 동일한 거래일 축에 표시합니다.

    문자열 날짜로 X축을 범주축(category)으로 만들어 휴장일·미래 날짜 빈 공간을 제거합니다.
    거래량 Y축은 반드시 0 이상으로 설정합니다.
    """
    if selected is None or selected.empty:
        raise ValueError('표시할 주가 데이터가 없습니다.')
    if chart_type not in ('캔들', '종가선'):
        raise ValueError('차트 유형은 캔들/종가선 중 하나입니다.')
    invalid = set(moving_averages) - set(MA_WINDOWS)
    if invalid:
        raise ValueError(f'허용하지 않는 이동평균선: {invalid}')
    df = selected.sort_values('날짜').copy()
    dates = df['날짜'].dt.strftime('%Y-%m-%d').tolist()
    opn, close = df['시가'], df['종가']
    color_rise, color_fall = '#e75a64', '#3478cf'
    colors = [color_rise if pd.notna(o) and c >= o else color_fall if pd.notna(o) else '#8490a5'
              for o, c in zip(opn, close)]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.045,
                        row_heights=[0.75, 0.25])
    valid = ohlc_valid_mask(df)
    use_candle = chart_type == '캔들' and valid.sum() >= 2
    if use_candle:
        fig.add_trace(go.Candlestick(
            x=df.loc[valid, '날짜'].dt.strftime('%Y-%m-%d').tolist(),
            open=df.loc[valid, '시가'], high=df.loc[valid, '고가'],
            low=df.loc[valid, '저가'], close=df.loc[valid, '종가'],
            name='일봉', increasing_line_color=color_rise, increasing_fillcolor=color_rise,
            decreasing_line_color=color_fall, decreasing_fillcolor=color_fall,
            showlegend=False), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=dates, y=df['종가'], name='종가', mode='lines',
            line={'color': '#3478cf', 'width': 2},
            hovertemplate='%{x}<br>종가 %{y:,.0f}원<extra></extra>'), row=1, col=1)

    for n in moving_averages:
        col = f'SMA{n}'
        if col not in df or df[col].notna().sum() == 0:
            continue
        fig.add_trace(go.Scatter(
            x=dates, y=df[col], mode='lines', name=f'{n}일 이동평균',
            line={'color': MA_COLORS[n], 'width': 1.8},
            hovertemplate=f'%{{x}}<br>{n}일 이동평균 %{{y:,.1f}}원<extra></extra>'),
            row=1, col=1)

    volumes = pd.to_numeric(df['거래량'], errors='coerce').where(df['거래량'] >= 0)
    fig.add_trace(go.Bar(
        x=dates, y=volumes, marker={'color': colors}, name='거래량', showlegend=False,
        hovertemplate='%{x}<br>거래량 %{y:,.0f}주<extra></extra>'), row=2, col=1)

    # 차트의 최소·최대축은 실제 가격/거래량에서만 계산합니다.
    valid_close = pd.to_numeric(df['종가'], errors='coerce')
    low_series = pd.to_numeric(df['저가'], errors='coerce').where(valid)
    high_series = pd.to_numeric(df['고가'], errors='coerce').where(valid)
    price_min = min(valid_close.min(), low_series.min() if low_series.notna().any() else valid_close.min())
    price_max = max(valid_close.max(), high_series.max() if high_series.notna().any() else valid_close.max())
    # SMA가 선택 기간의 고가/저가 범위를 벗어나더라도 잘려 보이지 않게 합니다.
    for n in moving_averages:
        line = pd.to_numeric(df.get(f'SMA{n}', pd.Series(dtype=float)), errors='coerce').dropna()
        if not line.empty:
            price_min = min(price_min, float(line.min()))
            price_max = max(price_max, float(line.max()))
    if math.isfinite(price_min) and math.isfinite(price_max):
        pad = max((price_max - price_min) * 0.09, price_max * 0.008, 1.0)
        fig.update_yaxes(range=[max(0, price_min - pad), price_max + pad], row=1, col=1)
    max_vol = volumes.max()
    fig.update_yaxes(range=[0, max_vol * 1.20 if pd.notna(max_vol) and max_vol > 0 else 1],
                     rangemode='nonnegative', row=2, col=1)

    # 거래일 수와 무관하게 6~8개 레이블만 표시합니다.
    tick_size = max(1, math.ceil(len(dates) / 7))
    selected_ticks = dates[::tick_size]
    if dates[-1] not in selected_ticks:
        selected_ticks.append(dates[-1])
    for axis in ('xaxis', 'xaxis2'):
        fig.update_layout(**{axis: {'type': 'category', 'categoryorder': 'array',
                                   'categoryarray': dates,
                                   'range': [-0.7, len(dates) - 0.3],
                                   'showgrid': False}})
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(tickmode='array', tickvals=selected_ticks,
                     ticktext=[x[5:] for x in selected_ticks],
                     tickangle=0, row=2, col=1)
    fig.update_yaxes(tickformat=',.0f', gridcolor='#eaeff5', zeroline=False,
                     title_text='원', row=1, col=1)
    fig.update_yaxes(tickformat='~s', gridcolor='#eaeff5', zeroline=False,
                     title_text='주', row=2, col=1)
    fig.update_layout(
        height=560, margin={'l': 8, 'r': 8, 't': 25, 'b': 4},
        plot_bgcolor='white', paper_bgcolor='white',
        font={'family': 'Arial, Malgun Gothic, sans-serif', 'size': 12, 'color': '#485366'},
        hovermode='x unified',
        legend={'orientation': 'h', 'y': 1.045, 'x': 0, 'font': {'size': 11}},
        xaxis_rangeslider_visible=False,
    )
    return fig
