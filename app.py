import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, date
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(
    page_title="배당금 교차투자 시뮬레이션",
    page_icon="💰",
    layout="wide"
)

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

# 메인 화면에 입력 파라미터
st.subheader("📊 투자 설정")
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    dividend_stock = st.text_input(
        "배당주 티커",
        value="JEPQ",
        placeholder="예: JEPQ, SCHD, VYM"
    ).upper()
with col2:
    invest_stock = st.text_input(
        "투자 대상 주식 티커",
        value="AMZN",
        placeholder="예: AMZN, AAPL, MSFT"
    ).upper()
col3, col4 = st.columns(2)
with col3:
    start_date = st.date_input(
        "시작 날짜",
        value=date(2025, 1, 1),
        max_value=date.today()
    )
with col4:
    shares_count = st.number_input(
        "보유 주식 수",
        min_value=1,
        max_value=100000,
        value=1000,
        step=100
    )

# 실행 버튼
st.markdown("---")
col_button = st.columns([1, 2, 1])
with col_button[1]:
    run_simulation = st.button("🚀 시뮬레이션 실행", type="primary", use_container_width=True)

# 헬퍼 함수 정의
@st.cache_resource
def get_stock_info(ticker_symbol):
    try:
        stock_ticker = yf.Ticker(ticker_symbol)
        info = stock_ticker.info
        currency = info.get('currency', 'N/A')
        return stock_ticker, currency
    except Exception:
        return None, None

@st.cache_data(ttl=3600)
def get_exchange_rate(from_currency, to_currency, trade_date):
    if from_currency == to_currency:
        return 1.0
    
    ticker_map = {
        ('USD', 'KRW'): 'USDKRW=X',
        ('KRW', 'USD'): 'KRWUSD=X',
    }
    
    rate_ticker = ticker_map.get((from_currency, to_currency))
    if not rate_ticker:
        st.warning(f"⚠️ {from_currency} 에서 {to_currency} 로의 환율 정보를 찾을 수 없습니다. 기본 환율 1.0을 적용합니다.")
        return 1.0

    try:
        rate_data = yf.Ticker(rate_ticker).history(start=trade_date.strftime('%Y-%m-%d'), period='5d')
        if not rate_data.empty:
            return rate_data['Close'].iloc[0]
    except Exception:
        st.warning(f"⚠️ {trade_date.strftime('%Y-%m-%d')} 환율 정보를 가져올 수 없습니다. 기본 환율 1.0을 적용합니다.")
        return 1.0

    return 1.0

# 메인 실행 로직
if run_simulation:
    if not dividend_stock or not invest_stock:
        st.error("배당주와 투자 대상 주식 티커를 모두 입력해주세요.")
        st.stop()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 1. 티커 정보 및 통화 가져오기
        status_text.text("📊 티커 정보를 가져오는 중...")
        progress_bar.progress(10)
        
        jepq_ticker, dividend_currency = get_stock_info(dividend_stock)
        invest_ticker, invest_currency = get_stock_info(invest_stock)
        
        if jepq_ticker is None or invest_ticker is None:
            st.error("❌ 유효하지 않은 티커 심볼입니다. 올바른 티커를 입력해주세요.")
            st.stop()

        # 2. 배당 정보 가져오기
        status_text.text("💰 배당 내역을 가져오는 중...")
        progress_bar.progress(30)
        dividends = jepq_ticker.dividends
        recent_dividends = dividends[dividends.index.date >= start_date]
        
        if recent_dividends.empty:
            st.warning(f"⚠️ {start_date} 이후 {dividend_stock}의 배당 내역이 없습니다.")
            st.stop()

        # 3. 투자 시뮬레이션 실행
        status_text.text("📈 투자 시뮬레이션 실행 중...")
        progress_bar.progress(50)
        
        total_shares_bought = 0.0
        total_invested_amount = 0.0
        investments = []
        
        for dividend_date_utc, dividend_per_share in recent_dividends.items():
            dividend_date_local = dividend_date_utc.tz_convert(None)
            
            invest_data = invest_ticker.history(start=dividend_date_local.strftime('%Y-%m-%d'), period='5d')
            if invest_data.empty:
                st.warning(f"⚠️ {dividend_date_local.strftime('%Y-%m-%d')} {invest_stock}의 주가 데이터를 찾을 수 없어 해당 배당금은 계산에서 제외됩니다.")
                continue
            
            invest_close_price = invest_data['Close'].iloc[0]
            actual_trade_date = invest_data.index[0].tz_convert(None)

            total_dividend = dividend_per_share * shares_count
            converted_amount = total_dividend
            exchange_rate = 1.0

            if dividend_currency != invest_currency:
                exchange_rate = get_exchange_rate(dividend_currency, invest_currency, actual_trade_date)
                converted_amount = total_dividend * exchange_rate
            
            shares_bought = converted_amount / invest_close_price
            
            total_shares_bought += shares_bought
            total_invested_amount += converted_amount
            
            investments.append({
                'date': actual_trade_date,
                'dividend_date': dividend_date_local.strftime('%Y-%m-%d'),
                'trade_date': actual_trade_date.strftime('%Y-%m-%d'),
                'dividend_per_share': dividend_per_share,
                'total_dividend_orig': total_dividend,
                'exchange_rate': exchange_rate,
                'total_dividend_converted': converted_amount,
                'stock_price': invest_close_price,
                'shares_bought': shares_bought,
                'cumulative_shares': total_shares_bought,
            })
            
        progress_bar.progress(80)
        
        # 4. 최종 결과 계산
        current_price_data = invest_ticker.history(period='1d')
        if current_price_data.empty:
            st.error("❌ 현재 주가를 가져올 수 없습니다.")
            st.stop()
        current_price = current_price_data['Close'].iloc[-1]
        
        average_price = total_invested_amount / total_shares_bought if total_shares_bought > 0 else 0
        current_value = total_shares_bought * current_price
        profit_loss = current_value - total_invested_amount
        profit_loss_pct = (profit_loss / total_invested_amount) * 100 if total_invested_amount > 0 else 0
        
        progress_bar.progress(100)
        status_text.empty()
        
        # 결과 표시
        if dividend_stock == invest_stock:
            st.info(f"✨ **동일 종목 재투자**")
        st.success("🎉 시뮬레이션이 성공적으로 완료되었습니다!")

        # 통화 심볼 설정
        currency_symbol = '₩' if invest_currency == 'KRW' else '$'

        # 메트릭 카드들
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                label="💵 총 투자금액",
                value=f"{currency_symbol}{total_invested_amount:,.2f}",
                delta=f"{len(investments)}회 투자"
            )
        with col2:
            st.metric(
                label=f"📊 보유 {invest_stock} 주식",
                value=f"{total_shares_bought:.6f}주",
                delta=f"평균단가 {currency_symbol}{average_price:,.2f}"
            )
        with col3:
            st.metric(
                label="💎 현재 평가금액",
                value=f"{currency_symbol}{current_value:,.2f}",
                delta=f"현재가 {currency_symbol}{current_price:,.2f}"
            )
        with col4:
            st.metric(
                label="📈 손익",
                value=f"{currency_symbol}{profit_loss:,.2f}",
                delta=f"{profit_loss_pct:+.2f}%"
            )
            
        # 차트 섹션
        st.subheader("📊 투자 현황 차트")
        df_investments = pd.DataFrame(investments)
        df_investments.set_index('date', inplace=True)
        
        tab1, tab2 = st.tabs(["📈 누적 주식 보유량", "📊 주가 및 단가 비교"])

        with tab1:
            fig_cumulative = go.Figure()
            fig_cumulative.add_trace(go.Scatter(
                x=df_investments.index,
                y=df_investments['cumulative_shares'],
                mode='lines+markers',
                name=f'누적 {invest_stock} 보유량',
                line=dict(color='#1f77b4', width=3)
            ))
            fig_cumulative.update_layout(
                title=f"누적 {invest_stock} 주식 보유량 변화",
                xaxis_title="날짜",
                yaxis_title="보유 주식 수",
                hovermode='x unified'
            )
            st.plotly_chart(fig_cumulative, use_container_width=True)
        
        with tab2:
            fig_price = go.Figure()
            fig_price.add_trace(go.Scatter(
                x=df_investments.index,
                y=df_investments['stock_price'],
                mode='lines+markers',
                name=f'{invest_stock} 매수가',
                line=dict(color='#ff7f0e', width=2)
            ))
            fig_price.add_hline(y=average_price, line_dash="dash", line_color="red",
                                 annotation_text=f"평균단가: {currency_symbol}{average_price:,.2f}")
            fig_price.add_hline(y=current_price, line_dash="dash", line_color="green",
                                 annotation_text=f"현재가: {currency_symbol}{current_price:,.2f}")
            fig_price.update_layout(
                title=f"{invest_stock} 주가 변화 및 매수가 비교",
                xaxis_title="날짜",
                yaxis_title=f"주가 ({currency_symbol})",
                hovermode='x unified'
            )
            st.plotly_chart(fig_price, use_container_width=True)

        # 상세 투자 내역 테이블
        st.subheader("📋 상세 투자 내역")
        display_df = pd.DataFrame(investments)
        display_df['배당일'] = display_df['dividend_date']
        display_df['거래일'] = display_df['trade_date']
        display_df['주당배당금'] = display_df['dividend_per_share'].apply(lambda x: f"${x:.4f}" if dividend_currency == 'USD' else f"₩{x:,.0f}")
        display_df['투자금액'] = display_df['total_dividend_converted'].apply(lambda x: f"{currency_symbol}{x:,.2f}")
        display_df['매수가'] = display_df['stock_price'].apply(lambda x: f"{currency_symbol}{x:,.2f}")
        display_df['매수주식수'] = display_df['shares_bought'].apply(lambda x: f"{x:.6f}")
        display_df['누적보유'] = display_df['cumulative_shares'].apply(lambda x: f"{x:.6f}")

        columns = ['배당일', '거래일', '주당배당금']
        if dividend_currency != invest_currency:
            display_df['환율'] = display_df['exchange_rate'].apply(lambda x: f"{x:,.2f}")
            columns.append('환율')
        columns.extend(['투자금액', '매수가', '매수주식수', '누적보유'])

        st.dataframe(display_df[columns], use_container_width=True)

        # 다운로드 버튼
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 투자 내역 CSV 다운로드",
            data=csv,
            file_name=f"{dividend_stock}_to_{invest_stock}_investment_history.csv",
            mime="text/csv"
        )
            
    except Exception as e:
        st.error(f"❌ 오류가 발생했습니다: {e}")
        st.info("티커 심볼이 올바른지, 날짜가 올바른지 확인하고 다시 시도해주세요.")
    finally:
        progress_bar.empty()
        status_text.empty()
else:
    st.info("💡 **Tip**: 위의 투자 설정을 입력하고 시뮬레이션을 실행해보세요! 왼쪽 사이드바에서 예시와 티커 입력 방법을 확인하실 수 있습니다.")

st.markdown("---")
st.markdown("💡 **Tip**: 다양한 배당주와 성장주 조합을 테스트해보세요!")
