# 🏦 ATM Transaction Simulator

## 📌 About the Project

The **ATM Transaction Simulator** is a web-based banking application designed to simulate the basic functionalities of an Automated Teller Machine (ATM). The project provides a simple and interactive interface for users to perform banking operations securely.

This project is developed using HTML, CSS, JavaScript, Python Flask, and SQLite. It demonstrates the integration of a web application with a relational database to manage user accounts and financial transactions.

## 🎯 Objectives

- To develop a simple and user-friendly ATM simulation system.
- To implement account authentication using card number and PIN.
- To manage account balances through database operations.
- To perform deposits, withdrawals, and fund transfers.
- To maintain transaction records in a database.
- To understand the practical implementation of DBMS concepts.

## ✨ Features

- User Login Authentication
- Account Balance Inquiry
- Cash Deposit
- Cash Withdrawal
- Fund Transfer Between Accounts
- User Profile Management
- Account Details Management
- Database-Driven Transactions
- Interactive Dashboard

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| HTML | Structure of the website |
| CSS | Website styling and design |
| JavaScript | Frontend interactivity |
| Python | Backend programming |
| Flask | Web application framework |
| SQLite | Database management |
| Visual Studio Code | Development environment |
| GitHub | Project hosting and version control |

## 📂 Project Structure

```text
ATM-Transaction-Simulator/
│
├── template/
│   └── index.html
│
├── app.py
├── smartatm.db
└── README.md
```

## 🗄️ Database Description

The project uses **SQLite** as its database management system.

The database file is named `smartatm.db`.

The database manages the following information:

### Accounts
Stores account details such as:
- Account ID
- Card Number
- PIN
- Account Holder Name
- Account Balance
- Account Type
- Account Status

### Transactions
Stores transaction details such as:
- Transaction ID
- Account ID
- Transaction Type
- Transaction Amount
- Balance After Transaction
- Transaction Description
- Transaction Date and Time

## ⚙️ Application Workflow

1. The user opens the ATM web application.
2. The user enters their card number and PIN.
3. The system verifies the login credentials.
4. After successful authentication, the dashboard is displayed.
5. The user selects a banking operation.
6. The backend processes the operation.
7. The database is updated accordingly.
8. The updated account information is displayed.

## ▶️ How to Run the Project

### Requirements
- Python installed on the system
- Flask installed
- Visual Studio Code or any Python IDE

### Installation

Install Flask using the following command:

```bash
pip install flask
```

### Execution

Run the backend application:

```bash
python app.py
```

Open the local URL displayed in the terminal in your web browser.

## 📚 Academic Purpose

This project is developed as an academic project to demonstrate the concepts of:

- Database Management Systems (DBMS)
- CRUD Operations
- Database Connectivity
- Web Application Development
- Backend Programming
- Data Management and Transactions

## 👩‍💻 Author
**Medha Parul**

**Shanchita Kumari**

## 📄 License

This project is created for educational and academic purposes.
