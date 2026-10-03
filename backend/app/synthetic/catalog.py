"""Bangladesh-flavoured merchant & phrasing catalog.

Used for two things:
  1. generating the synthetic training/test corpus for the expense categorizer, and
  2. generating realistic synthetic group transactions.

Includes common "Banglish" phrasings (e.g. "basha bhara" = house rent, "biddut bill" =
electricity bill, "nasta" = snacks) because that is how students actually type expenses.
Merchant names are public businesses used only as synthetic descriptions — no real
customer data is involved.
"""
from __future__ import annotations

CATALOG: dict[str, dict[str, list[str]]] = {
    "restaurant": {
        "merchants": ["Kacchi Bhai", "Sultan's Dine", "Star Kabab", "Haji Biriyani", "Nanna Biriyani", "Fakruddin Biriyani",
                      "Bismillah Kabab", "Mezban Bari", "Panshi Restaurant", "Kabab Factory", "Spice & Rice", "Thai Kitchen"],
        "templates": ["Lunch at {m}", "Dinner at {m}", "{m} dinner", "{m} biryani", "Group dinner at {m}", "Kacchi lunch",
                      "Biryani at {m}", "Birthday dinner at {m}", "Iftar at {m}", "Lunch with friends", "Dinner treat",
                      "Restaurant bill {m}", "{m} lunch for everyone", "Weekend dinner", "Thai food dinner",
                      "Chinese restaurant dinner", "Buffet at {m}", "Bhuna khichuri lunch", "Tehari lunch",
                      "Mezban dinner", "Lunch at restaurant", "Set menu dinner", "Kabab and naan dinner"],
    },
    "fast_food": {
        "merchants": ["KFC", "Pizza Hut", "Chillox", "Takeout", "Madchef", "Burger King", "Domino's", "Cheez", "Pizzaburg",
                      "BFC", "Herfy", "Burger Lab"],
        "templates": ["{m} burgers", "Burgers at {m}", "{m} pizza", "Pizza night", "Fried chicken from {m}",
                      "Fries and burgers", "{m} combo meal", "Shawarma", "Pizza at {m}", "Fast food", "{m} bucket",
                      "Burger and coke", "Sub sandwich", "Chicken wings {m}"],
    },
    "food_delivery": {
        "merchants": ["Foodpanda", "Pathao Food", "Foodi", "HungryNaki", "Shohoz Food"],
        "templates": ["{m} order", "Food delivery from {m}", "{m} pizza delivery", "Ordered biryani on {m}",
                      "{m} late night order", "Midnight food delivery", "Home delivery dinner", "Delivery order",
                      "{m} delivery", "Ordered food online", "Delivery charge and food"],
    },
    "cafe_snacks": {
        "merchants": ["North End Coffee", "Gloria Jean's", "Crimson Cup", "Tong", "Cha Bari", "Coffee World",
                      "Campus canteen", "Nobody's Cafe"],
        "templates": ["Coffee at {m}", "Cha and singara", "Tea and snacks", "Nasta", "Evening snacks", "{m} coffee",
                      "Fuchka", "Chotpoti", "Canteen snacks", "Singara samosa", "Cold coffee {m}", "Cha break",
                      "Jhalmuri", "Muri and tea", "Puri at canteen", "Ice cream", "Snacks after class",
                      "Tea at tong", "Cappuccino {m}", "Bakery snacks"],
    },
    "supermarket": {
        "merchants": ["Shwapno", "Agora", "Meena Bazar", "Unimart", "Prince Bazar", "Daily Shopping", "Chaldal"],
        "templates": ["{m} groceries", "Groceries from {m}", "Monthly grocery {m}", "Rice, oil, eggs",
                      "{m} shopping essentials", "Grocery run", "{m} order", "Monthly bazar list", "Oil and rice",
                      "Eggs and bread", "Milk and eggs", "Toiletries and groceries", "Dal and atta"],
    },
    "fresh_market": {
        "merchants": ["Karwan Bazar", "Mirpur kacha bazar", "Krishi Market", "Hatirpool bazar", "Local bazar"],
        "templates": ["Bazar from {m}", "Fish and vegetables", "Kacha bazar", "Vegetables", "Chicken and fish",
                      "Weekly bazar", "Fruits from {m}", "Beef for the week", "Morich peyaj", "Sobji bazar",
                      "{m} fish", "Mach bazar", "Murgi and dim"],
    },
    "ride_hailing": {
        "merchants": ["Pathao", "Uber", "Obhai", "Shohoz Ride"],
        "templates": ["{m} ride to campus", "{m} to Bashundhara", "{m} car to Dhanmondi", "{m} bike", "Uber to campus",
                      "Ride share home", "{m} trip to Gulshan", "{m} to airport", "Car ride back home",
                      "{m} ride", "Bike ride to university", "{m} to Mirpur"],
    },
    "rickshaw_cng": {
        "merchants": ["Rickshaw", "CNG", "Leguna", "Auto rickshaw"],
        "templates": ["Rickshaw fare", "CNG to Mirpur 10", "CNG to campus", "Rickshaw to Ashulia", "Rickshaw bhara",
                      "Gari bhara", "CNG fare to Farmgate", "Leguna fare", "{m} fare", "{m} to Dhanmondi",
                      "Rickshaw ride", "CNG back home"],
    },
    "bus_train": {
        "merchants": ["Green Line", "Shohagh Paribahan", "Hanif Enterprise", "Bangladesh Railway", "Shyamoli Paribahan",
                      "Ena Transport", "BRTC"],
        "templates": ["Bus tickets to Cox's Bazar", "{m} bus tickets", "Train tickets to Chittagong", "{m} tickets",
                      "Bus fare to Sylhet", "Return bus tickets", "Intercity train", "Launch ticket to Barisal",
                      "Bus ticket {m}", "AC bus to Khagrachari", "Night coach tickets"],
    },
    "fuel": {
        "merchants": ["Padma Oil", "Meghna Petroleum", "Trust Filling Station", "Petrol pump"],
        "templates": ["Fuel for the car", "Octane refill", "Petrol {m}", "Fuel top-up", "{m} octane",
                      "Diesel for microbus", "Car fuel"],
    },
    "accommodation": {
        "merchants": ["Sea Pearl Resort", "Hotel Sea Crown", "Long Beach Hotel", "Sajek Resort", "Megh Machang",
                      "Nature Park Resort", "Hotel Agrabad", "Airbnb"],
        "templates": ["Hotel booking {m}", "Hotel booking", "{m} room 2 nights", "Resort booking", "Cottage booking at {m}",
                      "Hotel advance", "Room rent at {m}", "{m} stay", "Guest house", "Resort check-in {m}",
                      "Hotel extra night"],
    },
    "tours_activities": {
        "merchants": ["Chander Gari", "Sajek jeep", "Boat ride", "Tour guide", "Nilgiri tour", "Speedboat",
                      "Ratargul boat"],
        "templates": ["Chander gari rent", "Jeep rental for Sajek", "Boat ride", "Tour guide fee", "Entry tickets",
                      "{m} fare", "Speedboat trip", "Sightseeing tickets", "Parasailing", "Trekking guide",
                      "Kayaking", "Waterfall entry fee"],
    },
    "flights": {
        "merchants": ["US-Bangla", "Biman", "NovoAir", "Air Astra"],
        "templates": ["{m} flight tickets", "Flight to Cox's Bazar", "Air tickets", "{m} airfare",
                      "Plane tickets to Sylhet", "Domestic flight"],
    },
    "rent": {
        "merchants": ["House rent", "Landlord"],
        "templates": ["House rent", "Flat rent {month}", "Monthly rent", "Basha bhara", "Rent for {month}", "Flat rent",
                      "Rent payment to landlord", "Room rent sublet", "Seat rent mess", "{month} basha bhara"],
    },
    "household_supplies": {
        "merchants": ["Daraz", "Hardware store", "Shwapno household", "Rahimafrooz"],
        "templates": ["Cleaning supplies", "Detergent and soap", "Kitchen utensils", "Light bulbs", "Toilet cleaner",
                      "Bucket and mop", "{m} order kitchen rack", "Mosquito coil", "Dish soap", "Tissue and handwash",
                      "Water filter cartridge", "Broom and dustpan", "Curtains for the flat"],
    },
    "home_services": {
        "merchants": ["Bua", "Maid", "Electrician", "Plumber", "Laundry", "Dhobi"],
        "templates": ["Maid salary", "Bua salary", "Electrician fee", "Plumber repair", "Laundry bill", "Dhobi bill",
                      "Guard bill", "Cleaning service", "Building service charge", "{m} payment", "Bua bill {month}"],
    },
    "electricity": {
        "merchants": ["DESCO", "DPDC", "NESCO", "Palli Bidyut"],
        "templates": ["{m} electricity bill", "Electricity bill", "Current bill", "Biddut bill", "Prepaid meter recharge {m}",
                      "{m} prepaid recharge", "Electric bill {month}", "{m} bill", "Meter recharge"],
    },
    "gas": {
        "merchants": ["Titas Gas", "Bashundhara LP Gas", "Omera LPG"],
        "templates": ["{m} bill", "Gas bill", "LPG cylinder refill", "{m} cylinder", "Titas gas bill {month}",
                      "Cooking gas", "Gas cylinder"],
    },
    "water": {
        "merchants": ["Dhaka WASA", "WASA"],
        "templates": ["WASA water bill", "Water bill", "Pani bill", "Drinking water jars", "{m} bill", "Water jar refill"],
    },
    "internet": {
        "merchants": ["Link3", "Carnival Internet", "Amber IT", "Dot Internet", "Samonline"],
        "templates": ["{m} wifi bill", "Wifi bill", "Internet bill {month}", "{m} broadband", "Broadband bill",
                      "Router payment", "{m} monthly package", "WiFi package renewal"],
    },
    "mobile_recharge": {
        "merchants": ["Grameenphone", "Robi", "Banglalink", "Airtel", "Teletalk"],
        "templates": ["{m} recharge", "Mobile recharge", "{m} data pack", "Internet pack {m}", "Flexiload",
                      "Minute pack", "{m} bundle"],
    },
    "movies": {
        "merchants": ["Star Cineplex", "Blockbuster Cinemas", "Shimanto Shambhar Cineplex", "Lion Cinemas"],
        "templates": ["Movie tickets at {m}", "{m} tickets", "Cinema night", "Movie and popcorn", "{m} movie",
                      "3D movie tickets", "Premiere show tickets"],
    },
    "gaming": {
        "merchants": ["Gaming zone", "PlayStation lounge", "Steam", "Jamuna bowling", "Toggi Fun World", "VR arcade"],
        "templates": ["Gaming zone hours", "PS5 lounge", "Steam game bundle", "Bowling night", "Arcade games",
                      "{m} tokens", "FIFA tournament fee", "Snooker", "{m} session", "Paintball"],
    },
    "events": {
        "merchants": ["Club fest", "Concert", "ICCB", "Freshers event", "Campus fair", "Cultural night"],
        "templates": ["Concert tickets", "Club event fee", "Picnic contribution", "Fest tickets", "Sound system rental",
                      "Event decoration", "Stall booking at fair", "Freshers party", "Farewell event",
                      "Sports day contribution", "Cultural program fee", "Tournament registration", "{m} tickets",
                      "{m} contribution", "Picnic bus and food"],
    },
    "subscriptions": {
        "merchants": ["Netflix", "Spotify", "YouTube Premium", "Chorki", "Hoichoi", "Bongo", "Disney+"],
        "templates": ["{m} subscription", "{m} monthly", "{m} family plan", "Streaming subscription", "{m} renewal"],
    },
    "books_stationery": {
        "merchants": ["Nilkhet", "Rokomari", "Book shop", "Stationery shop", "Boi Mela"],
        "templates": ["Books from {m}", "{m} order textbooks", "Stationery", "Notebooks and pens", "Data structures book",
                      "Calculator", "Textbook", "Lab manual", "Exam stationery", "Engineering drawing set",
                      "Algorithms book", "Highlighters and files"],
    },
    "printing": {
        "merchants": ["Photocopy shop", "Campus print shop", "Nilkhet print"],
        "templates": ["Photocopy notes", "Printing assignment", "Spiral binding", "Lecture sheet photocopy",
                      "Project report printing", "Print slides", "Thesis binding", "Xerox notes", "{m} prints",
                      "Color printing poster"],
    },
    "course_fees": {
        "merchants": ["Udemy", "Coursera", "10 Minute School", "IELTS registration", "Coaching centre"],
        "templates": ["{m} course", "Exam registration fee", "Workshop fee", "Coaching fee", "Course enrollment",
                      "Certification fee", "Lab fee", "{m} enrollment", "Bootcamp fee"],
    },
    "clothing": {
        "merchants": ["Aarong", "Yellow", "Ecstasy", "Sailor", "Richman", "Easy Fashion"],
        "templates": ["Matching t-shirts from {m}", "Club jerseys", "Team hoodies", "{m} shopping", "Punjabi from {m}",
                      "Eid shopping", "Batch t-shirts", "Jackets for the trip", "{m} clothes", "Caps for the tour"],
    },
    "electronics": {
        "merchants": ["Ryans Computers", "Star Tech", "Techland", "Gadget & Gear", "Walton"],
        "templates": ["{m} power bank", "Router from {m}", "HDMI cable", "Bluetooth speaker", "Projector rental",
                      "Laptop repair", "Extension board", "Keyboard and mouse", "Monitor for the flat",
                      "{m} purchase", "Rice cooker", "Electric kettle", "Table fan", "SSD for project laptop"],
    },
    "gifts": {
        "merchants": ["Cooper's", "Mr. Baker", "Well Food", "Gift shop", "Flower shop"],
        "templates": ["Birthday gift for {person}", "Birthday cake", "Cake from {m}", "Flowers", "Farewell gift",
                      "Gift for teacher", "{m} cake", "Wedding gift", "Anniversary gift", "Surprise gift for {person}"],
    },
    "pharmacy": {
        "merchants": ["Lazz Pharma", "Tamanna Pharmacy", "Arogga", "MedEasy", "Pharmacy"],
        "templates": ["Medicine from {m}", "First aid kit", "Medicines", "{m} order", "Paracetamol and ORS",
                      "Masks and sanitizer", "Pharmacy bill", "Saline and medicine"],
    },
    "doctor": {
        "merchants": ["Popular Diagnostic", "Ibn Sina", "Labaid", "Square Hospital"],
        "templates": ["Doctor visit", "{m} tests", "Blood test", "Doctor's fee", "Diagnostic test at {m}",
                      "Emergency checkup", "{m} consultation", "Dengue test"],
    },
    "other": {
        "merchants": ["Courier", "Parking", "Bank"],
        "templates": ["Misc", "Donation", "Tips", "Courier charge", "Parking fee", "Bank charge", "Miscellaneous",
                      "Sundarban courier", "Fine", "Lost and found", "Service charge"],
    },
}

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
PEOPLE = ["Rafi", "Nusrat", "Tahsin", "Mitu", "Sakib", "Riya", "Farhan", "Anika"]


def all_merchants() -> dict[str, str]:
    """Lower-cased merchant gazetteer → canonical merchant name."""
    out: dict[str, str] = {}
    for spec in CATALOG.values():
        for m in spec["merchants"]:
            out[m.lower()] = m
    return out


def merchant_subcategories() -> dict[str, set[str]]:
    """Canonical merchant → subcategories it is known for (a small knowledge base)."""
    out: dict[str, set[str]] = {}
    for key, spec in CATALOG.items():
        for m in spec["merchants"]:
            out.setdefault(m, set()).add(key)
    return out
