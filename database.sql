--- Database creation script

create table brands
(
    id          integer                                           not null
        constraint brands_pk
            primary key,
    name        varchar(100)                                      not null,
    start_url   varchar(1024)                                     not null,
    wait_method varchar(10)  default 'DOM'::character varying     not null,
    class_name  varchar(100) default 'generic'::character varying not null,
    logo_url    varchar(1024),
    colour_code varchar(10)
);

create table groups
(
    code      varchar(10) not null
        constraint groups_pk
            primary key,
    name      varchar(100) not null,
    image_url varchar(1024),
    colour    varchar(8)
);

create table products
(
    id          serial
        constraint products_pk
            primary key,
    name        varchar(100)         not null,
    group_code  varchar(10)          not null
        constraint products_groups_code_fk
            references groups
            on update cascade on delete cascade,
    search_term varchar(200)         not null,
    active      boolean default true not null,
    is_food     boolean default true not null
);

create table prices
(
    id             bigserial
        constraint prices_pk
            primary key,
    seller_id      integer                 not null
        constraint prices_brands_id_fk
            references brands,
    product_id     integer                 not null
        constraint prices_products_id_fk
            references products,
    title          text                    not null,
    recorded_at    timestamp default now() not null,
    unit_price     integer                 not null,
    price_per      integer                 not null,
    unit           varchar(3)              not null,
    screenshot_url varchar(1024),
    url            varchar(1024)           not null
);

