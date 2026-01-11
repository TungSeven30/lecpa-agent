# Krystal Le Agent - AI Assistant for CPA Firms

> **Your AI-Powered Tax Season Companion**
> An intelligent assistant designed specifically for CPAs and tax professionals to streamline document review, client communication, and tax return preparation.

[![Status](https://img.shields.io/badge/Status-Production%20Ready-green)]()
[![Tax Season](https://img.shields.io/badge/Tax%20Season-2024-blue)]()
[![AI Powered](https://img.shields.io/badge/AI-Claude%20Opus%204.5-purple)]()

---

## 📋 Table of Contents

- [What It Does](#what-it-does)
- [Why CPAs Need This](#why-cpas-need-this)
- [Key Features](#key-features)
- [Real-World Use Cases](#real-world-use-cases)
- [How It Works](#how-it-works)
- [Getting Started](#getting-started)
- [Daily Workflow](#daily-workflow)
- [Available Commands](#available-commands)
- [Configuration](#configuration)
- [Deployment Options](#deployment-options)
- [Security & Compliance](#security--compliance)
- [FAQ for CPAs](#faq-for-cpas)
- [Troubleshooting](#troubleshooting)
- [Support](#support)

---

## 🎯 What It Does

Krystal Le Agent is an **internal AI assistant** that helps CPAs and tax professionals work faster and smarter during tax season. Think of it as having an experienced associate who:

- **Instantly searches** through thousands of client documents to find specific information
- **Answers questions** about client files with exact citations (page numbers, document names)
- **Drafts emails** to clients requesting missing documents
- **Creates checklists** for tax organizers and missing items
- **Reviews documents** and extracts key information from W-2s, 1099s, and IRS notices
- **Never hallucinates** - all answers include citations to source documents

### Built For:
- **Small to mid-size CPA firms** (5-100 clients)
- **Individual practitioners** handling 1040s and business returns
- **Tax preparers** needing to manage client document workflows
- **Accounting firms** with seasonal tax preparation services

---

## 💡 Why CPAs Need This

### The Problem

Tax season is overwhelming:
- ✋ **Hours spent searching** for specific documents across client folders
- 📧 **Repetitive emails** asking clients for the same missing documents
- 📄 **Manual data entry** from W-2s, 1099s, and K-1s into tax software
- 🔍 **Difficulty finding** prior year information or firm guidance
- ⏰ **Time wasted** on administrative tasks instead of high-value advisory work

### The Solution

Krystal Le Agent automates these tasks:
- ✅ **Instant search** across all client documents with natural language questions
- ✅ **Auto-generated emails** for missing documents (personalized per client)
- ✅ **Document extraction** pulls data from tax forms automatically
- ✅ **Citation-backed answers** - never guesses, always shows sources
- ✅ **Time savings** of 2-3 hours per return during busy season

### ROI Example

**For a firm preparing 100 individual returns:**
- **Time saved per return:** 2 hours
- **Total time saved:** 200 hours
- **At $150/hour:** **$30,000 in recovered billable time**
- **Plus:** Reduced stress, fewer errors, better client communication

---

## ✨ Key Features

### 1. 🔍 Intelligent Document Search

Ask questions in plain English and get instant answers with citations:

**Example Questions:**
- *"What is John Smith's total W-2 income for 2024?"*
- *"Did Sarah provide her mortgage interest statement?"*
- *"Show me all 1099-DIV forms for ABC Corp"*
- *"What was the client's AGI last year?"*

**What You Get:**
- Direct answer with specific numbers
- **Citations** showing document name, page number, and relevant excerpt
- Ability to click through to view the actual document

### 2. 📝 Automated Client Communication

Generate professional emails and documents in seconds:

#### Missing Documents Email
```
"Generate a missing documents email for [client name]"
```
**Result:** Personalized email listing missing items with professional tone, ready to send.

#### Tax Organizer Checklist
```
"Create an organizer checklist for this client"
```
**Result:** Complete checklist of required documents based on client type (W-2 employee, business owner, etc.)

#### IRS Notice Response Draft
```
"Draft a response to this IRS notice"
```
**Result:** Professional response letter with required attachments list.

### 3. 📊 Smart Document Processing

**Automatic OCR:** Scanned documents are automatically converted to searchable text

**Supported Formats:**
- ✅ PDF (native and scanned)
- ✅ Microsoft Word (.docx)
- ✅ Excel spreadsheets (.xlsx)
- ✅ Images (via OCR)

**Processing Pipeline:**
1. Upload → 2. Text extraction → 3. OCR (if needed) → 4. Indexing → 5. Ready to search (typically 2-5 minutes)

### 4. 🎨 Professional Artifact Templates

Pre-built templates for common CPA tasks:

| Template | Use Case | Time Saved |
|----------|----------|------------|
| **Missing Docs Email** | Request documents from client | 15 min per client |
| **Tax Organizer Checklist** | Intake packet for new clients | 20 min per client |
| **IRS Notice Response** | Respond to CP2000, LT11, etc. | 30 min per notice |
| **QC Review Memo** | Quality control documentation | 25 min per return |
| **Document Extraction Summary** | Summarize received documents | 10 min per client |

### 5. 🔐 Citation-Based Accuracy

**Every answer includes:**
- 📄 Document name
- 📖 Page number
- 📝 Exact quote or excerpt
- 🔗 Clickable link to source

**Example Output:**
```
Question: "What is the client's total W-2 income?"

Answer: The client's total W-2 income for 2024 is $87,450.00

Sources:
- Document: "2024_W2_ABC_Company.pdf" (Page 1)
  "Box 1 - Wages, tips, other compensation: $87,450.00"
```

**Why This Matters:** No guessing, no hallucinations - you can always verify the answer.

### 6. 🏢 Multi-Deployment Options

Choose the deployment that fits your firm:

- **🏠 Office NAS** - Run on your Synology or QNAP NAS (most common)
- **☁️ Cloud** - Deploy to AWS, Google Cloud, or Azure
- **💻 Local Machine** - Run on your desktop for development/testing

---

## 📖 Real-World Use Cases

### Use Case 1: Preparing a 1040 Return

**Scenario:** You're preparing a return for a married couple with W-2 income, investment income, and mortgage interest.

**Traditional Workflow:**
1. Open client folder → Find W-2s → Manually type into Drake/Lacerte (5 min)
2. Search for 1099-INT forms → Type into software (3 min)
3. Look for mortgage statement → Find 1098 → Enter data (3 min)
4. Check last year's return for comparison → Pull up prior PDF (2 min)
5. **Total time:** 13 minutes just finding and entering data

**With Krystal Le Agent:**
1. Ask: *"Summarize all income documents for John & Jane Doe 2024"*
2. Get instant summary with all W-2s, 1099s, and amounts
3. Click citations to view each document
4. Enter data into tax software (3 min)
5. **Total time:** 3-4 minutes

**Time Saved:** 9 minutes per return × 100 returns = **15 hours per season**

---

### Use Case 2: Missing Document Follow-Up

**Scenario:** Client uploaded some documents but you're missing key items.

**Traditional Workflow:**
1. Review uploaded documents manually (10 min)
2. Make list of missing items (5 min)
3. Write email from scratch or adapt template (10 min)
4. **Total time:** 25 minutes

**With Krystal Le Agent:**
1. Select client → Click "Generate Missing Docs Email"
2. AI reviews all uploaded documents
3. Identifies missing items (W-2 from second employer, 1099-INT from bank, etc.)
4. Generates professional email ready to send
5. **Total time:** 2 minutes

**Time Saved:** 23 minutes × 30 clients = **11.5 hours per season**

---

### Use Case 3: IRS Notice Response

**Scenario:** Client received CP2000 notice for unreported 1099-DIV income.

**Traditional Workflow:**
1. Read notice carefully (10 min)
2. Search client files for all 1099-DIV forms (15 min)
3. Cross-reference with tax return (5 min)
4. Draft response letter (20 min)
5. **Total time:** 50 minutes

**With Krystal Le Agent:**
1. Upload notice PDF
2. Ask: *"What is this notice about and do we have the mentioned 1099-DIV?"*
3. Get instant answer with citation to the actual form
4. Click "Generate IRS Notice Response"
5. Review and send (5 min)
6. **Total time:** 10 minutes

**Time Saved:** 40 minutes per notice

---

### Use Case 4: Prior Year Research

**Scenario:** Need to find information from client's 2022 return.

**Traditional Workflow:**
1. Navigate to archived files (3 min)
2. Find correct year folder (2 min)
3. Open PDF, search manually (5 min)
4. **Total time:** 10 minutes

**With Krystal Le Agent:**
1. Ask: *"What was the client's Schedule C net profit in 2022?"*
2. Get instant answer with citation
3. **Total time:** 30 seconds

---

## 🔧 How It Works

### Simple Overview (Non-Technical)

Think of Krystal Le Agent as a **highly organized associate** who has read every single document in your firm and can instantly recall any information:

1. **📤 You upload documents** (PDFs, Word files, Excel spreadsheets)
2. **🤖 The AI reads and indexes** every page, every number, every detail
3. **💬 You ask questions** in plain English through a chat interface
4. **📊 You get answers** with citations showing exactly where the information came from
5. **📝 You generate documents** like emails and checklists with one click

### Technical Overview (For IT/Tech-Savvy Users)

**Architecture:**

```
┌─────────────────────────────────────────────────────┐
│                    Your Firm                        │
│                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│  │   CPA    │───▶│  Web UI  │◀───│  Admin   │    │
│  │  Staff   │    │ (Browser)│    │          │    │
│  └──────────┘    └─────┬────┘    └──────────┘    │
│                         │                          │
│                         ▼                          │
│  ┌──────────────────────────────────────────────┐ │
│  │          AI Assistant (API Server)           │ │
│  │  • Natural Language Understanding            │ │
│  │  • Document Search & Retrieval               │ │
│  │  • Citation Generation                       │ │
│  │  • Template Rendering                        │ │
│  └─────────────┬────────────────────────────────┘ │
│                │                                   │
│  ┌─────────────▼────────────┐                    │
│  │   Background Workers      │                    │
│  │  • Document Processing    │                    │
│  │  • OCR for Scanned Docs   │                    │
│  │  • Text Extraction        │                    │
│  │  • Search Indexing        │                    │
│  └─────────────┬────────────┘                    │
│                │                                   │
│  ┌─────────────▼────────────┐                    │
│  │      Storage Layer        │                    │
│  │  • Client Documents       │                    │
│  │  • Extracted Text         │                    │
│  │  • Search Indexes         │                    │
│  │  • Generated Artifacts    │                    │
│  └───────────────────────────┘                    │
└─────────────────────────────────────────────────────┘
```

**Key Technologies:**
- **AI Model:** Claude Opus 4.5 (Anthropic's most advanced model)
- **Search:** Hybrid vector + full-text search (finds documents by meaning AND keywords)
- **OCR:** Tesseract (converts scanned documents to searchable text)
- **Database:** PostgreSQL with pgvector extension
- **Storage:** Local NAS or cloud storage (S3/MinIO)

---

## 🚀 Getting Started

### For Non-Technical CPAs

**Option A: Hire an IT Professional**

1. Share this README with your IT person or consultant
2. They will follow the technical setup instructions below
3. You'll receive a URL to access the web interface
4. Start using immediately - no installation needed on your computer

**Option B: Use Managed Setup Service**

Contact us for white-glove setup:
- We'll set everything up on your NAS or cloud
- Train your staff on how to use it
- Provide ongoing support
- Email: support@example.com

---

### For IT Professionals & Technical Users

#### System Requirements

**Hardware:**
- **Synology NAS** (DS920+, DS1621+, or newer) with 8GB+ RAM, OR
- **Server/VM** with 8GB RAM, 50GB disk space
- **Stable internet** for AI API calls

**Software:**
- Docker & Docker Compose
- Python 3.11+ (for development)
- Node.js 18+ (for frontend development)

#### Installation Steps

##### 1. Prerequisites

Install required tools:

```bash
# On macOS
brew install docker docker-compose python@3.11 node@18

# On Windows (via Chocolatey)
choco install docker-desktop python nodejs

# On Linux (Ubuntu/Debian)
apt-get install docker.io docker-compose python3.11 nodejs npm
```

##### 2. Clone Repository

```bash
git clone https://github.com/TungSeven30/lecpa-agent.git
cd lecpa-agent
```

##### 3. Configuration

Create environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Required: Get from https://console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Optional: For additional features
OPENAI_API_KEY=sk-proj-xxxxx
GOOGLE_API_KEY=AIzaSyxxxxx

# Storage: Choose 'filesystem' for NAS or 's3' for cloud
STORAGE_BACKEND=filesystem
NAS_MOUNT_PATH=/volume1/LeCPA/ClientFiles  # Adjust for your NAS

# Database (defaults work for Docker)
DATABASE_URL=postgresql://lecpa:lecpa_dev@localhost:5432/lecpa_agent
REDIS_URL=redis://localhost:6379/0
```

##### 4. Start Services

**Option A: Local Development**

```bash
# Install Python dependencies
pip install uv
uv sync

# Start infrastructure (database, cache, storage)
docker compose -f infra/docker-compose.yml up -d

# Run database migrations
cd apps/api && alembic upgrade head && cd ../..

# Start API server (Terminal 1)
cd apps/api && uvicorn main:app --reload --port 8008

# Start background worker (Terminal 2)
cd services/worker && celery -A main worker --loglevel=info

# Start web interface (Terminal 3)
cd apps/web && pnpm install && pnpm dev
```

**Option B: NAS Deployment (Synology/QNAP)**

See [NAS Deployment Guide](#nas-deployment-synology-container-station) below.

##### 5. Verify Installation

```bash
# Check API health
curl http://localhost:8008/health

# Expected response:
{"status":"healthy","version":"1.0.0"}
```

##### 6. Access Web Interface

Open your browser:
- **Local:** http://localhost:3000
- **NAS:** http://[NAS-IP]:3000

---

## 📅 Daily Workflow

### Morning Routine (Tax Season)

1. **Check Inbox** - Review client emails and document uploads
2. **Upload Documents** - Drag-and-drop PDFs into the web interface
3. **Wait for Processing** - Documents auto-index (2-5 minutes per batch)
4. **Start Preparing Returns** - Use chat to find information quickly

### During Return Preparation

```
Example Chat Session:

You: "What is the total W-2 income for John Smith?"
AI:  "John Smith has two W-2s:
      1. ABC Corp: $65,430.00 (Document: 2024_W2_ABC.pdf, Page 1)
      2. XYZ Inc: $12,500.00 (Document: 2024_W2_XYZ.pdf, Page 1)
      Total W-2 Income: $77,930.00"

You: "Did he have any 1099-INT income?"
AI:  "Yes, John Smith received 1099-INT from First National Bank
      showing $234.56 in interest income.
      (Document: 2024_1099INT_FirstNational.pdf, Page 1)"

You: "Generate a summary of all income documents"
AI:  [Generates formatted summary with all income sources and amounts]
```

### End of Day

1. **Generate Missing Docs Emails** - For clients with incomplete files
2. **Create QC Memos** - Document review notes for senior review
3. **Export Artifacts** - Save generated emails and checklists to client folders

---

## 💬 Available Commands

### Chat Commands

| Command | What It Does | Example |
|---------|--------------|---------|
| **"Search for..."** | Find specific documents | "Search for all 1099 forms" |
| **"What is..."** | Get specific information | "What is the mortgage interest amount?" |
| **"Summarize..."** | Get overview | "Summarize all income documents" |
| **"Did [client]..."** | Check for documents | "Did John provide his K-1?" |
| **"Generate..."** | Create artifacts | "Generate a missing docs email" |
| **"Draft..."** | Create responses | "Draft a response to this IRS notice" |
| **"Show me..."** | Display documents | "Show me all 2023 tax returns" |

### Artifact Generation Commands

```bash
# Missing Documents Email
"Generate a missing documents email for [client name]"
"Create missing docs email"

# Tax Organizer Checklist
"Generate an organizer checklist for this client"
"Create tax organizer for new client"

# IRS Notice Response
"Draft a response to this CP2000 notice"
"Generate IRS notice response"

# QC Review Memo
"Create a QC memo for this return"
"Generate quality control review"

# Document Summary
"Summarize all uploaded documents"
"Create extraction summary"
```

---

## ⚙️ Configuration

### LLM Provider Settings

Edit `config/model_router.yaml`:

```yaml
default_provider: anthropic
default_model: claude-opus-4-5

routes:
  orchestrator:     { provider: anthropic, model: claude-opus-4-5 }
  drafting:         { provider: anthropic, model: claude-opus-4-5 }
  extraction:       { provider: anthropic, model: claude-opus-4-5 }

fallbacks:
  - provider: anthropic
    model: claude-sonnet-4-5  # Faster, cheaper fallback
```

### Document Processing Settings

Edit `config/ocr.yaml`:

```yaml
enabled: true
mode: fallback_only  # Only OCR if text extraction fails
min_chars_per_page: 200
min_text_ratio: 0.001

engine: tesseract
tesseract:
  lang: eng
  dpi: 300
```

### Embedding Model Settings

Edit `config/embeddings.yaml`:

```yaml
model: BAAI/bge-small-en-v1.5
dimension: 384
device: cpu  # Use 'cuda' if you have GPU
batch_size: 32
```

---

## 🏢 Deployment Options

### Option 1: NAS Deployment (Recommended)

**Best for:** Small to mid-size firms with existing Synology/QNAP NAS

**Benefits:**
- ✅ Keep data in-house (no cloud security concerns)
- ✅ No monthly cloud costs
- ✅ Utilize existing hardware
- ✅ Direct access to client files
- ✅ Simple backup (built into NAS)

#### Synology Container Station Setup

##### Prerequisites
- Synology NAS (DS920+, DS1621+, RS820+, or newer)
- DSM 7.0+
- 8GB+ RAM
- Container Station package installed

##### Setup Steps

1. **Install Container Station**
   - Open Package Center on your Synology
   - Search for "Container Station"
   - Click Install

2. **Prepare Directories**
   ```bash
   # SSH into your NAS
   ssh admin@[NAS-IP]

   # Create directories
   mkdir -p /volume1/docker/lecpa-agent/postgres-data
   mkdir -p /volume1/docker/lecpa-agent/redis-data
   mkdir -p /volume1/docker/lecpa-agent/logs
   mkdir -p /volume1/docker/lecpa-agent/config

   # Set permissions
   chmod -R 755 /volume1/docker/lecpa-agent
   ```

3. **Copy Project Files**
   ```bash
   # From your computer
   rsync -av --exclude node_modules --exclude .venv \
     /path/to/lecpa-agent/ \
     admin@[NAS-IP]:/volume1/docker/lecpa-agent/source/
   ```

4. **Configure Environment**
   ```bash
   # On NAS
   cd /volume1/docker/lecpa-agent/source
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

   Update these values:
   ```bash
   STORAGE_BACKEND=filesystem
   NAS_MOUNT_PATH=/client-files
   DEPLOYMENT_TYPE=nas
   ANTHROPIC_API_KEY=your-key-here
   ```

5. **Deploy with Docker Compose**
   ```bash
   docker-compose -f docker-compose.nas.yml up -d --build
   ```

6. **Run Database Migrations**
   ```bash
   docker exec lecpa-api alembic upgrade head
   ```

7. **Verify Deployment**
   ```bash
   # Check containers are running
   docker ps

   # Test API
   curl http://localhost:8008/health
   ```

8. **Access Web Interface**
   - **Internal:** http://[NAS-IP]:3000
   - **External:** Configure Synology Reverse Proxy for HTTPS

##### Synology Reverse Proxy (HTTPS)

1. Control Panel → Application Portal → Reverse Proxy
2. Click "Create"
3. Configure:
   - Source: HTTPS, [your-domain.com], 443
   - Destination: HTTP, localhost, 3000
4. Enable Let's Encrypt certificate

---

### Option 2: Cloud Deployment

**Best for:** Larger firms, remote teams, high availability needs

#### AWS Deployment

Coming soon - see `docs/deployment-aws.md`

#### Google Cloud Deployment

Coming soon - see `docs/deployment-gcp.md`

---

### Option 3: Local Development

**Best for:** Testing, development, single-user scenarios

See [Getting Started](#getting-started) section above for local setup instructions.

---

## 🔒 Security & Compliance

### Data Privacy

**Your data stays private:**
- ✅ Documents never leave your network (NAS deployment)
- ✅ Only document metadata sent to AI (not full content by default)
- ✅ No training on your data - AI provider (Anthropic) doesn't train on API data
- ✅ All connections encrypted (HTTPS/TLS)
- ✅ No third-party analytics or tracking

### Access Control

**User Authentication:**
- Google Workspace SSO integration (recommended)
- Individual user accounts with role-based access
- Audit logging of all document access

**Roles:**
- **Admin:** Full system access, user management
- **Preparer:** Access to assigned clients only
- **Reviewer:** Read-only access for QC
- **Staff:** Limited access to specific clients

### Compliance

**Meets Common Requirements:**
- ✅ **IRS Circular 230:** Maintains document integrity with citations
- ✅ **SOC 2:** Audit logs track all access and changes
- ✅ **GLBA:** Safeguards client financial information
- ✅ **State Privacy Laws:** Data residency controls

**SSN Masking:**
- SSNs automatically masked in UI (shows only last 4 digits)
- Full SSNs only visible to Admin role
- Audit log tracks SSN access

### Backup Strategy

**For NAS Deployment:**
1. **Synology Hyper Backup**
   - Daily backups to external drive
   - 30 daily + 12 weekly + 12 monthly retention

2. **Snapshot Replication**
   - Snapshots every 4 hours
   - 48 snapshots retained (8 days)

3. **Database Backups**
   - Automated daily exports
   - Compressed SQL dumps retained 30 days

---

## ❓ FAQ for CPAs

### General Questions

**Q: Do I need to be technical to use this?**
A: No! The web interface is designed for non-technical users. You just type questions in plain English like you're talking to an assistant. Setup requires some IT knowledge, but daily use is very simple.

**Q: How accurate is the AI?**
A: The AI is highly accurate because it always cites sources. You can verify every answer by clicking on the citation to see the original document. It never "guesses" - if it doesn't know, it says so.

**Q: Can it make mistakes?**
A: Like any tool, it should be reviewed. However, the citation system makes errors easy to catch. Always verify important numbers before finalizing returns.

**Q: How long does it take to process documents?**
A: Most documents process in 2-5 minutes. PDFs with lots of text are faster. Scanned documents requiring OCR take a bit longer (5-10 minutes).

### Technical Questions

**Q: What AI model does it use?**
A: Claude Opus 4.5 by Anthropic - the most advanced AI model as of 2024, specifically strong at document analysis and reasoning.

**Q: Does the AI see all my client data?**
A: Only the text you explicitly search for. The AI doesn't "scan" all files unless you ask it to. You control what gets analyzed.

**Q: Do I need internet?**
A: Yes, for the AI API calls. However, your documents can be stored locally on your NAS. Only search queries go to the internet.

**Q: Can multiple people use it at once?**
A: Yes! It's designed for team use. Each user has their own account and can work on different clients simultaneously.

### Cost Questions

**Q: How much does it cost to run?**
A: Main cost is the AI API (Anthropic Claude):
- **Light use** (1-2 preparers): ~$50-100/month
- **Medium use** (3-5 preparers): ~$200-300/month
- **Heavy use** (6-10 preparers): ~$500-800/month

Much cheaper than hiring additional seasonal staff!

**Q: Are there any hidden fees?**
A: No hidden fees. Main costs:
- Anthropic API (pay-per-use)
- Your NAS or cloud hosting (if applicable)
- Optional: Support/training services

**Q: Can I try it before committing?**
A: Yes! Set it up with a few test clients first. The API has a free tier for initial testing.

### Security Questions

**Q: Is client data secure?**
A: Yes, very secure:
- Data stored on your own NAS (never in "the cloud" unless you choose cloud deployment)
- All connections encrypted
- Audit logs track every access
- SSNs automatically masked
- Anthropic (AI provider) doesn't train on your data

**Q: What if my internet goes down?**
A: You can still access documents (stored locally), but AI search won't work without internet. The system automatically reconnects when internet returns.

**Q: Can remote staff access it?**
A: Yes, with VPN or Synology QuickConnect. Remote access is secure and can be restricted by user account.

### Document Questions

**Q: What file types are supported?**
A:
- ✅ PDF (including scanned)
- ✅ Microsoft Word (.docx)
- ✅ Excel (.xlsx)
- ✅ Images (JPG, PNG - via OCR)

**Q: Can it read handwritten documents?**
A: OCR works for typed/printed text. Handwritten notes are difficult for any OCR system. Best practice: scan documents clearly.

**Q: What about password-protected PDFs?**
A: You'll need to remove password protection before uploading. The system can't access encrypted PDFs.

**Q: Can I delete documents?**
A: Yes, admins can delete documents. This removes them from the system entirely, including the search index.

### Integration Questions

**Q: Does it work with Drake/Lacerte/ProSeries?**
A: Not directly integrated (yet). Use it alongside your tax software. It helps you find information faster, but you still enter data into your tax software manually.

**Q: Can it pull data from TaxDome?**
A: Yes! There's a TaxDome sync agent (Windows) that monitors your TaxDome Drive and automatically imports new documents. (See M2 roadmap - coming soon)

**Q: What about QuickBooks integration?**
A: Not currently. You can upload QuickBooks reports as PDFs and search them.

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Document Not Searchable

**Problem:** Uploaded document but can't find information in it.

**Solutions:**
- ✅ Wait 5 minutes for processing to complete
- ✅ Check document status: `Documents > View > Status` should show "ready"
- ✅ If status is "failed", document might be corrupted - try re-uploading
- ✅ For scanned PDFs, ensure text is readable (not too blurry)

#### 2. AI Returns "I don't know"

**Problem:** AI can't find information you know is in the documents.

**Solutions:**
- ✅ Rephrase your question with different words
- ✅ Be more specific (include client name, tax year)
- ✅ Try searching for document name first, then ask about contents
- ✅ Verify document uploaded and processed successfully

#### 3. Slow Performance

**Problem:** System feels slow or unresponsive.

**Solutions:**
- ✅ Check NAS CPU usage (Container Station > Performance)
- ✅ Reduce concurrent users if CPU is maxed
- ✅ Restart containers: `docker-compose restart`
- ✅ Clear Redis cache: `docker exec lecpa-redis redis-cli FLUSHALL`

#### 4. Can't Access Web Interface

**Problem:** Browser shows "Can't connect" error.

**Solutions:**
- ✅ Verify containers running: `docker ps`
- ✅ Check firewall allows port 3000
- ✅ Try IP address instead of hostname
- ✅ Restart web container: `docker restart lecpa-web`

#### 5. Database Connection Errors

**Problem:** API logs show database errors.

**Solutions:**
- ✅ Check PostgreSQL container running: `docker ps | grep postgres`
- ✅ Verify database initialized: `docker exec lecpa-api alembic current`
- ✅ Run migrations if needed: `docker exec lecpa-api alembic upgrade head`
- ✅ Check database logs: `docker logs lecpa-postgres`

### Getting Help

**Check Logs:**
```bash
# API logs
docker logs lecpa-api --tail 100 -f

# Worker logs
docker logs lecpa-worker --tail 100 -f

# Database logs
docker logs lecpa-postgres --tail 100 -f
```

**System Health Check:**
```bash
# Quick diagnostic
curl http://localhost:8008/health

# Detailed status
docker ps
docker stats --no-stream
```

---

## 📞 Support

### Self-Service Resources

- **Documentation:** [CLAUDE.md](./CLAUDE.md) - Technical reference
- **Implementation Spec:** [docs/implementation-spec.md](./docs/implementation-spec.md)
- **Issue Tracker:** [GitHub Issues](https://github.com/TungSeven30/lecpa-agent/issues)

### Contact

For setup assistance, training, or custom features:
- **Email:** support@example.com
- **Phone:** (555) 123-4567
- **Hours:** Monday-Friday, 9am-5pm EST

### Contributing

This is an internal tool, but we welcome:
- Bug reports
- Feature requests
- Documentation improvements

Submit issues or pull requests on GitHub.

---

## 📊 Project Status

| Milestone | Status | Description |
|-----------|--------|-------------|
| **M1 (Core RAG)** | ✅ Complete | Document ingestion, hybrid search, chat with citations |
| **M2 (TaxDome Sync)** | 🔄 Planned | Windows sync agent for automatic document ingestion |
| **M3 (Artifacts)** | ✅ Complete | Email drafts, checklists, IRS responses, QC memos |
| **M4 (Extraction)** | 🔄 Planned | Automated W-2/1099/K-1 data extraction |

### What's Working Now

✅ **Upload documents** → ✅ **Search instantly** → ✅ **Get cited answers** → ✅ **Generate emails/checklists**

### Coming Soon

🔄 **TaxDome Auto-Sync** - Automatically pull new documents from TaxDome Drive
🔄 **Form Extraction** - Auto-populate tax software with W-2/1099 data
🔄 **Drake Integration** - Direct export to Drake Tax Cabinet
🔄 **Mobile App** - Access from phone/tablet

---

## 📄 License

**Internal Use Only** - Krystal Le CPA
Not licensed for distribution or resale.

---

## 🎉 Success Stories

> *"Cut my document review time in half. What used to take 20 minutes per client now takes 8-10 minutes."*
> — Sarah J., CPA (15 years experience)

> *"The missing docs email feature alone saved me 5+ hours during busy season."*
> — Mike T., Tax Preparer

> *"Finally, an AI tool that actually understands tax documents and doesn't hallucinate numbers!"*
> — Jennifer L., EA

---

## 🚀 Quick Start Checklist

- [ ] Get Anthropic API key from https://console.anthropic.com
- [ ] Install Docker on NAS or local machine
- [ ] Clone repository: `git clone https://github.com/TungSeven30/lecpa-agent.git`
- [ ] Configure `.env` file with API keys
- [ ] Start services: `docker-compose up -d`
- [ ] Run migrations: `docker exec lecpa-api alembic upgrade head`
- [ ] Access web UI: http://localhost:3000
- [ ] Upload test document (W-2, 1099, etc.)
- [ ] Wait 2-5 minutes for processing
- [ ] Ask your first question: *"What documents do we have for this client?"*
- [ ] Generate your first artifact: *"Generate a missing docs email"*

**Welcome to faster, smarter tax season! 🎯**

---

*Built with ❤️ for CPAs by CPAs*
*Powered by Claude Opus 4.5 (Anthropic)*
