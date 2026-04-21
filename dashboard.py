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
API_BASE_URL = st.secrets.get("API_BASE_URL", "https://happyrobot-fde-production-bf9f.up.railway.app")
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
        return None
    except Exception as e:
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
        return None
    except Exception as e:
        return None

def create_gauge_chart(value, max_value, title, suffix=""):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
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
        }
    ))
    fig.update_layout(height=300)
    return fig

# ==================== MAIN DASHBOARD ====================
if mode == "📊 Dashboard":
    st.title("📊 Inbound Carrier Sales Dashboard")
    st.markdown("Real-time analytics for call outcomes and business performance")
    
    metrics = fetch_metrics()
    calls_data = fetch_calls()
    
    if metrics:
        df_calls = pd.DataFrame(calls_data['calls']) if calls_data and calls_data.get('calls') else pd.DataFrame()
        
        # Calculate Average Deal Value dynamically
        avg_deal_value = 0
        if not df_calls.empty and 'agreed_price' in df_calls.columns:
            agreed_deals = df_calls[df_calls['outcome'] == 'agreed']
            if not agreed_deals.empty:
                avg_deal_value = agreed_deals['agreed_price'].astype(float).mean()

        # Key Metrics Row 1 (Now with 5 columns!)
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("📞 Total Calls", metrics.get('total_calls', 0))
        with col2:
            st.metric("✅ Deals Closed", metrics.get('agreed_calls', 0), f"{metrics.get('conversion_rate', 0):.1f}% conv")
        with col3:
            st.metric("💰 Total Revenue", f"${metrics.get('total_revenue_generated', 0):,.2f}")
        with col4:
            st.metric("📈 Avg Deal Value", f"${avg_deal_value:,.2f}" if avg_deal_value > 0 else "$0.00")
        with col5:
            st.metric("🔄 Avg Rounds Negotiation", f"{metrics.get('avg_negotiation_rounds', 0):.1f}")
        
        st.markdown("---")
        
        # ==========================================
        # 💡 AUTOMATED BUSINESS INSIGHTS ENGINE
        # ==========================================
        st.subheader("💡 Actionable Insights & Recommendations")
        
        insight_col1, insight_col2 = st.columns(2)
        
        with insight_col1:
            conv_rate = metrics.get('conversion_rate', 0)
            if conv_rate < 30 and metrics.get('total_calls', 0) > 3:
                st.error(f"**📉 Low Conversion Alert ({conv_rate:.1f}%)**\n\n**Action:** Carriers are rejecting offers at a high rate. Consider increasing the 'Max Pay' ceiling in the negotiation logic by 5-10% to secure more capacity.")
            elif conv_rate > 75:
                st.warning(f"**📈 High Conversion Alert ({conv_rate:.1f}%)**\n\n**Action:** Carriers are accepting offers very easily. You might be leaving money on the table. Consider lowering the initial starting offer by 5% to capture more margin.")
            else:
                st.success(f"**✅ Conversion Rate Optimal ({conv_rate:.1f}%)**\n\n**Action:** Pricing is currently in the sweet spot. Maintain current guardrails.")

        with insight_col2:
            if not df_calls.empty and 'outcome' in df_calls.columns:
                lost_deals = df_calls[df_calls['outcome'] != 'agreed']
                if not lost_deals.empty:
                    most_common_loss = lost_deals['outcome'].mode()[0]
                    if most_common_loss == "no_match":
                        st.info("**🔍 High Rate of 'No Match'**\n\n**Action:** Carriers are calling in, but we don't have freight matching their equipment or lanes. We need to source more diverse freight for the loadboard.")
                    elif most_common_loss == "rejected":
                        st.error("**🛑 High Rate of Rejections**\n\n**Action:** Our final counter-offers are too low for current market conditions. Instruct human brokers to review lane averages.")
                    else:
                        st.info(f"**💬 Call Outcome Note:** Most failed calls result in `{most_common_loss}`.")
                else:
                    st.success("**🏆 Perfect Close Rate!**\n\nNo lost deals recorded yet.")
            else:
                st.info("Gathering outcome data...")
                
        st.markdown("---")
        
        # Charts Row (Now 3 Charts for maximum visual impact)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fig_gauge = create_gauge_chart(metrics.get('conversion_rate', 0), 100, "Conversion Rate", "%")
            st.plotly_chart(fig_gauge, use_container_width=True)
        
        with col2:
            sentiment_data = metrics.get('sentiment_breakdown', {})
            if sentiment_data:
                fig_sent = go.Figure(data=[go.Pie(labels=list(sentiment_data.keys()), values=list(sentiment_data.values()), hole=0.3, marker_colors=['#FF6B6B', '#4ECDC4', '#45B7D1'])])
                fig_sent.update_layout(title_text="Carrier Sentiment", height=300)
                st.plotly_chart(fig_sent, use_container_width=True)
                
        with col3:
            if not df_calls.empty and 'outcome' in df_calls.columns:
                outcome_counts = df_calls['outcome'].value_counts()
                fig_out = go.Figure(data=[go.Pie(labels=outcome_counts.index, values=outcome_counts.values, hole=0.3, marker_colors=['#2ECC71', '#E74C3C', '#F1C40F', '#95A5A6'])])
                fig_out.update_layout(title_text="Win/Loss Breakdown", height=300)
                st.plotly_chart(fig_out, use_container_width=True)
                
    else:
        st.error("Unable to fetch metrics. Is the API running?")

# ==================== CALL RECORDS ====================
elif mode == "📞 Call Records":
    st.title("📞 Call Records")
    st.markdown("Detailed view of all inbound carrier calls")
    
    calls_data = fetch_calls()
    
    if calls_data and calls_data.get('calls'):
        df = pd.DataFrame(calls_data['calls'])
        
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            df = df.rename(columns={
                'call_id': 'Call ID',
                'mc_number': 'MC Number',
                'carrier_name': 'Carrier Name',
                'load_id': 'Load ID',
                'outcome': 'Outcome',
                'sentiment': 'Sentiment',
                'agreed_price': 'Agreed Price',
                'created_at': 'Timestamp'
            })
            
            col1, col2, col3 = st.columns(3)
            with col1:
                outcome_filter = st.multiselect("Filter by Outcome", df['Outcome'].unique(), default=df['Outcome'].unique())
            with col2:
                sentiment_filter = st.multiselect("Filter by Sentiment", df['Sentiment'].dropna().unique(), default=df['Sentiment'].dropna().unique())
            with col3:
                sort_by = st.selectbox("Sort by", ["Timestamp (Latest)", "Agreed Price (High to Low)"])
            
            filtered_df = df[(df['Outcome'].isin(outcome_filter))]
            if len(sentiment_filter) > 0:
                filtered_df = filtered_df[filtered_df['Sentiment'].isin(sentiment_filter)]
            
            if sort_by == "Agreed Price (High to Low)":
                filtered_df = filtered_df.sort_values(by="Agreed Price", ascending=False)
            else:
                filtered_df = filtered_df.sort_values(by="Timestamp", ascending=False)
            
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
            
            csv = filtered_df.to_csv(index=False)
            st.download_button(label="📥 Download as CSV", data=csv, mime="text/csv")

            # ==========================================
            # 🔍 DEEP DIVE SECTION
            # ==========================================
            st.divider()
            st.subheader("🔍 Deep Dive: Call Review")
            
            call_options = filtered_df.apply(lambda x: f"{str(x['Call ID'])[:8]}... (MC: {x['MC Number']})", axis=1).tolist()
            
            if call_options:
                selected_label = st.selectbox("Select a Call to review the full transcript:", options=call_options)
                selected_idx = call_options.index(selected_label)
                call_data = filtered_df.iloc[selected_idx]
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Final Agreed Price", f"${call_data['Agreed Price']:,.2f}")
                with c2:
                    st.write(f"**Outcome:** `{call_data['Outcome']}`")
                    st.write(f"**Sentiment:** `{call_data['Sentiment']}`")
                with c3:
                    carrier_display = call_data.get('Carrier Name', 'Unknown')
                    st.write(f"**Carrier:** {carrier_display} (MC: {call_data['MC Number']})")
                    st.write(f"**Load ID:** {call_data['Load ID']}")

                st.markdown("### 📝 Full Conversation Transcript")
                
                raw_transcript = call_data.get('call_transcript') or call_data.get('transcript') or "[]"
                try:
                    messages = json.loads(raw_transcript)
                    for msg in messages:
                        role = msg.get("role", "")
                        content = msg.get("content", "")
                        
                        if not content or role == "tool":
                            continue
                            
                        if role == "assistant":
                            with st.chat_message("assistant", avatar="🤖"):
                                st.write(f"**Josh (AI):** {content}")
                        elif role == "user":
                            with st.chat_message("user", avatar="🚛"):
                                st.write(f"**Carrier:** {content}")
                except Exception as e:
                    st.info(str(raw_transcript).replace("\\n", "\n"))

# ==================== PERFORMANCE ====================
elif mode == "🎯 Performance":
    st.title("🎯 Advanced Business Analytics")
    st.markdown("Actionable intelligence for brokerage operations and margin optimization.")
    
    calls_data = fetch_calls()
    
    if calls_data and calls_data.get('calls'):
        df = pd.DataFrame(calls_data['calls'])
        
        if not df.empty:
            # 1. SETUP DATA FOR BUSINESS METRICS
            df['created_at'] = pd.to_datetime(df['created_at'])
            
            # Recreate the Load mapping so the frontend knows the origins, destinations, and target rates!
            SEED_LOADS = {
                "LOAD001": {"route": "Los Angeles, CA ➔ Chicago, IL", "target_rate": 3500},
                "LOAD002": {"route": "Houston, TX ➔ Atlanta, GA", "target_rate": 2800},
                "LOAD003": {"route": "Miami, FL ➔ New York, NY", "target_rate": 4200},
                "LOAD004": {"route": "Seattle, WA ➔ Denver, CO", "target_rate": 3100},
                "LOAD005": {"route": "Dallas, TX ➔ Phoenix, AZ", "target_rate": 2600},
            }
            
            # Map the load details into our dataframe
            df['Route'] = df['load_id'].apply(lambda x: SEED_LOADS.get(x, {}).get('route', 'Unknown Route'))
            df['Target Rate'] = df['load_id'].apply(lambda x: SEED_LOADS.get(x, {}).get('target_rate', 0))
            
            # Calculate savings only on agreed deals
            df['AI Savings'] = 0.0
            agreed_mask = df['outcome'] == 'agreed'
            df.loc[agreed_mask, 'AI Savings'] = df.loc[agreed_mask, 'Target Rate'] - df.loc[agreed_mask, 'agreed_price'].astype(float)
            
            total_savings = df['AI Savings'].sum()

            # 2. RENDER TOP MONEY METRICS
            st.subheader("💰 AI Margin Contribution")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total AI Cost Savings", f"${total_savings:,.2f}", "Added directly to margin")
            with col2:
                avg_savings = df[agreed_mask]['AI Savings'].mean() if not df[agreed_mask].empty else 0
                st.metric("Avg Savings Per Booked Load", f"${avg_savings:,.2f}")
            with col3:
                st.info("**Insight:** When AI Savings are consistently high, consider lowering target loadboard rates to capture even wider margins.")

            st.markdown("---")

            # 3. CAPACITY & LANE DEMAND
            col_lane, col_crm = st.columns(2)
            
            with col_lane:
                st.subheader("🗺️ Capacity Demand (Top Lanes)")
                st.markdown("Which routes are getting the most inbound carrier interest?")
                
                # Filter out unknown routes and count
                lane_df = df[df['Route'] != 'Unknown Route']
                if not lane_df.empty:
                    lane_counts = lane_df['Route'].value_counts().reset_index()
                    lane_counts.columns = ['Route', 'Inbound Calls']
                    
                    fig_lanes = px.bar(
                        lane_counts, 
                        x='Inbound Calls', 
                        y='Route', 
                        orientation='h',
                        color='Inbound Calls',
                        color_continuous_scale='Blues'
                    )
                    fig_lanes.update_layout(height=300, yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_lanes, use_container_width=True)
                else:
                    st.write("No lane data available yet.")

            # 4. CARRIER CRM & NETWORK HEALTH
            with col_crm:
                st.subheader("🤝 Carrier Network Health")
                st.markdown("Identify frequent callers for dedicated lane partnerships.")
                
                if 'carrier_name' in df.columns:
                    # Group by carrier to find our best partners
                    carrier_stats = df.groupby(['mc_number', 'carrier_name']).agg(
                        Total_Calls=('call_id', 'count'),
                        Deals_Won=('outcome', lambda x: (x == 'agreed').sum()),
                        Total_Spend=('agreed_price', lambda x: pd.to_numeric(x, errors='coerce').sum())
                    ).reset_index()
                    
                    carrier_stats['Win Rate'] = (carrier_stats['Deals_Won'] / carrier_stats['Total_Calls'] * 100).round(1).astype(str) + '%'
                    
                    # Clean up column names for display
                    carrier_stats = carrier_stats.rename(columns={
                        'mc_number': 'MC Number',
                        'carrier_name': 'Carrier Name'
                    }).sort_values('Total_Calls', ascending=False)
                    
                    st.dataframe(carrier_stats, use_container_width=True, hide_index=True, height=300)
                else:
                    st.write("Carrier CRM data is populating...")

        else:
            st.info("No call data available yet. Make some test calls!")
    else:
        st.error("Failed to fetch data from API.")

# ==================== SETTINGS ====================
elif mode == "⚙️ Settings":
    st.title("⚙️ Settings & Configuration")
    
    st.subheader("API Configuration")
    col1, col2 = st.columns(2)
    with col1:
        st.code(f"Base URL: {API_BASE_URL}")
    with col2:
        st.code(f"API Key: {API_KEY[:20]}...")
    
    st.subheader("Database Seeding")
    if st.button("🌱 Seed Sample Loads"):
        with st.spinner("Seeding database..."):
            try:
                response = requests.post(f"{API_BASE_URL}/loads/seed", headers=HEADERS, timeout=10)
                if response.status_code == 200:
                    st.success("✅ Sample loads seeded successfully")
                else:
                    st.error(f"Failed: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>🤖 HappyRobot Inbound Carrier Sales | Forward Deployment Engineer Challenge</p>
    <p style='font-size: 12px; color: gray;'>Built with Python, FastAPI, and Streamlit</p>
</div>
""", unsafe_allow_html=True)
