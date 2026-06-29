#!/usr/bin/env python3
"""Generate realistic PDF assets for the scenario demo guide."""

from __future__ import annotations

from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "demo-assets"
OUT.mkdir(parents=True, exist_ok=True)

PAGE_W, PAGE_H = A4
NAVY = colors.HexColor("#16324F")
BLUE = colors.HexColor("#1F6FEB")
GREEN = colors.HexColor("#1F7A5A")
GOLD = colors.HexColor("#A56A00")
RED = colors.HexColor("#A33A3A")
INK = colors.HexColor("#20242A")
MUTED = colors.HexColor("#657386")
PALE_BLUE = colors.HexColor("#EEF5FF")
PALE_GREEN = colors.HexColor("#EFF8F4")
PALE_GOLD = colors.HexColor("#FFF7E8")
LINE = colors.HexColor("#D6DEE8")

STYLES = getSampleStyleSheet()
STYLES.add(
    ParagraphStyle(
        "DocTitle",
        parent=STYLES["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=NAVY,
        spaceAfter=8,
    )
)
STYLES.add(
    ParagraphStyle(
        "SectionTitle",
        parent=STYLES["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=NAVY,
        spaceBefore=4,
        spaceAfter=8,
    )
)
STYLES.add(
    ParagraphStyle(
        "Body",
        parent=STYLES["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=INK,
        spaceAfter=7,
    )
)
STYLES.add(
    ParagraphStyle(
        "Small",
        parent=STYLES["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=MUTED,
    )
)
STYLES.add(
    ParagraphStyle(
        "Tiny",
        parent=STYLES["Normal"],
        fontName="Helvetica",
        fontSize=6.8,
        leading=8,
        textColor=MUTED,
    )
)
STYLES.add(
    ParagraphStyle(
        "TableHead",
        parent=STYLES["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
)
STYLES.add(
    ParagraphStyle(
        "TableCell",
        parent=STYLES["Normal"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=10.5,
        textColor=INK,
    )
)
STYLES.add(
    ParagraphStyle(
        "TableCellRight",
        parent=STYLES["TableCell"],
        alignment=TA_RIGHT,
    )
)
STYLES.add(
    ParagraphStyle(
        "CenterSmall",
        parent=STYLES["Small"],
        alignment=TA_CENTER,
    )
)


def p(text: str, style: str = "Body") -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), STYLES[style])


def cell(text: object, style: str = "TableCell") -> Paragraph:
    return p(str(text), style)


def rule(color=LINE, width=0.6):
    return HRFlowable(width="100%", thickness=width, color=color, spaceBefore=6, spaceAfter=8)


def table(rows, widths, header=True, grid=True, row_bg=None):
    data = []
    for r_idx, row in enumerate(rows):
        data.append([cell(v, "TableHead" if header and r_idx == 0 else "TableCell") for v in row])
    styles = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        styles.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ]
        )
    if grid:
        styles.append(("GRID", (0, 0), (-1, -1), 0.35, LINE))
    if row_bg:
        for idx, bg in row_bg.items():
            styles.append(("BACKGROUND", (0, idx), (-1, idx), bg))
    t = Table(data, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle(styles))
    return t


def amount_table(rows, widths):
    data = [[cell(v, "TableHead" if i == 0 else "TableCellRight" if j > 1 else "TableCell") for j, v in enumerate(row)] for i, row in enumerate(rows)]
    t = Table(data, colWidths=widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("BACKGROUND", (0, -1), (-1, -1), PALE_BLUE),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )
    return t


def on_page(title: str, issuer: str, doc_code: str, accent=NAVY):
    initials = "".join(part[0] for part in issuer.replace("&", " ").split()[:3]).upper()

    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(accent)
        canvas.rect(0, PAGE_H - 20 * mm, PAGE_W, 20 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.circle(18 * mm, PAGE_H - 10 * mm, 6 * mm, fill=0, stroke=1)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawCentredString(18 * mm, PAGE_H - 12 * mm, initials[:3])
        canvas.setFont("Helvetica-Bold", 10.5)
        canvas.drawString(30 * mm, PAGE_H - 9 * mm, issuer)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(30 * mm, PAGE_H - 14 * mm, title)
        canvas.setFillColor(colors.HexColor("#F3F6FA"))
        canvas.rect(0, 0, PAGE_W, 13 * mm, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(18 * mm, 5 * mm, f"{doc_code} | Demo document generated for Aethos scenario testing")
        canvas.drawRightString(PAGE_W - 18 * mm, 5 * mm, f"Page {doc.page}")
        canvas.restoreState()

    return draw


def build_pdf(filename: str, title: str, issuer: str, doc_code: str, story, accent=NAVY):
    path = OUT / filename
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        title=title,
        author=issuer,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=31 * mm,
        bottomMargin=18 * mm,
    )
    doc.build(story, onFirstPage=on_page(title, issuer, doc_code, accent), onLaterPages=on_page(title, issuer, doc_code, accent))
    return path


def signature_table():
    rows = [
        ["Accepted for and on behalf of Nexus Capital Partners LP", "Accepted for and on behalf of Meridian Advisory Group LLP"],
        ["Name:\nTitle:\nDate:\nSignature:", "Name:\nTitle:\nDate:\nSignature:"],
    ]
    return table(rows, [80 * mm, 80 * mm], header=False, row_bg={0: PALE_BLUE})


def nexus_engagement_letter():
    story = []

    def section(title, paras=None, rows=None, widths=None, bg=None, extra=None, page_break=True):
        story.append(p(title, "DocTitle" if not story else "SectionTitle"))
        if paras:
            for text in paras:
                story.append(p(text))
        if rows:
            story.append(table(rows, widths or [50 * mm, 110 * mm], row_bg=bg or {}))
            story.append(Spacer(1, 4 * mm))
        if extra:
            for item in extra:
                story.append(item)
        if page_break:
            story.append(PageBreak())

    section(
        "Engagement Letter and Service Schedule",
        [
            "Date: 20 December 2025",
            "Private and confidential. Meridian Advisory Group LLP is pleased to confirm the terms of our engagement with Nexus Capital Partners LP for accounting and advisory services for the period 1 January 2026 to 31 December 2026.",
            "This letter sets out the scope of work, fee basis, client responsibilities, timetable, approval process, and professional terms that govern the engagement. It should be read with the attached service schedule and acceptance page.",
        ],
        [
            ["Client", "Nexus Capital Partners LP"],
            ["Primary contact", "Emily Harcourt, Finance Director"],
            ["Meridian partner", "Marcus Chen, Managing Partner"],
            ["Service lines", "Accounting and Advisory, CFO Advisory, Group Reporting"],
            ["Period covered", "1 January 2026 to 31 December 2026"],
            ["Billing model", "Mixed: fixed fee, monthly retainer, time and materials, and reimbursable expenses"],
        ],
        [45 * mm, 115 * mm],
    )

    section(
        "1. Engagement Snapshot",
        [
            "Nexus Capital Partners LP operates a mid-market private equity group with six portfolio companies. The engagement is structured as a master relationship with separate projects for statutory consolidation, recurring management accounts, and CFO advisory support.",
            "Meridian will maintain separate project economics for each workstream while presenting Nexus with consolidated billing where appropriate.",
        ],
        [
            ["Workstream", "Billing basis", "Commercial terms"],
            ["Group consolidation accounts", "Fixed fee", "GBP 42,000 fixed fee for FY2025 statutory group accounts, billed in two milestones"],
            ["Monthly management accounts", "Monthly retainer", "GBP 8,500 per month for six portfolio companies"],
            ["CFO advisory services", "Time and materials", "GBP 350 per hour, billed monthly in arrears"],
            ["Out-of-pocket expenses", "Recharge at cost", "Travel, filing, and third-party costs recharged at cost with supporting evidence"],
        ],
        [56 * mm, 42 * mm, 62 * mm],
    )

    section(
        "2. Scope - Group Consolidation Accounts",
        [
            "Meridian will prepare the FY2025 statutory group consolidation pack and supporting schedules using information provided by Nexus and its portfolio companies.",
            "The work includes consolidation adjustments, intercompany eliminations, draft financial statement preparation, partner review, and response to agreed audit queries.",
        ],
        [
            ["Deliverable", "Included activity", "Expected evidence"],
            ["Consolidation workbook", "Trial balance import, mapping, eliminations, and review points", "Signed-off workbook and review log"],
            ["Draft statutory accounts", "Directors report, primary statements, notes, and accounting policy review", "Draft accounts pack"],
            ["Audit support", "Responses to reasonable auditor queries on consolidation mechanics", "Query tracker"],
            ["Milestone billing", "Milestone 1 at draft pack, milestone 2 at final sign-off", "Partner approval"],
        ],
        [48 * mm, 72 * mm, 40 * mm],
    )

    section(
        "3. Scope - Monthly Management Accounts",
        [
            "The monthly management accounts retainer covers recurring management accounts for six portfolio companies. Meridian will prepare management reporting outputs using monthly source records and agreed reporting templates.",
            "The retainer covers standard monthly preparation, review, and presentation support. Material changes in reporting requirements or additional entities will be scoped separately.",
        ],
        [
            ["Monthly process", "Responsibility", "Target timing"],
            ["Source data collection", "Nexus finance team provides ledgers, bank reports, and payroll summaries", "Business day 3"],
            ["Preparation", "Meridian prepares management accounts and variance commentary", "Business day 6"],
            ["Partner review", "Marcus Chen or delegate reviews exceptions and narrative", "Business day 8"],
            ["Pack issue", "Management pack issued to Nexus finance leadership", "Business day 10"],
        ],
        [45 * mm, 80 * mm, 35 * mm],
    )

    section(
        "4. Scope - CFO Advisory Services",
        [
            "CFO advisory services are provided on a time and materials basis. Typical advisory work includes board-pack review, cash-flow modelling, financing support, scenario analysis, and ad hoc reporting requests.",
            "Advisory time will be recorded by project and billed monthly in arrears. Non-billable internal planning time will be recorded separately for project profitability reporting.",
        ],
        [
            ["Role", "Indicative rate", "Notes"],
            ["CFO Advisory Partner", "GBP 350 per hour", "Primary advisory and board-facing work"],
            ["Manager", "GBP 240 per hour", "Model preparation, review support, and coordination"],
            ["Associate", "GBP 145 per hour", "Analysis, schedules, and data preparation"],
        ],
        [65 * mm, 40 * mm, 55 * mm],
    )

    section(
        "5. Deliverables and Timetable",
        [
            "The table below summarizes key expected deliverables. Dates may change where Nexus or third parties provide information later than agreed.",
            "Meridian will flag blockers promptly and maintain a shared action log for open requests, review points, and approvals.",
        ],
        [
            ["Deliverable", "Target date", "Owner", "Approval"],
            ["Engagement setup and project creation", "5 January 2026", "Meridian", "Nexus Finance Director"],
            ["January management accounts pack", "14 February 2026", "Meridian", "Marcus Chen"],
            ["FY2025 draft consolidation pack", "30 April 2026", "Meridian", "Nexus Finance Director"],
            ["FY2025 final statutory accounts", "30 June 2026", "Meridian", "Nexus Board"],
            ["Monthly CFO advisory billing", "Monthly in arrears", "Meridian", "Marcus Chen"],
        ],
        [55 * mm, 35 * mm, 35 * mm, 35 * mm],
    )

    section(
        "6. Fees, Billing, VAT, and Expenses",
        [
            "All amounts are stated excluding VAT unless stated otherwise. Meridian will invoice the fixed fee milestones when the associated deliverable is ready for client review or final sign-off.",
            "Monthly management accounts are billed on the first business day of each month. CFO advisory services and approved expenses are billed monthly in arrears.",
        ],
        [
            ["Fee component", "Amount", "Billing trigger"],
            ["Group consolidation accounts", "GBP 42,000 fixed", "50 percent on draft pack, 50 percent on final pack"],
            ["Monthly management accounts", "GBP 8,500 per month", "Monthly retainer"],
            ["CFO advisory services", "GBP 350 per hour", "Monthly in arrears"],
            ["Out-of-pocket expenses", "At cost", "Monthly in arrears with support"],
        ],
        [58 * mm, 42 * mm, 60 * mm],
    )

    section(
        "7. Client Responsibilities",
        [
            "Nexus is responsible for providing complete and accurate source records, responding to queries in a timely manner, and designating personnel who can approve deliverables and commercial changes.",
            "Where information is incomplete, late, or materially inconsistent, Meridian may defer delivery dates, issue a blocker notice, or request approval for additional scope.",
        ],
        [
            ["Responsibility", "Nexus owner", "Expected standard"],
            ["Portfolio company trial balances", "Finance Director", "Complete and reconciled to local ledgers"],
            ["Bank and debt schedules", "Treasury Lead", "Current to reporting period end"],
            ["Intercompany confirmations", "Portfolio controllers", "Matched and variance-explained"],
            ["Approval of deliverables", "Finance Director or Board", "Respond within five business days"],
        ],
        [55 * mm, 45 * mm, 60 * mm],
    )

    section(
        "8. Workflow, Review, and Approval Model",
        [
            "Meridian may use Aethos to coordinate document intake, project setup, billing preparation, time capture, and accounting evidence. Aethos will prepare work for review, but client-facing invoices and material commercial changes remain subject to approval.",
            "For this engagement, AI-assisted extraction or drafting will be reviewed by the Meridian engagement owner before records are finalized.",
        ],
        [
            ["Workflow stage", "System action", "Approval point"],
            ["Engagement intake", "Extracts client, billing model, rates, and first project", "Meridian owner approval"],
            ["Monthly billing", "Prepares retainer, T&M, fixed-fee, and expense lines", "Inbox approval before sending"],
            ["Journal evidence", "Posts invoice-backed journals after approval", "Accounting controls"],
            ["Audit trail", "Stores decision history, source links, and reviewer changes", "Available for audit review"],
        ],
        [42 * mm, 68 * mm, 50 * mm],
    )

    section(
        "9. Confidentiality and Data Protection",
        [
            "Each party will keep confidential information secure and use it only for the purposes of this engagement. Meridian will apply appropriate technical and organizational measures to protect client information.",
            "Personal data will be processed only as needed to perform the engagement and comply with professional, legal, and regulatory obligations.",
        ],
        [
            ["Control area", "Commitment"],
            ["Access", "Access is limited to personnel assigned to the engagement or quality review"],
            ["Retention", "Records retained in accordance with Meridian retention policy and professional obligations"],
            ["Sub-processors", "Used only where appropriate confidentiality and security obligations are in place"],
            ["Data subject requests", "Handled with cooperation between Meridian and Nexus as required by law"],
        ],
        [50 * mm, 110 * mm],
    )

    section(
        "10. Professional Standards and Limitation of Liability",
        [
            "Meridian will perform services with reasonable skill and care in accordance with applicable professional standards. The engagement does not constitute audit, assurance, legal, investment, or regulated financial advice unless separately agreed in writing.",
            "Meridian's aggregate liability for claims arising from this engagement is limited to the greater of the fees paid for the relevant workstream in the preceding twelve months or GBP 250,000, except where such limitation is prohibited by law.",
        ],
        [
            ["Matter", "Position"],
            ["No audit opinion", "No audit or assurance opinion will be issued under this engagement"],
            ["Reliance", "Advice is prepared for Nexus Capital Partners LP and may not be relied on by third parties"],
            ["Tax advice", "Tax structuring or compliance work requires separate written scope where not listed"],
            ["Changes in law", "Meridian is not responsible for changes after work is delivered unless separately engaged"],
        ],
        [50 * mm, 110 * mm],
    )

    section(
        "11. Acceptance",
        [
            "Please confirm your acceptance of this engagement letter and service schedule by signing below and returning a copy to Meridian Advisory Group LLP. Work will commence once acceptance is received and onboarding information has been provided.",
        ],
        extra=[signature_table(), Spacer(1, 8 * mm), p("For questions about this engagement, contact Marcus Chen at marcus@meridianadvisory.co.uk.", "Small")],
        page_break=False,
    )

    section(
        "Appendix A - Service Order Summary",
        [
            "This appendix is used by Meridian to configure the engagement, projects, rate card, billing terms, and review workflow in Aethos.",
        ],
        [
            ["Service order", "Project", "Billing arrangement", "Rate or fee"],
            ["SO-2026-NEX-001", "Statutory Accounts - FY2025", "Fixed fee milestone", "GBP 42,000"],
            ["SO-2026-NEX-002", "Monthly Management Accounts - Portfolio", "Monthly retainer", "GBP 8,500 per month"],
            ["SO-2026-NEX-003", "CFO Advisory", "Time and materials", "GBP 350 per hour partner rate"],
            ["SO-2026-NEX-004", "Expenses", "Recharge at cost", "Supported actuals"],
        ],
        [42 * mm, 54 * mm, 36 * mm, 28 * mm],
        page_break=False,
    )

    return build_pdf(
        "nexus_engagement_letter.pdf",
        "Nexus Capital Partners - Engagement Letter",
        "Meridian Advisory Group LLP",
        "MAG-NEX-EL-2026",
        story,
        NAVY,
    )


def brightwater_invoice():
    story = [
        p("Tax Invoice", "DocTitle"),
        table(
            [
                ["Invoice number", "FR-2026-0615", "Invoice date", "15 June 2026"],
                ["Payment terms", "Net 30", "Due date", "15 July 2026"],
                ["Client reference", "Brightwater Annual Accounts", "PO / service order", "Not supplied"],
                ["Vendor VAT", "GB123456789", "Currency", "GBP"],
            ],
            [35 * mm, 48 * mm, 35 * mm, 42 * mm],
            header=False,
            row_bg={0: PALE_BLUE, 2: PALE_GOLD},
        ),
        Spacer(1, 5 * mm),
        table(
            [
                ["From", "Forster & Reid Ltd\n45 King Street\nBristol BS1 4HX\naccounts@forsterreid.example"],
                ["Bill to", "Meridian Advisory Group LLP\n20 Finsbury Circus\nLondon EC2M 7AB\nSupplier inbox: ap@meridianadvisory.co.uk"],
            ],
            [35 * mm, 125 * mm],
            header=False,
        ),
        Spacer(1, 6 * mm),
        amount_table(
            [
                ["Description", "Project / client", "Qty", "Unit", "Amount"],
                ["Senior technical accounting support - audit schedules, revenue testing, and fixed-asset review", "Brightwater Manufacturing Ltd - Annual Accounts FY2025", "16.0", "200.00", "3,200.00"],
                ["Subtotal", "", "", "", "3,200.00"],
                ["VAT", "VAT not charged on this invoice", "", "", "0.00"],
                ["Total due", "", "", "", "GBP 3,200.00"],
            ],
            [67 * mm, 45 * mm, 14 * mm, 20 * mm, 24 * mm],
        ),
        Spacer(1, 6 * mm),
        table(
            [
                ["Exception notes for client review", "No approved PO was provided at the time of issue. Please match this invoice to the Brightwater Annual Accounts engagement or return with a query within five business days."],
                ["Payment details", "Forster & Reid Ltd Client Account | Bank: Northbridge Bank | Sort code: 12-34-56 | Account: ****7890 | Reference: FR-2026-0615"],
                ["Authorised by", "Hannah Forster, Partner"],
            ],
            [48 * mm, 112 * mm],
            header=False,
            row_bg={0: PALE_GOLD},
        ),
        Spacer(1, 8 * mm),
        p("This invoice is issued for professional services supplied to Meridian Advisory Group LLP in support of the Brightwater Manufacturing Ltd engagement. Please retain this document for accounts payable and project cost evidence.", "Small"),
    ]
    return build_pdf(
        "brightwater_subcontractor_invoice.pdf",
        "Forster & Reid - Brightwater Subcontractor Invoice",
        "Forster & Reid Ltd",
        "FR-INV-2026-0615",
        story,
        GREEN,
    )


def alderton_dividend_notice():
    story = [
        p("Dividend Income Notice", "DocTitle"),
        table(
            [
                ["Notice reference", "MPB-DIV-2026-03824", "Notice date", "28 March 2026"],
                ["Account name", "Alderton Trust (1985)", "Account number", "AT85-SG-0192"],
                ["Custodian", "Merlion Private Bank (Singapore)", "Currency", "SGD"],
            ],
            [35 * mm, 54 * mm, 34 * mm, 37 * mm],
            header=False,
            row_bg={0: PALE_GREEN},
        ),
        Spacer(1, 6 * mm),
        p("We confirm the following dividend income has been credited to the Singapore custody account referenced above.", "Body"),
        amount_table(
            [
                ["Security", "ISIN", "Pay date", "Holding", "Net credit"],
                ["Singapore Telecommunications Limited", "SG1T75931496", "28 Mar 2026", "1,400,000 ordinary shares", "S$42,000.00"],
                ["Gross dividend", "", "", "", "S$42,000.00"],
                ["Withholding tax", "Singapore dividend withholding tax", "", "", "S$0.00"],
                ["Net amount credited", "", "", "", "S$42,000.00"],
            ],
            [48 * mm, 31 * mm, 25 * mm, 41 * mm, 25 * mm],
        ),
        Spacer(1, 6 * mm),
        table(
            [
                ["Bank credit", "SGD income account ending 4471"],
                ["FX note", "No GBP conversion has been made by the custodian. Beneficiary accountants should translate using their accounting policy and applicable posting-date FX rate."],
                ["Tax note", "This notice is provided for income recording and is not a Singapore tax certificate."],
            ],
            [40 * mm, 120 * mm],
            header=False,
            row_bg={1: PALE_GOLD},
        ),
        Spacer(1, 8 * mm),
        p("Issued electronically by Merlion Private Bank (Singapore), Private Wealth Operations. For verification contact custody.operations@merlionpb.example quoting notice reference MPB-DIV-2026-03824.", "Small"),
    ]
    return build_pdf(
        "alderton_sgd_dividend_notice.pdf",
        "Alderton Trust 1985 - SGD Dividend Notice",
        "Merlion Private Bank (Singapore)",
        "MPB-DIV-2026-03824",
        story,
        GOLD,
    )


def thornton_cosec_instruction():
    story = [
        p("Company Secretarial Instruction", "DocTitle"),
        table(
            [
                ["Instruction date", "8 April 2026", "Client", "Thornton Tech Solutions Ltd"],
                ["Recipient", "Meridian Advisory Group LLP", "Requested completion", "April 2026 filing cycle"],
                ["Client contact", "Amelia Brooks, CEO", "Billing reference", "Thornton COSEC April 2026"],
            ],
            [35 * mm, 48 * mm, 38 * mm, 39 * mm],
            header=False,
            row_bg={0: PALE_BLUE},
        ),
        Spacer(1, 6 * mm),
        p("Please treat this letter as formal instruction to prepare the company secretarial filings and statutory register updates listed below for Thornton Tech Solutions Ltd.", "Body"),
        table(
            [
                ["Action", "Details", "Requested filing / output", "Fee basis"],
                ["Director appointment", "Appoint Dr Maya Shah as non-executive director effective 12 April 2026. DOB and residential address supplied separately through the client portal.", "Companies House AP01 and statutory register update", "GBP 650 fixed"],
                ["Share allotment", "Series A allotment following completion of the financing round. 1,420,000 ordinary shares of GBP 0.01 each allotted to investors listed in the cap-table schedule.", "Companies House SH01 and shareholder register update", "GBP 1,200 fixed"],
                ["Registered office update", "Change registered office to 4th Floor, 80 Great Eastern Street, London EC2A 3HU.", "Companies House AD01 and register update", "GBP 250 fixed"],
            ],
            [34 * mm, 62 * mm, 42 * mm, 32 * mm],
        ),
        Spacer(1, 6 * mm),
        table(
            [
                ["Authority", "This instruction has been approved by the board of Thornton Tech Solutions Ltd. Supporting minutes and investor consents are available in the client portal."],
                ["Billing", "Please consolidate the April 2026 COSEC work on the next Meridian invoice unless a separate invoice is required for Companies House filing evidence."],
                ["Contact", "Questions should be directed to legalops@thorntontech.example and copied to amelia.brooks@thorntontech.example."],
            ],
            [35 * mm, 125 * mm],
            header=False,
            row_bg={0: PALE_GREEN},
        ),
        Spacer(1, 12 * mm),
        table(
            [
                ["Authorised signatory", "Amelia Brooks\nChief Executive Officer\nThornton Tech Solutions Ltd\nSignature: ______________________________"],
            ],
            [45 * mm, 115 * mm],
            header=False,
        ),
    ]
    return build_pdf(
        "thornton_cosec_instruction.pdf",
        "Thornton Tech - COSEC Instruction",
        "Thornton Tech Solutions Ltd",
        "TTS-COSEC-2026-04",
        story,
        BLUE,
    )


def main():
    paths = [
        nexus_engagement_letter(),
        brightwater_invoice(),
        alderton_dividend_notice(),
        thornton_cosec_instruction(),
    ]
    for path in paths:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
