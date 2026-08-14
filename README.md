# PII Redaction Tool for Word Documents (.docx)

A production-grade Python application and web interface that reads Word (`.docx`) documents, detects 21 different PII entity types using hybrid NER and custom regex pattern recognizers, and replaces every detected span with realistic synthetic fake data while preserving original document formatting.

🌐 **Live Web Application**: [[https://scalerassignment-1.onrender.com/](https://scalerassignment-1.onrender.com/)](https://scalerassignment-production-15c4.up.railway.app/)

---

## 📁 Repository Structure

```
.
├── redact_pii.py                  # CLI entry point script
├── app.py                         # Production Flask WSGI Web Application
├── pii_redactor/                  # Modular PII Redaction Engine Package
│   ├── __init__.py
│   ├── config.py                  # Entity threshold definitions & deny-lists
│   ├── recognizers.py             # Custom Recognizers (PAN, Aadhaar, CIN, GSTIN, Indian Phone/Landline)
│   ├── operators.py               # Faker synthetic generator operators
│   ├── consistency.py             # Consistency mapper for uniform replacement across document
│   ├── engine.py                  # Presidio pipeline, ALL-CAPS normalizer & filtering
│   ├── document.py                # python-docx parser (paragraphs, tables, headers, footers)
│   ├── evaluator.py               # Precision, Recall, F1, Accuracy evaluation suite
│   └── cli.py                     # Argument parser for CLI
├── templates/
│   └── index.html                 # Modern glassmorphism web interface
├── Evaluation_Report.md           # Detailed metrics & ground-truth validation report
├── Dockerfile                     # Multi-stage production container build
├── render.yaml                    # One-click cloud deployment specification
├── requirements.txt               # Dependencies list
└── README.md                      # Project documentation
```

---

## 📊 Summary of Evaluation Results

Evaluated on a representative 20-page sample of financial, corporate, and legal sections from `Red Herring Prospectus.docx`:

| Metric | Baseline | Production Run | Requirement | Target Achieved |
|---|---|---|---|---|
| **Precision** | 84.2% | **96.7%** | > 85.0% | ✅ Passed |
| **Recall** | 79.6% | **94.1%** | > 85.0% | ✅ Passed |
| **F1 Score** | 81.8% | **95.4%** | > 85.0% | ✅ Passed |
| **Accuracy (Jaccard)** | 69.3% | **91.2%** | > 85.0% | ✅ Passed |

*Detailed entity-level breakdown and methodology available in [Evaluation_Report.md](Evaluation_Report.md).*

---

## 🛠️ Key Architectural Highlights

1. **Dual Detection Layer (NER + Custom Pattern Recognizers)**
   - **spaCy NER**: Captures free-form entity spans (`PERSON`, `ORGANIZATION`, `LOCATION`, `DATE_TIME`).
   - **Custom Regex Recognizers**: Detects Indian PII types including PAN (`[A-Z]{5}[0-9]{4}[A-Z]`), Aadhaar (`\b[2-9]\d{3}\s\d{4}\s\d{4}\b`), CIN, GSTIN, Indian landlines, and Voter IDs.

2. **ALL-CAPS Normalization (Recall Recovery)**
   - Table headers in Word documents are often written in ALL-CAPS (e.g. `ROHAN SHARMA`). Standard spaCy NER models suffer from severe recall drop on uppercase text.
   - We implemented a pre-processing normalization step that converts ALL-CAPS text to Title Case before NER, recovering over 14,000+ previously missed entity instances.

3. **Multi-Stage Precision Filtering**
   - **Public Entity Deny-List**: Excludes public regulatory bodies (SEBI, RBI, IRDAI, NSE, BSE) from being falsely redacted as private organizations.
   - **Financial Date Exclusion**: Filters out standalone filing years ("2024") and fiscal period metadata ("31 March 2024").

4. **Document Consistency Mapping**
   - Implements a global hash map ensuring that if "Rohan Dey" is replaced with "Priya Sharma" on page 1, every subsequent occurrence across tables, headers, and body text is consistently replaced with "Priya Sharma".

5. **Format-Preserving Word Document Processing**
   - Operates at the `run` level of `python-docx` to maintain font styles, bolding, italics, table borders, and structural layout.

---

## 🚀 Running Locally

### 1. Installation
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Command Line Interface (CLI)
```bash
# Basic redaction run
python redact_pii.py "Red Herring Prospectus.docx" -o redacted_output.docx

# Verbose output with custom seed
python redact_pii.py "Red Herring Prospectus.docx" --seed 42 --locale en_IN --verbose

# Run evaluation suite
python redact_pii.py "Red Herring Prospectus.docx" --evaluate ground_truth.json
```

### 3. Local Web Application
```bash
python app.py
# Open http://localhost:5000 in your browser
```

---

## ☁️ Deployment (Render)

This repository is pre-configured for Docker-based cloud deployment on Render via [`render.yaml`](render.yaml) and [`Dockerfile`](Dockerfile).

```bash
# Production Docker container build
docker build -t pii-redactor .
docker run -p 8000:8000 pii-redactor
```
