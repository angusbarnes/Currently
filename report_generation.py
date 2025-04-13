import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
from io import BytesIO

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
