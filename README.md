# Good Indian Textile — Billing Website

A local billing workspace for **Good Indian Textile**. Create itemised bills, apply discounts, print professional invoices, and keep a searchable billing history.

## Features

- Customer name, customer ID, phone, date, and automatic bill number
- Item dropdown with Saree, Shirt, Pant, Slippers, Inner Wear B, Inner Wear G, Kids Wear, T-Shirt, Shorts, Belt, and Makeup Items
- Multiple items per bill with quantity, cost, and per-item discount
- Live subtotal, total discount, and grand total
- Cash, UPI, and Card payment tracking
- Saved bills with search by bill number, name, customer ID, or phone
- Printable A4 invoice with amount in words
- Dashboard with sales, monthly revenue, discounts, and top categories
- Data stored locally in SQLite (`instance/good_indian_textile.db`)

## Run the website

```powershell
cd "C:\Users\Muthu Arasu\Documents\Default Project\GoodIndianTextile"
python -m pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5001** in your browser.

> Port `5000` is used by another local project (SHIVAJI BIKERS), so this website runs on port `5001`.

You can also double-click `run.bat` to start the website on Windows.

The database is created automatically the first time the website starts.
If `FLASK_SECRET_KEY` is not set, the app generates a temporary key at startup,
so browser sessions (including flash messages) will not persist across restarts.
For a stable key, set `FLASK_SECRET_KEY` in the environment before starting the app.

## Project structure

```text
GoodIndianTextile/
├── app.py
├── requirements.txt
├── instance/
│   └── good_indian_textile.db   (created automatically)
├── static/
│   ├── css/style.css
│   └── js/
│       ├── app.js
│       └── billing.js
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── bill_form.html
    ├── bills.html
    └── invoice.html
```
