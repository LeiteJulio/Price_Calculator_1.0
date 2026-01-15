import streamlit as st
import pandas as pd
import io
#from fpdf import FPDF
import datetime
import altair as alt
import os

# 1. Configuration & Exchange Rates
RATES = {"USD": 0.92, "EUR": 1.0, "GBP": 1.18, "CNY": 0.13}

st.set_page_config(page_title="Freight Procurement Hub", layout="wide")




@st.cache_data
def load_data():
    try:
        data = pd.read_csv("master_rates.csv")
        # Ensure File_Month is treated as a string for sorting
        data['File_Month'] = data['File_Month'].astype(str)
        return data
    except FileNotFoundError:
        return None


df = load_data()

# --- HELPER FUNCTIONS FOR DOWNLOADS ---
# 
# def to_excel(df_to_export):
#     output = io.BytesIO()
#     with pd.ExcelWriter(output, engine='openpyxl') as writer:
#         df_to_export.to_excel(writer, index=False, sheet_name='Freight_Quote')
#     return output.getvalue()
# 
# 
# def create_pdf(df_to_export, corridor_name):
#     pdf = FPDF()
#     pdf.add_page()
#     pdf.set_font("Arial", 'B', 16)
#     pdf.cell(200, 10, txt=f"Freight Quote: {corridor_name}", ln=True, align='C')
#     pdf.set_font("Arial", size=10)
#     pdf.ln(10)
#     for index, row in df_to_export.iterrows():
#         line = f"{row['Supplier']} | {row['Container']} | {row['Mode']} | Total: EUR {row['Total All-In (EUR)']}"
#         pdf.cell(200, 8, txt=line, ln=True)
#     return pdf.output(dest='S').encode('latin-1')


# --- CALCULATION LOGIC ---
def calc_total(row, haz_status):
    # Origin Cost
    o_col = 'O_Cost_Haz' if haz_status else 'O_Cost_NonHaz'
    o = row[o_col] * RATES.get(row['O_Curr'], 1.0)
    # Ocean Cost (IMO only if Haz)
    imo = row['Sea_IMO'] if haz_status else 0
    s = (row['Sea_Base'] + imo) * RATES.get(row['Sea_Curr'], 1.0)
    # Destination Cost
    d_col = 'D_Cost_Haz' if haz_status else 'D_Cost_NonHaz'
    d = row[d_col] * RATES.get(row['D_Curr'], 1.0)
    return round(o + s + d, 2)




# --- MAIN APP INTERFACE ---
if df is None:
    st.error("⚠️ 'master_rates.csv' not found. Please run your prep script first.")
else:

    # --- TOP HEADER WITH LOGO ---
    col1, col2 = st.columns([1, 4])  # Adjust ratios (1:4) to fit your logo size

    with col1:
        # Use your actual logo file name here
        # use_container_width=True ensures it fits the column nicely
        try:
            st.image("era_logo.png", width=150)
        except:
            st.info("Logo Placeholder")  # Prevents error if file is missing

    with col2:
        st.title("🚢 TFL XXX - Sea Freight Price Calculator",text_alignment='center')
        st.caption("version 202512")

    st.divider()



    # 1. SIDEBAR: GLOBAL FILTERS
    with st.sidebar:
        st.header("Global Filters")

        # 1. Create a helper function to convert '202601' -> 'Jan 2026'
        def format_month(month_str):
            date_obj = datetime.datetime.strptime(str(month_str), "%Y%m")
            return date_obj.strftime("%b %Y")

        # 2. Prepare the list of available months (codes)
        available_month_codes = sorted(df['File_Month'].unique(), reverse=True)

        # 3. Create a mapping for the selectbox: { "Jan 2026": "202601", ... }
        month_mapping = {format_month(m): m for m in available_month_codes}

        # 4. Show the user-friendly names, but capture the code in 'selected_month'
        selected_display = st.selectbox("📅 Select Month", list(month_mapping.keys()), index=0)
        selected_month = month_mapping[selected_display]  # This turns 'Jan 2026' back into '202601'

        selected_dest = st.selectbox("🎯 Select Destination (corridor)", sorted(df['Destination'].unique()))

        st.divider()
        st.info(f"Currently viewing data for: **{selected_display}**")
        st.divider()
        if os.path.exists("master_rates.csv"):
            mtime = os.path.getmtime("master_rates.csv")
            last_update = datetime.datetime.fromtimestamp(mtime).strftime('%d %b %Y, %H:%M')
            st.caption(f"📅 **Database Refresh:** {last_update}")

        # # Determine the most recent month automatically
        # available_months = sorted(df['File_Month'].unique(), reverse=True)
        # latest_month = available_months[0]
        #
        # selected_month = st.selectbox("📅 Select Analysis Month", available_months, index=0)
        # selected_dest = st.selectbox("🎯 Select Destination (corridor)", sorted(df['Destination'].unique()))
        #
        # st.divider()
        # st.info(f"Currently viewing data for: **{selected_month}**")

    # Filter data for the chosen month and corridor
    corridor_data = df[(df['Destination'] == selected_dest) & (df['File_Month'] == selected_month)].copy()

    if not corridor_data.empty:
        corridor_data['Price_NonHaz'] = corridor_data.apply(lambda r: calc_total(r, False), axis=1)
        corridor_data['Price_Haz'] = corridor_data.apply(lambda r: calc_total(r, True), axis=1)

        # 2. COMPARISON TABLES
        st.header(f"All-in Prices per container for :green[{selected_dest} - {selected_display}]", divider='blue')


        def display_grid(data, price_col, title, color):
            st.subheader(title)

            # Create the pivot table
            pivot = data.pivot_table(index='Container', columns=['Mode', 'Supplier'], values=price_col, aggfunc='min')

            # Custom highlighting logic per mode
            def highlight_min_per_mode(row):
                styles = ['' for _ in row]
                modes = row.index.get_level_values(0).unique()

                for mode in modes:
                    mode_series = row[mode]
                    if not mode_series.dropna().empty:
                        min_val = mode_series.min()
                        for i, (m, s) in enumerate(row.index):
                            if m == mode and row.iloc[i] == min_val:
                                # Highlight only the background color
                                styles[i] = f'background-color: {color}; color: black;'
                return styles

            # Display using standard dataframe with the mode-specific highlighting
            st.dataframe(
                pivot.style.apply(highlight_min_per_mode, axis=1).format("€{:,.2f}"),
                use_container_width=True
            )


        display_grid(corridor_data, 'Price_NonHaz', "🟢 Non-Dangerous Goods", "lightgreen")
        display_grid(corridor_data, 'Price_Haz', "🔴 Dangerous Goods", "lightsalmon")

        # # 2. COMPARISON TABLES
        # st.header(f"All-in Prices per container for :green[{selected_dest} - {selected_display}]",divider='blue')
        #
        #
        # def display_grid(data, price_col, title, color):
        #     st.subheader(title)
        #     pivot = data.pivot_table(index='Container', columns=['Mode', 'Supplier'], values=price_col, aggfunc='min')
        #     st.dataframe(pivot.style.highlight_min(axis=1, color=color).format("€{:,.2f}"), use_container_width=True)
        #
        #
        # display_grid(corridor_data, 'Price_NonHaz', "🟢 Non-Dangerous Goods", "lightgreen")
        # display_grid(corridor_data, 'Price_Haz', "🔴 Dangerous Goods", "lightsalmon")

        # 3. SUPPLIER CATALOG (DRILL DOWN) - Filtered by Global Month
        with st.expander("🔍 View/Hide full price list per supplier"):
            sel_sup = st.selectbox("Select Supplier to view their full catalog:",
                                   ["Choose..."] + list(df['Supplier'].unique()))

            if sel_sup != "Choose...":
                # Apply filter: Match the Supplier AND the Global Month from the sidebar
                catalog_data = df[(df['Supplier'] == sel_sup) & (df['File_Month'] == selected_month)].copy()

                if not catalog_data.empty:
                    st.write(f"Showing all quoted corridors for **{sel_sup}** in **{selected_display}**:")
                    # Display the data
                    st.dataframe(catalog_data, hide_index=True, use_container_width=True)
                else:
                    st.warning(f"No data found for {sel_sup} in {selected_display}.")

        # --- 4. NARROWED RESULTS & EXPORT ---
        st.divider()
        st.header("📋 Filtered Prices per features")

        c1, c2, c3 = st.columns(3)
        with c1:
            f_size = st.multiselect("Select Container Size", corridor_data['Container'].unique())
        with c2:
            f_mode = st.multiselect("Select Transport Mode", corridor_data['Mode'].unique())
        with c3:
            f_haz = st.radio("Dangerous Goods?", ["Non-Dangerous", "Dangerous"], horizontal=True)

        # Apply filters to the current month's data
        narrowed = corridor_data.copy()
        if f_size: narrowed = narrowed[narrowed['Container'].isin(f_size)]
        if f_mode: narrowed = narrowed[narrowed['Mode'].isin(f_mode)]

        price_field = 'Price_Haz' if f_haz == "Dangerous" else 'Price_NonHaz'


        def pretty_date(month_str):
            return datetime.datetime.strptime(str(month_str), "%Y%m").strftime("%b %Y")

        if not narrowed.empty:

            with st.expander("🔍 Hide/View Prices for the selected filters",expanded=True):
                # Display the filtered current results
                export_df = narrowed[
                    ['Supplier', 'Container', 'Mode', 'Carrier', 'Transit_Days', 'Validity_Internal', price_field]].copy()
                export_df = export_df.rename(columns={price_field: 'Total All-In (EUR)'}).sort_values('Total All-In (EUR)')

                st.dataframe(export_df.style.format({'Total All-In (EUR)': '€{:,.2f}'}), use_container_width=True,
                             hide_index=True)

                # Download Buttons
                #col_dl1, col_dl2 = st.columns(2)
                #with col_dl1:
                #    st.download_button("📥 Excel Export", to_excel(export_df), f"Quote_{selected_dest}.xlsx")
                #with col_dl2:
                #    st.download_button("📥 PDF Export", create_pdf(export_df, selected_dest), f"Quote_{selected_dest}.pdf")



            # --- 5. DYNAMIC TREND ANALYSIS (With Month Selection & DG Labels) ---
            st.divider()
            with st.expander("🔍 Hide/View detailed Price Evolution for the selected filters", expanded=True):
                st.subheader(f"📈 Detailed Price Evolution")

                # 1. Month Filter (Start with everything selected)
                all_months_available = sorted(df['File_Month'].unique())
                # Format them for the user (Jan 2026) but keep the codes for logic
                month_options = {pretty_date(m): m for m in all_months_available}

                selected_months_pretty = st.multiselect(
                    "Select Months to Display",
                    options=list(month_options.keys()),
                    default=list(month_options.keys())
                )
                selected_month_codes = [month_mapping[m] for m in selected_months_pretty]

                # 2. Filter history data based on ALL selections
                history_data = df[df['Destination'] == selected_dest].copy()

                # Filter by selected months
                history_data = history_data[history_data['File_Month'].isin(selected_month_codes)]

                # Filter by Container and Mode
                if f_size: history_data = history_data[history_data['Container'].isin(f_size)]
                if f_mode: history_data = history_data[history_data['Mode'].isin(f_mode)]

                # 3. Calculation & Series Labeling
                is_haz_bool = True if f_haz == "Dangerous" else False
                haz_tag = "DG" if is_haz_bool else "NDG"

                history_data['Total_EUR'] = history_data.apply(lambda r: calc_total(r, is_haz_bool), axis=1)

                # Include the Haz Tag in the series label for the legend
                history_data['Series_Label'] = (
                        history_data['Supplier'] + " | " +
                        history_data['Container'] + " | " +
                        history_data['Mode'] + " | " +
                        haz_tag
                )

                # 4. Sorting and Pivoting
                history_data['Month_Label'] = history_data['File_Month'].apply(pretty_date)
                history_data = history_data.sort_values('File_Month')

                if not history_data.empty:
                    trend_pivot = history_data.pivot_table(
                        index='Month_Label',
                        columns='Series_Label',
                        values='Total_EUR',
                        aggfunc='min',
                        sort=False
                    )

                    # 5. Plotting with Altair
                    import altair as alt

                    # --- STEP E: PLOT WITH ENHANCED LEGEND ---
                    import altair as alt

                    chart_data = trend_pivot.reset_index().melt('Month_Label', var_name='Option', value_name='Price')

                    line_chart = alt.Chart(chart_data).mark_line(point=True, strokeWidth=3).encode(
                        x=alt.X('Month_Label:N', sort=None, title='Month', axis=alt.Axis(labelAngle=0)),
                        y=alt.Y('Price:Q', title='Total EUR', scale=alt.Scale(zero=False)),
                        # We use alt.Color to define the legend properties specifically
                        color=alt.Color('Option:N',
                                        title='Transport Configuration',
                                        legend=alt.Legend(
                                            orient='bottom',  # Moves legend below the chart
                                            columns=2,  # Splits items into 2 columns to save height
                                            labelFontSize=12,  # Makes text larger
                                            titleFontSize=13,  # Makes legend header larger
                                            symbolSize=100,  # Makes the color icons larger
                                            padding=10,
                                            direction='vertical'
                                        )
                                        ),
                        tooltip=['Month_Label', 'Option', 'Price']
                    ).properties(
                        height=450  # Give the chart enough vertical space
                    ).configure_view(
                        strokeWidth=0
                    ).configure_legend(
                        labelLimit=0,  # Prevents long names from being cut off with "..."
                        titleLimit=0
                    ).interactive()

                    st.altair_chart(line_chart, use_container_width=True)


                    # line_chart = alt.Chart(chart_data).mark_line(point=True).encode(
                    #     x=alt.X('Month_Label:N', sort=None, title='Month', axis=alt.Axis(labelAngle=0)),
                    #     y=alt.Y('Price:Q', title='Total EUR', scale=alt.Scale(zero=False)),
                    #     color=alt.Color('Option:N', title='Supplier | Container | Mode | Status'),
                    #     tooltip=['Month_Label', 'Option', 'Price']
                    # ).interactive()
                    #
                    # st.altair_chart(line_chart, use_container_width=True)
                else:
                    st.warning("No data available for the selected month range.")



        else:
            st.warning("No rates match your filters for the trend analysis.")




    else:
        st.warning(f"No data found for {selected_dest} in {selected_month}.")