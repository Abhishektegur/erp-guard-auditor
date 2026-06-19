import os
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_pdf_report(engine, violations_df, graph_path, output_pdf_path):
    # Setup document geometry (letter size, 0.75 inch margins)
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Premium Color Palette
    primary_color = colors.HexColor("#1A365D")  # Deep Navy Blue
    secondary_color = colors.HexColor("#2B6CB0") # Steel Blue
    accent_red = colors.HexColor("#C53030")      # Crimson Red
    text_dark = colors.HexColor("#2D3748")       # Charcoal
    bg_light = colors.HexColor("#EDF2F7")        # Light Gray
    
    # Custom Paragraph Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=primary_color,
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=text_dark,
        spaceAfter=8
    )
    
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=body_style,
        fontName='Helvetica-Oblique',
        fontSize=9,
        textColor=colors.HexColor("#718096")
    )
    
    story = []
    
    # ------------------ COVER HEADER ------------------
    story.append(Paragraph("ERP-GUARD COMPLIANCE AUDIT REPORT", title_style))
    story.append(Paragraph(f"System: SAP/ERP Instance Alpha  |  Audit Date: {datetime.now().strftime('%Y-%m-%d')}  |  Scope: Q2 Compliance Check", meta_style))
    story.append(Spacer(1, 15))
    
    # Draw a colored rule
    divider = Table([[""]], colWidths=[504])
    divider.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 2, primary_color),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(divider)
    story.append(Spacer(1, 15))

    # ------------------ EXECUTIVE SUMMARY ------------------
    story.append(Paragraph("1. Executive Summary", h1_style))
    
    total_txs = len(engine.logs_df)
    total_violations = len(violations_df)
    unique_violators = violations_df["user_id"].nunique() if total_violations > 0 else 0
    critical_count = len(violations_df[violations_df["risk_level"] == "CRITICAL"]) if total_violations > 0 else 0
    high_count = len(violations_df[violations_df["risk_level"] == "HIGH"]) if total_violations > 0 else 0
    
    summary_text = (
        f"This compliance audit was programmatically executed across ERP access directories and transactional ledgers. "
        f"A total of <b>{total_txs} transactions</b> and <b>{len(engine.users_df)} user accounts</b> were evaluated against "
        f"the Segregation of Duties (SoD) rule matrix. A total of <b>{total_violations} compliance violations</b> "
        f"were identified across <b>{unique_violators} unique user accounts</b>. Out of these, "
        f"<font color='#C53030'><b>{critical_count} critical risks</b></font> and <b>{high_count} high risks</b> require immediate mitigation."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 10))

    # Summary Stats Table
    stats_data = [
        ["Audit Metric", "Value", "Risk Level Classification"],
        ["Total Transactions Analyzed", str(total_txs), "Operational Baseline"],
        ["Consolidated Violations", str(total_violations), "Action Required" if total_violations > 0 else "Compliant"],
        ["Critical Severity Violations", str(critical_count), "IMMEDIATE MITIGATION" if critical_count > 0 else "None"],
        ["High Severity Violations", str(high_count), "HIGH PRIORITY" if high_count > 0 else "None"]
    ]
    
    stats_table = Table(stats_data, colWidths=[200, 104, 200])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BACKGROUND', (0,1), (-1,-1), bg_light),
        ('TEXTCOLOR', (0,1), (-1,-1), text_dark),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.white),
        ('TEXTCOLOR', (1,2), (1,3), accent_red),
        ('FONTNAME', (1,2), (1,3), 'Helvetica-Bold')
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 20))

    # ------------------ DETAILED FINDINGS ------------------
    story.append(Paragraph("2. Static Entitlements & Role Conflict Audit", h1_style))
    story.append(Paragraph(
        "Static audits inspect authorization profiles and role assignments. These identify users who hold the capability "
        "to perform conflicting activities, regardless of whether they have executed them yet.", body_style
    ))
    
    static_df = violations_df[violations_df["violation_type"] == "STATIC_SOD"]
    if static_df.empty:
        story.append(Paragraph("<i>No static SoD authorization conflicts detected.</i>", body_style))
    else:
        static_data = [["User ID", "Name", "Department", "Conflict Name", "Risk"]]
        for _, row in static_df.iterrows():
            static_data.append([
                row["user_id"],
                row["user_name"],
                row["department"],
                row["conflict_name"],
                row["risk_level"]
            ])
        
        static_table = Table(static_data, colWidths=[65, 85, 75, 219, 60])
        static_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), secondary_color),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('TEXTCOLOR', (4,1), (4,-1), accent_red),
        ]))
        story.append(static_table)
    story.append(Spacer(1, 15))

    # ------------------ TRANSACTIONAL VIOLATIONS ------------------
    story.append(Paragraph("3. Transactional Activity & Cycle Audit", h1_style))
    story.append(Paragraph(
        "Transactional audits parse chronological application logs to detect actual cross-transaction cycles "
        "executed by the same user credential within the audit period. Transaction-cycle violations represent concrete internal control failures.", body_style
    ))
    
    tx_df = violations_df[violations_df["violation_type"].isin(["TRANSACTION_CYCLE_VIOLATION", "TRANSACTION_SOD_CROSSOVER"])]
    if tx_df.empty:
        story.append(Paragraph("<i>No transactional SoD violations detected.</i>", body_style))
    else:
        tx_data = [["User ID", "Name", "Violation Type", "Details", "Risk"]]
        for _, row in tx_df.iterrows():
            # Paragraph-wrapped details to prevent table overflow
            details_para = Paragraph(row["details"], ParagraphStyle('DetailWrap', parent=styles['Normal'], fontSize=8, leading=10, textColor=text_dark))
            tx_data.append([
                row["user_id"],
                row["user_name"],
                row["violation_type"].replace("_", " "),
                details_para,
                row["risk_level"]
            ])
            
        tx_table = Table(tx_data, colWidths=[65, 80, 110, 209, 40])
        tx_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), secondary_color),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('TEXTCOLOR', (4,1), (4,-1), accent_red),
        ]))
        story.append(tx_table)
    story.append(Spacer(1, 15))

    # Page Break for clean visual presentation
    story.append(PageBreak())

    # ------------------ GHOST & TERMINATED USERS ------------------
    story.append(Paragraph("4. Account Integrity & Ghost User Audit", h1_style))
    story.append(Paragraph(
        "Account integrity audits compare transaction logs against active HR rosters. Transactions processed "
        "by unregistered accounts (ghosts) or accounts belonging to terminated employees represent major audit findings.", body_style
    ))
    
    integrity_df = violations_df[violations_df["violation_type"].isin(["GHOST_ACCOUNT_ACTIVITY", "TERMINATED_USER_ACTIVITY"])]
    if integrity_df.empty:
        story.append(Paragraph("<i>No account integrity violations detected.</i>", body_style))
    else:
        integrity_data = [["User ID", "Name", "Department", "Incident Type", "Details"]]
        for _, row in integrity_df.iterrows():
            details_para = Paragraph(row["details"], ParagraphStyle('DetailWrap2', parent=styles['Normal'], fontSize=8, leading=10, textColor=text_dark))
            integrity_data.append([
                row["user_id"],
                row["user_name"],
                row["department"],
                row["violation_type"].replace("_", " "),
                details_para
            ])
            
        integrity_table = Table(integrity_data, colWidths=[65, 80, 80, 110, 169])
        integrity_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), secondary_color),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(integrity_table)
    story.append(Spacer(1, 15))

    # ------------------ SPLIT & THRESHOLD AUDIT ------------------
    story.append(Paragraph("5. Split Transaction Threshold Audit", h1_style))
    story.append(Paragraph(
        "Split transaction audits search for sequences of purchase orders or payments made by the same user to "
        "the same vendor within a narrow time window, where each individual transaction is under the user's approval "
        "limit, but the cumulative total exceeds that limit.", body_style
    ))
    
    split_df = violations_df[violations_df["violation_type"] == "SPLIT_TRANSACTION_LIMIT_AVOIDANCE"]
    if split_df.empty:
        story.append(Paragraph("<i>No split transaction threshold avoidance patterns detected.</i>", body_style))
    else:
        split_data = [["User ID", "Name", "Department", "Details"]]
        for _, row in split_df.iterrows():
            details_para = Paragraph(row["details"], ParagraphStyle('DetailWrap3', parent=styles['Normal'], fontSize=8, leading=10, textColor=text_dark))
            split_data.append([
                row["user_id"],
                row["user_name"],
                row["department"],
                details_para
            ])
            
        split_table = Table(split_data, colWidths=[65, 90, 90, 259])
        split_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), secondary_color),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(split_table)
    story.append(Spacer(1, 15))

    # ------------------ DEPARTMENT AUDIT ------------------
    story.append(Paragraph("6. Departmental Restriction Audit", h1_style))
    story.append(Paragraph(
        "Departmental checks verify that users hold roles aligned with their specific business units. Users holding "
        "permissions outside their business context (e.g. marketing users holding ledger posting privileges) are flagged.", body_style
    ))
    
    dept_df = violations_df[violations_df["violation_type"] == "DEPARTMENT_RESTRICTION_VIOLATION"]
    if dept_df.empty:
        story.append(Paragraph("<i>No departmental restriction violations detected.</i>", body_style))
    else:
        dept_data = [["User ID", "Name", "Department", "Conflict Code", "Details"]]
        for _, row in dept_df.iterrows():
            details_para = Paragraph(row["details"], ParagraphStyle('DetailWrap4', parent=styles['Normal'], fontSize=8, leading=10, textColor=text_dark))
            dept_data.append([
                row["user_id"],
                row["user_name"],
                row["department"],
                row["conflict_id"],
                details_para
            ])
            
        dept_table = Table(dept_data, colWidths=[65, 80, 80, 110, 169])
        dept_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), secondary_color),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(dept_table)
    story.append(Spacer(1, 15))

    story.append(PageBreak())

    # ------------------ APPENDIX: VISUAL GRAPH ------------------
    story.append(Paragraph("Appendix A: Access Conflict Visualization", h1_style))
    story.append(Paragraph(
        "The graph below maps the bipartite relationships between violating users (red nodes) "
        "and conflicting transactional permissions (orange nodes) they possess. Intersecting edges represent "
        "authorization paths that cause static SoD conflicts.", body_style
    ))
    story.append(Spacer(1, 10))
    
    if os.path.exists(graph_path):
        # Resize graph image to fit printable area width cleanly (400 width, 240 height)
        risk_img = Image(graph_path, width=5.5*inch, height=3.3*inch)
        risk_img.hAlign = 'CENTER'
        story.append(risk_img)
    else:
        story.append(Paragraph("<i>Visualization file not found.</i>", body_style))
        
    # Build document
    doc.build(story)
    print(f"Compliance audit report successfully built at: {output_pdf_path}")
