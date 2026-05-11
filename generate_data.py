"""Generate 100 realistic invoice records for testing."""
import csv
import random
from datetime import date, timedelta

random.seed(42)

first_names = [
    "Aarav", "Aditi", "Ajay", "Anil", "Anita", "Arjun", "Bhavna", "Chetan",
    "Deepa", "Deepak", "Devika", "Dinesh", "Divya", "Gaurav", "Geeta", "Hari",
    "Ishaan", "Jaya", "Karan", "Kavita", "Lakshmi", "Manoj", "Meena", "Mohit",
    "Nandini", "Naveen", "Neha", "Nikhil", "Pallavi", "Pooja", "Pradeep",
    "Priya", "Rahul", "Rajesh", "Ravi", "Rekha", "Rohit", "Sachin", "Sandeep",
    "Sanjay", "Seema", "Shilpa", "Shweta", "Sneha", "Sunil", "Sunita",
    "Suresh", "Tanvi", "Uday", "Varun", "Vijay", "Vinod", "Vivek", "Yash",
    "Zara", "Aisha", "Kabir", "Kriti", "Manish", "Nisha", "Omkar", "Pankaj",
    "Ritika", "Sagar", "Tara", "Uma", "Vandana", "Wasim", "Yogesh", "Zubin"
]

last_names = [
    "Sharma", "Patel", "Nair", "Reddy", "Iyer", "Kumar", "Singh", "Gupta",
    "Joshi", "Deshmukh", "Kulkarni", "Rao", "Menon", "Pillai", "Verma",
    "Chauhan", "Mishra", "Kapoor", "Malhotra", "Bhat", "Hegde", "Shetty",
    "Agarwal", "Bansal", "Chopra", "Dutta", "Fernandes", "Gandhi", "Hussain",
    "Iyengar", "Jain", "Khanna", "Lal", "Mukherjee", "Naidu", "Oberoi",
    "Pandey", "Qureshi", "Rajan", "Saxena", "Thakur"
]

domains = [
    "technovate.in", "cloudmatrix.in", "infracore.in", "visionlabs.in",
    "nextgenfinance.in", "meridiangroup.in", "bharatindustries.in",
    "skylinetech.in", "orangesoft.in", "primelogistics.in", "zenithcorp.in",
    "alphaventures.in", "betasolutions.in", "cosmicdata.in", "deltaforge.in",
    "echonetworks.in", "fusionworks.in", "globaledge.in", "horizonit.in",
    "innovateq.in"
]

today = date(2026, 5, 10)

rows = []
for i in range(1, 101):
    inv_no = f"INV-2025-{i:03d}"
    first = random.choice(first_names)
    last = random.choice(last_names)
    client_name = f"{first} {last}"
    amount = round(random.randint(10000, 100000) / 100) * 100

    if i <= 25:
        days_overdue = random.randint(1, 7)
    elif i <= 50:
        days_overdue = random.randint(8, 14)
    elif i <= 65:
        days_overdue = random.randint(15, 21)
    elif i <= 80:
        days_overdue = random.randint(22, 30)
    elif i <= 90:
        days_overdue = random.randint(31, 60)
    else:
        days_overdue = random.randint(-10, 0)

    due_date = today - timedelta(days=days_overdue)

    email_local = f"{first.lower()}.{last.lower()}"
    domain = random.choice(domains)
    contact_email = f"{email_local}@{domain}"

    follow_up = min(max(0, days_overdue // 7), 5)
    payment_link = f"https://pay.example.com/inv/{inv_no}"

    rows.append([inv_no, client_name, f"{amount:.2f}", due_date.isoformat(),
                 contact_email, follow_up, payment_link])

rows[0][3] = "2026-05-06"
rows[0][4] = "jinia9350@gmail.com"

with open("data/invoices.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["invoice_no", "client_name", "amount_due", "due_date",
                     "contact_email", "follow_up_count", "payment_link"])
    writer.writerows(rows)

print(f"Generated {len(rows)} invoice records in data/invoices.csv")