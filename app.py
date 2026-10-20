"""AI 기업 통합분석 Streamlit 실행: python -m streamlit run app.py"""
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from core import collect_all, ai_review, excel_bytes, report_markdown

# .env 파일은 반드시 app.py가 있는 폴더에 두세요.
load_dotenv(dotenv_path=Path(__file__).with_name('.env'), override=False)
st.set_page_config(page_title='AI 기업 통합 투자검토', page_icon='📊', layout='wide')
st.title('📊 AI 기업 재무·주가·뉴스 통합분석')
st.caption('기업명 입력 → 금융위원회 재무·주식시세 API + 뉴스 → pandas 분석 → OpenAI 투자검토')


def get_secret(name, *aliases):
    """로컬 .env / Streamlit Community Cloud Secrets 양쪽 모두 지원."""
    for key in (name, *aliases):
        value = os.getenv(key, '').strip()
        if value and not value.startswith('발급받은_') and not value.startswith('YOUR_'):
            return value
        try:
            value = str(st.secrets.get(key, '')).strip()
            if value and not value.startswith('발급받은_') and not value.startswith('YOUR_'):
                return value
        except Exception:
            pass
    return ''


common_key = get_secret('DATA_GO_KR_API_KEY', 'DATA_GO_KR_KEY')
finance_key = get_secret('FINANCE_API_KEY') or common_key
stock_key = get_secret('STOCK_API_KEY') or common_key
openai_key = get_secret('OPENAI_API_KEY')
news_key = get_secret('NEWS_API_KEY')
serpapi_key = get_secret('SERPAPI_KEY')
model = get_secret('OPENAI_MODEL') or 'gpt-4.1-mini'

with st.sidebar:
    st.header('분석 조건')
    company = st.text_input('기업명', value='삼성전자', help='상장기업 정식 명칭을 입력하세요.')
    years = st.selectbox('재무 조회 연도 수', [3, 2, 1], index=0)
    selected_crno = st.text_input('법인등록번호 (동일 기업명 중복 시에만)', value='',
                                 help='일반적으로 비워 둡니다. 같은 이름의 법인이 여러 개일 때만 13자리를 입력하세요.')
    st.caption('재무: 금융위원회 기업기본정보·기업 재무정보 API')
    st.caption('주가: 금융위원회 주식시세정보 API V2 우선 (일별 자료)')
    st.markdown('**환경변수 연결 상태**')
    st.write('재무 API:', '설정됨' if finance_key else '미설정')
    st.write('주식시세 API:', '설정됨' if stock_key else '미설정')
    st.write('OpenAI API:', '설정됨' if openai_key else '미설정')
    st.write('NewsAPI:', '설정됨' if news_key else '미설정')
    st.write('SerpAPI:', '설정됨' if serpapi_key else '미설정')
    st.caption('뉴스 조회 순서: NewsAPI → SerpAPI → Google 뉴스 RSS')
    if not finance_key or not stock_key:
        st.warning('공공데이터 키가 없으면 .env의 DATA_GO_KR_API_KEY 또는 개별 키를 입력하세요.')
    analyze = st.button('1단계 · 데이터 수집 및 pandas 분석', type='primary', use_container_width=True)

if analyze:
    st.session_state.pop('result', None)
    st.session_state.pop('ai_report', None)
    try:
        with st.spinner('재무·주가·뉴스를 수집하고 pandas로 검증하고 있습니다...'):
            st.session_state['result'] = collect_all(
                company=company, finance_key=finance_key, stock_key=stock_key,
                year_count=years, news_key=news_key, serpapi_key=serpapi_key,
                selected_crno=selected_crno.strip() or None)
    except Exception as exc:
        # API 키나 URL 등 민감한 값이 출력되지 않도록 상세 외부 오류는 별도 기록하지 않습니다.
        st.error(f'데이터 수집을 완료하지 못했습니다: {type(exc).__name__}. 입력 기업명/연결 상태를 확인하세요.')

if 'result' not in st.session_state:
    st.info('왼쪽에서 기업명을 입력하고 **1단계 · 데이터 수집 및 pandas 분석**을 누르세요.')
    st.stop()

result = st.session_state['result']
fin, prices, news = result['재무'], result['주가'], result['뉴스']
st.header('1단계 · pandas 분석 결과')
st.caption(' / '.join([
    '기업명: ' + result['기업명'],
    '종목코드: ' + (result['종목코드'] or '확인 필요'),
    '조회 시각: ' + result['수집시각'],
]))

for warning in result['경고']:
    st.warning(warning)

cols = st.columns(5)
latest = fin.sort_values('연도').iloc[-1] if not fin.empty else None


def format_100m(value):
    return f'{float(value)/100000000:,.1f}억 원' if pd.notna(value) else '확인 필요'


for col, label, field in zip(cols[:4], ['매출액', '영업이익', '당기순이익', '총부채'],
                             ['매출액', '영업이익', '당기순이익', '총부채']):
    col.metric((f"{int(latest['연도'])}년 " if latest is not None else '') + label,
               format_100m(latest[field]) if latest is not None else '확인 필요')
cols[4].metric('최근 종가',
               f"{prices.sort_values('날짜').iloc[-1]['종가']:,.0f}원" if not prices.empty else '확인 필요')

financial_tab, stock_tab, news_tab, quality_tab = st.tabs([
    '재무 · 수익성/안정성', '주가 · 거래량', '뉴스 · 기사', '데이터 품질/사실검증'
])

with financial_tab:
    st.subheader('재무분석 표 (금액: 원)')
    if fin.empty:
        st.info('재무정보 조회 실패 또는 미제공. 기업기본정보와 재무정보 API 승인 여부를 확인하세요.')
    else:
        st.dataframe(fin, use_container_width=True, hide_index=True)
        st.caption('같은 연도에 연결·별도 결과가 모두 있으면 연결을 우선 선택합니다. 연도별 기준이 다르면 단순 비교에 주의하세요.')
        chart = fin.sort_values('연도').set_index('연도')
        st.subheader('연도별 매출액 · 영업이익 · 당기순이익 (억 원)')
        st.bar_chart(chart[['매출액', '영업이익', '당기순이익']] / 100000000)
        st.subheader('영업이익률 · 순이익률 · 부채비율 (%)')
        st.line_chart(chart[['영업이익률(%)', '순이익률(%)', '부채비율(%)']])

with stock_tab:
    st.subheader('주식시세 및 거래량')
    if prices.empty:
        st.info('주가정보 없음. 금융위원회 주식시세 API 키/활용신청을 확인하세요.')
    else:
        newest = prices.sort_values('날짜').iloc[-1]
        st.caption('출처: ' + str(newest['출처']) + ' | 최근 데이터 기준일: ' +
                   newest['날짜'].strftime('%Y-%m-%d'))
        if '금융위원회' in str(newest['출처']):
            st.info('금융위원회 주식시세 API는 실시간 시세가 아닙니다. 통상 다음 영업일 오후 갱신됩니다.')
        st.line_chart(prices.set_index('날짜')['종가'])
        st.bar_chart(prices.set_index('날짜')['거래량'])
        st.dataframe(prices.tail(30), hide_index=True, use_container_width=True)

with news_tab:
    st.caption('뉴스의 제목과 검색 요약만 수집합니다. 기사 내용·진위 여부는 원문 확인이 필요합니다.')
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
    st.subheader('기계적 사실 검증')
    st.dataframe(result['사실검증'], use_container_width=True, hide_index=True)
    st.subheader('자료 출처 / 기준일')
    st.dataframe(result['출처'], use_container_width=True, hide_index=True)
    st.caption('기계적 검증은 AI 서술, 기사 진위, 투자 전망이 사실임을 보증하지 않습니다.')

st.download_button(
    'pandas 분석 결과 Excel 다운로드 (.xlsx)', data=excel_bytes(result),
    file_name=f"{result['기업명']}_통합분석.xlsx",
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    use_container_width=True,
)

st.divider()
st.header('2단계 · OpenAI 투자검토 보고서')
st.caption('수익성 · 안정성 · 주가 추세 · 뉴스 위험 요인을 검토합니다. 수치표는 pandas가 계산하고 AI는 정성 의견을 작성합니다.')

if not openai_key:
    st.warning('OPENAI_API_KEY가 없어 AI 보고서 생성을 실행할 수 없습니다. .env를 확인하세요.')
if st.button('2단계 · AI 투자검토 보고서 생성', type='primary', disabled=not bool(openai_key)):
    try:
        with st.spinner('OpenAI 투자검토 보고서 생성 중...'):
            st.session_state['ai_report'] = ai_review(result, openai_key, model=model)
    except Exception as exc:
        st.error(f'AI 보고서 생성 실패 ({type(exc).__name__}). 모델 접근권한 또는 응답 형식을 확인하세요.')

report = st.session_state.get('ai_report')
if report:
    for key, title in [('profitability', '수익성'), ('stability', '안정성'),
                       ('trend', '주가 추세'), ('news_risks', '뉴스 위험 요인'),
                       ('conclusion', '종합 검토')]:
        st.subheader(title)
        st.write(report[key])
    st.warning('AI의 정성 판단과 뉴스의 사실 여부는 자동 검증되지 않습니다. 중요 사항은 원문과 공시를 확인하세요.')
    md = report_markdown(result, report)
    st.download_button('투자검토 보고서 다운로드 (.md)', data=md,
                       file_name=f"{result['기업명']}_AI투자검토보고서.md",
                       mime='text/markdown', use_container_width=True)
    st.download_button('AI 보고서 포함 Excel 다운로드 (.xlsx)',
                       data=excel_bytes(result, report),
                       file_name=f"{result['기업명']}_AI투자검토_통합보고서.xlsx",
                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                       use_container_width=True)

st.caption('교육·연구용 자료이며 투자 수익을 보장하거나 개인화된 매매를 권유하지 않습니다.')
