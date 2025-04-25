import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import xlsxwriter
import seaborn as sns
from fpdf import FPDF
from io import BytesIO

def export_excel_report(data, output_path="load_report.xlsx"):
    # Create Excel writer using xlsxwriter backend
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        wb = writer.book

        # Write metadata sheet
        metadata = pd.DataFrame({
            "Field": ["Substation ID", "Start Date", "End Date", "Data Points", "Mean % Imbalance", "Cumulative Energy Delivered"],
            "Value": [
                data['substation_id'],
                data['start_date'],
                data['end_date'],
                data['data_points'],
                data['imbalance'],
                data['energy']
            ]
        })
        metadata.to_excel(writer, sheet_name="Summary", index=False)

        # Format metadata
        summary_ws : xlsxwriter.Workbook.worksheet_class = writer.sheets["Summary"]
        summary_ws.set_column("A:A", 30)
        summary_ws.set_column("B:B", 30)
        bold = wb.add_format({"bold": True})
        summary_ws.write("A1", "Field", bold)
        summary_ws.write("B1", "Value", bold)

        summary_ws.write_string(10, 0, "Characterised Load Conditions", bold)
        summary_ws.write_string(11, 0, "Base P load (kW)")
        summary_ws.write_number(11, 1, data['pload'])
        summary_ws.write_string(12, 0, "Base Q load (kVAr)")
        summary_ws.write_number(12, 1, data['qload'])
        summary_ws.write_string(13, 0, "P90 P load (kW)")
        summary_ws.write_number(13, 1, data['90pload'])
        summary_ws.write_string(14, 0, "P90 Q load (kVAr)")
        summary_ws.write_number(14, 1, data['90qload'])

        # Write monthly stats
        monthly_stats: pd.DataFrame = np.round(data['monthly_stats'], 3)
        monthly_stats.to_excel(writer, sheet_name="Monthly Stats", index=False)

        stats_ws = writer.sheets["Monthly Stats"]
        for i, col in enumerate(monthly_stats.columns):
            stats_ws.set_column(i, i, 15)
        for col_num, value in enumerate(monthly_stats.columns.values):
            stats_ws.write(0, col_num, value, bold)

            # Create a chart object
        phase_chart = wb.add_chart({'type': 'line'})

        # Configure the chart using worksheet cell ranges
        phase_chart.add_series({
            'name':       'Phase A',
            'categories': f"='Monthly Stats'!$A$2:$A${len(monthly_stats)+1}", 
            'values':     f"='Monthly Stats'!$R$2:$R${len(monthly_stats)+1}", 
        })

        phase_chart.add_series({
            'name':       'Phase B',
            'categories': f"='Monthly Stats'!$A$2:$A${len(monthly_stats)+1}", 
            'values':     f"='Monthly Stats'!$V$2:$V${len(monthly_stats)+1}", 
        })

        phase_chart.add_series({
            'name':       'Phase C',
            'categories': f"='Monthly Stats'!$A$2:$A${len(monthly_stats)+1}", 
            'values':     f"='Monthly Stats'!$Z$2:$Z${len(monthly_stats)+1}", 
        })

        phase_chart.set_title({'name': '99th Percentile Currents'})
        phase_chart.set_x_axis({'name': 'Year-Month'})
        phase_chart.set_y_axis({'name': 'Mean'})

        # Insert the chart into the worksheet
        stats_ws.insert_chart(f'B{len(monthly_stats)+3}', phase_chart)


        energy_chart = wb.add_chart({'type': 'line'})

        # Configure the chart using worksheet cell ranges
        energy_chart.add_series({
            'name':       'Energy',
            'categories': f"='Monthly Stats'!$A$2:$A${len(monthly_stats)+1}", 
            'values':     f"='Monthly Stats'!$E$2:$E${len(monthly_stats)+1}", 
        })

        energy_chart.set_title({'name': 'Monthly Energy Delivered'})
        energy_chart.set_x_axis({'name': 'Year-Month'})
        energy_chart.set_y_axis({'name': 'Energy Delivered'})

        # Insert the chart into the worksheet
        stats_ws.insert_chart(f'H{len(monthly_stats)+3}', energy_chart)

        # # Plot chart and insert it as image
        # fig, ax = plt.subplots(figsize=(8, 4))


        #         # Ensure mean is numeric
        # monthly_stats["mean"] = pd.to_numeric(monthly_stats["mean"], errors="coerce")

        # # Convert year_month to string or datetime (whichever you prefer)
        # monthly_stats["year_month"] = monthly_stats["year_month"].astype(str)

        # sns.lineplot(x="year_month", y="mean", data=monthly_stats, marker="o", ax=ax)
        # ax.set_title("Monthly Mean Apparent Power")
        # ax.tick_params(axis='x', rotation=45)

        # img_data = BytesIO()
        # fig.savefig(img_data, format='png', bbox_inches='tight')
        # img_data.seek(0)
        # plt.close(fig)

        # stats_ws.insert_image("G2", "chart.png", {"image_data": img_data, "x_scale": 0.8, "y_scale": 0.8})

# ---------- Plot Charts ----------
def plot_monthly_apparent_power(df):
    df = df.copy()
    df['year_month'] = pd.to_datetime(df['year_month'], errors='coerce')
    df['year_month'] = df['year_month'].dt.strftime('%Y-%m')

    plt.figure(figsize=(10, 4))
    sns.lineplot(x='year_month', y='mean', data=df, marker='o')
    plt.title("Monthly Mean Apparent Power")
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png')
    plt.close()  # Important: free memory
    buf.seek(0)
    return buf

def plot_seasonal_bar(seasonal_stats):
    seasons = list(seasonal_stats.keys())
    means = [s['Mean'] for s in seasonal_stats.values()]
    plt.figure(figsize=(6, 4))
    sns.barplot(x=seasons, y=means)
    plt.title("Seasonal Mean Apparent Power")
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return buf

# ---------- PDF Generation ----------
class PDFReport(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(None, 10, "LOAD CHARACTERISATION REPORT", ln=1, align='C')

    def chapter_title(self, title):
        self.set_font("Arial", "B", 12)
        self.ln(5)
        self.cell(None, 10, title, ln=1, align='L')

    def chapter_text(self, text):
        self.set_font("Arial", "", 10)
        self.multi_cell(180, 5, text)
        self.ln(5)

    def insert_image(self, img_buf, w=180):
        self.ln(5)
        self.image(img_buf, x=None, y=None, w=w)

    def header(self):
        # Logo
        self.image('logo_pb.png', 10, 8, 33)
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Move to the right
        self.cell(80)
        # Title
        self.cell(30, 10, 'Title', 1, 0, 'C')
        # Line break
        self.ln(20)

    # Page footer
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')
