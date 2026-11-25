# Nexzen ERP — সম্পূর্ণ ইউজার গাইড, আর্কিটেকচার ও টেস্টিং ম্যানুয়াল

**প্রোডাক্ট:** Nexzen ERP
**নির্মাতা:** Nexzen Solution Ltd.
**টার্গেট মার্কেট:** বাংলাদেশের ক্ষুদ্র, মাঝারি ও বৃহৎ ব্যবসা (Cloud SaaS ও On-Premise দুটি মোডেই ব্যবহারযোগ্য)

---

## ১. এই সফটওয়্যারটির কাজ কী? (Overview)

**Nexzen ERP** একটি পূর্ণাঙ্গ, এন্টারপ্রাইজ-গ্রেড **Enterprise Resource Planning (ERP)** সফটওয়্যার যা একটি কোম্পানির **হিসাববিজ্ঞান (Accounting & GL), বিক্রয় (Sales), ক্রয় (Purchase), গুদাম ও স্টক (Inventory), বাংলাদেশ ভ্যাট ও মূসক (VAT/Mushak), মানবসম্পদ ও বেতন (HR & Payroll), এবং আর্থিক বিশ্লেষণ (Dashboard, P&L, Balance Sheet)**—সবকিছু একটি কেন্দ্রীয় ডাবল-এন্ট্রি সিস্টেমে পরিচালনা করে।

### মূল বিশেষত্বসমূহ
1. **ডাবল-এন্ট্রি জেনারেল লেজার (Double-Entry GL Core):** প্রতিটি সেলস ইনভয়েস, পারচেজ বিল, পেমেন্ট এবং মাসিক পেরোল পোস্ট করার সাথে সাথে স্বয়ংক্রিয়ভাবে সুষম (`Total Debit = Total Credit`) জার্নাল তৈরি হয়।
2. **মাল্টি-টেন্যান্ট ও ডাটাবেস-লেভেল নিরাপত্তা (PostgreSQL RLS):** একই ক্লাউড ডাটাবেসে একাধিক কোম্পানি থাকলেও PostgreSQL Row-Level Security (RLS) নিশ্চিত করে যে এক কোম্পানির ডেটা অন্য কোম্পানি কখনোই দেখতে পারবে না।
3. **অপরিবর্তনীয় অডিট লগ (Immutable Audit Trail):** সিস্টেমে কে, কখন, কী পরিবর্তন করেছে তা `audit_logs` টেবিলে সংরক্ষিত থাকে এবং ডাটাবেস ট্রিগারের মাধ্যমে এটি মুছে ফেলা বা এডিট করা সম্পূর্ণ নিষিদ্ধ।
4. **বাংলাদেশি লোকালাইজেশন:** `৳` (BDT) লাখ/কোটি ফরম্যাটিং (`৳15,00,000.00`), বাংলা ও ইংরেজি ভাষা সুইচ, বাংলা ডিজিট (`১২৩`) টগল, এবং কনফিগারেবল ভ্যাট/টিডিএস/ভিডিএস ও মূসক (৬.১, ৬.২, ৬.৩, ৯.১) রিপোর্ট।
5. **নিখুঁত আর্থিক হিসাব:** পুরো ব্যাকএন্ডে `Decimal` এবং PostgreSQL-এ `NUMERIC(18,2)` ব্যবহৃত হয়েছে—কোনো `float` নেই, ফলে ১ পয়সারও হিসাবের গরমিল হয় না।

---

## ২. লাইভ লিংক ও ডেমো লগইন ক্রেডেনশিয়াল (Demo Credentials)

### লোকাল সার্ভার লিংক
| সার্ভিস | URL | বিবরণ |
|---|---|---|
| **ওয়েব অ্যাপ (Frontend)** | `http://127.0.0.1:5173` | মূল ERP ইউজার ইন্টারফেস (ডেক্সটপ ও মোবাইল রেসপন্সিভ) |
| **API ডকুমেন্টেশন (Swagger)** | `http://127.0.0.1:8000/docs` | সব REST API সরাসরি টেস্ট করার ইন্টারঅ্যাক্টিভ পেজ |
| **সিস্টেম হেলথ চেক** | `http://127.0.0.1:8000/health/ready` | PostgreSQL (Neon) ও Redis কানেকশন স্ট্যাটাস |

### ডেমো ইউজার অ্যাকাউন্ট (Tenant: `nexzen-demo`)
| রোল (Role) | কোম্পানি কোড (`Company Code`) | ইমেইল (`Email`) | পাসওয়ার্ড (`Password`) | ক্ষমতা (Access) |
|---|---|---|---|---|
| **Tenant Admin (পূর্ণ নিয়ন্ত্রণ)** | `nexzen-demo` | `admin@nexzen.com` | `NexzenAdmin!2026` | সব মডিউল দেখা, তৈরি, পোস্ট ও পরিচালনা |
| **Auditor (শুধু দেখার অনুমতি)** | `nexzen-demo` | `auditor@nexzen.com` | `NexzenAudit!2026` | সব রিপোর্ট, লেজার, মূসক ও অডিট লগ Read-Only |

> **টিপস:** লগইন করার পর ব্রাউজার রিলোড দিলেও লগআউট হবে না—সেশন স্বয়ংক্রিয়ভাবে Refresh Token Rotation-এর মাধ্যমে রিস্টোর হয়।

---

## ৩. সিস্টেমটি কীভাবে কাজ করে? (Architecture & Data Flow)

```text
[React 18 + TypeScript + TanStack Query + Recharts]
                        │  HTTPS / JWT Bearer Token
                        ▼
[FastAPI Router (Thin Layer — Zero Business Logic)]
                        │  RBAC Permission Check (require_permission)
                        ▼
[Service Layer (Double-Entry Math, Stock Rules, Audit Recording)]
                        │  Tenant-Scoped Atomic Transaction
                        ▼
[Repository Layer (Parameterized SQLAlchemy 2.0 Async Queries)]
                        │  SET LOCAL app.current_tenant_id = '<tenant_uuid>'
                        ▼
[PostgreSQL 18 (Neon) with Row-Level Security + Redis Cloud (Auth/Lockout)]
```

---

## ৪. মডিউল-ভিত্তিক কার্যকারিতা ও স্টেপ-বাই-স্টেপ টেস্টিং গাইড

সিস্টেমে আগে থেকেই বাংলাদেশের বাস্তব ব্যবসার ডেমো ডেটা সিড করা আছে, যাতে আপনি লগইন করেই সব গ্রাফ, রিপোর্ট ও মডিউল সরাসরি টেস্ট করতে পারেন।

---

### মডিউল ০: এক্সিকিউটিভ ড্যাশবোর্ড (`/`)
**কাজ:** পুরো ব্যবসার আর্থিক ও অপারেশনাল অবস্থা এক নজরে দেখায়।
- **আর্থিক KPI:** মোট আয় (Revenue), মোট ব্যয় (Expense), নিট লাভ (Net Profit), মোট সম্পদ (Assets)।
- **ইন্টারঅ্যাক্টিভ গ্রাফ (Recharts):**
  - **মাসিক আয় ও ব্যয়ের গ্রাফ:** ৩ মাসের (সেপ্টেম্বর–নভেম্বর ২০২৬) ডেটা দিয়ে Area ও Bar চার্ট সুইচ করে দেখতে পারবেন।
  - **ব্যয়ের বিভাজন ডোনাট চার্ট:** কোন খাতে কত খরচ হয়েছে তার শতাংশ।
- **অপারেশনাল KPI:** কাস্টমার বকেয়া (AR), সাপ্লায়ার বকেয়া (AP), সক্রিয় কর্মচারী সংখ্যা ও লো-স্টক অ্যালার্ট।

**কীভাবে টেস্ট করবেন:**
1. `admin@nexzen.com` দিয়ে লগইন করুন।
2. ড্যাশবোর্ডে ৮টি KPI কার্ড ও ২টি ইন্টারঅ্যাক্টিভ চার্ট দেখুন।
3. চার্টের উপরে **Area / Bar** বাটনে ক্লিক করে চার্ট মোড পরিবর্তন করুন এবং মাউস হোভার করে `৳` টুলটিপ দেখুন।
4. উপরের ডানদিকে **বাংলা / EN** এবং **বাংলা ডিজিট (`১২৩`)** টগল করে পুরো অ্যাপে বাংলা ফরম্যাটিং দেখুন।

---

### মডিউল ১: হিসাববিজ্ঞান ও জেনারেল লেজার (Accounting & GL)
**পেজসমূহ:**
- `/accounting/accounts` — চার্ট অব অ্যাকাউন্টস (Chart of Accounts)
- `/accounting/journals` — জার্নাল ভাউচার (Journal Vouchers)
- `/accounting/trial-balance` — ট্রায়াল ব্যালেন্স (Trial Balance)
- `/reports/statements` — লাভ-ক্ষতি (P&L) ও ব্যালেন্স শিট (Balance Sheet)

**কীভাবে কাজ করে:**
- প্রতিটি হিসাব খাত ৫টি প্রধান ধরনের একটি: `Asset`, `Liability`, `Equity`, `Revenue`, `Expense`।
- জার্নাল ভাউচারে `Total Debit == Total Credit` না হলে সিস্টেম পোস্ট করতে দেয় না।
- পোস্টকৃত জার্নাল এডিট বা ডিলিট করা যায় না—ভুল সংশোধনের জন্য **Reverse** বাটনে ক্লিক করলে বিপরীত এন্ট্রি তৈরি হয়।

**কীভাবে টেস্ট করবেন:**
1. **Chart of Accounts:** ২০টি বাংলাদেশি স্ট্যান্ডার্ড খাত (`1110 Cash`, `1120 Bank`, `4100 Sales`, `5200 Salaries` ইত্যাদি) দেখতে পাবেন। চাইলে **New Account** দিয়ে নতুন একটি খাত (যেমন `5400 Marketing Expense`) যোগ করুন।
2. **Journal Vouchers:** **New Journal Voucher** ক্লিক করে `DR 5300 Office Rent 10000` এবং `CR 1110 Cash 10000` দিয়ে **Save Draft** -> তারপর **Post** করুন।
3. **Trial Balance & P&L / Balance Sheet:** `/accounting/trial-balance` এবং `/reports/statements` পেজে গিয়ে দেখুন `Balanced` ব্যাজ দেখাচ্ছে এবং `Total Assets = Total Liabilities + Equity` সম্পূর্ণ মিলে গেছে।

---

### মডিউল ২: বিক্রয় ও ইনভয়েসিং (Sales & Invoicing)
**পেজসমূহ:** `/sales/customers` ও `/sales/invoices`

**কীভাবে কাজ করে:**
- প্রতিটি ইনভয়েসে লাইন-ভিত্তিক কনফিগারেবল ভ্যাট (%) যোগ করা যায়।
- **Post to GL** ক্লিক করলে স্বয়ংক্রিয়ভাবে তৈরি হয়:
  - `DR 1200 Accounts Receivable` = সর্বমোট (Grand Total)
  - `CR 4100 Sales Revenue` = উপ-মোট (Subtotal)
  - `CR 2200 VAT Output Payable` = মোট ভ্যাট (VAT Total)
- **Receive Payment** ক্লিক করলে `DR Cash/Bank`, `CR 1200 Accounts Receivable` পোস্ট হয় এবং ইনভয়েস স্ট্যাটাস `PARTIALLY PAID` বা `PAID` হয়।

**ডেমো ডেটা যা আগে থেকে আছে:**
- ২টি কাস্টমার: `Dhaka Retail Mart Ltd.` (BIN সহ) ও `Chattogram Tech Solutions` (BIN সহ)।
- ২টি পোস্টকৃত সেলস ইনভয়েস (একটি আংশিক পরিশোধিত, একটি বকেয়া)।

**কীভাবে টেস্ট করবেন:**
1. `/sales/invoices`-এ গিয়ে বকেয়া ইনভয়েসটিতে **Receive Payment** ক্লিক করে `1120 Bank Account` সিলেক্ট করে টাকা রিসিভ করুন।
2. ড্যাশবোর্ডে ফিরে গিয়ে দেখুন **কাস্টমার বকেয়া (AR)** কমে গেছে!

---

### মডিউল ৩: ক্রয় ও সাপ্লায়ার (Purchase & Supplier)
**পেজসমূহ:** `/purchase/suppliers` ও `/purchase/bills`

**কীভাবে কাজ করে:**
- সাপ্লায়ার বিলে কনফিগারেবল **Input VAT %**, **TDS %** এবং **VDS %** হিসাব করা হয়।
- **Post to GL** ক্লিক করলে স্বয়ংক্রিয়ভাবে তৈরি হয়:
  - `DR Expense / Inventory Account` = Subtotal
  - `DR 1400 VAT Input Receivable` = Input VAT
  - `CR 2100 Accounts Payable` = Net Payable (`Gross - TDS - VDS`)
  - `CR 2210 TDS / VDS Payable` = `TDS + VDS`

**ডেমো ডেটা যা আগে থেকে আছে:**
- ২টি সাপ্লায়ার: `Meghna Wholesale Supplies` ও `Gazipur Industrial Traders`।
- ১টি পোস্টকৃত পারচেজ বিল (`15% VAT`, `3% TDS`, `5% VDS` এবং আংশিক পেমেন্টসহ)।

**কীভাবে টেস্ট করবেন:**
1. `/purchase/bills`-এ **New Purchase Bill** তৈরি করে সাপ্লায়ার, খরচ খাত (`5100`), ১৫% ভ্যাট, ৩% TDS, ৫% VDS দিয়ে **Save Draft** -> **Post to GL** করুন।
2. **Pay Supplier** ক্লিক করে সাপ্লায়ারকে পেমেন্ট দিন।

---

### মডিউল ৪: ইনভেন্টরি ও গুদাম (Inventory & Warehouse)
**পেজসমূহ:** `/inventory/catalog` ও `/inventory/stock`

**কীভাবে কাজ করে:**
- একাধিক গুদাম (Warehouse) ও প্রোডাক্ট SKU পরিচালনা করা যায়।
- **নেগেটিভ স্টক প্রোটেকশন:** মজুদের চেয়ে বেশি পণ্য Stock Out করতে চাইলে সিস্টেম `422` এরর দিয়ে ব্লক করে।
- কোনো পণ্যের মজুদ `Reorder Level`-এর নিচে নামলে স্বয়ংক্রিয়ভাবে **Low-Stock Alert** দেখায়।

**ডেমো ডেটা যা আগে থেকে আছে:**
- ২টি গুদাম: `WH-DHK` (Dhaka Central Warehouse), `WH-CTG` (Chattogram Port Depot)।
- ৪টি পণ্য: এর মধ্যে `SKU-RBN-04` (Thermal Wax Ribbon Roll) এর মজুদ `6` এবং Reorder Level `15`—ফলে লাইভ **Low-Stock Alert** দেখাবে!

**কীভাবে টেস্ট করবেন:**
1. `/inventory/stock`-এ গিয়ে মোট ইনভেন্টরি ভ্যালুয়েশন ও লো-স্টক অ্যালার্ট দেখুন।
2. `SKU-RBN-04`-এ `10` পিস **Stock In** করুন—দেখবেন লো-স্টক অ্যালার্ট কমে ০ হয়ে যাবে।
3. মজুদের চেয়ে বেশি **Stock Out** দিয়ে দেখুন সিস্টেম নেগেটিভ স্টক আটকে দেয়।

---

### মডিউল ৫: বাংলাদেশ ভ্যাট ও মূসক (VAT & Mushak)
**পেজ:** `/vat/mushak`

**কীভাবে কাজ করে:**
- কোনো সরকারি রেট হার্ডকোড করা হয়নি—সব ভ্যাট রেট টেন্যান্ট নিজে কনফিগার করতে পারে (`VAT-15`, `VAT-7.5`, `VAT-0`)।
- পোস্টকৃত পারচেজ বিল ও সেলস ইনভয়েস থেকে রিয়েল-টাইমে তৈরি হয়:
  - **মূসক ৯.১ (Mushak 9.1 Summary):** Output VAT, Input VAT, Net VAT Payable / Carry-Forward Credit, VDS ও TDS প্রদেয়।
  - **মূসক ৬.১ (Purchase Register):** সাপ্লায়ারের BIN-সহ ক্রয় হিসাব।
  - **মূসক ৬.২ (Sales Register):** কাস্টমারের BIN-সহ বিক্রয় হিসাব।
  - **মূসক ৬.৩ (Tax Invoice Challan):** যেকোনো বিক্রয় ইনভয়েসের পাশে **Mushak 6.3** ক্লিক করলে প্রিন্টযোগ্য কর চালানপত্র ওপেন হয়।

**কীভাবে টেস্ট করবেন:**
1. `/vat/mushak`-এ গিয়ে ৪টি ট্যাব (**Mushak 9.1**, **Mushak 6.1**, **Mushak 6.2**, **VAT Rates**) ঘুরে দেখুন।
2. **Mushak 6.2** ট্যাবে যেকোনো ইনভয়েসের পাশে **Mushak 6.3** ক্লিক করুন এবং **Print Challan** চেপে প্রিন্ট প্রিভিউ দেখুন।

> **NBR নোট:** মূসক ৯.১ ও কর রেটসমূহ ওয়ার্কিং পেপার হিসেবে তৈরি—চূড়ান্ত সরকারি রিটার্ন দাখিলের আগে আপনার ট্যাক্স/ভ্যাট পরামর্শকের সাথে যাচাই করে নেবেন।

---

### মডিউল ৬: মানবসম্পদ ও মাসিক বেতন (HR & Payroll)
**পেজসমূহ:** `/hr/employees` ও `/hr/payroll`

**কীভাবে কাজ করে:**
- প্রতিটি কর্মচারীর মূল বেতন, বাড়ি ভাড়া, চিকিৎসা, যাতায়াত, PF % এবং মাসিক আয়কর (AIT) কনফিগার করা যায়।
- **Generate Payroll Run** ক্লিক করলে সব সক্রিয় কর্মচারীর পে-স্লিপ স্বয়ংক্রিয়ভাবে হিসাব হয় (একই মাসে ডুপ্লিকেট পেরোল রান ব্লক করা হয়)।
- **Post to GL** ক্লিক করলে স্বয়ংক্রিয়ভাবে তৈরি হয়:
  - `DR Salary Expense (5200)` = মোট Gross বেতন
  - `CR Bank / Payment Account (1120)` = মোট নিট বেতন (Net Pay)
  - `CR PF & Tax Payable (2210)` = মোট কর্তন (PF + Tax)

**ডেমো ডেটা যা আগে থেকে আছে:**
- ৩ জন কর্মচারী (`EMP-001`, `EMP-002`, `EMP-003`)।
- `PAY-2026-10` (অক্টোবর ২০২৬) — **POSTED** (ইতিমধ্যে GL-এ যুক্ত)।
- `PAY-2026-11` (নভেম্বর ২০২৬) — **DRAFT** (আপনার টেস্ট করার জন্য প্রস্তুত!)।

**কীভাবে টেস্ট করবেন:**
1. `/hr/payroll`-এ গিয়ে `PAY-2026-11`-এর পাশে **Payslips** ক্লিক করে ৩ জন কর্মচারীর বিস্তারিত বেতন হিসাব দেখুন।
2. এরপর `PAY-2026-11`-এর পাশে **Post to GL** ক্লিক করুন -> `5200 Salaries & Wages`, `1120 Bank Account`, `2210 TDS/VDS Payable` সিলেক্ট করে পোস্ট করুন।
3. সাথে সাথে `/reports/statements` (P&L) ও ড্যাশবোর্ডে বেতন খরচ আপডেট হয়ে যাবে!

---

### মডিউল ৭: অডিট লগ ও RBAC নিরাপত্তা (`/audit-logs`)
**কীভাবে টেস্ট করবেন:**
1. `admin@nexzen.com` থেকে `/audit-logs` পেজে গিয়ে দেখুন আপনি যত কাজ করেছেন (লগইন, ইনভয়েস পোস্ট, পেরোল পোস্ট, স্টক মুভমেন্ট) সব ক্রমানুসারে Request ID-সহ জমা আছে।
2. লগআউট করে **Auditor** (`auditor@nexzen.com` / `NexzenAudit!2026`) দিয়ে লগইন করুন—দেখবেন সে সব রিপোর্ট ও অডিট লগ দেখতে পারবে কিন্তু কোনো নতুন ইনভয়েস, অ্যাকাউন্ট বা পেরোল তৈরি/পোস্ট করার বাটন পাবে না!

---

## ৫. ডেভেলপমেন্ট ও পরিচালনার কমান্ড (PowerShell)

### ব্যাকএন্ড সার্ভার চালু করা
```powershell
Set-Location d:\ERP\backend
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

### ফ্রন্টএন্ড সার্ভার চালু করা
```powershell
Set-Location d:\ERP\frontend
npm run dev
```

### ডাটাবেস মাইগ্রেশন ও ডেমো ডেটা রিসিড করা
```powershell
# ১. সব Alembic মাইগ্রেশন চালানো
powershell -NoProfile -ExecutionPolicy Bypass -File d:\ERP\scripts\migrate.ps1

# ২. বেস টেন্যান্ট ও অ্যাডমিন সিড করা (Idempotent)
Set-Location d:\ERP\backend
$env:SEED_TENANT_CODE="nexzen-demo"
$env:SEED_ADMIN_EMAIL="admin@nexzen.com"
$env:SEED_ADMIN_PASSWORD="NexzenAdmin!2026"
.venv\Scripts\python.exe -m app.seed

# ৩. সম্পূর্ণ ডেমো বিজনেস ডেটা সিড করা (Idempotent)
.venv\Scripts\python.exe -m app.seed_demo
```

### সব টেস্ট ও লিন্ট চালানো
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File d:\ERP\scripts\lint.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File d:\ERP\scripts\test.ps1
```
