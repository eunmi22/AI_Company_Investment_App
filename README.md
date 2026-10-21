# AI 기업 재무·주식시세·뉴스 통합분석 — 주식차트 고도화판

> **교육·연구용 프로젝트.** 검증되지 않은 자료나 수치를 채워 넣지 않으며, 투자 매수·매도 자동판단 기능은 없습니다.


## 이번 고도화에서 달라진 점 (주가 차트 1·2차 개선)

| 개선 항목 | 기존 화면 | 이번 고도화 |
|---|---|---|
| 주가차트 | Streamlit 기본 선 차트 | **Plotly 캔들(일봉) / 종가선 전환** |
| 거래량 | 별도의 막대그래프 | **캔들 아래 동일 거래일 X축의 막대그래프** |
| 축 오류 | 휴장일·미래 날짜 여백, 거래량 음수 축 가능 | **거래일 범주축, 실제 데이터 범위, 거래량 Y축 0 이상** |
| 기간 선택 | 고정 전체 기간 | **1개월 / 3개월 / 6개월 / 1년 / 전체** |
| 추세 분석 | 종가 추세만 | **SMA 5·20·60·120거래일**, 표시 여부 선택 |
| 종목 요약 | 최근 종가만 | **등락률, 거래량, 시가총액, 기간 수익률, 장중 최고·최저가와 날짜** |
| 거래량 특이점 | 단순 막대 | **20거래일 평균 대비 2배 이상 거래량 날짜 표** |
| 비정상 원자료 | 고가≥저가 위주 검사 | **OHLC 정합성, 음수 거래량 검사, 캔들 불가 시 선 차트 대체** |
| 숫자 표시 | 긴 억 원 숫자 | **조·억 원 단위 자동 표시** |

**차트 디자인은 참고 앱과 유사한 정보 구조만 채택했습니다.** 실시간 호가·체결·시간외 가격·매매 기능은 구현하지 않습니다.

### UI에서 사용하는 데이터와 계산 방식

- 기간 필터는 **현재 시각이 아닌 실제 가장 최근 조회된 거래일**을 기준으로 합니다. 낡은 데이터라도 미래 날짜를 생성하지 않습니다.
- 이동평균선(SMA)은 해당 거래일까지 **최근 N거래일 종가의 단순 평균**이며, N거래일 미만이면 표시하지 않습니다.
- 선택 기간 수익률은 **선택 기간 첫 거래일 종가 대비 마지막 거래일 종가** 변화율입니다. 사용자가 지정한 '1개월'과 동일한 달력 날짜의 정밀 총수익률을 뜻하지 않습니다.
- 기간 최고·최저가는 정상적인 **OHLC 자료의 장중 고가·저가**입니다. 종가 최고·최저가와 다릅니다.
- 빨강은 해당 거래일의 양봉(종가 ≥ 시가), 파랑은 음봉을 의미합니다. 이동평균선이나 거래량 급증은 투자 신호가 아닙니다.
- 금융위원회 주식시세 V2는 **일별·비실시간**입니다. 사용자 증권사의 정규장 가격, 장중 가격 또는 시간외 가격과 다를 수 있습니다.
- 공공데이터 조회 실패 시 `pykrx`, `yfinance`로 대체될 수 있습니다. **데이터 출처는 UI와 결과에 표시되며**, Yahoo Finance의 수정주가는 공식 비조정 시세와 달라질 수 있습니다.

### 추가된 파일

| 파일 | 역할 |
|---|---|
| `stock_chart.py` | 날짜·가격 정제, 기간별 통계, SMA, Plotly 통합 캔들/거래량 차트 |
| `test_stock_chart.py` | 13개 신규 모의 데이터 단위 테스트 (인증키·인터넷 불필요) |

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
| `stock_chart.py` | Plotly 캔들차트·이동평균선·기간별 통계 계산 |
| `core.py` | 공식 API, 보조 출처, 기업 식별, pandas 분석, 검증, Excel, OpenAI |
| `실습_검증.ipynb` | Jupyter 단계별 실습 / 별도 `assert` 검증 셀 |
| `test_core.py` | 인증키·외부 접속 불필요한 기존 단위 테스트 18개 |
| `test_stock_chart.py` | 고도화한 차트 단위 테스트 13개 |
| `.env.example` | 공공데이터·OpenAI·NewsAPI·SerpAPI 및 개별 키 설정 예시 (실제 키 없음) |
| `secrets.toml.example` | Streamlit Community Cloud 시크릿 설정 예시 |
| `.gitignore` | `.env`, 각종 캐시, 보고서 등 추적 제외 |
| `requirements.txt` | 의존성 패키지 |

## 1. Windows / Anaconda Prompt 실행

프로젝트를 `C:\Users\ASUS\Python\AI_Company_Investment_App`에 풀었다면 다음 명령을 사용합니다. 경로는 실제 압축 해제 위치에 맞추세요.

```bat
cd /d "C:\Users\ASUS\Python\AI_Company_Investment_App"
"C:\Users\ASUS\anaconda3\python.exe" -m pip install -r requirements.txt
if not exist .env copy .env.example .env
notepad .env
"C:\Users\ASUS\anaconda3\python.exe" -m streamlit run app.py
```

기존 프로젝트를 업데이트하는 경우 `.env`를 **덮어쓰지 마세요**. 위 명령은 `.env`가 없을 때만 예시 파일을 복사합니다.

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
- **주가 고도화**: 1개월~전체 기간 선택, 캔들·종가선 선택, 5/20/60/120일 이동평균, 기간 수익률, 장중 고가/저가, 평균 대비 거래량 급증
- **뉴스정보**: 날짜, 기사 제목, 언론사, 검색 요약, 원문 링크, 출처
- **pandas 품질**: 데이터별 원본 행수, 중복 행수, 결측 셀수, 정리후 행수
- **통계집계**: 재무 금액/비율 평균, 주가 최소·최대·평균, 평균 거래량, 상위 언론사별 기사수
- **사실검증**: 자산=부채+자본(허용 오차 표시), 영업/순이익률·부채비율 수치 재계산, 고가≥저가, 뉴스 원문 진위 별도 확인 안내
- **차트**: Streamlit 재무·주가·거래량 차트 + Excel 파일의 `차트` 시트
- **다운로드**: 분석 Excel(.xlsx), OpenAI 보고서(.md), AI 의견이 포함된 Excel(.xlsx)

## 5. 테스트

외부 API 인증키나 인터넷 접속 없이 **기존 18개 + 신규 13개 = 총 31개** 테스트를 실행합니다.

```bat
python -m unittest discover -v -p "test_*.py"
```

캔들/거래량 실제 시각화는 Plotly 코드 수준으로 검증했습니다. **실제 사용자의 API 인증키 및 브라우저 환경에서의 최종 동작 확인은 테스트 예정**입니다.

Jupyter Notebook `실습_검증.ipynb`에서는 **검증 셀을 별도로** 제공합니다. API 실데이터가 없다면 관련 assert가 실패할 수 있으며 이는 정확한 동작입니다. **현재 실 API / OpenAI 호출은 인증키가 없어 테스트 예정**입니다.

## 6. Streamlit Community Cloud

GitHub에 올릴 때 `.env`를 제외하세요. 실제 환경변수 값은 Streamlit Community Cloud의 `App Settings → Secrets`에 `secrets.toml.example`과 같은 TOML 형태로 입력하세요. 공개 배포 전에 반드시 데이터 사용조건을 검토하세요.

**저작권/이용조건:** 제공된 주식시세 활용가이드 p.42는 해당 데이터에 대해 공공누리 4유형과 제3자 무단제공/재배포 제한을 고지합니다. 타인에게 시세 원자료를 제공하는 공개 웹 앱이나 상업적 활용 시 한국거래소(KRX)의 허락·라이선스 및 데이터 사용조건을 먼저 확인하세요. 내부 교육용으로 테스트하는 편이 안전합니다.


## GitHub 기존 저장소 업데이트 (처음부터 새 저장소를 만들 필요 없음)

1. 본 ZIP을 압축 해제하고 기존 GitHub 저장소와 같은 폴더에 파일을 덮어씁니다. **기존 `.env`는 덮어쓰지 않습니다.**
2. 이번에 새로 들어온 `stock_chart.py`, `test_stock_chart.py`도 GitHub에 포함합니다.
3. `requirements.txt`에 추가된 `plotly`가 올라갔는지 확인합니다.
4. Git Bash 또는 Anaconda Prompt에서 기존 저장소로 이동해 다음처럼 제출합니다.

```bat
git status
git check-ignore .env
git add app.py core.py stock_chart.py test_stock_chart.py requirements.txt README.md "실습_검증.ipynb"
git commit -m "Improve stock charts and dashboard"
git push origin main
```

- `.env`를 GitHub에 **절대로 업로드하지 마세요**. `git check-ignore .env`가 `.env`를 출력하는지 확인해야 합니다. 이미 추적되는 경우 `.gitignore`만으로 제외되지 않습니다.
- GitHub 웹에서 직접 업로드하는 경우에는 업로드 목록에서 **`.env`를 직접 제외**해야 합니다.
- 기존 Streamlit Community Cloud가 해당 저장소의 `main`과 `app.py`를 가리키고 있다면 커밋 후 보통 다시 배포됩니다. 배포 로그에 `plotly` 설치 실패나 다른 오류가 없는지 확인하세요.
- Streamlit Cloud의 기존 **Secrets는 그대로 유지**합니다. `.env` 파일을 업로드할 필요가 없습니다.

## 7. 참고

- 금융위원회 기업기본정보: https://www.data.go.kr/data/15043184/openapi.do
- 금융위원회 기업 재무정보: https://www.data.go.kr/data/15043459/openapi.do
- 금융위원회 주식시세정보: https://www.data.go.kr/
- NewsAPI: https://newsapi.org/
- SerpAPI Google News: https://serpapi.com/google-news-api

모든 데이터는 출처·조회 기준일을 확인하세요. 본 프로그램은 학습용 정보 서비스이며 수익 보장이나 개인화된 투자자문이 아닙니다.
