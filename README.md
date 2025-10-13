# 📈 배당금 교차투자 시뮬레이터 (Dividend Reinvestment Simulator)

**🔗 실행 (Launch App):** [https://dividend-simulatorv2.streamlit.app/](https://dividend-simulatorv2.streamlit.app/)

---

## 📝 소개 (Summary)

**KR:**  
이 앱은 **배당금을 모두 재투자했을 경우 오늘 시점의 결과**를 시뮬레이션해주는 도구입니다. 

**예시 시나리오:**
- JEPQ 1000주를 2025년 1월 1일에 보유 시작  
- 배당금이 지급될 때마다 전액을 AMZN에 투자  
- 현재 몇 주를 보유하게 되었는지, 수익률은 얼마인지 확인 가능  

**EN:**  
This app simulates the **results of reinvesting all dividends up to today’s date**.

**Example scenario:**
- Start with 1000 shares of JEPQ on Jan 1, 2025  
- Reinvest every dividend payout fully into AMZN  
- Check how many shares you own now and what your return is  

---

## 🔑 주요 기능 (Features)

**KR:**
- ✅ 누적 배당금 조회  
- ✅ 재투자된 주식 수 확인  
- ✅ 현재 평가금액 및 수익률 계산  
- ✅ 상세 내역(배당 지급일, 금액, 투자 내역) 조회 가능  

**EN:**
- ✅ View total dividends received  
- ✅ Track number of reinvested shares  
- ✅ Calculate current value and return rate  
- ✅ Check detailed history (dividend dates, amounts, reinvestment logs)  

---

## ▶️ 실행 예시 (Simulation Example)

**KR:**  
아래는 JEPQ 1000주를 2025-01-01 시점에 보유 후, 배당금을 모두 AMZN에 재투자했을 때의 결과 예시입니다.

**EN:**  
Below is an example result when starting with 1000 shares of JEPQ on 2025-01-01, reinvesting all dividends into AMZN.

| 구분 (Item)              | 결과 (Result)               |
|---------------------------|-----------------------------|
| 누적 배당금 (Total Dividends) | **$3,630.00** (7회 지급)   |
| 보유 AMZN 주식 (AMZN Shares) | **17.52 shares**           |
| 평균 매수가 (Avg. Buy Price) | **$207.20**                |
| 현재 평가금액 (Current Value) | **$4,006.77**              |
| 수익 (Profit)              | **$376.77 (+10.38%)**      |

---

## 🛠 사용 방법 (How to Use)

**KR:**
1. 투자 시작 시점과 보유 주식 수를 입력  
2. 배당금을 어떤 종목에 재투자할지 선택  
3. **시뮬레이션 실행** 버튼 클릭  
4. 결과 화면에서 보유 주식 수, 평가금액, 수익률, 상세 내역 확인 가능  

**EN:**
1. Enter start date and number of shares you own  
2. Select which stock to reinvest dividends into  
3. Click **Run Simulation**  
4. See the results: shares owned, portfolio value, return rate, and detailed logs  

---

## 🧰 기술 스택 (Tech Stack)

- **Streamlit**  
- **Python** (pandas, yfinance, etc.)  

---

## ⚠️ 유의사항 (Disclaimer)

**KR:**  
본 시뮬레이터는 **교육 및 참고용**입니다.  
실제 투자 결과와 차이가 있을 수 있으며, 투자 판단은 본인 책임입니다.  

**EN:**  
This simulator is for **educational and reference purposes only**.  
Actual investment results may differ. Use at your own discretion.  

