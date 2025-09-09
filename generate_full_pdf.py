from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Create PDF
pdf_file = "/mnt/data/TradingPlan_5_10EMA_Strategy.pdf"
doc = SimpleDocTemplate(pdf_file, pagesize=A4)
styles = getSampleStyleSheet()
story = []

# Title
title_style = styles["Title"]
story.append(Paragraph("Trading Plan – 5/10 EMA + Stoch + Daily S/R", title_style))
story.append(Spacer(1, 12))

# Section 1: Market Scan
story.append(Paragraph("<b>1. Market Scan (Daily Close)</b>", styles["Heading2"]))
market_scan = [
    ["[ ] Have I marked today’s key support & resistance?"],
    ["[ ] Are the 5 EMA & 10 EMA aligned (uptrend / downtrend)?"],
    ["[ ] Is the Stochastic Oscillator confirming (crossing up from oversold for buys, down from overbought for sells)?"]
]
t = Table(market_scan, colWidths=[450])
t.setStyle(TableStyle([("FONT", (0,0), (-1,-1), "Helvetica", 10), ("ALIGN", (0,0), (-1,-1), "LEFT")]))
story.append(t)
story.append(Spacer(1, 12))

# Section 2: Trade Setup Rules
story.append(Paragraph("<b>2. Trade Setup Rules</b>", styles["Heading2"]))
story.append(Paragraph("<b>Buy Setup</b>", styles["Heading3"]))
buy_points = [
    ["- Price above both EMAs"],
    ["- Retrace into daily support zone or EMAs"],
    ["- Stoch turning up from oversold"],
    ["- Entry: next daily open or limit order at support"],
    ["- SL: below support"],
    ["- TP: next resistance / 2R"]
]
t = Table(buy_points, colWidths=[450])
story.append(t)
story.append(Spacer(1, 8))

story.append(Paragraph("<b>Sell Setup</b>", styles["Heading3"]))
sell_points = [
    ["- Price below both EMAs"],
    ["- Retrace into daily resistance zone or EMAs"],
    ["- Stoch turning down from overbought"],
    ["- Entry: next daily open or limit order at resistance"],
    ["- SL: above resistance"],
    ["- TP: next support / 2R"]
]
t = Table(sell_points, colWidths=[450])
story.append(t)from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Create PDF
pdf_file = "/mnt/data/TradingPlan_5_10EMA_Strategy.pdf"
doc = SimpleDocTemplate(pdf_file, pagesize=A4)
styles = getSampleStyleSheet()
story = []

# Title
title_style = styles["Title"]
story.append(Paragraph("Trading Plan – 5/10 EMA + Stoch + Daily S/R", title_style))
story.append(Spacer(1, 12))

# Section 1: Market Scan
story.append(Paragraph("<b>1. Market Scan (Daily Close)</b>", styles["Heading2"]))
market_scan = [
    ["[ ] Have I marked today’s key support & resistance?"],
    ["[ ] Are the 5 EMA & 10 EMA aligned (uptrend / downtrend)?"],
    ["[ ] Is the Stochastic Oscillator confirming (crossing up from oversold for buys, down from overbought for sells)?"]
]
t = Table(market_scan, colWidths=[450])
t.setStyle(TableStyle([("FONT", (0,0), (-1,-1), "Helvetica", 10), ("ALIGN", (0,0), (-1,-1), "LEFT")]))
story.append(t)
story.append(Spacer(1, 12))

# Section 2: Trade Setup Rules
story.append(Paragraph("<b>2. Trade Setup Rules</b>", styles["Heading2"]))
story.append(Paragraph("<b>Buy Setup</b>", styles["Heading3"]))
buy_points = [
    ["- Price above both EMAs"],
    ["- Retrace into daily support zone or EMAs"],
    ["- Stoch turning up from oversold"],
    ["- Entry: next daily open or limit order at support"],
    ["- SL: below support"],
    ["- TP: next resistance / 2R"]
]
t = Table(buy_points, colWidths=[450])
story.append(t)
story.append(Spacer(1, 8))

story.append(Paragraph("<b>Sell Setup</b>", styles["Heading3"]))
sell_points = [
    ["- Price below both EMAs"],
    ["- Retrace into daily resistance zone or EMAs"],
    ["- Stoch turning down from overbought"],
    ["- Entry: next daily open or limit order at resistance"],
    ["- SL: above resistance"],
    ["- TP: next support / 2R"]
]
t = Table(sell_points, colWidths=[450])
story.append(t)
story.append(Spacer(1, 12))

# Section 3: Trade Management
story.append(Paragraph("<b>3. Trade Management</b>", styles["Heading2"]))
management = [
    ["[ ] Risk per trade = max 1–2% of equity"],
    ["[ ] Stop loss always beyond structure"],
    ["[ ] Exit partial at 1R (optional), let rest run to target"],
    ["[ ] No more than X trades open at once"]
]
t = Table(management, colWidths=[450])
story.append(t)
story.append(Spacer(1, 12))

# Section 4: Daily Review Routine
story.append(Paragraph("<b>4. Daily Review Routine</b>", styles["Heading2"]))
review = [
    ["[ ] Mark fresh S/R zones"],
    ["[ ] Check EMA trend bias"],
    ["[ ] Note which pairs meet setup conditions"],
    ["[ ] Plan next day’s watchlist"],
    ["[ ] Log decisions in journal (even if no trades)"]
]
t = Table(review, colWidths=[450])
story.append(t)
story.append(PageBreak())

# Flowchart (as preformatted text)
story.append(Paragraph("<b>Flowchart (Decision Process)</b>", styles["Heading2"]))
flowchart_text = """
Daily Close
   ↓
Mark S/R levels
   ↓
Check EMA alignment (5 vs 10)
   ↓
Trend clear?
   ↓ Yes                      No → Wait
Check Stochastic (OB/OS cross?)
   ↓
Price near S/R zone?
   ↓ Yes                      No → Wait
Setup valid
   ↓
Plan entry at open + set SL & TP
   ↓
Log & prep watchlist
"""
story.append(Paragraph(f"<pre>{flowchart_text}</pre>", ParagraphStyle('Code', fontName="Courier", fontSize=9, leading=12)))

# Build PDF
doc.build(story)
pdf_file

story.append(Spacer(1, 12))

# Section 3: Trade Management
story.append(Paragraph("<b>3. Trade Management</b>", styles["Heading2"]))
management = [
    ["[ ] Risk per trade = max 1–2% of equity"],
    ["[ ] Stop loss always beyond structure"],
    ["[ ] Exit partial at 1R (optional), let rest run to target"],
    ["[ ] No more than X trades open at once"]
]
t = Table(management, colWidths=[450])
story.append(t)
story.append(Spacer(1, 12))

# Section 4: Daily Review Routine
story.append(Paragraph("<b>4. Daily Review Routine</b>", styles["Heading2"]))
review = [
    ["[ ] Mark fresh S/R zones"],
    ["[ ] Check EMA trend bias"],
    ["[ ] Note which pairs meet setup conditions"],
    ["[ ] Plan next day’s watchlist"],
    ["[ ] Log decisions in journal (even if no trades)"]
]
t = Table(review, colWidths=[450])
story.append(t)
story.append(PageBreak())

# Flowchart (as preformatted text)
story.append(Paragraph("<b>Flowchart (Decision Process)</b>", styles["Heading2"]))
flowchart_text = """
Daily Close
   ↓
Mark S/R levels
   ↓
Check EMA alignment (5 vs 10)
   ↓
Trend clear?
   ↓ Yes                      No → Wait
Check Stochastic (OB/OS cross?)
   ↓
Price near S/R zone?
   ↓ Yes                      No → Wait
Setup valid
   ↓
Plan entry at open + set SL & TP
   ↓
Log & prep watchlist
"""
story.append(Paragraph(f"<pre>{flowchart_text}</pre>", ParagraphStyle('Code', fontName="Courier", fontSize=9, leading=12)))

# Build PDF
doc.build(story)
pdf_file
