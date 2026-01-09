# Golden Test Dataset

This directory contains sample tax documents for end-to-end testing.

## Required Files

**Note:** These files must be added manually with appropriate test data.
Do NOT commit real client documents.

### Text-based PDFs (normal extraction)

1. `w2_sample.pdf` - Sample W-2 form
   - Should contain: employer name, wages, federal withholding
   - Used for: extraction pipeline testing

2. `1099_sample.pdf` - Sample 1099-INT or 1099-DIV
   - Should contain: payer name, amounts
   - Used for: extraction pipeline testing

3. `k1_sample.pdf` - Sample Schedule K-1
   - Should contain: partnership info, income items
   - Used for: extraction pipeline testing

### Scanned PDFs (OCR testing)

4. `notice_scanned.pdf` - Scanned IRS notice
   - Should be an image-only PDF (no embedded text)
   - Used for: OCR fallback testing

## Creating Test Files

You can create test PDFs using:

1. IRS fillable forms (blank or with test data)
2. PDF generators with sample data
3. Scans of blank IRS forms

## Important

- Use fake/test data only
- Never commit real SSNs, EINs, or client information
- Files in this directory are for testing purposes only
