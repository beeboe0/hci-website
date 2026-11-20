DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS listing;
DROP TABLE IF EXISTS bookmark;
DROP TABLE IF EXISTS "transaction";
DROP TABLE IF EXISTS chat_message;

CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    display_name TEXT,
    bio TEXT,
    university TEXT DEFAULT 'UEA',
    birthday TEXT,
    year_study TEXT
);

CREATE TABLE listing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    isbn TEXT,
    subject TEXT,
    price REAL NOT NULL,
    return_window TEXT,
    image_url TEXT DEFAULT '',
    status TEXT DEFAULT 'available',
    FOREIGN KEY(user_id) REFERENCES user(id)
);

CREATE TABLE bookmark (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    listing_id INTEGER,
    FOREIGN KEY(user_id) REFERENCES user(id),
    FOREIGN KEY(listing_id) REFERENCES listing(id)
);

CREATE TABLE "transaction" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lender_id INTEGER,
    borrower_id INTEGER,
    listing_id INTEGER,
    amount REAL,
    type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(lender_id) REFERENCES user(id),
    FOREIGN KEY(borrower_id) REFERENCES user(id)
);

CREATE TABLE chat_message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_uid INTEGER,
    to_uid INTEGER,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(from_uid) REFERENCES user(id),
    FOREIGN KEY(to_uid) REFERENCES user(id)
);
