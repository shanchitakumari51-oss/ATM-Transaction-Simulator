from flask import Flask, request, jsonify, send_from_directory, session
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "template")
DATABASE = os.path.join(BASE_DIR, "smartatm.db")

app = Flask(__name__, static_folder="template")
app.secret_key = os.environ.get(
    "ATM_SECRET_KEY", "smartatm-demo-change-this-secret"
)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)

DEMO_USERS = [
    ("Aarav Sharma", "1111222233334444", "100000000001", "1234", 25000),
    ("Diya Patel", "2222333344445555", "100000000002", "5678", 18400),
    ("Kabir Das", "3333444455556666", "100000000003", "9012", 9750),
    ("Ananya Roy", "4444555566667777", "100000000004", "2468", 42000),
]


def get_db():
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                holder_name TEXT NOT NULL,
                card_number TEXT UNIQUE NOT NULL,
                account_number TEXT UNIQUE,
                pin TEXT NOT NULL,
                balance INTEGER NOT NULL DEFAULT 0 CHECK(balance >= 0)
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount INTEGER NOT NULL CHECK(amount > 0),
                balance_after INTEGER NOT NULL CHECK(balance_after >= 0),
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
        """)

        account_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(accounts)")
        }
        if "account_number" not in account_columns:
            connection.execute("ALTER TABLE accounts ADD COLUMN account_number TEXT")

        transaction_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(transactions)")
        }
        if "note" not in transaction_columns:
            connection.execute("ALTER TABLE transactions ADD COLUMN note TEXT")

        # Add any demo accounts that are missing without overwriting existing balances/PINs.
        for holder, card, account_no, pin, balance in DEMO_USERS:
            connection.execute("""
                INSERT OR IGNORE INTO accounts
                (holder_name, card_number, account_number, pin, balance)
                VALUES (?, ?, ?, ?, ?)
            """, (holder, card, account_no, pin, balance))

        # Fill account numbers for rows created by older versions of the project.
        for holder, card, account_no, pin, balance in DEMO_USERS:
            connection.execute("""
                UPDATE accounts SET account_number = ?
                WHERE card_number = ? AND (account_number IS NULL OR account_number = '')
            """, (account_no, card))
        connection.commit()


def get_logged_in_account(connection):
    account_id = session.get("account_id")
    if account_id is None:
        return None
    return connection.execute("""
        SELECT id, card_number, account_number, holder_name, balance, pin
        FROM accounts WHERE id = ?
    """, (account_id,)).fetchone()


def valid_amount(amount):
    return (
        isinstance(amount, int)
        and not isinstance(amount, bool)
        and 0 < amount <= 10_000_000
    )


def account_json(account):
    return {
        "accountNumber": account["account_number"],
        "cardNumber": account["card_number"],
        "holderName": account["holder_name"],
        "balance": account["balance"],
        "last4": account["card_number"][-4:]
    }


@app.route("/")
def home():
    return send_from_directory(TEMPLATE_DIR, "index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(status="ok", message="SmartATM backend is running.")


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    card_number = str(data.get("cardNumber", data.get("card_number", ""))).strip()
    pin = str(data.get("pin", "")).strip()

    if not card_number.isdigit() or len(card_number) != 16:
        return jsonify(error="Enter a valid 16-digit card number."), 400
    if not pin.isdigit() or len(pin) != 4:
        return jsonify(error="Enter a valid 4-digit PIN."), 400

    with get_db() as connection:
        account = connection.execute("""
            SELECT id, card_number, account_number, pin, holder_name, balance
            FROM accounts WHERE card_number = ?
        """, (card_number,)).fetchone()
        if account is None or account["pin"] != pin:
            return jsonify(error="Incorrect card number or PIN."), 401
        session.clear()
        session["account_id"] = account["id"]
        return jsonify(message="Login successful.", account=account_json(account))


@app.route("/api/balance", methods=["GET"])
def balance():
    with get_db() as connection:
        account = get_logged_in_account(connection)
        if account is None:
            return jsonify(error="Please log in first."), 401
        return jsonify(
            holderName=account["holder_name"],
            accountNumber=account["account_number"],
            cardNumber=account["card_number"],
            balance=account["balance"]
        )


@app.route("/api/withdraw", methods=["POST"])
def withdraw():
    data = request.get_json(silent=True) or {}
    amount = data.get("amount")
    if not valid_amount(amount):
        return jsonify(error="Enter a valid positive whole-number amount."), 400

    connection = get_db()
    try:
        account = get_logged_in_account(connection)
        if account is None:
            return jsonify(error="Please log in first."), 401
        connection.execute("BEGIN IMMEDIATE")
        current = connection.execute(
            "SELECT balance FROM accounts WHERE id = ?", (account["id"],)
        ).fetchone()
        if amount > current["balance"]:
            connection.rollback()
            return jsonify(error="Insufficient balance."), 400
        new_balance = current["balance"] - amount
        connection.execute("UPDATE accounts SET balance = ? WHERE id = ?",
                           (new_balance, account["id"]))
        connection.execute("""
            INSERT INTO transactions
            (account_id, transaction_type, amount, balance_after, note)
            VALUES (?, 'Cash Withdrawal', ?, ?, ?)
        """, (account["id"], amount, new_balance, "Simulated cash withdrawal"))
        connection.commit()
        return jsonify(message="Withdrawal successful. Simulation only.",
                       withdrawn=amount, balance=new_balance)
    except Exception:
        connection.rollback()
        app.logger.exception("Withdrawal failed")
        return jsonify(error="Withdrawal failed. Please try again."), 500
    finally:
        connection.close()


@app.route("/api/deposit", methods=["POST"])
def deposit():
    data = request.get_json(silent=True) or {}
    amount = data.get("amount")
    if not valid_amount(amount):
        return jsonify(error="Enter a valid positive whole-number amount."), 400

    connection = get_db()
    try:
        account = get_logged_in_account(connection)
        if account is None:
            return jsonify(error="Please log in first."), 401
        connection.execute("BEGIN IMMEDIATE")
        current = connection.execute(
            "SELECT balance FROM accounts WHERE id = ?", (account["id"],)
        ).fetchone()
        new_balance = current["balance"] + amount
        connection.execute("UPDATE accounts SET balance = ? WHERE id = ?",
                           (new_balance, account["id"]))
        connection.execute("""
            INSERT INTO transactions
            (account_id, transaction_type, amount, balance_after, note)
            VALUES (?, 'Cash Deposit', ?, ?, ?)
        """, (account["id"], amount, new_balance, "Simulated cash deposit"))
        connection.commit()
        return jsonify(message="Deposit successful.", deposited=amount, balance=new_balance)
    except Exception:
        connection.rollback()
        app.logger.exception("Deposit failed")
        return jsonify(error="Deposit failed. Please try again."), 500
    finally:
        connection.close()


@app.route("/api/recipients", methods=["GET"])
def recipients():
    """List registered accounts, excluding the currently logged-in account."""
    with get_db() as connection:
        sender = get_logged_in_account(connection)
        if sender is None:
            return jsonify(error="Please log in first."), 401
        rows = connection.execute("""
            SELECT holder_name AS holderName, account_number AS accountNumber,
                   card_number AS cardNumber
            FROM accounts WHERE id != ? ORDER BY holder_name
        """, (sender["id"],)).fetchall()
        return jsonify(recipients=[dict(row) for row in rows])


@app.route("/api/transfer", methods=["POST"])
def transfer():
    """Transfer demo funds using a recipient account number or card number."""
    data = request.get_json(silent=True) or {}
    recipient_value = str(
        data.get("recipientAccount", data.get("accountNumber", data.get("recipient", "")))
    ).strip().replace(" ", "")
    amount = data.get("amount")

    if not recipient_value:
        return jsonify(error="Enter the recipient account number or card number."), 400
    if not recipient_value.isdigit():
        return jsonify(error="Recipient account/card number must contain digits only."), 400
    if not valid_amount(amount):
        return jsonify(error="Enter a valid positive whole-number amount."), 400

    connection = get_db()
    try:
        sender = get_logged_in_account(connection)
        if sender is None:
            return jsonify(error="Please log in first."), 401

        connection.execute("BEGIN IMMEDIATE")
        sender_current = connection.execute(
            "SELECT id, balance FROM accounts WHERE id = ?", (sender["id"],)
        ).fetchone()
        recipient = connection.execute("""
            SELECT id, holder_name, account_number, card_number, balance
            FROM accounts
            WHERE account_number = ? OR card_number = ?
            LIMIT 1
        """, (recipient_value, recipient_value)).fetchone()

        if recipient is None:
            connection.rollback()
            return jsonify(error="Recipient account was not found."), 404
        if recipient["id"] == sender_current["id"]:
            connection.rollback()
            return jsonify(error="You cannot transfer money to your own account."), 400
        if amount > sender_current["balance"]:
            connection.rollback()
            return jsonify(error="Insufficient balance for this transfer."), 400

        sender_balance = sender_current["balance"] - amount
        recipient_balance = recipient["balance"] + amount
        connection.execute("UPDATE accounts SET balance = ? WHERE id = ?",
                           (sender_balance, sender_current["id"]))
        connection.execute("UPDATE accounts SET balance = ? WHERE id = ?",
                           (recipient_balance, recipient["id"]))

        connection.execute("""
            INSERT INTO transactions
            (account_id, transaction_type, amount, balance_after, note)
            VALUES (?, 'Fund Transfer', ?, ?, ?)
        """, (sender_current["id"], amount, sender_balance,
              "Transfer sent to " + recipient["holder_name"] + " (" + recipient["account_number"] + ")"))
        connection.execute("""
            INSERT INTO transactions
            (account_id, transaction_type, amount, balance_after, note)
            VALUES (?, 'Fund Transfer Received', ?, ?, ?)
        """, (recipient["id"], amount, recipient_balance,
              "Transfer received from " + sender["holder_name"] + " (" + sender["account_number"] + ")"))

        connection.commit()
        return jsonify(
            message="Fund transfer successful.",
            transferred=amount,
            balance=sender_balance,
            senderBalance=sender_balance,
            recipient={
                "holderName": recipient["holder_name"],
                "accountNumber": recipient["account_number"],
                "last4": recipient["card_number"][-4:]
            }
        )
    except Exception:
        connection.rollback()
        app.logger.exception("Fund transfer failed")
        return jsonify(error="Fund transfer failed. Please try again."), 500
    finally:
        connection.close()


@app.route("/api/history", methods=["GET"])
def history():
    with get_db() as connection:
        account = get_logged_in_account(connection)
        if account is None:
            return jsonify(error="Please log in first."), 401
        rows = connection.execute("""
            SELECT id, transaction_type AS type, amount,
                   balance_after AS balanceAfter, created_at AS createdAt, note
            FROM transactions WHERE account_id = ? ORDER BY id DESC LIMIT 50
        """, (account["id"],)).fetchall()
        return jsonify(transactions=[dict(row) for row in rows])


@app.route("/api/change-pin", methods=["POST"])
def change_pin():
    """Validate and save a new four-digit PIN for the logged-in account."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Please submit the PIN details and try again."), 400

    current_pin = str(data.get("currentPin", "")).strip()
    new_pin = str(data.get("newPin", "")).strip()
    confirm_pin = str(data.get("confirmPin", "")).strip()

    if not current_pin.isdigit() or len(current_pin) != 4:
        return jsonify(error="Current PIN must contain exactly 4 digits."), 400
    if not new_pin.isdigit() or len(new_pin) != 4:
        return jsonify(error="New PIN must contain exactly 4 digits."), 400
    if new_pin != confirm_pin:
        return jsonify(error="PIN confirmation does not match."), 400
    if new_pin == current_pin:
        return jsonify(error="Your new PIN must be different from your current PIN."), 400

    connection = get_db()
    try:
        # Lock the database for this short update and read the latest PIN from disk.
        connection.execute("BEGIN IMMEDIATE")
        account_id = session.get("account_id")
        if account_id is None:
            connection.rollback()
            return jsonify(error="Your session has expired. Please log in again."), 401

        account = connection.execute(
            "SELECT id, pin FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if account is None:
            connection.rollback()
            session.clear()
            return jsonify(error="Account not found. Please log in again."), 401

        if str(account["pin"]) != current_pin:
            connection.rollback()
            return jsonify(error="Incorrect current PIN. Please enter your existing PIN."), 400

        result = connection.execute(
            "UPDATE accounts SET pin = ? WHERE id = ? AND pin = ?",
            (new_pin, account_id, current_pin)
        )
        if result.rowcount != 1:
            connection.rollback()
            return jsonify(error="PIN was not updated. Please try again."), 409

        connection.commit()
        return jsonify(message="PIN changed successfully. Use your new PIN next time you log in.")
    except Exception:
        connection.rollback()
        app.logger.exception("PIN change failed")
        return jsonify(error="The server could not save your new PIN. Please try again."), 500
    finally:
        connection.close()


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify(message="Logged out successfully.")


if __name__ == "__main__":
    if not os.path.isfile(os.path.join(TEMPLATE_DIR, "index.html")):
        raise FileNotFoundError("index.html must be inside the template folder.")
    initialize_database()
    print("SmartATM is ready at http://127.0.0.1:5000/")
    app.run(host="127.0.0.1", port=5000, debug=False)
