#!/usr/bin/env python3
"""Console application for managing a rental fleet using SQLite."""

import sqlite3
from contextlib import closing
from typing import Any, Iterable, Optional

DB_NAME = "fleet.db"


class DatabaseManager:
    """Simple helper around sqlite3 to initialize schema and run queries."""

    def __init__(self, db_name: str = DB_NAME) -> None:
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self) -> None:
        with closing(self.conn.cursor()) as cur:
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS tblFleet (
                    FleetID TEXT PRIMARY KEY,
                    SerialNo TEXT,
                    FleetType TEXT,
                    Ownership TEXT CHECK(Ownership IN ('Owned','Rented-in')),
                    Capacity REAL,
                    Status TEXT
                );
                CREATE TABLE IF NOT EXISTS tblDriver (
                    DriverID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Name TEXT NOT NULL,
                    PhoneNo TEXT,
                    Status TEXT,
                    Notes TEXT
                );
                CREATE TABLE IF NOT EXISTS tblSupplier (
                    SupplierID INTEGER PRIMARY KEY AUTOINCREMENT,
                    CompanyName TEXT NOT NULL,
                    ContactPerson TEXT,
                    PhoneNo TEXT,
                    Email TEXT
                );
                CREATE TABLE IF NOT EXISTS tblCustomer (
                    CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Name TEXT NOT NULL,
                    PhoneNo TEXT,
                    Email TEXT,
                    Address TEXT
                );
                CREATE TABLE IF NOT EXISTS tblHire (
                    HireID INTEGER PRIMARY KEY AUTOINCREMENT,
                    FleetID TEXT NOT NULL,
                    DriverID INTEGER NOT NULL,
                    CustomerID INTEGER NOT NULL,
                    SupplierID INTEGER,
                    HireType TEXT CHECK(HireType IN ('Daily','Weekly','Monthly','Trip')),
                    StartDate TEXT NOT NULL,
                    EndDate TEXT,
                    Rate REAL NOT NULL,
                    Quantity INTEGER NOT NULL DEFAULT 1,
                    TotalAmount REAL NOT NULL,
                    Status TEXT DEFAULT 'Open',
                    FOREIGN KEY (FleetID) REFERENCES tblFleet(FleetID),
                    FOREIGN KEY (DriverID) REFERENCES tblDriver(DriverID),
                    FOREIGN KEY (CustomerID) REFERENCES tblCustomer(CustomerID),
                    FOREIGN KEY (SupplierID) REFERENCES tblSupplier(SupplierID)
                );
                CREATE TABLE IF NOT EXISTS tblCustomerInvoice (
                    InvoiceID INTEGER PRIMARY KEY AUTOINCREMENT,
                    InvoiceNo TEXT UNIQUE NOT NULL,
                    HireID INTEGER NOT NULL,
                    CustomerID INTEGER NOT NULL,
                    InvoiceDate TEXT NOT NULL,
                    Amount REAL NOT NULL,
                    PaymentStatus TEXT DEFAULT 'Unpaid',
                    FOREIGN KEY (HireID) REFERENCES tblHire(HireID),
                    FOREIGN KEY (CustomerID) REFERENCES tblCustomer(CustomerID)
                );
                CREATE TABLE IF NOT EXISTS tblSupplierPayment (
                    PaymentID INTEGER PRIMARY KEY AUTOINCREMENT,
                    SupplierID INTEGER NOT NULL,
                    HireID INTEGER NOT NULL,
                    PaymentDate TEXT NOT NULL,
                    Amount REAL NOT NULL,
                    PaymentStatus TEXT DEFAULT 'Pending',
                    FOREIGN KEY (SupplierID) REFERENCES tblSupplier(SupplierID),
                    FOREIGN KEY (HireID) REFERENCES tblHire(HireID)
                );
                """
            )
            self.conn.commit()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        cur = self.conn.cursor()
        cur.execute(sql, tuple(params))
        self.conn.commit()
        return cur

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute(sql, tuple(params))
        return cur.fetchall()

    def close(self) -> None:
        self.conn.close()


db = DatabaseManager()


# ----------------------------- Helper utilities -----------------------------

def prompt(message: str, default: Optional[str] = None) -> str:
    value = input(f"{message}: ")
    if not value and default is not None:
        return default
    return value.strip()


def prompt_float(message: str, default: Optional[float] = None) -> float:
    while True:
        value = prompt(message, str(default) if default is not None else None)
        try:
            return float(value)
        except (TypeError, ValueError):
            print("Please enter a valid number.")


def prompt_int(message: str, default: Optional[int] = None) -> int:
    while True:
        value = prompt(message, str(default) if default is not None else None)
        try:
            return int(value)
        except (TypeError, ValueError):
            print("Please enter a valid integer.")


def record_exists(table: str, key_field: str, value: Any) -> bool:
    rows = db.query(f"SELECT 1 FROM {table} WHERE {key_field} = ?", (value,))
    return bool(rows)


def choose_from_table(table: str, id_field: str, label_field: str) -> Optional[int]:
    rows = db.query(f"SELECT {id_field}, {label_field} FROM {table}")
    if not rows:
        print("No records found.")
        return None
    for row in rows:
        print(f"{row[id_field]} - {row[label_field]}")
    try:
        choice = int(input(f"Enter {id_field}: "))
    except ValueError:
        print("Invalid choice.")
        return None
    if not record_exists(table, id_field, choice):
        print("ID does not exist.")
        return None
    return choice


# ----------------------------- Fleet module -----------------------------

def add_fleet() -> None:
    print("\nAdd Fleet")
    fleet_id = prompt("Fleet ID")
    if record_exists("tblFleet", "FleetID", fleet_id):
        print("Fleet ID already exists.")
        return
    serial = prompt("Serial No")
    fleet_type = prompt("Fleet Type")
    ownership = prompt("Ownership (Owned/Rented-in)")
    capacity = prompt_float("Capacity")
    status = prompt("Status")
    db.execute(
        """INSERT INTO tblFleet (FleetID, SerialNo, FleetType, Ownership, Capacity, Status)
            VALUES (?, ?, ?, ?, ?, ?)""",
        (fleet_id, serial, fleet_type, ownership, capacity, status),
    )
    print("Fleet added successfully.")


def update_fleet() -> None:
    fleet_id = prompt("Enter Fleet ID to update")
    rows = db.query("SELECT * FROM tblFleet WHERE FleetID = ?", (fleet_id,))
    if not rows:
        print("Fleet not found.")
        return
    row = rows[0]
    serial = prompt("Serial No", row["SerialNo"])
    fleet_type = prompt("Fleet Type", row["FleetType"])
    ownership = prompt("Ownership", row["Ownership"])
    capacity = prompt_float("Capacity", row["Capacity"])
    status = prompt("Status", row["Status"])
    db.execute(
        """UPDATE tblFleet SET SerialNo=?, FleetType=?, Ownership=?, Capacity=?, Status=?
            WHERE FleetID=?""",
        (serial, fleet_type, ownership, capacity, status, fleet_id),
    )
    print("Fleet updated.")


def delete_fleet() -> None:
    fleet_id = prompt("Enter Fleet ID to delete")
    confirm = prompt("Type YES to confirm")
    if confirm.upper() != "YES":
        print("Deletion cancelled.")
        return
    db.execute("DELETE FROM tblFleet WHERE FleetID = ?", (fleet_id,))
    print("Fleet deleted (if existed).")


def list_fleet() -> None:
    rows = db.query("SELECT * FROM tblFleet ORDER BY FleetID")
    for row in rows:
        print(dict(row))
    if not rows:
        print("No fleet records.")


def search_fleet() -> None:
    field = prompt("Search by (FleetType/Ownership/Status)")
    value = prompt("Enter search value")
    rows = db.query(f"SELECT * FROM tblFleet WHERE {field} LIKE ?", (f"%{value}%",))
    for row in rows:
        print(dict(row))
    if not rows:
        print("No matches.")


def fleet_menu() -> None:
    options = {
        "1": add_fleet,
        "2": update_fleet,
        "3": delete_fleet,
        "4": list_fleet,
        "5": search_fleet,
    }
    while True:
        print("""\nFleet Menu\n1. Add Fleet\n2. Update Fleet\n3. Delete Fleet\n4. List Fleet\n5. Search Fleet\n0. Back""")
        choice = input("Choose: ")
        if choice == "0":
            break
        func = options.get(choice)
        if func:
            func()
        else:
            print("Invalid choice.")


# ----------------------------- Driver module -----------------------------

def add_driver() -> None:
    name = prompt("Driver Name")
    phone = prompt("Phone No")
    status = prompt("Status")
    notes = prompt("Notes", "")
    db.execute(
        "INSERT INTO tblDriver (Name, PhoneNo, Status, Notes) VALUES (?, ?, ?, ?)",
        (name, phone, status, notes),
    )
    print("Driver added.")


def update_driver() -> None:
    driver_id = prompt_int("Driver ID")
    rows = db.query("SELECT * FROM tblDriver WHERE DriverID = ?", (driver_id,))
    if not rows:
        print("Driver not found.")
        return
    row = rows[0]
    name = prompt("Name", row["Name"])
    phone = prompt("Phone", row["PhoneNo"])
    status = prompt("Status", row["Status"])
    notes = prompt("Notes", row["Notes"])
    db.execute(
        """UPDATE tblDriver SET Name=?, PhoneNo=?, Status=?, Notes=? WHERE DriverID=?""",
        (name, phone, status, notes, driver_id),
    )
    print("Driver updated.")


def delete_driver() -> None:
    driver_id = prompt_int("Driver ID")
    confirm = prompt("Type YES to confirm")
    if confirm.upper() != "YES":
        print("Cancelled.")
        return
    db.execute("DELETE FROM tblDriver WHERE DriverID=?", (driver_id,))
    print("Driver deleted (if existed).")


def list_drivers() -> None:
    rows = db.query("SELECT * FROM tblDriver ORDER BY DriverID")
    for row in rows:
        print(dict(row))
    if not rows:
        print("No driver records.")


def search_drivers() -> None:
    status = prompt("Filter by Status")
    rows = db.query("SELECT * FROM tblDriver WHERE Status LIKE ?", (f"%{status}%",))
    for row in rows:
        print(dict(row))
    if not rows:
        print("No matches.")


def driver_menu() -> None:
    options = {
        "1": add_driver,
        "2": update_driver,
        "3": delete_driver,
        "4": list_drivers,
        "5": search_drivers,
    }
    while True:
        print("""\nDriver Menu\n1. Add Driver\n2. Update Driver\n3. Delete Driver\n4. List Drivers\n5. Search Drivers\n0. Back""")
        choice = input("Choose: ")
        if choice == "0":
            break
        func = options.get(choice)
        if func:
            func()
        else:
            print("Invalid choice.")


# ----------------------------- Supplier module -----------------------------

def add_supplier() -> None:
    company = prompt("Company Name")
    contact = prompt("Contact Person")
    phone = prompt("Phone No")
    email = prompt("Email", "")
    db.execute(
        "INSERT INTO tblSupplier (CompanyName, ContactPerson, PhoneNo, Email) VALUES (?, ?, ?, ?)",
        (company, contact, phone, email),
    )
    print("Supplier added.")


def update_supplier() -> None:
    supplier_id = prompt_int("Supplier ID")
    rows = db.query("SELECT * FROM tblSupplier WHERE SupplierID=?", (supplier_id,))
    if not rows:
        print("Supplier not found.")
        return
    row = rows[0]
    company = prompt("Company Name", row["CompanyName"])
    contact = prompt("Contact Person", row["ContactPerson"])
    phone = prompt("Phone", row["PhoneNo"])
    email = prompt("Email", row["Email"])
    db.execute(
        """UPDATE tblSupplier SET CompanyName=?, ContactPerson=?, PhoneNo=?, Email=?
            WHERE SupplierID=?""",
        (company, contact, phone, email, supplier_id),
    )
    print("Supplier updated.")


def delete_supplier() -> None:
    supplier_id = prompt_int("Supplier ID")
    confirm = prompt("Type YES to confirm")
    if confirm.upper() != "YES":
        print("Cancelled.")
        return
    db.execute("DELETE FROM tblSupplier WHERE SupplierID=?", (supplier_id,))
    print("Supplier deleted (if existed).")


def list_suppliers() -> None:
    rows = db.query("SELECT * FROM tblSupplier ORDER BY SupplierID")
    for row in rows:
        print(dict(row))
    if not rows:
        print("No supplier records.")


def search_suppliers() -> None:
    name = prompt("Search company")
    rows = db.query("SELECT * FROM tblSupplier WHERE CompanyName LIKE ?", (f"%{name}%",))
    for row in rows:
        print(dict(row))
    if not rows:
        print("No matches.")


def supplier_menu() -> None:
    options = {
        "1": add_supplier,
        "2": update_supplier,
        "3": delete_supplier,
        "4": list_suppliers,
        "5": search_suppliers,
    }
    while True:
        print("""\nSupplier Menu\n1. Add Supplier\n2. Update Supplier\n3. Delete Supplier\n4. List Suppliers\n5. Search Suppliers\n0. Back""")
        choice = input("Choose: ")
        if choice == "0":
            break
        func = options.get(choice)
        if func:
            func()
        else:
            print("Invalid choice.")


# ----------------------------- Customer module -----------------------------

def add_customer() -> None:
    name = prompt("Customer Name")
    phone = prompt("Phone No")
    email = prompt("Email", "")
    address = prompt("Address", "")
    db.execute(
        "INSERT INTO tblCustomer (Name, PhoneNo, Email, Address) VALUES (?, ?, ?, ?)",
        (name, phone, email, address),
    )
    print("Customer added.")


def update_customer() -> None:
    customer_id = prompt_int("Customer ID")
    rows = db.query("SELECT * FROM tblCustomer WHERE CustomerID=?", (customer_id,))
    if not rows:
        print("Customer not found.")
        return
    row = rows[0]
    name = prompt("Name", row["Name"])
    phone = prompt("Phone", row["PhoneNo"])
    email = prompt("Email", row["Email"])
    address = prompt("Address", row["Address"])
    db.execute(
        """UPDATE tblCustomer SET Name=?, PhoneNo=?, Email=?, Address=? WHERE CustomerID=?""",
        (name, phone, email, address, customer_id),
    )
    print("Customer updated.")


def delete_customer() -> None:
    customer_id = prompt_int("Customer ID")
    confirm = prompt("Type YES to confirm")
    if confirm.upper() != "YES":
        print("Cancelled.")
        return
    db.execute("DELETE FROM tblCustomer WHERE CustomerID=?", (customer_id,))
    print("Customer deleted (if existed).")


def list_customers() -> None:
    rows = db.query("SELECT * FROM tblCustomer ORDER BY CustomerID")
    for row in rows:
        print(dict(row))
    if not rows:
        print("No customer records.")


def search_customers() -> None:
    name = prompt("Search name")
    rows = db.query("SELECT * FROM tblCustomer WHERE Name LIKE ?", (f"%{name}%",))
    for row in rows:
        print(dict(row))
    if not rows:
        print("No matches.")


def customer_menu() -> None:
    options = {
        "1": add_customer,
        "2": update_customer,
        "3": delete_customer,
        "4": list_customers,
        "5": search_customers,
    }
    while True:
        print("""\nCustomer Menu\n1. Add Customer\n2. Update Customer\n3. Delete Customer\n4. List Customers\n5. Search Customers\n0. Back""")
        choice = input("Choose: ")
        if choice == "0":
            break
        func = options.get(choice)
        if func:
            func()
        else:
            print("Invalid choice.")


# ----------------------------- Hire module -----------------------------

def add_hire() -> None:
    fleet_id = prompt("Fleet ID")
    if not record_exists("tblFleet", "FleetID", fleet_id):
        print("Fleet not found.")
        return
    driver_id = choose_from_table("tblDriver", "DriverID", "Name")
    if driver_id is None:
        return
    customer_id = choose_from_table("tblCustomer", "CustomerID", "Name")
    if customer_id is None:
        return
    ownership_row = db.query("SELECT Ownership FROM tblFleet WHERE FleetID=?", (fleet_id,))
    require_supplier = ownership_row and ownership_row[0]["Ownership"] == "Rented-in"
    supplier_id: Optional[int] = None
    if require_supplier:
        supplier_id = choose_from_table("tblSupplier", "SupplierID", "CompanyName")
        if supplier_id is None:
            return
    else:
        supplier_input = prompt("Enter Supplier ID (optional)")
        if supplier_input:
            try:
                supplier_id = int(supplier_input)
            except ValueError:
                print("Invalid supplier ID.")
                return

    hire_type = prompt("Hire Type (Daily/Weekly/Monthly/Trip)")
    start_date = prompt("Start Date (YYYY-MM-DD)")
    end_date = prompt("End Date (YYYY-MM-DD or blank)", "")
    rate = prompt_float("Rate")
    quantity = prompt_int("Quantity", 1)
    total = rate * quantity
    status = "Open"
    db.execute(
        """INSERT INTO tblHire (FleetID, DriverID, CustomerID, SupplierID, HireType, StartDate,
            EndDate, Rate, Quantity, TotalAmount, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (fleet_id, driver_id, customer_id, supplier_id, hire_type, start_date, end_date or None,
         rate, quantity, total, status),
    )
    print("Hire created with total amount", total)


def update_hire_status() -> None:
    hire_id = prompt_int("Hire ID")
    if not record_exists("tblHire", "HireID", hire_id):
        print("Hire not found.")
        return
    status = prompt("New Status (Open/Completed/Cancelled)")
    db.execute("UPDATE tblHire SET Status=? WHERE HireID=?", (status, hire_id))
    print("Hire status updated.")


def list_hires() -> None:
    rows = db.query(
        """SELECT h.HireID, h.FleetID, c.Name AS Customer, h.HireType, h.StartDate,
                   h.EndDate, h.TotalAmount, h.Status
            FROM tblHire h
            JOIN tblCustomer c ON h.CustomerID = c.CustomerID
            ORDER BY h.HireID"""
    )
    for row in rows:
        print(dict(row))
    if not rows:
        print("No hires found.")


def search_hires() -> None:
    status = prompt("Filter by Status")
    rows = db.query(
        """SELECT HireID, FleetID, HireType, StartDate, EndDate, TotalAmount, Status
            FROM tblHire WHERE Status LIKE ?""",
        (f"%{status}%",),
    )
    for row in rows:
        print(dict(row))
    if not rows:
        print("No matches.")


def hire_menu() -> None:
    options = {
        "1": add_hire,
        "2": update_hire_status,
        "3": list_hires,
        "4": search_hires,
    }
    while True:
        print("""\nHire Menu\n1. Add Hire\n2. Update Hire Status\n3. List Hires\n4. Search Hires\n0. Back""")
        choice = input("Choose: ")
        if choice == "0":
            break
        func = options.get(choice)
        if func:
            func()
        else:
            print("Invalid choice.")


# ----------------------------- Invoice module -----------------------------

def generate_invoice_no() -> str:
    rows = db.query("SELECT InvoiceNo FROM tblCustomerInvoice ORDER BY InvoiceID DESC LIMIT 1")
    if not rows:
        return "INV-0001"
    last = rows[0]["InvoiceNo"]
    try:
        number = int(last.split("-")[-1]) + 1
    except ValueError:
        number = 1
    return f"INV-{number:04d}"


def create_invoice_from_hire() -> None:
    hires = db.query("SELECT HireID, CustomerID, TotalAmount FROM tblHire WHERE Status='Completed'")
    if not hires:
        print("No completed hires available.")
        return
    for h in hires:
        print(f"Hire {h['HireID']} - Amount {h['TotalAmount']}")
    hire_id = prompt_int("Choose Hire ID")
    selected = next((h for h in hires if h["HireID"] == hire_id), None)
    if not selected:
        print("Invalid Hire ID.")
        return
    invoice_no = generate_invoice_no()
    invoice_date = prompt("Invoice Date (YYYY-MM-DD)")
    db.execute(
        """INSERT INTO tblCustomerInvoice (InvoiceNo, HireID, CustomerID, InvoiceDate, Amount, PaymentStatus)
            VALUES (?, ?, ?, ?, ?, 'Unpaid')""",
        (invoice_no, hire_id, selected["CustomerID"], invoice_date, selected["TotalAmount"]),
    )
    print("Invoice created with number", invoice_no)


def update_invoice_status() -> None:
    invoice_id = prompt_int("Invoice ID")
    if not record_exists("tblCustomerInvoice", "InvoiceID", invoice_id):
        print("Invoice not found.")
        return
    status = prompt("Payment Status (Unpaid/Partially Paid/Paid)")
    db.execute("UPDATE tblCustomerInvoice SET PaymentStatus=? WHERE InvoiceID=?", (status, invoice_id))
    print("Invoice status updated.")


def list_invoices() -> None:
    rows = db.query(
        """SELECT i.InvoiceID, i.InvoiceNo, c.Name AS Customer, i.Amount, i.PaymentStatus
            FROM tblCustomerInvoice i
            JOIN tblCustomer c ON i.CustomerID = c.CustomerID"""
    )
    for row in rows:
        print(dict(row))
    if not rows:
        print("No invoices found.")


def search_invoices() -> None:
    status = prompt("Filter by Payment Status (leave blank for all)", "")
    customer = prompt("Filter by Customer Name (leave blank for all)", "")
    query = """SELECT i.InvoiceID, i.InvoiceNo, c.Name, i.Amount, i.PaymentStatus
               FROM tblCustomerInvoice i JOIN tblCustomer c ON i.CustomerID=c.CustomerID WHERE 1=1"""
    params: list[Any] = []
    if status:
        query += " AND i.PaymentStatus LIKE ?"
        params.append(f"%{status}%")
    if customer:
        query += " AND c.Name LIKE ?"
        params.append(f"%{customer}%")
    rows = db.query(query, params)
    for row in rows:
        print(dict(row))
    if not rows:
        print("No matches.")


def invoice_menu() -> None:
    options = {
        "1": create_invoice_from_hire,
        "2": update_invoice_status,
        "3": list_invoices,
        "4": search_invoices,
    }
    while True:
        print("""\nInvoice Menu\n1. Create Invoice from Hire\n2. Update Invoice Status\n3. List Invoices\n4. Search Invoices\n0. Back""")
        choice = input("Choose: ")
        if choice == "0":
            break
        func = options.get(choice)
        if func:
            func()
        else:
            print("Invalid choice.")


# ----------------------------- Supplier payments module -----------------------------

def add_supplier_payment() -> None:
    hire_id = prompt_int("Hire ID")
    hire_rows = db.query("SELECT SupplierID FROM tblHire WHERE HireID=?", (hire_id,))
    if not hire_rows:
        print("Hire not found.")
        return
    supplier_id = hire_rows[0]["SupplierID"]
    if not supplier_id:
        print("This hire has no supplier.")
        return
    payment_date = prompt("Payment Date (YYYY-MM-DD)")
    amount = prompt_float("Amount")
    db.execute(
        """INSERT INTO tblSupplierPayment (SupplierID, HireID, PaymentDate, Amount, PaymentStatus)
            VALUES (?, ?, ?, ?, 'Pending')""",
        (supplier_id, hire_id, payment_date, amount),
    )
    print("Supplier payment recorded.")


def update_supplier_payment_status() -> None:
    payment_id = prompt_int("Payment ID")
    if not record_exists("tblSupplierPayment", "PaymentID", payment_id):
        print("Payment not found.")
        return
    status = prompt("Payment Status (Pending/Paid)")
    db.execute("UPDATE tblSupplierPayment SET PaymentStatus=? WHERE PaymentID=?", (status, payment_id))
    print("Payment status updated.")


def list_supplier_payments() -> None:
    rows = db.query(
        """SELECT p.PaymentID, s.CompanyName, p.HireID, p.PaymentDate, p.Amount, p.PaymentStatus
            FROM tblSupplierPayment p JOIN tblSupplier s ON p.SupplierID = s.SupplierID"""
    )
    for row in rows:
        print(dict(row))
    if not rows:
        print("No payments found.")


def search_supplier_payments() -> None:
    supplier = prompt("Filter by Supplier Name", "")
    status = prompt("Filter by Status", "")
    query = """SELECT p.PaymentID, s.CompanyName, p.HireID, p.Amount, p.PaymentStatus
               FROM tblSupplierPayment p JOIN tblSupplier s ON p.SupplierID=s.SupplierID WHERE 1=1"""
    params: list[Any] = []
    if supplier:
        query += " AND s.CompanyName LIKE ?"
        params.append(f"%{supplier}%")
    if status:
        query += " AND p.PaymentStatus LIKE ?"
        params.append(f"%{status}%")
    rows = db.query(query, params)
    for row in rows:
        print(dict(row))
    if not rows:
        print("No matches.")


def supplier_payment_menu() -> None:
    options = {
        "1": add_supplier_payment,
        "2": update_supplier_payment_status,
        "3": list_supplier_payments,
        "4": search_supplier_payments,
    }
    while True:
        print("""\nSupplier Payment Menu\n1. Add Supplier Payment\n2. Update Payment Status\n3. List Payments\n4. Search Payments\n0. Back""")
        choice = input("Choose: ")
        if choice == "0":
            break
        func = options.get(choice)
        if func:
            func()
        else:
            print("Invalid choice.")


# ----------------------------- Main menu -----------------------------

def main_menu() -> None:
    options = {
        "1": fleet_menu,
        "2": driver_menu,
        "3": supplier_menu,
        "4": customer_menu,
        "5": hire_menu,
        "6": invoice_menu,
        "7": supplier_payment_menu,
    }
    while True:
        print(
            """\nRental Fleet Management\n1. Manage Fleet\n2. Manage Drivers\n3. Manage Suppliers\n4. Manage Customers\n5. Manage Hire Records\n6. Manage Customer Invoices\n7. Manage Supplier Payments\n0. Exit"""
        )
        choice = input("Select an option: ")
        if choice == "0":
            break
        func = options.get(choice)
        if func:
            func()
        else:
            print("Invalid choice.")
    db.close()


if __name__ == "__main__":
    main_menu()
