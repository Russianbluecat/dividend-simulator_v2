import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date
import plotly.graph_objects as go
import plotly.express as px

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

# 통화 및 환율 처리 함수들
def get_currency_info(ticker):
    """티커의 통화 정보 반환"""
    if ticker.endswith('.KS'):
        return 'KRW', '₩'
    else:
        return 'USD', '$'

def get_exchange_rate(date_str, from_currency, to_currency):
    """특정 날짜의 환율 반환"""
    if from_currency == to_currency:
        return 1.0
    
    try:
        if from_currency == 'USD' and to_currency == 'KRW':
            usd_krw = yf.Ticker("USDKRW=X")
            exchange_data = usd_krw.history(start=date_str, period='5d')
            if len(exchange_data) > 0:
                return exchange_data['Close'].iloc[0]
        elif from_currency == 'KRW' and to_currency == 'USD':
            usd_krw = yf.Ticker("USDKRW=X")
            exchange_data = usd_krw.history(start=date_str, period='5d')
            if len(exchange_data) > 0:
                return 1.0 / exchange_data['Close'].iloc[0]
    except:
        pass
    
    # 기본 환율 (데이터 없을 경우)
    if from_currency == 'USD' and to_currency == 'KRW':
        return 1300.0
    elif from_currency == 'KRW' and to_currency == 'USD':
        return 1.0 / 1300.0
    
    return 1.0

def convert_currency(amount, from_currency, to_currency, exchange_rate):
    """통화 변환"""
    if from_currency == to_currency:
        return amount
    return amount * exchange_rate

# 메인 화면에 입력 파라미터
st.subheader("📊 투자 설정")

st.markdown("---")

# 입력 폼을 2x2 그리드로 메인 화면에 배치
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

# 통화 정보 미리보기
if dividend_stock and invest_stock:
    div_currency, div_symbol = get_currency_info(dividend_stock)
    inv_currency, inv_symbol = get_currency_info(invest_stock)
    
    col_preview1, col_preview2 = st.columns(2)
    with col_preview1:
        st.info(f"📊 **배당주**: {dividend_stock} ({div_symbol} {div_currency})")
    with col_preview2:
        st.info(f"💎 **투자 대상**: {invest_stock} ({inv_symbol} {inv_currency}) ← **결과 표기 기준**")

# 실행 버튼 - 중앙 배치
st.markdown("---")
col_button = st.columns([1, 2, 1])
with col_button[1]:
    run_simulation = st.button("🚀 시뮬레이션 실행", type="primary", use_container_width=True)

# 메인 영역
if run_simulation:
    if not dividend_stock or not invest_stock:
        st.error("배당주와 투자 대상 주식 티커를 모두 입력해주세요.")
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
            # 동일 통화 투자 시 명확한 표시
            if dividend_currency == "KRW":
                st.info(f"💰 **동일 통화 투자**:₩ 원화 배당금 → ₩ 원화 투자")
            else:  # USD
                st.info(f"💰 **동일 통화 투자**:$ 달러 배당금 → $ 달러 투자")
    
    # 프로그레스 바
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 1. 배당 정보 가져오기
        status_text.text("📊 배당 정보를 가져오는 중...")
        progress_bar.progress(20)
        
        dividend_ticker = yf.Ticker(dividend_stock)
        dividends = dividend_ticker.dividends
        
        # 시작일 이후 배당 필터링
        start_datetime = pd.Timestamp(start_date)
        dividends_naive = dividends.tz_localize(None)
        recent_dividends = dividends[dividends_naive.index >= start_datetime]
        
        if len(recent_dividends) == 0:
            st.warning(f"⚠️ {start_date} 이후 {dividend_stock}의 배당 내역이 없습니다.")
            st.stop()
        
        # 2. 투자 대상 주식 정보 가져오기
        status_text.text(f"📊 {invest_stock} 주가 정보를 가져오는 중...")
        invest_ticker = yf.Ticker(invest_stock)
        
        progress_bar.progress(60)
        
        # 3. 투자 시뮬레이션 실행
        status_text.text("💰 투자 시뮬레이션 실행 중...")
        
        total_shares_bought = 0.0
        total_invested_amount = 0.0  # 결과 통화 기준
        investments = []
        
        for dividend_date, dividend_per_share in recent_dividends.items():
            dividend_date_str = dividend_date.strftime('%Y-%m-%d')
            
            try:
                # 배당금 계산 (배당주 통화 기준)
                total_dividend_original = dividend_per_share * shares_count
                
                # 환율 가져오기
                exchange_rate = get_exchange_rate(
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
                invest_data = invest_ticker.history(start=dividend_date_str, period='5d')
                
                if len(invest_data) > 0:
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
                    
            except Exception as e:
                st.warning(f"⚠️ {dividend_date_str} 데이터 처리 중 오류: {str(e)}")
        
        progress_bar.progress(80)
        
        # 4. 현재 주가 및 결과 계산
        status_text.text("📈 현재 주가 정보 가져오는 중...")
        current_data = invest_ticker.history(period='1d')
        current_price = current_data['Close'].iloc[-1]
        
        # 계산 (모두 결과 통화 기준)
        average_price = total_invested_amount / total_shares_bought if total_shares_bought > 0 else 0
        current_value = total_shares_bought * current_price
        profit_loss = current_value - total_invested_amount
        profit_loss_pct = (profit_loss / total_invested_amount) * 100 if total_invested_amount > 0 else 0
        
        progress_bar.progress(100)
        status_text.text("✅ 시뮬레이션 완료!")
        
        # 결과 표시
        st.success("🎉 시뮬레이션이 성공적으로 완료되었습니다!")
        
        # 환전 정보 표시
        if dividend_currency != invest_currency:
            avg_exchange_rate = sum(inv['exchange_rate'] for inv in investments) / len(investments)
            st.info(f"💱 **평균 환율**: 1 {dividend_currency} = {avg_exchange_rate:.4f} {invest_currency}")
        
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
        
        # 차트 섹션
        if dividend_stock == invest_stock:
            st.subheader("📊 배당 재투자 현황 차트")
        else:
            st.subheader("📊 투자 현황 차트")
        
        # 투자 데이터 준비
        df_investments = pd.DataFrame(investments)
        
        # 탭으로 차트 분리
        if dividend_stock == invest_stock:
            tab1, tab2 = st.tabs(["📈 누적 재투자량", "📊 재투자 효과"])
        else:
            tab1, tab2, tab3 = st.tabs(["📈 누적 주식 보유량", "📊 주가 비교", "💱 환율 변화"])
        
        with tab1:
            fig_cumulative = go.Figure()
            fig_cumulative.add_trace(go.Scatter(
                x=df_investments['date'],
                y=df_investments['cumulative_shares'],
                mode='lines+markers',
                name=f'누적 {invest_stock} 보유량',
                line=dict(color='#1f77b4', width=3)
            ))
            fig_cumulative.update_layout(
                title=f"누적 {invest_stock} 주식 보유량 변화" if dividend_stock != invest_stock else f"{dividend_stock} 배당 재투자로 인한 보유량 증가",
                xaxis_title="날짜",
                yaxis_title="보유 주식 수",
                hovermode='x unified'
            )
            st.plotly_chart(fig_cumulative, use_container_width=True)
        
        with tab2:
            if dividend_stock == invest_stock:
                # 같은 종목인 경우: 재투자 효과 차트
                fig_reinvest = go.Figure()
                
                # 원래 보유량 (고정)
                original_shares_line = [shares_count] * len(df_investments)
                fig_reinvest.add_trace(go.Scatter(
                    x=df_investments['date'],
                    y=original_shares_line,
                    mode='lines',
                    name=f'원래 보유량 ({shares_count}주)',
                    line=dict(color='red', width=2, dash='dash')
                ))
                
                # 재투자로 늘어난 총 보유량
                total_shares_line = [shares_count + cum_shares for cum_shares in df_investments['cumulative_shares']]
                fig_reinvest.add_trace(go.Scatter(
                    x=df_investments['date'],
                    y=total_shares_line,
                    mode='lines+markers',
                    name='재투자 후 총 보유량',
                    line=dict(color='green', width=3)
                ))
                
                fig_reinvest.update_layout(
                    title=f"{dividend_stock} 배당 재투자 효과",
                    xaxis_title="날짜",
                    yaxis_title="총 보유 주식 수",
                    hovermode='x unified'
                )
                st.plotly_chart(fig_reinvest, use_container_width=True)
                
                # 재투자 효과 요약
                final_total_shares = shares_count + total_shares_bought
                reinvest_increase_pct = (total_shares_bought / shares_count) * 100
                st.info(f"📈 **재투자 효과**: 원래 {shares_count}주 → 현재 {final_total_shares:.2f}주 (+{reinvest_increase_pct:.2f}% 증가)")
                
            else:
                # 다른 종목인 경우: 주가 비교 차트
                fig_price = go.Figure()
                fig_price.add_trace(go.Scatter(
                    x=df_investments['date'],
                    y=df_investments['stock_price'],
                    mode='lines+markers',
                    name=f'{invest_stock} 매수가',
                    line=dict(color='#ff7f0e', width=2)
                ))
                fig_price.add_hline(
                    y=average_price, 
                    line_dash="dash", 
                    line_color="red",
                    annotation_text=f"평균단가: {result_symbol}{average_price:.2f}"
                )
                fig_price.add_hline(
                    y=current_price, 
                    line_dash="dash", 
                    line_color="green",
                    annotation_text=f"현재가: {result_symbol}{current_price:.2f}"
                )
                fig_price.update_layout(
                    title=f"{invest_stock} 주가 변화 및 매수가 비교",
                    xaxis_title="날짜",
                    yaxis_title=f"주가 ({result_symbol})",
                    hovermode='x unified'
                )
                st.plotly_chart(fig_price, use_container_width=True)
        
        # 환율 차트 (교차 투자인 경우에만 표시)
        if dividend_stock != invest_stock and dividend_currency != invest_currency:
            with tab3:
                fig_exchange = go.Figure()
                fig_exchange.add_trace(go.Scatter(
                    x=df_investments['date'],
                    y=df_investments['exchange_rate'],
                    mode='lines+markers',
                    name=f'{dividend_currency}/{invest_currency} 환율',
                    line=dict(color='#2ca02c', width=2)
                ))
                
                avg_rate = sum(df_investments['exchange_rate']) / len(df_investments)
                fig_exchange.add_hline(
                    y=avg_rate,
                    line_dash="dash", 
                    line_color="orange",
                    annotation_text=f"평균 환율: {avg_rate:.4f}"
                )
                
                fig_exchange.update_layout(
                    title=f"{dividend_currency} → {invest_currency} 환율 변화",
                    xaxis_title="날짜",
                    yaxis_title="환율",
                    hovermode='x unified'
                )
                st.plotly_chart(fig_exchange, use_container_width=True)
        
        # 상세 투자 내역 테이블
        st.subheader("📋 상세 투자 내역")
        
        # 테이블 데이터 준비
        display_df = df_investments.copy()
        display_df['배당일'] = display_df['dividend_date']
        display_df['거래일'] = display_df['trade_date']
        display_df['주당배당금'] = display_df['dividend_per_share_original'].apply(
            lambda x: f"{dividend_symbol}{x:.4f}"
        )
        
        if dividend_currency != invest_currency:
            display_df['환율'] = display_df['exchange_rate'].apply(lambda x: f"{x:.4f}")
            display_df['배당금(원화)'] = display_df['total_dividend_original'].apply(
                lambda x: f"{dividend_symbol}{x:,.2f}"
            )
            display_df['배당금(변환)'] = display_df['total_dividend_converted'].apply(
                lambda x: f"{result_symbol}{x:,.2f}"
            )
        else:
            display_df['총배당금'] = display_df['total_dividend_converted'].apply(
                lambda x: f"{result_symbol}{x:,.2f}"
            )
        
        display_df['매수가'] = display_df['stock_price'].apply(
            lambda x: f"{result_symbol}{x:,.2f}"
        )
        display_df['매수주식수'] = display_df['shares_bought'].apply(lambda x: f"{x:.6f}")
        display_df['누적보유'] = display_df['cumulative_shares'].apply(lambda x: f"{x:.6f}")
        
        # 테이블 컬럼 선택
        if dividend_currency != invest_currency:
            table_columns = ['배당일', '거래일', '주당배당금', '환율', '배당금(원화)', '배당금(변환)', '매수가', '매수주식수', '누적보유']
        else:
            table_columns = ['배당일', '거래일', '주당배당금', '총배당금', '매수가', '매수주식수', '누적보유']
        
        st.dataframe(
            display_df[table_columns],
            use_container_width=True
        )
        
        # 다운로드 버튼
        csv = df_investments.to_csv(index=False)
        st.download_button(
            label="📥 투자 내역 CSV 다운로드",
            data=csv,
            file_name=f"{dividend_stock}_to_{invest_stock}_investment_history.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"❌ 오류가 발생했습니다: {str(e)}")
        st.info("티커 심볼이 올바른지 확인하고 다시 시도해주세요.")
    
    finally:
        progress_bar.empty()
        status_text.empty()

else:
    # 초기 화면 - 간단한 안내 메시지만
    st.info("💡 **Tip**: 위의 투자 설정을 입력하고 시뮬레이션을 실행해보세요! 왼쪽 사이드바에서 예시와 티커 입력 방법을 확인하실 수 있습니다.")

# 푸터
st.markdown("---")
st.markdown("💡 **Tip**: 다양한 배당주와 성장주 조합을 테스트해보세요!")
