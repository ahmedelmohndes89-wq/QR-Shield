# QR Shield

A beginner-friendly Flask web application that reads QR code images in the browser, extracts their content, checks URLs for common warning signs, and stores recent scan history in SQLite.

## Features

- Upload PNG, JPG, or WEBP QR code images.
- Decode QR codes in the browser using jsQR.
- Analyze extracted URL text using simple heuristic checks.
- Display a 0–100 risk score and explain the findings.
- Store the latest scans in a local SQLite database.
- View scan statistics and clear scan history.
- Responsive dark cybersecurity-themed interface.

## Requirements

- Python 3.10 or newer
- Internet connection for the jsQR and Google Fonts CDN resources (the app can still run without Google Fonts, but QR decoding needs jsQR).

## Run locally (Windows)

1. Extract the ZIP file.
2. Open the extracted `QR-Shield` folder in Visual Studio Code.
3. Open Terminal > New Terminal.
4. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

5. Activate it:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt terminal and run:

   ```cmd
   .venv\Scripts\activate.bat
   ```

6. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

7. Start the app:

   ```bash
   python app.py
   ```

8. Open http://127.0.0.1:5000 in your browser.

## How to test

Use a QR code image that encodes a URL. You can create a test QR code with any trusted offline QR generator, or use a QR code you already have. Do not test with a real suspicious link by opening it. QR Shield does not visit the destination website.

## Important security limitations

- The scanner uses transparent, basic URL heuristics. It is an educational demonstration, not a commercial threat-intelligence product.
- A low score does not mean a URL is definitely safe; a high score does not prove malicious intent.
- The app does not open, crawl, or download content from scanned destinations.
- Scan history is stored in `qr_shield.db` on the machine running Flask.
- The app is intended for local coursework/demo use. Before public deployment, turn off Flask debug mode, configure production hosting, add authentication/rate limiting as appropriate, and review privacy requirements.
- The browser loads jsQR from jsDelivr. For fully offline use, download and serve the library locally.
