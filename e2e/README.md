# Browser walks

These drive the real app in Microsoft Edge and check each step on the page. They're for checking the whole product before a demo.

`walk.mjs` covers the main demo path: login, product, quotation, portal acceptance, activation, invoice, payments, printing, billing twice, reports, role limits and phone widths.

`walk2.mjs` covers the other scenes: plans, discounts, templates, draft editing, renewals, cancel and reissue, bulk confirm, filters, staff and password reset.

**To run them**, start the backend and frontend on freshly seeded data, then:

```bash
cd e2e
npm install
mkdir -p shots
node walk.mjs shots
node walk2.mjs shots path/to/backend-terminal-output.log
```

`walk2.mjs` reads the password reset link from the backend's output, so save that output to a file. Each walk changes data, so reseed before a real demo:

```bash
cd backend
python manage.py flush --noinput
python manage.py seed_demo
```
