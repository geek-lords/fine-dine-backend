create table users
(
    id            varchar(36) primary key,
    name          text         not null,
    email         varchar(100) not null unique,
    password_hash text         not null
);



create table restaurant
(
    id          varchar(36) primary key,
    name        text          not null,
    description text          not null,
    photo_url   text          not null,
    tax_percent numeric(7, 2) not null,
    admin_id    varchar(36)   not null references admin (id)
);
-- will add more things like co ordinates when we get to browse
-- lets focus on core features first

create table menu
(
    id            serial primary key,
    name          text          not null,
    description   text          not null,
    photo_url     text          not null,
    restaurant_id varchar(36)   not null references restaurant (id),
    price         numeric(7, 2) not null
);


create table orders
(
    id                  varchar(36) primary key,
    user_id             varchar(36) not null references users (id),
    restaurant_id       varchar(36) not null references restaurant (id),
    table_name          text        not null references tables (id),
    payment_status      int         not null,
    price_excluding_tax numeric(7, 2),
    tax                 numeric(7, 2),
    time_and_date       timestamp   not null default now()
);


create table order_items
(
    order_id varchar(36)   not null references orders (id),
    menu_id  int           not null references menu (id),
    quantity int           not null check ( quantity > 0 ),
    price    numeric(7, 2) not null,
    primary key (order_id, menu_id)
);

create table tables
(
    id            serial primary key,
    name          text        not null,
    restaurant_id varchar(36) not null references restaurant (id)
);

create table transactions
(
    id             varchar(36) primary key,
    order_id       varchar(36)   not null references orders (id),
    price          numeric(7, 2) not null,
    payment_status int           not null
);

create table admin
(
    id             varchar(36) primary key,
    f_name         varchar(60)         not null,
    l_name         varchar(60)         not null,
    email_address  varchar(100) unique not null,
    contact_number varchar(15) unique  not null,
    password       varchar(100)        not null
);
