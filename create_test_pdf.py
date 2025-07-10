#!/usr/bin/env python3
"""
Simple script to create a test PDF for demonstrating document viewer functionality
"""

from fpdf import FPDF
import os

def create_test_pdf():
    # Create a simple PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Test Document for IDIS Document Viewer", ln=1, align='C')
    pdf.cell(200, 10, txt="", ln=1, align='C')  # Empty line
    pdf.cell(200, 10, txt="This is a test document to demonstrate the document viewer functionality", ln=1, align='L')
    pdf.cell(200, 10, txt="in the IDIS system.", ln=1, align='L')
    pdf.cell(200, 10, txt="", ln=1, align='L')  # Empty line
    pdf.cell(200, 10, txt="Document Type: Test Document", ln=1, align='L')
    pdf.cell(200, 10, txt="Amount: $99.99", ln=1, align='L')
    pdf.cell(200, 10, txt="Date: 2025-07-09", ln=1, align='L')
    
    # Save the PDF
    pdf_path = "data/scanner_output/test_document.pdf"
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    
    pdf.output(pdf_path)
    print(f"Test PDF created at: {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    create_test_pdf()