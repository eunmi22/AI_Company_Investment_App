"""고도화된 AI 기업 통합분석 Streamlit 앱.

실행: python -m streamlit run app.py
기존 core.py 기반 금융위원회 재무/주식시세 + 뉴스 + AI 보고서를 유지합니다.
"""
import math
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from core import collect_all, ai_review, excel_bytes, report_markdown
from stock_chart import (
    PERIODS, MA_WINDOWS, make_stock_figure, ohlc_valid_mask,
    prepare_stock_history, select_stock_period, summarize_stock_period,
)

load_dotenv(dotenv_path=Path(__file__).with_name('.env'), override=False)
st.set_page_config(page_title='AI 기업 재무·주가·뉴스 투자검토', page_icon='📈', layout='wide')


def get_secret(name, *aliases):
    """로컬 .env 또는 Streamlit Cloud Secrets를 읽습니다. 실제 값은 표시하지 않습니다."""
    for key in (name, *aliases):
        value = os.getenv(key, '').strip()
        if value and not value.startswith(('발급받은_', 'YOUR_', '본인의_')):
            return value
        try:
            value = str(st.secrets.get(key, '')).strip()
            if value and not value.startswith(('발급받은_', 'YOUR_', '본인의_')):
                return value
        except Exception:
            pass
    return ''


def kr_amount(value, unit='원'):
    """큰 원화 수치를 조·억 원으로 간단히 표시합니다."""
    if value is None or pd.isna(value):
        return '확인 필요'
    v = float(value)
    sign = '-' if v < 0 else ''
    a = abs(v)
    if a >= 1_000_000_000_000:
        return f'{sign}{a/1_000_000_000_000:,.1f}조 {unit}'
    if a >= 100_000_000:
        return f'{sign}{a/100_000_000:,.1f}억 {unit}'
    return f'{v:,.0f}{unit}'


def kr_price(value):
    return f'{float(value):,.0f}원' if value is not None and pd.notna(value) else '확인 필요'


def pct(value, signed=False):
    if value is None or pd.isna(value):
        return '확인 필요'
    return f'{float(value):+,.2f}%' if signed else f'{float(value):,.2f}%'


def units(value, unit='주'):
    return f'{float(value):,.0f}{unit}' if value is not None and pd.notna(value) else '확인 필요'


st.title('📈 AI 기업 재무·주가·뉴스 통합분석')
st.caption('공식 공공데이터 기반 · 주가 차트 고도화 · pandas 검증 · AI 투자검토 보고서')

common_key = get_secret('DATA_GO_KR_API_KEY', 'DATA_GO_KR_KEY')
finance_key = get_secret('FINANCE_API_KEY') or common_key
stock_key = get_secret('STOCK_API_KEY') or common_key
openai_key = get_secret('OPENAI_API_KEY')
news_key = get_secret('NEWS_API_KEY')
serpapi_key = get_secret('SERPAPI_KEY')
model = get_secret('OPENAI_MODEL') or 'gpt-4.1-mini'

with st.sidebar:
    st.header('분석 조건')
    company = st.text_input('기업명', value='삼성전자', help='상장기업의 정식 기업명을 입력하세요.')
    years = st.selectbox('재무 조회 연도 수', [3, 2, 1], index=0)
    selected_crno = st.text_input('법인등록번호 (동명 법인 중복 시)', value='',
                                 help='일반적으로 비웁니다. 동일 기업명으로 여러 법인이 검색된 경우에만 입력하세요.')
    st.caption('재무: 금융위원회 기업기본정보 및 기업 재무정보 API')
    st.caption('주가: 금융위원회 주식시세정보 API V2 우선 (최대 최근 2년 조회)')
    st.markdown('**환경변수 연결 상태 (키 존재만 확인)**')
    for label, key in [('재무 API', finance_key), ('주식시세 API', stock_key),
                       ('OpenAI', openai_key), ('NewsAPI', news_key), ('SerpAPI', serpapi_key)]:
        st.write(f'{label}:', '설정됨' if key else '미설정')
    if not finance_key or not stock_key:
        st.warning('공공데이터 키가 없습니다. DATA_GO_KR_API_KEY 또는 개별 키를 설정하세요.')
    st.caption('뉴스 조회: NewsAPI → SerpAPI → Google 뉴스 RSS')
    analyze = st.button('1단계 · 데이터 수집 및 pandas 분석', type='primary',
                        use_container_width=True)

if analyze:
    st.session_state.pop('result', None)
    st.session_state.pop('ai_report', None)
    try:
        with st.spinner('재무·주식시세·뉴스 수집 및 데이터 검증 중...'):
            st.session_state['result'] = collect_all(
                company=company, finance_key=finance_key, stock_key=stock_key,
                year_count=years, news_key=news_key, serpapi_key=serpapi_key,
                selected_crno=selected_crno.strip() or None, stock_days=730)
    except Exception as exc:
        # 예외를 그대로 보여주면 일부 라이브러리에서 호출 URL/키가 유출될 수 있습니다.
        st.error(f'수집 실패 ({type(exc).__name__}). 기업명·인증키 승인·네트워크 상태를 확인하세요.')

if 'result' not in st.session_state:
    st.info('왼쪽에서 기업명을 입력한 다음 **1단계 · 데이터 수집 및 pandas 분석**을 실행하세요.')
    st.stop()

result = st.session_state['result']
fin, prices, news = result['재무'], result['주가'], result['뉴스']
history = prepare_stock_history(prices)
st.header('1단계 · 데이터 분석 결과')
st.caption(' / '.join([
    '기업명: ' + result['기업명'],
    '종목코드: ' + (result['종목코드'] or '확인 필요'),
    '수집시각: ' + result['수집시각'],
]))
for warning in result['경고']:
    st.warning(warning)

latest_fin = fin.sort_values('연도').iloc[-1] if not fin.empty else None
latest_stock = history.iloc[-1] if not history.empty else None
metrics = st.columns(5)
for col, label, name in zip(metrics[:4], ('매출액', '영업이익', '당기순이익', '총부채'),
                             ('매출액', '영업이익', '당기순이익', '총부채')):
    title = (f"{int(latest_fin['연도'])}년 " if latest_fin is not None else '') + label
    col.metric(title, kr_amount(latest_fin[name]) if latest_fin is not None else '확인 필요')
metrics[4].metric('최근 종가', kr_price(latest_stock['종가']) if latest_stock is not None else '확인 필요')
if latest_stock is not None:
    st.caption('최근 종가 기준일: ' + latest_stock['날짜'].strftime('%Y-%m-%d') +
               ' | 공식 주식시세는 비실시간 일별 자료입니다.')

financial_tab, stock_tab, news_tab, quality_tab = st.tabs([
    '재무 · 수익성/안정성', '주가 · 캔들/거래량', '뉴스 · 기사', '데이터 품질/사실검증'
])

with financial_tab:
    st.subheader('재무분석 표 (금액 단위: 원)')
    if fin.empty:
        st.info('재무정보가 없습니다. 금융위원회 기업기본정보·기업 재무정보 API 활용신청을 확인하세요.')
    else:
        st.dataframe(fin, use_container_width=True, hide_index=True)
        st.caption('연도별 연결 재무제표를 우선 사용합니다. 연결·별도 기준이 혼재하면 단순 비교에 주의하세요.')
        chart = fin.sort_values('연도').set_index('연도')
        st.subheader('매출 · 영업이익 · 당기순이익 (억 원)')
        st.bar_chart(chart[['매출액', '영업이익', '당기순이익']] / 100_000_000)
        st.subheader('영업이익률 · 순이익률 · 부채비율 (%)')
        st.line_chart(chart[['영업이익률(%)', '순이익률(%)', '부채비율(%)']])

with stock_tab:
    st.subheader('주식시세 분석 · 일봉 / 이동평균선 / 거래량')
    if history.empty:
        st.info('주식시세 데이터가 없습니다. 공식 API 승인 상태와 종목코드를 확인하세요.')
    else:
        latest = history.iloc[-1]
        st.caption('출처: ' + str(latest.get('출처', '확인 필요')) +
                   ' | 최신 데이터 기준일: ' + latest['날짜'].strftime('%Y-%m-%d') +
                   ' | 단위: 원·주')
        if '금융위원회' in str(latest.get('출처', '')):
            st.info('공식 주식시세 V2는 실시간이 아닙니다. 최신 체결가·시간외 가격과 차이가 날 수 있습니다.')
        elif 'Yahoo' in str(latest.get('출처', '')):
            st.warning('Yahoo Finance 수정주가를 사용 중입니다. 공식 비조정 종가와 비교할 때 주의하세요.')
        else:
            st.warning('금융위원회 공식 API 대신 대체 출처를 사용하고 있습니다. 데이터출처 탭을 확인하세요.')

        period = st.radio('조회 기간', PERIODS, index=1, horizontal=True,
                          help='실제 마지막 거래일을 기준으로 계산합니다. 빈 미래 날짜를 만들지 않습니다.')
        selected = select_stock_period(history, period)
        stats = summarize_stock_period(history, selected)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric('최근 종가', kr_price(stats['최근종가']))
        c2.metric('최근 거래일 등락률', pct(stats['최근등락률(%)'], signed=True))
        c3.metric(f'{period} 종가 수익률', pct(stats['선택기간수익률(%)'], signed=True))
        c4.metric('거래량', units(stats['최근거래량']))
        c5.metric('시가총액', kr_amount(stats['시가총액']))
        st.caption('기간 수익률 = 선택 기간 첫 거래일 종가 대비 마지막 거래일 종가 변화율. '
                   '당일 등락률은 API 제공값이 있으면 우선하며, 없으면 직전 종가로 계산합니다.')

        hi, lo, count = st.columns(3)
        hi.metric(f'{period} 장중 최고가', kr_price(stats['기간최고가']))
        lo.metric(f'{period} 장중 최저가', kr_price(stats['기간최저가']))
        count.metric('표시 거래일', f"{stats['거래일수']:,}일")
        dates_text = []
        if pd.notna(stats['최고가일']):
            dates_text.append('최고가: ' + stats['최고가일'].strftime('%Y-%m-%d'))
        if pd.notna(stats['최저가일']):
            dates_text.append('최저가: ' + stats['최저가일'].strftime('%Y-%m-%d'))
        if dates_text:
            st.caption(' / '.join(dates_text))

        options = st.columns([1, 3])
        with options[0]:
            chart_type = st.radio('차트 유형', ['캔들', '종가선'], horizontal=True)
        with options[1]:
            ma = st.multiselect('이동평균선 (거래일)', list(MA_WINDOWS),
                                default=[5, 20, 60],
                                help='SMA: 직전 N거래일 종가의 단순평균. 데이터가 모자라면 표시하지 않습니다.')
        candles = ohlc_valid_mask(selected)
        if chart_type == '캔들' and candles.sum() < 2:
            st.warning('캔들 표시 가능한 시가·고가·저가·종가 자료가 부족하여 종가선으로 표시합니다.')
        elif chart_type == '캔들' and candles.sum() < len(selected):
            st.warning(f'OHLC 오류/누락 {len(selected)-int(candles.sum())}거래일의 캔들은 제외했습니다. '
                       '데이터 품질/사실검증 탭을 확인하세요.')
        fig = make_stock_figure(selected, chart_type=chart_type, moving_averages=ma)
        st.plotly_chart(fig, use_container_width=True,
                        config={'displaylogo': False, 'scrollZoom': False})
        st.caption('휴장일 간격을 접은 거래일 축으로 표시합니다. 거래량 축은 0 이상이며, '
                   '가격축과 이동평균선은 실제 조회 데이터만 사용합니다.')

        if len(selected) >= 20 and selected['거래량배율(20일)'].notna().any():
            spikes = selected.loc[selected['거래량배율(20일)'] >= 2,
                                  ['날짜', '종가', '거래량', '거래량20일평균', '거래량배율(20일)']]
            if not spikes.empty:
                with st.expander(f'20거래일 평균 대비 거래량 2배 이상: {len(spikes)}건'):
                    st.dataframe(spikes.sort_values('날짜', ascending=False),
                                 hide_index=True, use_container_width=True)
                st.caption('거래량 급증 자체는 매수·매도 신호가 아닙니다.')
        with st.expander('주식시세 원자료 / 이동평균 계산표 보기'):
            columns = ['날짜', '시가', '고가', '저가', '종가', '등락률(%)', '거래량',
                       'SMA5', 'SMA20', 'SMA60', 'SMA120', '거래량20일평균', '거래량배율(20일)', '출처']
            view = selected[[k for k in columns if k in selected.columns]].sort_values('날짜', ascending=False)
            st.dataframe(view, hide_index=True, use_container_width=True)

with news_tab:
    st.caption('뉴스는 검색 제목·요약이며 기사 본문이나 보도 내용의 진위를 자동 확인한 것이 아닙니다.')
    if news.empty:
        st.info('검색된 뉴스가 없습니다.')
    else:
        st.dataframe(news, use_container_width=True, hide_index=True,
                     column_config={'링크': st.column_config.LinkColumn('기사 바로가기')})

with quality_tab:
    st.subheader('결측값 및 중복 점검')
    st.dataframe(result['품질'], use_container_width=True, hide_index=True)
    st.subheader('통계·집계')
    st.dataframe(result['통계'], use_container_width=True, hide_index=True)
    st.subheader('원자료 기계적 사실 검증')
    st.dataframe(result['사실검증'], use_container_width=True, hide_index=True)
    st.subheader('출처 · 기준일')
    st.dataframe(result['출처'], use_container_width=True, hide_index=True)
    st.caption('위 검증은 숫자의 내부 일관성을 확인하며 AI 의견이나 기사 진위를 보증하지 않습니다.')

st.download_button('pandas 통합 분석 Excel 다운로드 (.xlsx)', data=excel_bytes(result),
                   file_name=f"{result['기업명']}_통합분석.xlsx",
                   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                   use_container_width=True)
st.divider()
st.header('2단계 · OpenAI 투자검토 보고서')
st.caption('수익성 · 안정성 · 주가 추세 · 뉴스 위험 요인 · 사실 검증. 숫자 계산은 pandas가 수행합니다.')
if not openai_key:
    st.warning('OPENAI_API_KEY 미설정: AI 보고서 생성은 실행할 수 없습니다.')
if st.button('2단계 · AI 투자검토 보고서 생성', type='primary',
             disabled=not bool(openai_key)):
    try:
        with st.spinner('OpenAI가 입력 데이터로 정성 보고서를 작성하고 있습니다...'):
            st.session_state['ai_report'] = ai_review(result, openai_key, model=model)
    except Exception as exc:
        st.error(f'AI 보고서 생성 실패 ({type(exc).__name__}). 모델 권한·응답 형식을 확인하세요.')
report = st.session_state.get('ai_report')
if report:
    for key, title in [('profitability', '수익성'), ('stability', '안정성'),
                       ('trend', '주가 추세'), ('news_risks', '뉴스 위험 요인'),
                       ('conclusion', '종합 검토')]:
        st.subheader(title)
        st.write(report[key])
    st.warning('AI의 정성 판단과 뉴스 진위는 자동 사실 보증 대상이 아닙니다. 공시 및 기사 원문을 확인하세요.')
    st.download_button('투자검토 보고서 다운로드 (.md)', data=report_markdown(result, report),
                       file_name=f"{result['기업명']}_AI투자검토보고서.md",
                       mime='text/markdown', use_container_width=True)
    st.download_button('AI 보고서 포함 Excel 다운로드 (.xlsx)',
                       data=excel_bytes(result, report),
                       file_name=f"{result['기업명']}_AI투자검토_통합보고서.xlsx",
                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                       use_container_width=True)

st.caption('교육·연구용 참고자료입니다. 실시간 시세·개인화된 매매 권유가 아니며, '
           '공개 배포 시 KRX 시세 원자료의 이용·재배포 허락 조건을 먼저 확인하세요.')
