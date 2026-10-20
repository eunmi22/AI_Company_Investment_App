# AI 기업 재무·주식시세·뉴스 통합분석 (최종 실습)

> **교육·연구용 프로젝트.** 검증되지 않은 자료나 수치를 채워 넣지 않으며, 투자 매수·매도 자동판단 기능은 없습니다.

## 핵심 기능

기업명 `삼성전자` 입력 → 금융위원회 기업기본정보 API로 법인등록번호 확인 → 금융위원회 기업 재무정보 API로 사업연도별 매출·영업이익·순이익·부채·자본 조회 → **금융위원회 주식시세정보 V2 API**로 시가·고가·저가·종가·거래량·거래대금 조회 → 뉴스(NewsAPI, SerpAPI, Google 뉴스 RSS) 수집 → **pandas 분석**(결측·중복·수익성·안정성·기초 통계) → Streamlit 차트/엑셀 다운로드 → **OpenAI 투자검토 보고서**(수익성·안정성·주가 추세·뉴스 위험 요인·수치 사실검증).

- 종목코드 검색: 삼성전자·SK하이닉스는 사전 확인된 코드로 조회하고 다른 기업은 pykrx에서 탐색합니다. 정확히 일치하는 기업명이 여러 개의 법인번호로 조회되면 임의 선택하지 않고 확인을 요청합니다.
- 재무 연도: 최근 완료된 사업연도 최대 3개. **연결 우선, 별도 차선**으로 선택하며 누락 여부와 기준을 표기합니다. 데이터가 조회되지 않으면 임의로 숫자를 생성하지 않습니다.
- 주식시세: **금융위원회 공공데이터 API가 우선**입니다. 연결이 실패하면 pykrx → yfinance 순으로 시도하고, 대체출처를 표·Excel에 표시합니다.
- 뉴스: **NewsAPI → SerpAPI → Google 뉴스 RSS**. 뉴스 기사 전문이 아니라 제목/검색 요약이라는 점을 명시합니다.
- AI 보고서: OpenAI가 수익성·안정성·주가 추세·뉴스 위험 요인·종합 의견의 **정성 부분만 생성**합니다. 표와 수치 검증은 pandas 계산 결과를 그대로 사용합니다. AI 문장의 진실성 및 기사 원문 진위는 완전히 자동검증되지 않습니다.

## 포함된 파일

| 파일 | 용도 |
|---|---|
| `app.py` | Streamlit UI / 차트 / Excel 다운로드 / AI 보고서 출력 |
| `core.py` | 공식 API, 보조 출처, 기업 식별, pandas 분석, 검증, Excel, OpenAI |
| `실습_검증.ipynb` | Jupyter 단계별 실습 / 별도 `assert` 검증 셀 |
| `test_core.py` | 인증키·외부 접속 불필요한 테스트 |
| `.env.example` | 공공데이터·OpenAI·NewsAPI·SerpAPI 및 개별 키 설정 예시 (실제 키 없음) |
| `secrets.toml.example` | Streamlit Community Cloud 시크릿 설정 예시 |
| `.gitignore` | `.env`, 각종 캐시, 보고서 등 추적 제외 |
| `requirements.txt` | 의존성 패키지 |

## 1. Windows / Anaconda Prompt 실행

프로젝트를 `C:\Users\ASUS\Python\AI_Company_Investment_App`에 풀었다면 다음 명령을 사용합니다. 경로는 실제 압축 해제 위치에 맞추세요.

```bat
cd /d "C:\Users\ASUS\Python\AI_Company_Investment_App"
"C:\Users\ASUS\anaconda3\python.exe" -m pip install -r requirements.txt
copy .env.example .env
notepad .env
"C:\Users\ASUS\anaconda3\python.exe" -m streamlit run app.py
```

Jupyter에서 `실습_검증.ipynb`를 열 때에도 동일한 Python 환경을 사용하세요.

## 2. .env 인증키

```dotenv
DATA_GO_KR_API_KEY=본인의_공공데이터포털_일반인증키
FINANCE_API_KEY=
STOCK_API_KEY=
OPENAI_API_KEY=본인의_새_OpenAI_API_키
OPENAI_MODEL=gpt-4.1-mini
NEWS_API_KEY=본인의_NewsAPI_키
SERPAPI_KEY=본인의_SerpAPI_키
```

- **공공데이터 인증키가 하나라면** `DATA_GO_KR_API_KEY`에만 입력하고 `FINANCE_API_KEY`, `STOCK_API_KEY`는 비워 두세요. 별개 키로 관리한다면 두 변수에 따로 지정할 수 있습니다.
- **기업기본정보 API / 기업 재무정보 API / 주식시세정보 API** 각각의 공공데이터포털 활용신청이 필요합니다. 주식시세 API 승인만으로 재무/기본 API의 승인이 보장되지는 않습니다.
- 뉴스: `NEWS_API_KEY`가 설정되어 있으면 먼저 시도하고, 실패하면 `SERPAPI_KEY`, 마지막으로 Google 뉴스 RSS를 시도합니다. 두 뉴스 API 키는 비워 두어도 됩니다. 무료 플랜에서는 뉴스 수집 범위/호출 횟수 제한이 있을 수 있습니다.
- `OPENAI_API_KEY`가 없으면 **1단계 데이터 분석만** 수행할 수 있습니다. 실시간 OpenAI 호출은 사용자 계정에 요금이 발생할 수 있습니다.
- 환경변수 이름을 정확히 맞추세요. 키 앞뒤 공백, 따옴표, 줄바꿈이 없도록 합니다. 인증키를 화면에 출력하지 않습니다.
- **이전에 스크린샷으로 노출된 OpenAI/NewsAPI/SerpAPI 키는 해당 발급처에서 폐기·재발급하여 새 키로 교체하세요.** `.env`는 GitHub에 올리지 마세요.

## 3. 금융위원회 공식 API 명세

기업기본정보 (기업명 → 법인번호):

`https://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2/getCorpOutline_V2`

기업 재무정보 (`crno`, `bizYear`):

`https://apis.data.go.kr/1160100/service/GetFinaStatInfoService_V2/getSummFinaStat_V2`

주식시세정보 V2 (요청 파라미터: `serviceKey`, `resultType=json`, `likeSrtnCd`, `beginBasDt`, `endBasDt`):

`https://apis.data.go.kr/1160100/GetStockSecuritiesInfoService_V2/getStockPriceInfo_V2`

응답 필드: `basDt`(기준일자), `srtnCd`(종목코드), `itmsNm`(종목명), `mkp`(시가), `hipr`(고가), `lopr`(저가), `clpr`(종가), `fltRt`(등락률), `trqu`(거래량), `trPrc`(거래대금), `mrktTotAmt`(시가총액). `endBasDt`는 **미만** 조건이므로 코드에서는 오늘 날짜의 다음 날을 설정합니다.

**주식시세정보 V2는 실시간 데이터가 아닙니다.** 첨부된 `금융위원회_주식시세정보_활용자가이드.docx`에 따르면 일 1회 갱신하며 일반적으로 다음 영업일 오후 1시 이후 반영됩니다. 화면에 실제 최신 기준일을 표시합니다.

## 4. 분석 결과

- **재무정보**: 매출액/영업이익/순이익/자산/부채/자본, 영업이익률, 순이익률, 부채비율, 전년대비 매출증감률(연속된 연도에만 계산)
- **주가정보**: 종가/시가/고가/저가, 거래량·거래대금, 시가총액, 기준일, 출처
- **뉴스정보**: 날짜, 기사 제목, 언론사, 검색 요약, 원문 링크, 출처
- **pandas 품질**: 데이터별 원본 행수, 중복 행수, 결측 셀수, 정리후 행수
- **통계집계**: 재무 금액/비율 평균, 주가 최소·최대·평균, 평균 거래량, 상위 언론사별 기사수
- **사실검증**: 자산=부채+자본(허용 오차 표시), 영업/순이익률·부채비율 수치 재계산, 고가≥저가, 뉴스 원문 진위 별도 확인 안내
- **차트**: Streamlit 재무·주가·거래량 차트 + Excel 파일의 `차트` 시트
- **다운로드**: 분석 Excel(.xlsx), OpenAI 보고서(.md), AI 의견이 포함된 Excel(.xlsx)

## 5. 테스트

외부 호출/인증키가 불필요한 모의 데이터 단위 테스트:

```bat
python -m unittest -v test_core.py
```

Jupyter Notebook `실습_검증.ipynb`에서는 **검증 셀을 별도로** 제공합니다. API 실데이터가 없다면 관련 assert가 실패할 수 있으며 이는 정확한 동작입니다. **현재 실 API / OpenAI 호출은 인증키가 없어 테스트 예정**입니다.

## 6. Streamlit Community Cloud

GitHub에 올릴 때 `.env`를 제외하세요. 실제 환경변수 값은 Streamlit Community Cloud의 `App Settings → Secrets`에 `secrets.toml.example`과 같은 TOML 형태로 입력하세요. 공개 배포 전에 반드시 데이터 사용조건을 검토하세요.

**저작권/이용조건:** 제공된 주식시세 활용가이드 p.42는 해당 데이터에 대해 공공누리 4유형과 제3자 무단제공/재배포 제한을 고지합니다. 타인에게 시세 원자료를 제공하는 공개 웹 앱이나 상업적 활용 시 한국거래소(KRX)의 허락·라이선스 및 데이터 사용조건을 먼저 확인하세요. 내부 교육용으로 테스트하는 편이 안전합니다.

## 7. 참고

- 금융위원회 기업기본정보: https://www.data.go.kr/data/15043184/openapi.do
- 금융위원회 기업 재무정보: https://www.data.go.kr/data/15043459/openapi.do
- 금융위원회 주식시세정보: https://www.data.go.kr/
- NewsAPI: https://newsapi.org/
- SerpAPI Google News: https://serpapi.com/google-news-api

모든 데이터는 출처·조회 기준일을 확인하세요. 본 프로그램은 학습용 정보 서비스이며 수익 보장이나 개인화된 투자자문이 아닙니다.
