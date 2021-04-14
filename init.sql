create table users
(
    id            uuid primary key,
    name          text not null,
    email         text not null unique,
    password_hash text not null
);
