"""
Official statutory Form-1 PDF template generator for India Post Savings Schemes.
Generates an authentic 2-page Department of Posts Form-1 (GSPR 2018 / SB-AOF) layout.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

def create_form1_template(output_path="dak-backend/assets/forms/form1_en_v2024.pdf"):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4  # 595.27 x 841.89

    # ---------------- PAGE 1 ----------------
    # Header
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2.0, height - 35, "DEPARTMENT OF POSTS : INDIA")
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2.0, height - 50, "APPLICATION FOR OPENING OF AN ACCOUNT (FORM - 1)")
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(width / 2.0, height - 62, "[See Rule 4 of Government Savings Promotion General Rules, 2018]")

    # Post office line
    c.setFont("Helvetica", 9)
    c.drawString(35, height - 80, "To, The Postmaster,")
    c.drawString(35, height - 95, "Post Office: _____________________________________")
    c.drawString(35, height - 110, "Date (DD/MM/YYYY): ___________________")

    # Photo Box
    c.rect(width - 125, height - 145, 90, 95)
    c.setFont("Helvetica", 7)
    c.drawCentredString(width - 80, height - 95, "Paste Recent")
    c.drawCentredString(width - 80, height - 105, "Passport Photo")
    c.drawCentredString(width - 80, height - 115, "(Applicant 1)")

    # Scheme Selection Box
    c.setFillColor(colors.HexColor("#f4f4f4"))
    c.rect(35, height - 180, width - 70, 30, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(42, height - 163, "1. Applicable Scheme:")
    c.setFont("Helvetica", 8)
    c.drawString(145, height - 163, "[   ] POSA       [   ] RD       [   ] TD (1/2/3/5 Yr)       [   ] MIS       [   ] SCSS")
    c.drawString(145, height - 176, "[   ] PPF         [   ] SSA     [   ] NSC (VIII)             [   ] KVP       [   ] MSSC")

    # Account Type & Mode
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(35, height - 198, "2. Account Type: [   ] Single      [   ] Either or Survivor (Joint B)      [   ] Joint A      [   ] On Behalf of Minor")
    
    # Amount & Mode
    c.drawString(35, height - 220, "3. Initial Deposit Amount: Rs. _________________ (in figures)")
    c.drawString(35, height - 235, "   In Words: ____________________________________________________________________")
    c.drawString(35, height - 250, "   Mode of Deposit: [   ] Cash      [   ] Cheque / DD No. __________________ Dated: ___________")

    # Personal Details Table Header
    c.setFillColor(colors.HexColor("#e8e8e8"))
    c.rect(35, height - 275, width - 70, 18, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(42, height - 268, "4. APPLICANT DETAILS (IN BLOCK LETTERS)")

    y_pos = height - 295
    row_height = 20
    fields_p1 = [
        "Full Name of Applicant:",
        "Father / Mother / Spouse Name:",
        "Date of Birth (DD/MM/YYYY):                                Gender: [  ] Male  [  ] Female  [  ] Other",
        "Aadhaar Number (12 digits):                                 PAN Card Number (10 chars):",
        "Mobile Number (10 digits):                                  Email ID:",
        "Present Residential Address:",
        "City / District / State:                                    PIN Code (6 digits):",
        "Permanent Address:"
    ]

    for label in fields_p1:
        c.rect(35, y_pos - 12, width - 70, row_height, fill=0, stroke=1)
        c.setFont("Helvetica", 8)
        c.drawString(40, y_pos - 4, label)
        y_pos -= row_height

    # Minor Details Section (for SSA / Minor accounts)
    c.setFillColor(colors.HexColor("#f4f4f4"))
    c.rect(35, y_pos - 10, width - 70, 16, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(42, y_pos - 4, "5. IN CASE OF MINOR / SUKANYA SAMRIDDHI (SSA) ACCOUNT:")
    y_pos -= 18

    c.rect(35, y_pos - 12, width - 70, row_height, fill=0, stroke=1)
    c.setFont("Helvetica", 7.5)
    c.drawString(40, y_pos - 4, "Name of Minor: ________________________________________ Date of Birth: ____________ Birth Cert No: ________________")
    y_pos -= row_height

    c.rect(35, y_pos - 12, width - 70, row_height, fill=0, stroke=1)
    c.setFont("Helvetica", 7.5)
    c.drawString(40, y_pos - 4, "Name of Guardian: ____________________________________ Relationship: [  ] Father  [  ] Mother  [  ] Legal Guardian")
    y_pos -= row_height

    # Specimen signature box on Page 1
    c.rect(width - 175, 45, 140, 45)
    c.setFont("Helvetica", 7)
    c.drawCentredString(width - 105, 50, "Specimen Signature / Thumb (1)")
    c.setFont("Helvetica-Oblique", 7)
    c.drawString(35, 30, "Page 1 of 2 — Form-1 (GSPR 2018) — Department of Posts, Government of India")

    c.showPage()

    # ---------------- PAGE 2 ----------------
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2.0, height - 35, "FORM-1 : NOMINATION DETAILS & DECLARATIONS")
    c.line(35, height - 42, width - 35, height - 42)

    # Nomination Header (Schedule I)
    c.setFillColor(colors.HexColor("#e8e8e8"))
    c.rect(35, height - 65, width - 70, 18, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(42, height - 58, "6. NOMINATION (Under Rule 5 of GSPR, 2018)")
    
    c.setFont("Helvetica", 8)
    c.drawString(35, height - 80, "I/We hereby nominate the following person(s) to receive the amount due in the event of my/our death:")

    # Nomination Table
    y_nom = height - 100
    c.rect(35, y_nom - 30, width - 70, 30, fill=0, stroke=1)
    c.line(220, y_nom, 220, y_nom - 30)
    c.line(330, y_nom, 330, y_nom - 30)
    c.line(420, y_nom, 420, y_nom - 30)
    c.line(490, y_nom, 490, y_nom - 30)

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(40, y_nom - 12, "Name & Full Address of Nominee")
    c.drawString(225, y_nom - 12, "Relationship")
    c.drawString(335, y_nom - 12, "Share (%)")
    c.drawString(425, y_nom - 12, "DOB (if Minor)")
    c.drawString(495, y_nom - 12, "Guardian Name")

    # Blank nomination row 1
    y_nom -= 30
    c.rect(35, y_nom - 35, width - 70, 35, fill=0, stroke=1)
    c.line(220, y_nom, 220, y_nom - 35)
    c.line(330, y_nom, 330, y_nom - 35)
    c.line(420, y_nom, 420, y_nom - 35)
    c.line(490, y_nom, 490, y_nom - 35)

    # Declarations
    y_dec = y_nom - 55
    c.setFillColor(colors.HexColor("#e8e8e8"))
    c.rect(35, y_dec, width - 70, 18, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(42, y_dec + 5, "7. DECLARATION BY APPLICANT")

    c.setFont("Helvetica", 7.5)
    dec_text = [
        "1. I/We hereby declare that I/we have read and understood the rules governing the chosen scheme and agree to abide by them.",
        "2. I/We undertake to inform the Post Office immediately of any change in my/our residential address or KYC information.",
        "3. I/We confirm that I/we do not hold any other account of the same scheme in contravention of the maximum limit / rules.",
        "4. The particulars given above are true and correct to the best of my/our knowledge and belief."
    ]
    dy = y_dec - 15
    for dt in dec_text:
        c.drawString(35, dy, dt)
        dy -= 14

    # Signatures
    c.drawString(35, dy - 20, "Place: ___________________________")
    c.drawString(35, dy - 38, "Date:  ___________________________")

    c.rect(width - 180, dy - 55, 145, 45)
    c.setFont("Helvetica", 7)
    c.drawCentredString(width - 107, dy - 50, "Signature / Thumb Impression of Applicant(s)")

    # For Post Office Use Only
    po_use_y = dy - 80
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(35, po_use_y - 120, width - 70, 120, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(width / 2.0, po_use_y - 12, "FOR POST OFFICE USE ONLY")
    
    c.setFont("Helvetica", 8)
    c.drawString(45, po_use_y - 30, "Account Number Allocated: __________________________   CIF ID: __________________________")
    c.drawString(45, po_use_y - 50, "KYC Documents Verified:   [  ] Aadhaar Verified    [  ] PAN Card Verified    [  ] Photo Matched")
    c.drawString(45, po_use_y - 70, "Date of Account Opening: __________________________   Amount Deposited: Rs. ______________")
    c.drawString(45, po_use_y - 90, "Signature of Counter PA: __________________________   Signature of Postmaster / APM: _____")
    c.drawString(45, po_use_y - 110, "Post Office Round Stamp: [                                          ]")

    c.setFont("Helvetica-Oblique", 7)
    c.drawString(35, 25, "Page 2 of 2 — Statutory India Post Form-1 (GSPR 2018) — Unsigned Pre-fill Copy")

    c.save()
    print(f"[+] Form-1 Template successfully generated at: {output_path}")

if __name__ == "__main__":
    create_form1_template()
