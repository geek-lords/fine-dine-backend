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
    admin_id    varchar(36)   not null
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


create table tables
(
    name          text        not null,
    restaurant_id varchar(36) not null references restaurant (id)
);


create table orders
(
    id                  varchar(36) primary key,
    user_id             varchar(36) not null references users (id),
    restaurant_id       varchar(36) not null references restaurant (id),
    table_name          text        not null references tables (name),
    payment_status      int         not null,
    price_excluding_tax numeric(7, 2),
    tax                 numeric(7, 2),
    time_and_data timestamp not null default now()
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

create table admins
(
    id              varchar(36) primary key,
    name            text(50) not null,
    hashed_password text     not null,
    email_id        varchar(50) unique,
    phone           varchar(13) unique
);