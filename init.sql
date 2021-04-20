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
    tax_percent numeric(7, 2) not null
);


create table menu
(
    id            serial primary key,
    name          text          not null,
    description   text          not null,
    photo_url     text          not null,
    restaurant_id varchar(36)   not null,
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
    user_id             varchar(36) not null,
    restaurant_id       varchar(36) not null references restaurant (id),
    table_name          text        not null references tables (name),
    payment_status      int         not null,
    price_excluding_tax numeric(7, 2),
    tax                 numeric(7, 2)
);


create table order_items
(
    order_id varchar(36)   not null references orders (id),
    menu_id  int           not null references menu (id),
    quantity int           not null check ( quantity > 0 ),
    price    numeric(7, 2) not null,
    primary key(order_id, menu_id)
);

create table tables
(
    name          text        not null,
    restaurant_id varchar(36) not null references restaurant (id)
);

create table transactions
(
    id       varchar(36) primary key,
    order_id varchar(36)   not null references orders (id),
    price    numeric(7, 2) not null,
    payment_status int not null
);