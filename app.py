import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, date
import plotly.graph_objects as go
from typing import Tuple, Optional, List, Dict

# 상수 정의
DEFAULT_DIVIDEND_STOCK = "JEPQ"
DEFAULT_INVEST_STOCK = "AMZN"
DEFAULT_START_DATE = date(2025, 1, 1)
DEFAULT_SHARES = 1000

EXCHANGE_RATE_TICKERS = {
    ('USD', 'KRW'): 'USDKRW=X',
    ('KRW', 'USD'): 'KRWUSD=X',
}

CURRENCY_SYMBOLS = {
    'KRW': '₩',
    'USD': '$'
}

# 페이지 설정
st.set_page_config(
    page_title="배당금 재투자 시뮬레이션",
    page_icon="💰",
    layout="wide"
)

class DividendReinvestmentSimulator:
    """배당금 재투자 시뮬레이션 클래스"""
    
    def __init__(self, dividend_ticker: str, invest_ticker: str, start_date: date, shares: int):
        self.dividend_ticker = dividend_ticker
        self.invest_ticker = invest_ticker
        self.start_date = start_date
        self.shares = shares
        
    @st.cache_resource
    def get_stock_info(_self, ticker_symbol: str) -> Tuple[Optional[yf.Ticker], Optional[str]]:
        """주식 정보 및 통화 정보 가져오기"""
        try:
            ticker = yf.Ticker(ticker_symbol)
            # info 호출을 최소화하여 API 부하 줄임
            info = ticker.info
            currency = info.get('currency', 'USD')  # 기본값 USD로 설정
            return ticker, currency
        except Exception as e:
            st.error(f"티커 {ticker_symbol} 정보를 가져오는데 실패했습니다: {str(e)}")
            return None, None

    @st.cache_data(ttl=3600)
    def get_exchange_rate(_self, from_currency: str, to_currency: str, trade_date: datetime) -> float:
        """환율 정보 가져오기"""
        if from_currency == to_currency:
            return 1.0
        
        rate_ticker = EXCHANGE_RATE_TICKERS.get((from_currency, to_currency))
        if not rate_ticker:
            st.warning(f"⚠️ {from_currency}→{to_currency} 환율 정보가 없습니다. 기본값 1.0 적용")
            return 1.0

        try:
            rate_data = yf.Ticker(rate_ticker).history(
                start=trade_date.strftime('%Y-%m-%d'), 
                period='5d'
            )
            if not rate_data.empty:
                return float(rate_data['Close'].iloc[0])
        except Exception as e:
            st.warning(f"⚠️ 환율 정보 조회 실패: {str(e)}")
        
        return 1.0

    def get_dividends(self, ticker: yf.Ticker) -> pd.Series:
        """배당금 내역 가져오기"""
        try:
            dividends = ticker.dividends
            recent_dividends = dividends[dividends.index.date >= self.start_date]
            return recent_dividends
        except Exception as e:
            st.error(f"배당 내역을 가져오는데 실패했습니다: {str(e)}")
            return pd.Series()

    def simulate_investments(self, dividend_ticker: yf.Ticker, invest_ticker: yf.Ticker, 
                           dividend_currency: str, invest_currency: str, 
                           dividends: pd.Series) -> List[Dict]:
        """투자 시뮬레이션 실행"""
        investments = []
        total_shares = 0.0
        
        for dividend_date_utc, dividend_per_share in dividends.items():
            dividend_date = dividend_date_utc.tz_convert(None)
            
            # 투자 주식의 해당 날짜 주가 조회
            try:
                invest_data = invest_ticker.history(
                    start=dividend_date.strftime('%Y-%m-%d'), 
                    period='5d'
                )
                if invest_data.empty:
                    st.warning(f"⚠️ {dividend_date.strftime('%Y-%m-%d')} 주가 데이터 없음")
                    continue
                    
                invest_price = float(invest_data['Close'].iloc[0])
                actual_trade_date = invest_data.index[0].tz_convert(None)
                
            except Exception as e:
                st.warning(f"⚠️ 주가 데이터 조회 실패: {str(e)}")
                continue

            # 배당금 계산 및 환율 적용
            total_dividend = dividend_per_share * self.shares
            exchange_rate = self.get_exchange_rate(dividend_currency, invest_currency, actual_trade_date)
            converted_amount = total_dividend * exchange_rate
            
            # 매수 가능한 주식 수 계산
            shares_bought = converted_amount / invest_price
            total_shares += shares_bought
            
            investments.append({
                'dividend_date': dividend_date.strftime('%Y-%m-%d'),
                'trade_date': actual_trade_date.strftime('%Y-%m-%d'),
                'dividend_per_share': dividend_per_share,
                'total_dividend': total_dividend,
                'exchange_rate': exchange_rate,
                'converted_amount': converted_amount,
                'stock_price': invest_price,
                'shares_bought': shares_bought,
                'cumulative_shares': total_shares,
                'date': actual_trade_date  # 차트용
            })
            
        return investments

    def calculate_final_results(self, investments: List[Dict], invest_ticker: yf.Ticker) -> Dict:
        """최종 결과 계산"""
        if not investments:
            return {}
            
        try:
            current_price_data = invest_ticker.history(period='1d')
            if current_price_data.empty:
                raise ValueError("현재 주가 데이터를 가져올 수 없습니다")
                
            current_price = float(current_price_data['Close'].iloc[-1])
            
            total_invested = sum(inv['converted_amount'] for inv in investments)
            total_shares = investments[-1]['cumulative_shares']
            avg_price = total_invested / total_shares if total_shares > 0 else 0
            current_value = total_shares * current_price
            profit_loss = current_value - total_invested
            profit_loss_pct = (profit_loss / total_invested) * 100 if total_invested > 0 else 0
            
            return {
                'total_invested': total_invested,
                'total_shares': total_shares,
                'avg_price': avg_price,
                'current_price': current_price,
                'current_value': current_value,
                'profit_loss': profit_loss,
                'profit_loss_pct': profit_loss_pct,
                'investment_count': len(investments)
            }
            
        except Exception as e:
            st.error(f"최종 결과 계산 실패: {str(e)}")
            return {}

def create_ui_components():
    """UI 컴포넌트 생성"""
    # 제목 및 설명
    st.title("💰 배당금 재투자 시뮬레이션")
    st.markdown("""
    **배당금을 모두 재투자했다면?**  
    배당주 보유 시 받은 배당금을  
    특정 주식에 재투자하는 시뮬레이션    
    (소숫점 단위 투자 포함)
    """)
    # 사이드바
    create_sidebar()
    # 입력 파라미터
    st.subheader("📊 투자 설정")
    
    # 4행 1열 배열로 변경 (세로 배치)
    dividend_stock = st.text_input(
        "배당주 티커",
        value=DEFAULT_DIVIDEND_STOCK,
        placeholder="예: JEPQ, SCHD, VYM"
    ).upper().strip()
    
    invest_stock = st.text_input(
        "재투자 주식 티커",
        value=DEFAULT_INVEST_STOCK,
        placeholder="예: AMZN, AAPL, MSFT"
    ).upper().strip()

    start_date = st.date_input(
        "시작 날짜",
        value=DEFAULT_START_DATE,
        max_value=date.today()
    )
    
    shares_count = st.number_input(
        "보유 주식 수",
        min_value=1,
        max_value=1000000,
        value=DEFAULT_SHARES,
        step=100
    )
    
    return dividend_stock, invest_stock, start_date, shares_count
# 상수에 UI 데이터 추가
TICKER_EXAMPLES = {
    "미국주식/ETF": "<br> JEPQ, SCHD, AAPL, MSFT",
    "한국주식": "<br> 005930.KS (삼성전자),<br>000660.KS (SK하이닉스)"
    
}

EXAMPLE_RESULT = {
    "stock_combo": "JEPQ 1000주 → AMZN 재투자",
    "period": "2025.01.01~08.27 기준",
    "dividend_count": "7회 배당 ($3,630)",
    "shares_owned": "AMZN 17.5주 보유",
    "return_rate": "+10.01% 수익률"
}

def create_info_box(content: str, bg_color: str = "#e3f2fd", border_color: str = "#1976d2") -> str:
    """정보 박스 HTML 생성"""
    return f"""
    <div style="background-color: {bg_color}; padding: 15px; border-radius: 8px; 
                border-left: 4px solid {border_color}; margin: 10px 0;">
        {content}
    </div>
    """

def create_sidebar():
    """사이드바 생성"""
    st.sidebar.header("🎯 예시 결과")
    st.sidebar.markdown(f"""
    **{EXAMPLE_RESULT['stock_combo']}**
    ({EXAMPLE_RESULT['period']})

    - 📊 {EXAMPLE_RESULT['dividend_count']}  
    - 💎 {EXAMPLE_RESULT['shares_owned']}  
    - 📈 {EXAMPLE_RESULT['return_rate']}
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.header("💡 사용 가이드")
    
    # 티커 예시를 동적으로 생성
    ticker_content = '<h4 style="color: #1565c0; margin-top: 0; font-size: 16px;">📝 티커 입력 예시:</h4>'
    ticker_content += '<div style="color: #424242; line-height: 1.6;">'
    
    for category, examples in TICKER_EXAMPLES.items():
        ticker_content += f'<strong>• {category}:</strong> {examples}<br>'
    
    ticker_content += '</div>'
    
    st.sidebar.markdown(
        create_info_box(ticker_content), 
        unsafe_allow_html=True
    )
    
    st.sidebar.markdown("---")
    st.sidebar.header("📊 환율 기준")
    
    # 환율 정보 박스
    exchange_content = '<div style="color: #4a148c; font-weight: 500;">📈 Yahoo Finance 실시간 환율 적용</div>'
    st.sidebar.markdown(
        create_info_box(exchange_content, "#f3e5f5", "#7b1fa2"), 
        unsafe_allow_html=True
    )

def display_results(results: Dict, investments: List[Dict], invest_stock: str, 
                   invest_currency: str, dividend_currency: str):
    """결과 표시"""
    if not results:
        return
        
    currency_symbol = CURRENCY_SYMBOLS.get(invest_currency, '$')
    
    # 메트릭 표시
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "💵 총 투자금액",
            f"{currency_symbol}{results['total_invested']:,.2f}",
            f"{results['investment_count']}회 투자"
        )
    with col2:
        st.metric(
            f"📊 보유 {invest_stock}",
            f"{results['total_shares']:.6f}주",
            f"평균 {currency_symbol}{results['avg_price']:,.2f}"
        )
    with col3:
        st.metric(
            "💎 현재 가치",
            f"{currency_symbol}{results['current_value']:,.2f}",
            f"현재가 {currency_symbol}{results['current_price']:,.2f}"
        )
    with col4:
        st.metric(
            "📈 손익",
            f"{currency_symbol}{results['profit_loss']:,.2f}",
            f"{results['profit_loss_pct']:+.2f}%"
        )

    # 차트 표시
    display_charts(investments, invest_stock, results, currency_symbol)
    
    # 상세 내역 표시
    display_investment_details(investments, dividend_currency, invest_currency, currency_symbol)

def display_charts(investments: List[Dict], invest_stock: str, results: Dict, currency_symbol: str):
    """차트 표시"""
    st.subheader("📊 투자 현황 차트")
    df = pd.DataFrame(investments)
    df.set_index('date', inplace=True)
    
    tab1, tab2 = st.tabs(["📈 누적 보유량", "📊 주가 비교"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['cumulative_shares'],
            mode='lines+markers',
            name=f'누적 {invest_stock} 보유량',
            line=dict(color='#1f77b4', width=3)
        ))
        fig.update_layout(
            title=f"누적 {invest_stock} 보유량 변화",
            xaxis_title="날짜",
            yaxis_title="보유 주식 수"
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['stock_price'],
            mode='lines+markers',
            name=f'{invest_stock} 매수가',
            line=dict(color='#ff7f0e', width=2)
        ))
        fig.add_hline(
            y=results['avg_price'], 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"평균단가: {currency_symbol}{results['avg_price']:,.2f}"
        )
        fig.add_hline(
            y=results['current_price'], 
            line_dash="dash", 
            line_color="green",
            annotation_text=f"현재가: {currency_symbol}{results['current_price']:,.2f}"
        )
        fig.update_layout(
            title=f"{invest_stock} 주가 변화",
            xaxis_title="날짜",
            yaxis_title=f"주가 ({currency_symbol})"
        )
        st.plotly_chart(fig, use_container_width=True)

def display_investment_details(investments: List[Dict], dividend_currency: str, 
                             invest_currency: str, currency_symbol: str):
    """상세 투자 내역 표시"""
    st.subheader("📋 상세 투자 내역")
    
    df = pd.DataFrame(investments)
    
    # 표시용 데이터 포맷팅
    display_columns = {
        '배당일': df['dividend_date'],
        '거래일': df['trade_date'],
        '주당배당금': df['dividend_per_share'].apply(
            lambda x: f"${x:.4f}" if dividend_currency == 'USD' else f"₩{x:,.0f}"
        ),
        '투자금액': df['converted_amount'].apply(lambda x: f"{currency_symbol}{x:,.2f}"),
        '매수가': df['stock_price'].apply(lambda x: f"{currency_symbol}{x:,.2f}"),
        '매수주식수': df['shares_bought'].apply(lambda x: f"{x:.6f}"),
        '누적보유': df['cumulative_shares'].apply(lambda x: f"{x:.6f}")
    }
    
    # 환율 정보 추가 (다른 통화인 경우)
    if dividend_currency != invest_currency:
        display_columns['환율'] = df['exchange_rate'].apply(lambda x: f"{x:,.2f}")
    
    display_df = pd.DataFrame(display_columns)
    st.dataframe(display_df, use_container_width=True)

    # CSV 다운로드
    csv = display_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        "📥 투자 내역 CSV 다운로드",
        data=csv,
        file_name=f"dividend_reinvestment_{df.iloc[0]['dividend_date']}_{df.iloc[-1]['dividend_date']}.csv",
        mime="text/csv"
    )

def main():
    """메인 함수"""
    # UI 컴포넌트 생성
    dividend_stock, invest_stock, start_date, shares_count = create_ui_components()

    # 실행 버튼
    if st.button("🚀 시뮬레이션 실행", type="primary", use_container_width=True):
        
        # 입력값 검증
        if not dividend_stock or not invest_stock:
            st.error("❌ 배당주와 재투자 주식 티커를 모두 입력해주세요.")
            return

        # 시뮬레이터 생성 및 실행
        simulator = DividendReinvestmentSimulator(dividend_stock, invest_stock, start_date, shares_count)
        
        with st.spinner("📊 시뮬레이션 실행 중..."):
            try:
                # 1. 주식 정보 가져오기
                dividend_ticker, dividend_currency = simulator.get_stock_info(dividend_stock)
                invest_ticker, invest_currency = simulator.get_stock_info(invest_stock)
                
                if not dividend_ticker or not invest_ticker:
                    st.error("❌ 유효하지 않은 티커입니다.")
                    return

                # 2. 배당 내역 가져오기
                dividends = simulator.get_dividends(dividend_ticker)
                if dividends.empty:
                    st.warning(f"⚠️ {start_date} 이후 {dividend_stock}의 배당 내역이 없습니다.")
                    return

                # 3. 투자 시뮬레이션 실행
                investments = simulator.simulate_investments(
                    dividend_ticker, invest_ticker, dividend_currency, invest_currency, dividends
                )
                
                if not investments:
                    st.warning("⚠️ 시뮬레이션할 투자 내역이 없습니다.")
                    return

                # 4. 최종 결과 계산
                results = simulator.calculate_final_results(investments, invest_ticker)
                if not results:
                    return

                # 5. 결과 표시
                st.success("🎉 시뮬레이션 완료!")
                
                if dividend_stock == invest_stock:
                    st.info("✨ **동일 종목 재투자**")
                
                display_results(results, investments, invest_stock, invest_currency, dividend_currency)

            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")
                st.info("티커와 날짜를 확인하고 다시 시도해주세요.")
    
    else:
        st.info("💡 투자 설정을 입력하고 시뮬레이션을 실행해보세요!")

    st.markdown("---")
    st.markdown("💡 **Tip**: 다양한 배당주와 성장주 조합을 테스트해보세요!")

if __name__ == "__main__":
    main()
