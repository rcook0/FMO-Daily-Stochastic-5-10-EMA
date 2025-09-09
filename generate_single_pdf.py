from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Create condensed PDF
pdf_file_condensed = "/mnt/data/TradingPlan_5_10EMA_Strategy_Condensed.pdf"
doc = SimpleDocTemplate(pdf_file_condensed, pagesize=A4)
styles = getSampleStyleSheet()
story = []

# Title
title_style = styles["Title"]
story.append(Paragraph("Condensed Trading Plan – 5/10 EMA + Stoch + Daily S/R", title_style))
story.append(Spacer(1, 12))

# Combine into compact checklist
condensed = [
    ["<b>Market Scan (Daily Close)</b>"],
    ["[ ] Mark key support & resistance"],
    ["[ ] Check 5/10 EMA alignment (trend bias)"],
    ["[ ] Confirm Stoch (OB/OS cross)"],

    ["<b>Buy Setup</b>"],
    ["- Price above EMAs, retrace to support/EMAs"],
    ["- Stoch up from oversold"],
    ["- SL below support, TP next resistance/2R"],

    ["<b>Sell Setup</b>"],
    ["- Price below EMAs, retrace to resistance/EMAs"],
    ["- Stoch down from overbought"],
    ["- SL above resistance, TP next support/2R"],

    ["<b>Management</b>"],
    ["[ ] Risk 1–2% max"],
    ["[ ] SL beyond structure"],
    ["[ ] Optional partial at 1R"],
    ["[ ] Max open trades = X"],

    ["<b>Daily Review</b>"],
    ["[ ] Update S/R zones, EMA trend, watchlist"],
    ["[ ] Journal decisions (even no trade)"]
]
t = Table(condensed, colWidths=[500])
t.setStyle(TableStyle([("FONT", (0,0), (-1,-1), "Helvetica", 9),
                       ("ALIGN", (0,0), (-1,-1), "LEFT"),
                       ("VALIGN", (0,0), (-1,-1), "TOP")]))
story.append(t)
story.append(Spacer(1, 16))

# Flowchart (small version)
flowchart_text = """
Daily Close → Mark S/R → EMA aligned?
Yes → Check Stoch (OB/OS cross?) → Price near S/R?
Yes → Valid setup → Plan entry (SL+TP) → Log & prep
No at any step → Wait
"""
story.append(Paragraph("<b>Flowchart (Quick Reference)</b>", styles["Heading2"]))
story.append(Paragraph(f"<pre>{flowchart_text}</pre>", ParagraphStyle('Code', fontName="Courier", fontSize=8, leading=10)))

# Build condensed PDF
doc.build(story)
pdf_file_condensed
