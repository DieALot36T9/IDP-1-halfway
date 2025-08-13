Table users {
  user_id integer [pk, increment]
  name varchar(100) [not null]
  email varchar(100) [unique, not null]
  phone varchar(20)
  password varchar(100) [not null]
  session_token varchar(100)
  token_expiry timestamp
}

Table publishers {
  publisher_id integer [pk, increment]
  name varchar(100) [not null]
  email varchar(100) [unique, not null]
  phone varchar(20)
  address varchar(255)
  description varchar(1000)
  image_path varchar(255)
  password varchar(100) [not null]
  session_token varchar(100)
  token_expiry timestamp
}

Table admins {
  admin_id integer [pk, increment]
  name varchar(100) [not null]
  email varchar(100) [unique, not null]
  password varchar(100) [not null]
  session_token varchar(100)
  token_expiry timestamp
}

Table categories {
  category_id integer [pk, increment]
  category_name varchar(100) [unique, not null]
}

Table books {
  book_id integer [pk, increment]
  name varchar(255) [not null]
  author_name varchar(100)
  description varchar(2000)
  cover_path varchar(255)
  pdf_path varchar(255)
  publisher_id integer
  category_id integer
}

Table user_subscriptions {
  subscription_id integer [pk, increment]
  user_id integer [not null]
  category_id integer [not null]
  expiry_date date [not null]
  
  indexes {
    (user_id, category_id) [unique]
  }
}

Table bookmarks {
  bookmark_id integer [pk, increment]
  user_id integer [not null]
  book_id integer [not null]

  indexes {
    (user_id, book_id) [unique]
  }
}

Table reading_history {
  history_id integer [pk, increment]
  user_id integer [not null]
  book_id integer [not null]
  last_read_timestamp timestamp

  indexes {
    (user_id, book_id) [unique]
  }
}



Ref: books.publisher_id > publishers.publisher_id [note: 'ON DELETE SET NULL']
Ref: books.category_id > categories.category_id [note: 'ON DELETE SET NULL']

Ref: user_subscriptions.user_id > users.user_id [note: 'ON DELETE CASCADE']
Ref: user_subscriptions.category_id > categories.category_id [note: 'ON DELETE CASCADE']

Ref: bookmarks.user_id > users.user_id [note: 'ON DELETE CASCADE']
Ref: bookmarks.book_id > books.book_id [note: 'ON DELETE CASCADE']

Ref: reading_history.user_id > users.user_id [note: 'ON DELETE CASCADE']
Ref: reading_history.book_id > books.book_id [note: 'ON DELETE CASCADE']