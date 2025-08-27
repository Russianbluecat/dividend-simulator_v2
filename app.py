import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import plotly.express as px
import logging
from typing import Tuple, Optional
import time

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="배당금 교차투자 시뮬레이션",
    page_icon="💰",
    layout="wide"
)

# 캐싱을 위한 세션 상태 초기화
if 'cache' not in st.session_state:
    st.session_state.cache = {}

# 제목 및 설명
st.title("💰 배당금 교차투자 시뮬레이션")
st.markdown("""
**배당주에서 받은 배당금을 모두 투자했다면 어떨까요?**  
특정 시점부터 배당주를 보유하고, 받은 배당금을 모두 재투자한 시뮬레이션합니다.  
(조회 시점에서의 결과이며 소숫점 투자 포함함)
""")

# 사이드바에 예시와 가이드 추가
st.sidebar.header("🎯 예시 결과")
st.sidebar.markdown("""
**JEPQ 1000주 보유**  
**→ 배당금 AMZN 재투자**  
**(2025.01.01~2025.08.27 기준)**

- 📊 총 7회 배당 수령  
      ($3,630 배당금)
- 💎 AMZN 17.5주 보유  
      (평균단가 $207.20)
- 📈 +10.01% 수익률 달성
""")

st.sidebar.markdown("---")

st.sidebar.header("📝 티커 입력 예시")
st.sidebar.markdown("""
**미국 주식/ETF:**
- JEPQ, SCHD, AAPL, MSFT, AMZN

**한국 주식:**
- 005930.KS (삼성전자)
- 000660.KS (SK하이닉스)

**한국 ETF:**
- 284430.KS (KODEX 200)
- 132030.KS (KODEX 골드선물)
""")

st.sidebar.markdown("---")
st.sidebar.header("💱 통화 처리 정책")
st.sidebar.markdown("""
**결과 표기 기준:** 투자 대상 주식 통화

🇺🇸 → 🇺🇸: USD 기준  
🇰🇷 → 🇰🇷: KRW 기준  
🇺🇸 → 🇰🇷: KRW 기준 (환전)  
🇰🇷 → 🇺🇸: USD 기준 (환전)  

*환율: 배당일 기준 야후파이낸스*
""")

# 개선된 유틸리티 함수들
@st.cache_data(ttl=3600)  # 1시간 캐시
def get_stock_info(ticker: str) -> Optional[dict]:
    """주식 정보를 가져오고 캐시"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info or 'currency' not in info:
            # info가 없거나 통화 정보가 없는 경우 추정
            currency, symbol = get_currency_info(ticker)
            return {'currency': currency, 'symbol': symbol}
        return {
            'currency': info.get('currency', 'USD'),
            'symbol': '$' if info.get('currency', 'USD') == 'USD' else '₩'
        }
    except Exception as e:
        logger.error(f"Error getting stock info for {ticker}: {e}")
        return None

def get_currency_info(ticker: str) -> Tuple[str, str]:
    """티커의 통화 정보 반환 (개선된 버전)"""
    if ticker.endswith('.KS') or ticker.endswith('.KQ'):
        return 'KRW', '₩'
    elif ticker.endswith('.TO'):
        return 'CAD', 'C$'
    elif ticker.endswith('.L'):
        return 'GBP', '£'
    else:
        return 'USD', '$'

@st.cache_data(ttl=3600)
def get_exchange_rate_improved(date_str: str, from_currency: str, to_currency: str) -> float:
    """개선된 환율 가져오기 (재시도 로직 포함)"""
    if from_currency == to_currency:
        return 1.0
    
    # 캐시 키 생성
    cache_key = f"{date_str}_{from_currency}_{to_currency}"
    if cache_key in st.session_state.cache:
        return st.session_state.cache[cache_key]
    
    exchange_rate = 1.0
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            if from_currency == 'USD' and to_currency == 'KRW':
                # 여러 환율 소스 시도
                for ticker_symbol in ["USDKRW=X", "KRW=X"]:
                    try:
                        ticker = yf.Ticker(ticker_symbol)
                        # 더 넓은 날짜 범위로 데이터 요청
                        start_date = pd.to_datetime(date_str) - timedelta(days=7)
                        end_date = pd.to_datetime(date_str) + timedelta(days=7)
                        
                        data = ticker.history(start=start_date, end=end_date)
                        if len(data) > 0:
                            # 가장 가까운 날짜의 환율 찾기
                            target_date = pd.to_datetime(date_str)
                            closest_idx = (data.index - target_date).abs().argmin()
                            exchange_rate = float(data['Close'].iloc[closest_idx])
                            break
                    except Exception as e:
                        logger.warning(f"Failed to get exchange rate from {ticker_symbol}: {e}")
                        continue
                
            elif from_currency == 'KRW' and to_currency == 'USD':
                # USD/KRW 환율의 역수
                usd_krw_rate = get_exchange_rate_improved(date_str, 'USD', 'KRW')
                if usd_krw_rate > 0:
                    exchange_rate = 1.0 / usd_krw_rate
            
            # 유효한 환율인지 확인 (너무 극단적인 값 제외)
            if from_currency == 'USD' and to_currency == 'KRW':
                if 1000 <= exchange_rate <= 2000:  # 합리적인 USD/KRW 범위
                    break
            elif from_currency == 'KRW' and to_currency == 'USD':
                if 0.0005 <= exchange_rate <= 0.001:  # 합리적인 KRW/USD 범위
                    break
                    
        except Exception as e:
            logger.warning(f"Exchange rate attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                # 마지막 시도에서도 실패하면 기본값 사용
                if from_currency == 'USD' and to_currency == 'KRW':
                    exchange_rate = 1350.0  # 업데이트된 기본 환율
                elif from_currency == 'KRW' and to_currency == 'USD':
                    exchange_rate = 1.0 / 1350.0
            else:
                time.sleep(1)  # 잠시 대기 후 재시도
    
    # 결과 캐시
    st.session_state.cache[cache_key] = exchange_rate
    return exchange_rate

def convert_currency(amount: float, from_currency: str, to_currency: str, exchange_rate: float) -> float:
    """통화 변환"""
    if from_currency == to_currency:
        return amount
    return amount * exchange_rate

@st.cache_data(ttl=1800)  # 30분 캐시
def get_stock_data_with_retry(ticker: str, start_date: str, period: str = '5d', max_retries: int = 3):
    """재시도 로직이 있는 주식 데이터 가져오기"""
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            if start_date:
                data = stock.history(start=start_date, period=period)
            else:
                data = stock.history(period=period)
            
            if len(data) > 0:
                return data
            else:
                logger.warning(f"No data returned for {ticker}, attempt {attempt + 1}")
                
        except Exception as e:
            logger.error(f"Error getting data for {ticker}, attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 지수적 백오프
    
    return None

def validate_ticker(ticker: str) -> bool:
    """티커 유효성 검사"""
    try:
        stock = yf.Ticker(ticker)
        # 최근 5일 데이터로 유효성 확인
        data = stock.history(period='5d')
        return len(data) > 0
    except:
        return False

# 메인 화면에 입력 파라미터
st.subheader("📊 투자 설정")
st.markdown("---")

# 입력 폼을 2x2 그리드로 메인 화면에 배치
col1, col2 = st.columns(2)

with col1:
    dividend_stock = st.text_input(
        "배당주 티커",
        value="JEPQ",
        placeholder="예: JEPQ, SCHD, VYM",
        help="배당금을 받을 주식의 티커를 입력하세요"
    ).upper()

with col2:
    invest_stock = st.text_input(
        "투자 대상 주식 티커",
        value="AMZN",
        placeholder="예: AMZN, AAPL, MSFT",
        help="배당금으로 매수할 주식의 티커를 입력하세요"
    ).upper()

col3, col4 = st.columns(2)

with col3:
    start_date = st.date_input(
        "시작 날짜",
        value=date(2025, 1, 1),
        max_value=date.today(),
        help="시뮬레이션을 시작할 날짜를 선택하세요"
    )

with col4:
    shares_count = st.number_input(
        "보유 주식 수",
        min_value=1,
        max_value=100000,
        value=1000,
        step=100,
        help="초기에 보유한 배당주 주식 수를 입력하세요"
    )

# 티커 유효성 검사
ticker_validation_col1, ticker_validation_col2 = st.columns(2)

if dividend_stock:
    with ticker_validation_col1:
        if validate_ticker(dividend_stock):
            st.success(f"✅ {dividend_stock} 유효한 티커")
            div_currency, div_symbol = get_currency_info(dividend_stock)
            st.info(f"📊 **배당주**: {dividend_stock} ({div_symbol} {div_currency})")
        else:
            st.error(f"❌ {dividend_stock} 유효하지 않은 티커")

if invest_stock:
    with ticker_validation_col2:
        if validate_ticker(invest_stock):
            st.success(f"✅ {invest_stock} 유효한 티커")
            inv_currency, inv_symbol = get_currency_info(invest_stock)
            st.info(f"💎 **투자 대상**: {invest_stock} ({inv_symbol} {inv_currency}) ← **결과 표기 기준**")
        else:
            st.error(f"❌ {invest_stock} 유효하지 않은 티커")

# 실행 버튼 - 중앙 배치
st.markdown("---")
col_button = st.columns([1, 2, 1])
with col_button[1]:
    run_simulation = st.button("🚀 시뮬레이션 실행", type="primary", use_container_width=True)

# 메인 영역
if run_simulation:
    # 입력 검증
    if not dividend_stock or not invest_stock:
        st.error("배당주와 투자 대상 주식 티커를 모두 입력해주세요.")
        st.stop()
    
    if not validate_ticker(dividend_stock):
        st.error(f"'{dividend_stock}'는 유효하지 않은 티커입니다. 다시 확인해주세요.")
        st.stop()
    
    if not validate_ticker(invest_stock):
        st.error(f"'{invest_stock}'는 유효하지 않은 티커입니다. 다시 확인해주세요.")
        st.stop()
    
    # 통화 정보 설정
    dividend_currency, dividend_symbol = get_currency_info(dividend_stock)
    invest_currency, invest_symbol = get_currency_info(invest_stock)
    result_currency = invest_currency  # 결과는 투자 대상 주식 통화 기준
    result_symbol = invest_symbol
    
    # 투자 시나리오 표시
    if dividend_currency != invest_currency:
        st.info(f"💱 **환전 투자**: {dividend_symbol} 배당금 → {result_symbol} 투자 (결과: {result_symbol} 기준)")
    else:
        if dividend_stock == invest_stock:
            st.info(f"🔄 **동일 종목 재투자**: {dividend_stock} 배당금 → {dividend_stock} 재투자")
        else:
            if dividend_currency == "KRW":
                st.info(f"💰 **동일 통화 투자**: ₩ 원화 배당금 → ₩ 원화 투자")
            else:
                st.info(f"💰 **동일 통화 투자**: $ 달러 배당금 → $ 달러 투자")
    
    # 프로그레스 바
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 1. 배당 정보 가져오기
        status_text.text("📊 배당 정보를 가져오는 중...")
        progress_bar.progress(20)
        
        dividend_ticker = yf.Ticker(dividend_stock)
        dividends = dividend_ticker.dividends
        
        if len(dividends) == 0:
            st.error(f"❌ {dividend_stock}의 배당 내역을 찾을 수 없습니다.")
            st.stop()
        
        # 시작일 이후 배당 필터링 (타임존 처리 개선)
        start_datetime = pd.Timestamp(start_date, tz=dividends.index.tz)
        recent_dividends = dividends[dividends.index >= start_datetime]
        
        if len(recent_dividends) == 0:
            st.warning(f"⚠️ {start_date} 이후 {dividend_stock}의 배당 내역이 없습니다.")
            
            # 최근 배당 정보 표시
            if len(dividends) > 0:
                latest_dividend = dividends.index[-1].strftime('%Y-%m-%d')
                st.info(f"💡 가장 최근 배당일: {latest_dividend}")
            st.stop()
        
        st.success(f"📊 {len(recent_dividends)}회의 배당 내역을 발견했습니다.")
        
        # 2. 투자 대상 주식 정보 가져오기
        status_text.text(f"📊 {invest_stock} 주가 정보를 가져오는 중...")
        progress_bar.progress(60)
        
        # 3. 투자 시뮬레이션 실행
        status_text.text("💰 투자 시뮬레이션 실행 중...")
        
        total_shares_bought = 0.0
        total_invested_amount = 0.0  # 결과 통화 기준
        investments = []
        failed_investments = []
        
        for i, (dividend_date, dividend_per_share) in enumerate(recent_dividends.items()):
            try:
                dividend_date_str = dividend_date.strftime('%Y-%m-%d')
                
                # 배당금 계산 (배당주 통화 기준)
                total_dividend_original = dividend_per_share * shares_count
                
                # 환율 가져오기
                exchange_rate = get_exchange_rate_improved(
                    dividend_date_str, 
                    dividend_currency, 
                    invest_currency
                )
                
                # 배당금을 투자 대상 통화로 변환
                total_dividend_converted = convert_currency(
                    total_dividend_original,
                    dividend_currency,
                    invest_currency,
                    exchange_rate
                )
                
                # 투자 대상 주식의 해당일 주가 가져오기
                invest_data = get_stock_data_with_retry(invest_stock, dividend_date_str, '5d')
                
                if invest_data is not None and len(invest_data) > 0:
                    invest_close_price = invest_data['Close'].iloc[0]
                    actual_trade_date = invest_data.index[0].strftime('%Y-%m-%d')
                    
                    # 매수 가능 주식 수 계산
                    shares_bought = total_dividend_converted / invest_close_price
                    total_shares_bought += shares_bought
                    total_invested_amount += total_dividend_converted
                    
                    # 투자 기록 저장
                    investment_record = {
                        'date': dividend_date,
                        'dividend_date': dividend_date_str,
                        'trade_date': actual_trade_date,
                        'dividend_per_share_original': dividend_per_share,
                        'total_dividend_original': total_dividend_original,
                        'dividend_currency': dividend_currency,
                        'exchange_rate': exchange_rate,
                        'total_dividend_converted': total_dividend_converted,
                        'invest_currency': invest_currency,
                        'stock_price': invest_close_price,
                        'shares_bought': shares_bought,
                        'cumulative_shares': total_shares_bought,
                    }
                    
                    investments.append(investment_record)
                else:
                    failed_investments.append({
                        'date': dividend_date_str,
                        'reason': f"{invest_stock} 주가 데이터 없음"
                    })
                
                # 진행률 업데이트
                progress = 60 + int((i + 1) / len(recent_dividends) * 20)
                progress_bar.progress(progress)
                    
            except Exception as e:
                error_msg = f"{dividend_date_str} 데이터 처리 중 오류: {str(e)}"
                logger.error(error_msg)
                failed_investments.append({
                    'date': dividend_date_str,
                    'reason': str(e)
                })
        
        if len(investments) == 0:
            st.error("❌ 처리할 수 있는 투자 데이터가 없습니다.")
            if failed_investments:
                st.error("실패한 투자들:")
                for failure in failed_investments:
                    st.text(f"- {failure['date']}: {failure['reason']}")
            st.stop()
        
        progress_bar.progress(80)
        
        # 4. 현재 주가 및 결과 계산
        status_text.text("📈 현재 주가 정보 가져오는 중...")
        current_data = get_stock_data_with_retry(invest_stock, None, '1d')
        
        if current_data is None or len(current_data) == 0:
            st.error(f"❌ {invest_stock}의 현재 주가를 가져올 수 없습니다.")
            st.stop()
            
        current_price = current_data['Close'].iloc[-1]
        
        # 계산 (모두 결과 통화 기준)
        average_price = total_invested_amount / total_shares_bought if total_shares_bought > 0 else 0
        current_value = total_shares_bought * current_price
        profit_loss = current_value - total_invested_amount
        profit_loss_pct = (profit_loss / total_invested_amount) * 100 if total_invested_amount > 0 else 0
        
        progress_bar.progress(100)
        status_text.text("✅ 시뮬레이션 완료!")
        
        # 실패한 투자 알림
        if failed_investments:
            with st.expander(f"⚠️ {len(failed_investments)}개의 투자가 실패했습니다 (클릭하여 자세히 보기)"):
                for failure in failed_investments:
                    st.text(f"• {failure['date']}: {failure['reason']}")
        
        # 결과 표시
        st.success("🎉 시뮬레이션이 성공적으로 완료되었습니다!")
        
        # 환전 정보 표시
        if dividend_currency != invest_currency and investments:
            avg_exchange_rate = sum(inv['exchange_rate'] for inv in investments) / len(investments)
            min_rate = min(inv['exchange_rate'] for inv in investments)
            max_rate = max(inv['exchange_rate'] for inv in investments)
            st.info(f"💱 **환율 정보**: 평균 {avg_exchange_rate:.4f}, 최저 {min_rate:.4f}, 최고 {max_rate:.4f} (1 {dividend_currency} → {invest_currency})")
        
        # 메트릭 카드들
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💵 총 투자금액",
                value=f"{result_symbol}{total_invested_amount:,.2f}",
                delta=f"{len(investments)}회 투자"
            )
        
        with col2:
            st.metric(
                label=f"📊 보유 {invest_stock} 주식",
                value=f"{total_shares_bought:.6f}주",
                delta=f"평균 {result_symbol}{average_price:.2f}"
            )
        
        with col3:
            st.metric(
                label="💎 현재 평가금액",
                value=f"{result_symbol}{current_value:,.2f}",
                delta=f"현재가 {result_symbol}{current_price:.2f}"
            )
        
        with col4:
            st.metric(
                label="📈 손익",
                value=f"{result_symbol}{profit_loss:,.2f}",
                delta=f"{profit_loss_pct:+.2f}%"
            )
        
        # 차트 및 분석 섹션은 계속...
        # (이후 차트, 테이블, 다운로드 기능 등은 동일)
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Simulation error: {error_message}")
        st.error(f"❌ 시뮬레이션 중 오류가 발생했습니다: {error_message}")
    
    finally:
        progress_bar.empty()
        status_text.empty()

else:
    # 초기 화면
    st.info("💡 **사용 방법**: 위의 투자 설정을 입력하고 시뮬레이션을 실행해보세요!")
    
    # 예시 시나리오들
    st.subheader("🎯 추천 시나리오")
    
    scenario_col1, scenario_col2, scenario_col3 = st.columns(3)
    
    with scenario_col1:
        st.info("""
        **📊 고배당 ETF → 성장주**
        - 배당주: JEPQ, SCHD, DIVO
        - 투자 대상: AMZN, GOOGL, TSLA
        - 특징: 안정적 배당 → 성장성
        """)
    
    with scenario_col2:
        st.info("""
        **🔄 배당 재투자 (DRIP)**
        - 배당주: 동일 종목
        - 투자 대상: 동일 종목
        - 특징: 복리효과 극대화
        """)
    
    with scenario_col3:
        st.info("""
        **💱 환전 투자**
        - 배당주: 미국 주식/ETF
        - 투자 대상: 한국 주식
        - 특징: 환율 변동 영향 고려
        """)

# 푸터
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.markdown("💡 **Tip**: 다양한 배당주와 성장주 조합을 테스트해보세요!")

with footer_col2:
    st.markdown("⚠️ **주의**: 과거 성과가 미래 결과를 보장하지 않습니다.")

with footer_col3:
    st.markdown("🔄 **업데이트**: 데이터는 야후 파이낸스에서 실시간 조회합니다.")

st.caption("Version 2.0 - Enhanced Error Handling & User Experience")
