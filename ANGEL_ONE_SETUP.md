# Angel One SmartAPI Setup Guide

## 🎯 Why Angel One? BEST Free Option!

| Feature | Angel One | Zerodha | Upstox |
|---------|-----------|---------|--------|
| **API Cost** | **₹0 FREE** ✅ | ₹2,000/month | ₹1,500/month |
| **Paper Trading** | Yes (local) | Workaround | Official |
| **Python SDK** | Excellent | Excellent | Good |
| **Community** | Growing | Huge | Medium |
| **Documentation** | Very Good | Excellent | Good |
| **Real-time Data** | Included | Included | Included |
| **Recommendation** | **BEST FOR YOU** ✅ | Alternative | Alternative |

**💰 SAVINGS: ₹6,000 over 3 months of paper trading!**

---

## 📋 Step-by-Step Setup (30 Minutes)

### Step 1: Open Angel One Account (1-2 Days)

1. **Visit:** https://www.angelone.in
2. **Click:** "Open Demat Account"
3. **Documents needed:**
   - PAN Card
   - Aadhaar Card
   - Bank details
   - Photo & Signature
4. **Cost:** ₹0 (Free account opening)
5. **Timeline:** Approval in 24-48 hours

**Important:** You need a regular trading account first before getting API access.

---

### Step 2: Get API Access (5 Minutes)

Once your account is active:

1. **Login:** https://smartapi.angelone.in
2. **Navigate:** My Profile → API
3. **Click:** "Create App"
4. **Fill Details:**
   - App Name: "My Trading Bot"
   - Redirect URL: http://localhost:5000 (for testing)
   - Description: "Automated trading system"
5. **Submit:** You'll get your **API Key** immediately

**Note:** API access is **completely FREE** for retail users! No monthly charges.

---

### Step 3: Install SmartAPI Library

Open PowerShell in your Trading ALGO folder:

```powershell
cd "d:\Trading ALGO"
.\venv\Scripts\python.exe -m pip install smartapi-python pyotp
```

**Packages:**
- `smartapi-python`: Official Angel One Python SDK
- `pyotp`: For 2FA (two-factor authentication)

---

### Step 4: Setup TOTP for 2FA

Angel One requires 2FA for security. Here's how:

**Option A: Use Authenticator App (Recommended)**

1. Enable TOTP in Angel One app settings
2. Scan QR code with Google Authenticator
3. Save the secret key (backup!)
4. Use this in your code

**Option B: Get TOTP Secret**

1. Login to Angel One web
2. Go to Settings → API → TOTP
3. Click "Generate New TOTP"
4. **Save the secret key** (looks like: `JBSWY3DPEHPK3PXP`)

---

### Step 5: Update broker_interface.py

I've already added Angel One support! Just use it:

```python
from broker_interface import BrokerInterface
import pyotp

# Your credentials (get from Angel One portal)
API_KEY = "your_api_key_here"
CLIENT_ID = "your_client_id"  # Your Angel One login ID
PASSWORD = "your_password"
TOTP_SECRET = "JBSWY3DPEHPK3PXP"  # Your TOTP secret

# Generate TOTP token
totp = pyotp.TOTP(TOTP_SECRET)
totp_token = totp.now()

# Connect to Angel One
broker = BrokerInterface(
    broker="angelone",
    api_key=API_KEY,
    client_id=CLIENT_ID,
    password=PASSWORD,
    totp_token=totp_token,
    paper_trading=True  # Start with paper trading!
)

# Test connection
quote = broker.get_live_quote("RELIANCE.NS")
print(f"RELIANCE: Rs. {quote['last_price']:.2f}")
```

---

### Step 6: Create Secure Credentials File

**NEVER commit credentials to git!** Create a `.env` file:

```bash
# .env (keep this SECRET!)
ANGEL_API_KEY=your_api_key
ANGEL_CLIENT_ID=your_client_id
ANGEL_PASSWORD=your_password
ANGEL_TOTP_SECRET=your_totp_secret
```

Then load in Python:

```python
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv('ANGEL_API_KEY')
CLIENT_ID = os.getenv('ANGEL_CLIENT_ID')
# ... etc
```

Install: `.\venv\Scripts\python.exe -m pip install python-dotenv`

---

## 🧪 Testing Your Setup

### Test 1: Demo Mode (No credentials needed)

```python
from broker_interface import BrokerInterface

# Test with demo mode first (FREE, no broker account needed)
broker = BrokerInterface(broker="demo", paper_trading=True)

# Fetch a quote
quote = broker.get_live_quote("RELIANCE.NS")
print(f"✅ Demo working: Rs. {quote['last_price']:.2f}")
```

### Test 2: Angel One Connection (After setup)

```python
from broker_interface import BrokerInterface
import pyotp

# Your credentials
API_KEY = "your_key"
CLIENT_ID = "your_id"
PASSWORD = "your_password"
TOTP_SECRET = "your_secret"

# Generate TOTP
totp = pyotp.TOTP(TOTP_SECRET)

# Connect (still paper trading)
broker = BrokerInterface(
    broker="angelone",
    api_key=API_KEY,
    client_id=CLIENT_ID,
    password=PASSWORD,
    totp_token=totp.now(),
    paper_trading=True  # Safe mode!
)

# Test quote (real-time data from Angel One)
quote = broker.get_live_quote("RELIANCE.NS")
print(f"✅ Angel One working: Rs. {quote['last_price']:.2f}")

# Test paper order
order_id = broker.place_order("RELIANCE.NS", "BUY", 10)
print(f"✅ Paper order placed: {order_id}")
```

### Test 3: Full Integration Test

Run this complete test:

```python
# test_angel_one.py
from broker_interface import BrokerInterface
import pyotp
import yaml

# Load config
with open('config/phase6a_production.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Setup broker
API_KEY = "your_key"
CLIENT_ID = "your_id"
PASSWORD = "your_password"
TOTP_SECRET = "your_secret"

totp = pyotp.TOTP(TOTP_SECRET)
broker = BrokerInterface(
    broker="angelone",
    api_key=API_KEY,
    client_id=CLIENT_ID,
    password=PASSWORD,
    totp_token=totp.now(),
    paper_trading=True
)

# Test all stocks
stocks = config['stocks']
excluded = config['portfolio'].get('excluded_stocks', [])
active_stocks = [s for s in stocks if s not in excluded]

print("\n🧪 Testing Angel One Integration\n" + "="*50)

for symbol in active_stocks:
    try:
        quote = broker.get_live_quote(symbol)
        if quote:
            print(f"✅ {symbol:<20} Rs. {quote['last_price']:>10,.2f}")
        else:
            print(f"❌ {symbol:<20} Failed to fetch")
    except Exception as e:
        print(f"❌ {symbol:<20} Error: {e}")

print("="*50)
print(f"\n✅ Integration test complete!")
```

---

## 📊 Expected Results

After setup, you should see:

```
✅ Connected to Angel One SmartAPI (LIVE MODE - FREE!)
✅ RELIANCE.NS         Rs.  1,376.60
✅ TCS.NS              Rs.  3,161.70
✅ HDFCBANK.NS         Rs.    923.90
...
✅ All 14 stocks fetched successfully!
```

---

## 🔐 Security Best Practices

### 1. Never Share Credentials
- Don't commit `.env` to git
- Don't share API keys in screenshots
- Regenerate keys if accidentally exposed

### 2. Add .env to .gitignore

Create/update `.gitignore`:

```
# Credentials
.env
*.env
credentials.py

# Python
__pycache__/
*.pyc
venv/
*.log
```

### 3. Use Environment Variables

Always load credentials from environment:

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Safe - credentials not in code
API_KEY = os.getenv('ANGEL_API_KEY')

# NEVER do this:
# API_KEY = "abc123xyz"  # ❌ DON'T HARDCODE!
```

---

## 🚨 Common Issues & Solutions

### Issue 1: "Invalid TOTP"

**Cause:** TOTP token expired (changes every 30 seconds)

**Solution:**
```python
import pyotp
import time

totp = pyotp.TOTP(TOTP_SECRET)

# Generate fresh token
token = totp.now()
print(f"Current TOTP: {token}")

# Wait if near expiry
remaining = 30 - (int(time.time()) % 30)
if remaining < 5:
    print(f"Waiting {remaining}s for new TOTP...")
    time.sleep(remaining)
    token = totp.now()
```

### Issue 2: "Session Expired"

**Cause:** Angel One session expires after some time

**Solution:** Re-login when needed:
```python
# Add session refresh logic
def get_fresh_token():
    totp = pyotp.TOTP(TOTP_SECRET)
    return totp.now()

# Use in your trading loop
if session_expired:
    broker = BrokerInterface(
        broker="angelone",
        totp_token=get_fresh_token(),
        # ... other params
    )
```

### Issue 3: "Rate Limit Exceeded"

**Cause:** Too many API calls per second

**Solution:**
```python
import time

# Add delay between calls
for symbol in stocks:
    quote = broker.get_live_quote(symbol)
    time.sleep(0.5)  # 500ms delay
```

**Angel One Limits:**
- Quote API: 1 request/second
- Order API: 10 requests/second
- Historical: 3 requests/second

### Issue 4: "Symbol Not Found"

**Cause:** Wrong symbol format

**Solution:**
```python
# Correct formats:
NSE_stocks = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]  # ✅
BSE_stocks = ["RELIANCE.BO", "TCS.BO"]  # ✅

# Angel One internal format (handled automatically):
# NSE:RELIANCE-EQ, NSE:TCS-EQ
```

---

## 📈 Paper Trading Workflow

### Month 1: Demo Mode (FREE)

```python
# No broker credentials needed
broker = BrokerInterface(broker="demo", paper_trading=True)

# Test your system
# - Verify code works
# - Check signal generation
# - Test order logic
```

### Month 2: Angel One Paper Trading (FREE)

```python
# Use real Angel One data, but paper orders
broker = BrokerInterface(
    broker="angelone",
    api_key=API_KEY,
    client_id=CLIENT_ID,
    password=PASSWORD,
    totp_token=totp.now(),
    paper_trading=True  # Still simulated!
)

# Real-time data, simulated orders
# - Compare to backtest expectations
# - Track performance metrics
# - Build confidence
```

### Month 3: Continue Validation (FREE)

- Run for 30+ trades
- Verify win rate within 10% of backtest
- Check returns within 20% of expectations
- No system crashes or bugs

### Month 4+: Deploy Small Capital

Only after successful paper trading:

```python
# Start with ₹20,000 only
broker = BrokerInterface(
    broker="angelone",
    paper_trading=False,  # LIVE MODE!
    # ... credentials
)

# Real money, real trades
# Monitor closely!
```

---

## 💰 Cost Comparison (3 Month Paper Trading)

| Broker | API Cost | Paper Trading | Total |
|--------|----------|---------------|-------|
| **Angel One** | **₹0** | **Free** | **₹0** ✅ |
| Zerodha | ₹6,000 | Workaround | ₹6,000 |
| Upstox | ₹4,500 | Official | ₹4,500 |

**You save ₹6,000 by using Angel One during paper trading phase!**

---

## 🎯 Next Steps

### TODAY:
1. Open Angel One account (takes 1-2 days)
2. While waiting: Test with demo mode
3. Read this guide completely

### AFTER ACCOUNT APPROVAL:
1. Get API key from Angel One portal
2. Setup TOTP (Google Authenticator)
3. Install smartapi-python: `pip install smartapi-python pyotp`
4. Create .env file with credentials
5. Run test_angel_one.py

### THIS WEEK:
1. Run demo mode daily
2. Test Angel One connection
3. Fetch quotes for all 14 stocks
4. Place paper orders
5. Verify everything works

### MONTH 1-3:
1. Paper trade with Angel One (FREE!)
2. Track all metrics vs backtest
3. Build confidence in execution
4. No money at risk

### MONTH 4+:
1. If paper trading successful (30+ trades, good metrics)
2. Deploy ₹20,000 real capital
3. Monitor every trade
4. Scale gradually

---

## 📞 Support & Resources

### Angel One Resources:
- **Portal:** https://smartapi.angelone.in
- **Docs:** https://smartapi.angelone.in/docs
- **Python SDK:** https://github.com/angelbroking-github/smartapi-python
- **Support:** support@angelone.in

### Your System:
- **Demo Test:** `python quick_start_demo.py`
- **Broker Interface:** `broker_interface.py` (Angel One support added!)
- **Config:** `config/phase6a_production.yaml`

### Community:
- Angel One has active Telegram/Discord groups
- Many algo traders in Bangalore use this
- Good community support

---

## ✅ Checklist

Before going live, complete this:

**Setup:**
- [ ] Angel One account opened
- [ ] API key obtained
- [ ] TOTP setup (Google Authenticator)
- [ ] smartapi-python installed
- [ ] .env file created
- [ ] Test connection successful

**Testing:**
- [ ] Demo mode tested (demo broker)
- [ ] Angel One quotes fetching
- [ ] All 14 stocks accessible
- [ ] Paper orders executing
- [ ] Capital tracking working
- [ ] No errors for 1 week

**Paper Trading:**
- [ ] Month 1: 10+ paper trades
- [ ] Month 2: 20+ paper trades
- [ ] Month 3: 30+ paper trades
- [ ] Win rate within 10% of backtest (61.76%)
- [ ] Returns within 20% of backtest (18.70%)
- [ ] Max drawdown < 5%

**Go-Live:**
- [ ] All paper trading successful
- [ ] Confidence in system
- [ ] Risk protocols defined
- [ ] Emergency procedures ready
- [ ] Start with ₹20K only
- [ ] Mental preparedness

---

## 🎉 Summary

**Angel One SmartAPI is PERFECT for you:**

✅ **FREE API** (saves ₹6,000 over 3 months)
✅ **Mature Python SDK** (smartapi-python)
✅ **Real-time data** (no delays like demo mode)
✅ **Paper trading** (simulated orders, zero risk)
✅ **Popular with algo traders** (good community)
✅ **Easy setup** (30 minutes)

**Your Path:**
1. Open Angel One account (1-2 days)
2. Get API access (5 minutes)
3. Test with paper trading (2-3 months, FREE!)
4. Deploy small capital (₹20K)
5. Scale gradually (₹20K/month)

**Expected Results:**
- Backtest: 18.70% annual return
- Paper Trading: 12-20% (acceptable variance)
- Live Trading: Start small, scale gradually

---

**You made an excellent choice with Angel One! It's the perfect platform for your Phase 6A system.** 🚀

**Next:** Open your Angel One account TODAY, then start testing in demo mode while you wait for approval!
