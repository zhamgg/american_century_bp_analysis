import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="American Century Boardingpass Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom CSS styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5em;
        color: #003366;
        text-align: center;
        margin-bottom: 30px;
    }
    .section-header {
        font-size: 1.8em;
        color: #2c3e50;
        margin-top: 30px;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .info-text {
        font-size: 1em;
        color: #7f8c8d;
    }
    .highlight {
        font-weight: bold;
        color: #2980b9;
    }
</style>
""", unsafe_allow_html=True)

# Title and description
st.markdown("<div class='main-header'>American Century Boardingpass Dashboard</div>", unsafe_allow_html=True)
st.markdown("""
This dashboard provides metrics for the onboarding of American Century plans. It shows the percentage of plans in each status,
and breaks down status by Advisor, Recordkeeper, and NSCC Firm.
""")

# File upload section
uploaded_file = st.file_uploader("Upload the boardingpass Excel file", type=["xlsx"])

# Function to load and process data
@st.cache_data
def load_and_process_data(file):
    """Load and process the boardingpass Excel file"""
    try:
        df = pd.read_excel(file)
        
        # Filter to American Century plans
        ac_plans = df[df['Fund Name'].str.contains('American Century', case=False, na=False)]
        
        # If no American Century plans found, check if we have other American funds
        if len(ac_plans) == 0:
            st.warning("No plans with 'American Century' in Fund Name found. Showing all plans with 'American' or 'Century' in the Fund Name instead.")
            ac_plans = df[df['Fund Name'].str.contains('American|Century', case=False, na=False)]
        
        if len(ac_plans) == 0:
            st.error("No relevant plans found in the dataset.")
            return None
            
        # Convert date columns to datetime
        date_columns = ['Request Date', 'Estimated Funding Date', 'Report As of Date']
        for col in date_columns:
            if col in ac_plans.columns:
                ac_plans[col] = pd.to_datetime(ac_plans[col], errors='coerce')
                
        return ac_plans
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

# Only process data if file is uploaded
if uploaded_file is not None:
    # Load and process data
    df = load_and_process_data(uploaded_file)
    
    if df is not None:
        # Show data refresh date
        if 'Report As of Date' in df.columns and not df['Report As of Date'].isna().all():
            latest_date = df['Report As of Date'].max()
            st.info(f"Data as of: {latest_date.strftime('%Y-%m-%d')}")
        
        # Sidebar filters
        st.sidebar.markdown("## Filters")
        
        # Date range filter
        if 'Request Date' in df.columns and not df['Request Date'].isna().all():
            min_date = df['Request Date'].min().date()
            max_date = df['Request Date'].max().date()
            
            date_range = st.sidebar.date_input(
                "Request Date Range",
                [min_date, max_date],
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                df_filtered = df[(df['Request Date'].dt.date >= start_date) & 
                              (df['Request Date'].dt.date <= end_date)]
            else:
                df_filtered = df
        else:
            df_filtered = df
        
        # Advisor Firm filter
        if 'Advisor Firm Name' in df.columns:
            advisor_firms = sorted(df['Advisor Firm Name'].unique())
            selected_advisors = st.sidebar.multiselect(
                "Advisor Firms",
                options=advisor_firms,
                default=[]
            )
            
            if selected_advisors:
                df_filtered = df_filtered[df_filtered['Advisor Firm Name'].isin(selected_advisors)]
        
        # Recordkeeper filter
        if 'Recordkeeper Name' in df.columns:
            recordkeepers = sorted(df['Recordkeeper Name'].unique())
            selected_recordkeepers = st.sidebar.multiselect(
                "Recordkeepers",
                options=recordkeepers,
                default=[]
            )
            
            if selected_recordkeepers:
                df_filtered = df_filtered[df_filtered['Recordkeeper Name'].isin(selected_recordkeepers)]
        
        # Calculate key metrics
        total_plans = len(df_filtered['Plan Name'].unique())
        total_requests = len(df_filtered)
        
        # Calculate status metrics
        status_counts = df_filtered['Request Status'].value_counts()
        status_pct = (status_counts / total_requests * 100).round(1)
        
        status_detail_counts = df_filtered['Status Detail'].value_counts()
        status_detail_pct = (status_detail_counts / total_requests * 100).round(1)
        
        # Completion metrics - plans in Ready to Trade status
        completed_requests = df_filtered[df_filtered['Status Detail'].str.contains('Ready to Trade', case=False, na=False)]
        completion_rate = len(completed_requests) / total_requests * 100 if total_requests > 0 else 0
        
        # Display key metrics
        st.markdown("<div class='section-header'>Key Metrics</div>", unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.metric("Total Plans", total_plans)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col2:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.metric("Total Requests", total_requests)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col3:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.metric("Completed Requests", len(completed_requests))
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col4:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.metric("Completion Rate", f"{completion_rate:.1f}%")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Display status distribution
        st.markdown("<div class='section-header'>Status Distribution</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Create pie chart for Request Status
            fig1 = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Distribution by Request Status",
                color_discrete_sequence=px.colors.qualitative.Bold,
                labels={'label': 'Status', 'value': 'Count'},
                hole=0.4
            )
            
            # Add percentages to hover data
            fig1.update_traces(
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent:.1%}<extra></extra>',
                textinfo='label+percent'
            )
            
            st.plotly_chart(fig1, use_container_width=True)
            
        with col2:
            # Create bar chart for Status Detail
            fig2 = px.bar(
                x=status_detail_counts.index,
                y=status_detail_counts.values,
                title="Distribution by Status Detail",
                color=status_detail_counts.index,
                labels={'x': 'Status Detail', 'y': 'Count'},
                text=status_detail_pct.values.astype(str) + '%'
            )
            
            fig2.update_layout(showlegend=False, xaxis_tickangle=-45)
            
            st.plotly_chart(fig2, use_container_width=True)
        
        # Status by different dimensions
        st.markdown("<div class='section-header'>Status by Dimension</div>", unsafe_allow_html=True)
        
        # Create tabs for each dimension
        tab1, tab2, tab3 = st.tabs(["By Advisor Firm", "By Recordkeeper", "By NSCC Firm"])
        
        # Function to create stacked bar chart by dimension
        def create_dimension_chart(dimension_col, title):
            if dimension_col in df_filtered.columns:
                # Group by dimension and status
                grouped = df_filtered.groupby([dimension_col, 'Request Status']).size().unstack(fill_value=0)
                
                # Calculate percentages
                pct = grouped.div(grouped.sum(axis=1), axis=0) * 100
                
                # Add total column and sort by it
                grouped['Total'] = grouped.sum(axis=1)
                sorted_data = grouped.sort_values('Total', ascending=False)
                
                # Limit to top 10 for readability
                plot_data = sorted_data.head(10)
                
                # Create stacked bar chart
                fig = go.Figure()
                
                for status in plot_data.columns:
                    if status != 'Total':
                        fig.add_trace(go.Bar(
                            x=plot_data.index,
                            y=plot_data[status],
                            name=status,
                            text=plot_data[status].apply(lambda x: f'{x}'),
                            textposition='inside'
                        ))
                
                fig.update_layout(
                    title=title,
                    barmode='stack',
                    xaxis_title=dimension_col,
                    yaxis_title='Count',
                    xaxis_tickangle=-45,
                    legend_title='Status',
                    height=500
                )
                
                return fig, sorted_data
            return None, None
        
        # Tab 1: By Advisor Firm
        with tab1:
            advisor_fig, advisor_data = create_dimension_chart('Advisor Firm Name', 'Request Status by Advisor Firm (Top 10)')
            if advisor_fig:
                st.plotly_chart(advisor_fig, use_container_width=True)
                
                # Calculate percentage distribution
                if advisor_data is not None:
                    with st.expander("View Advisor Firm Details"):
                        # Drop Total column for percentage calculation
                        advisor_pct = advisor_data.drop('Total', axis=1).div(advisor_data.drop('Total', axis=1).sum(axis=1), axis=0) * 100
                        
                        # Round percentages
                        advisor_pct = advisor_pct.round(1)
                        
                        # Add total count column
                        advisor_pct['Total Count'] = advisor_data['Total']
                        
                        st.dataframe(advisor_pct)
            else:
                st.info("Advisor Firm data not available")
        
        # Tab 2: By Recordkeeper
        with tab2:
            rk_fig, rk_data = create_dimension_chart('Recordkeeper Name', 'Request Status by Recordkeeper (Top 10)')
            if rk_fig:
                st.plotly_chart(rk_fig, use_container_width=True)
                
                if rk_data is not None:
                    with st.expander("View Recordkeeper Details"):
                        # Drop Total column for percentage calculation
                        rk_pct = rk_data.drop('Total', axis=1).div(rk_data.drop('Total', axis=1).sum(axis=1), axis=0) * 100
                        
                        # Round percentages
                        rk_pct = rk_pct.round(1)
                        
                        # Add total count column
                        rk_pct['Total Count'] = rk_data['Total']
                        
                        st.dataframe(rk_pct)
            else:
                st.info("Recordkeeper data not available")
        
        # Tab 3: By NSCC Firm
        with tab3:
            nscc_fig, nscc_data = create_dimension_chart('NSCC Firm Name', 'Request Status by NSCC Firm (Top 10)')
            if nscc_fig:
                st.plotly_chart(nscc_fig, use_container_width=True)
                
                if nscc_data is not None:
                    with st.expander("View NSCC Firm Details"):
                        # Drop Total column for percentage calculation
                        nscc_pct = nscc_data.drop('Total', axis=1).div(nscc_data.drop('Total', axis=1).sum(axis=1), axis=0) * 100
                        
                        # Round percentages
                        nscc_pct = nscc_pct.round(1)
                        
                        # Add total count column
                        nscc_pct['Total Count'] = nscc_data['Total']
                        
                        st.dataframe(nscc_pct)
            else:
                st.info("NSCC Firm data not available")
        
        # Add status transition flow if we have detailed status
        if 'Status Detail' in df_filtered.columns:
            st.markdown("<div class='section-header'>Status Progression</div>", unsafe_allow_html=True)
            
            # Create a sankey diagram of status progression
            status_order = [
                'Awaiting Signature', 
                'Account Setup', 
                'Ready to Trade'
            ]
            
            # Count plans in each status
            status_counts = {}
            for status in status_order:
                count = len(df_filtered[df_filtered['Status Detail'].str.contains(status, case=False, na=False)])
                status_counts[status] = count
            
            # Create sankey diagram data
            source = []
            target = []
            value = []
            
            # Assume progression from one status to the next
            for i in range(len(status_order)-1):
                source.append(i)
                target.append(i+1)
                # The value is the minimum of the current status count and the next one
                # This is simplified - in a real app you'd track actual plan transitions
                value.append(min(status_counts[status_order[i]], status_counts[status_order[i+1]]))
            
            # Create the figure
            flow_fig = go.Figure(data=[go.Sankey(
                node = dict(
                    pad = 15,
                    thickness = 20,
                    line = dict(color = "black", width = 0.5),
                    label = status_order,
                    color = "blue"
                ),
                link = dict(
                    source = source,
                    target = target,
                    value = value
                )
            )])
            
            flow_fig.update_layout(title_text="Plan Status Progression", font_size=12)
            
            st.plotly_chart(flow_fig, use_container_width=True)
        
        # Raw data explorer
        st.markdown("<div class='section-header'>Data Explorer</div>", unsafe_allow_html=True)
        
        with st.expander("View and Filter Raw Data"):
            # Select columns to display
            all_columns = df_filtered.columns.tolist()
            default_columns = ['Plan Name', 'Fund Name', 'Request Status', 'Status Detail', 
                               'Advisor Firm Name', 'Recordkeeper Name', 'NSCC Firm Name']
            
            # Only include default columns that actually exist in the data
            default_columns = [col for col in default_columns if col in all_columns]
            
            selected_columns = st.multiselect(
                "Select columns to display",
                options=all_columns,
                default=default_columns
            )
            
            if selected_columns:
                st.dataframe(df_filtered[selected_columns])
            else:
                st.dataframe(df_filtered)
            
            # Download option
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download filtered data as CSV",
                data=csv,
                file_name=f"american_century_boardingpass_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    # Show instructions if no file uploaded
else:
    st.info("Please upload the boardingpass Excel file to begin analysis.")
    
    st.markdown("""
    ## Instructions
    
    1. Click on the "Browse files" button above and select the boardingpass Excel file.
    2. The dashboard will automatically filter for plans with "American Century" in the Fund Name.
    3. Use the filters in the sidebar to narrow down your analysis.
    4. Explore the different tabs to see status breakdowns by Advisor, Recordkeeper, and NSCC Firm.
    5. Download filtered data as CSV for further analysis if needed.
    
    This dashboard focuses on these key metrics:
    - Percentage of plans in each status
    - Status distribution by Advisor Firm
    - Status distribution by Recordkeeper
    - Status distribution by NSCC Firm
    
    For any questions or additional metrics, please contact the analytics team.
    """)

# Footer
st.markdown("---")
st.markdown("<div class='info-text'>Data is refreshed daily. Last dashboard update: March 2025</div>", unsafe_allow_html=True)
