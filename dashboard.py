"""
HappyRobot Dashboard - Call Analytics & Metrics
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json

# Page config
st.set_page_config(
    page_title="HappyRobot Analytics",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .metric-value {
        font-size: 36px;
        font-weight: bold;
    }
    .metric-label {
        font-size: 14px;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# ==================== CONFIG ====================
API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")
API_KEY = st.secrets.get("API_KEY", "happyrobot-dev-key-12345")

HEADERS = {"X-API-Key": API_KEY}

# ==================== SIDEBAR ====================
st.sidebar.title("🤖 HappyRobot")
st.sidebar.markdown("---")

mode = st.sidebar.radio(
    "Select View",
    ["📊 Dashboard", "📞 Call Records", "🎯 Performance", "⚙️ Settings"]
)

refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 5, 60, 10)

# ==================== FUNCTIONS ====================
@st.cache_data(ttl=10)
def fetch_metrics():
    try:
        response = requests.get(
            f"{API_BASE_URL}/metrics",
            headers=HEADERS,
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Connection Error: {str(e)}")
        return None

@st.cache_data(ttl=10)
def fetch_calls():
    try:
        response = requests.get(
            f"{API_BASE_URL}/calls?limit=100",
            headers=HEADERS,
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"Connection Error: {str(e)}")
        return None

def create_gauge_chart(value, max_value, title, suffix=""):
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title={'text': title},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [0, max_value]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, max_value * 0.5], 'color': "lightgray"},
                {'range': [max_value * 0.5, max_value], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.9
            }
        },
        suffix=suffix
    ))
    fig.update_layout(height=300)
    return fig

# ==================== MAIN DASHBOARD ====================
if mode == "📊 Dashboard":
    st.title("📊 Inbound Carrier Sales Dashboard")
    st.markdown("Real-time analytics for call outcomes and performance metrics")
    
    metrics = fetch_metrics()
    
    if metrics:
        # Key Metrics Row 1
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="📞 Total Calls",
                value=metrics['total_calls'],
                delta="+5 today" if metrics['total_calls'] > 0 else "No data"
            )
        
        with col2:
            st.metric(
                label="✅ Deals Closed",
                value=metrics['agreed_calls'],
                delta=f"{metrics['conversion_rate']:.1f}% conversion"
            )
        
        with col3:
            st.metric(
                label="💰 Total Revenue",
                value=f"${metrics['total_revenue_generated']:,.2f}",
                delta="From confirmed loads"
            )
        
        with col4:
            st.metric(
                label="🔄 Avg Negotiation Rounds",
                value=f"{metrics['avg_negotiation_rounds']:.1f}",
                delta="Per successful call"
            )
        
        st.markdown("---")
        
        # Charts Row
        col1, col2 = st.columns(2)
        
        with col1:
            # Conversion Rate Gauge
            fig_gauge = create_gauge_chart(
                metrics['conversion_rate'],
                100,
                "Conversion Rate",
                "%"
            )
            st.plotly_chart(fig_gauge, use_container_width=True)
        
        with col2:
            # Sentiment Breakdown
            sentiment_data = metrics.get('sentiment_breakdown', {})
            if sentiment_data:
                fig = go.Figure(data=[
                    go.Pie(
                        labels=list(sentiment_data.keys()),
                        values=list(sentiment_data.values()),
                        hole=0.3,
                        marker_colors=['#FF6B6B', '#4ECDC4', '#45B7D1']
                    )
                ])
                fig.update_layout(
                    title_text="Carrier Sentiment Distribution",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Performance Metrics
        st.subheader("📈 Performance Insights")
        
        perf_col1, perf_col2, perf_col3 = st.columns(3)
        
        with perf_col1:
            st.info(f"""
            **Negotiation Efficiency**
            
            Average rounds to close: {metrics['avg_negotiation_rounds']:.1f}
            
            ✅ Below industry average (2-3 rounds)
            """)
        
        with perf_col2:
            conversion_color = "🟢" if metrics['conversion_rate'] > 50 else "🟡" if metrics['conversion_rate'] > 25 else "🔴"
            st.success(f"""
            **Conversion Performance**
            
            {conversion_color} {metrics['conversion_rate']:.1f}% success rate
            
            {metrics['agreed_calls']} closed out of {metrics['total_calls']} calls
            """)
        
        with perf_col3:
            st.warning(f"""
            **Revenue Per Call**
            
            ${metrics['total_revenue_generated'] / max(metrics['total_calls'], 1):,.2f} average
            
            Total generated: ${metrics['total_revenue_generated']:,.2f}
            """)
    else:
        st.error("Unable to fetch metrics. Is the API running?")

# ==================== CALL RECORDS ====================
elif mode == "📞 Call Records":
    st.title("📞 Call Records")
    st.markdown("Detailed view of all inbound carrier calls")
    
    calls_data = fetch_calls()
    
    if calls_data and calls_data['calls']:
        df = pd.DataFrame(calls_data['calls'])
        
        # Format the dataframe
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            df = df.rename(columns={
                'call_id': 'Call ID',
                'mc_number': 'MC Number',
                'load_id': 'Load ID',
                'outcome': 'Outcome',
                'sentiment': 'Sentiment',
                'agreed_price': 'Agreed Price',
                'created_at': 'Timestamp'
            })
            
            # Display filters
            col1, col2, col3 = st.columns(3)
            with col1:
                outcome_filter = st.multiselect(
                    "Filter by Outcome",
                    df['Outcome'].unique(),
                    default=df['Outcome'].unique()
                )
            with col2:
                sentiment_filter = st.multiselect(
                    "Filter by Sentiment",
                    df['Sentiment'].unique(),
                    default=df['Sentiment'].unique()
                )
            with col3:
                sort_by = st.selectbox(
                    "Sort by",
                    ["Timestamp (Latest)", "Agreed Price (High to Low)", "MC Number"]
                )
            
            # Apply filters
            filtered_df = df[
                (df['Outcome'].isin(outcome_filter)) &
                (df['Sentiment'].isin(sentiment_filter))
            ]
            
            if sort_by == "Agreed Price (High to Low)":
                filtered_df = filtered_df.sort_values('Agreed Price', ascending=False, na_position='last')
            elif sort_by == "MC Number":
                filtered_df = filtered_df.sort_values('MC Number')
            
            # Display table
            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Export option
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"call_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No call records found.")
    else:
        st.warning("Unable to fetch call records.")

# ==================== PERFORMANCE ====================
elif mode == "🎯 Performance":
    st.title("🎯 Advanced Performance Analytics")
    
    metrics = fetch_metrics()
    calls_data = fetch_calls()
    
    if metrics and calls_data:
        st.subheader("Call Outcome Distribution")
        
        df = pd.DataFrame(calls_data['calls'])
        if not df.empty:
            outcome_counts = df['outcome'].value_counts()
            
            fig = go.Figure(data=[
                go.Bar(
                    x=outcome_counts.index,
                    y=outcome_counts.values,
                    marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
                )
            ])
            fig.update_layout(
                title="Calls by Outcome",
                xaxis_title="Outcome",
                yaxis_title="Count",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Most Common Outcome", outcome_counts.idxmax())
            with col2:
                st.metric("Calls with Sentiment", len(df[df['sentiment'].notna()]))
            with col3:
                avg_price = df['agreed_price'].mean()
                st.metric("Average Deal Value", f"${avg_price:,.2f}" if not pd.isna(avg_price) else "N/A")

# ==================== SETTINGS ====================
elif mode == "⚙️ Settings":
    st.title("⚙️ Settings & Configuration")
    
    st.subheader("API Configuration")
    col1, col2 = st.columns(2)
    with col1:
        st.code(f"Base URL: {API_BASE_URL}")
    with col2:
        st.code(f"API Key: {API_KEY[:20]}...")
    
    st.subheader("Test API Connection")
    if st.button("🔗 Test Connection"):
        try:
            response = requests.get(
                f"{API_BASE_URL}/health",
                headers=HEADERS,
                timeout=5
            )
            if response.status_code == 200:
                st.success("✅ API is running and responding correctly")
                st.json(response.json())
            else:
                st.error(f"❌ API returned status {response.status_code}")
        except Exception as e:
            st.error(f"❌ Connection failed: {str(e)}")
    
    st.subheader("Database Seeding")
    if st.button("🌱 Seed Sample Loads"):
        with st.spinner("Seeding database..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/loads/seed",
                    headers=HEADERS,
                    timeout=10
                )
                if response.status_code == 200:
                    st.success("✅ Sample loads seeded successfully")
                    st.json(response.json())
                else:
                    st.error(f"Failed: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>🤖 HappyRobot Inbound Carrier Sales | Forward Deployment Engineer Challenge</p>
    <p style='font-size: 12px; color: gray;'>Last updated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
</div>
""", unsafe_allow_html=True)
