-- Table: public.users

-- DROP TABLE IF EXISTS public.users;

CREATE TABLE IF NOT EXISTS public.users
(
    id integer NOT NULL DEFAULT nextval('users_id_seq'::regclass),
    email character varying(255) COLLATE pg_catalog."default" NOT NULL,
    password character varying(255) COLLATE pg_catalog."default" NOT NULL,
    username character varying(50) COLLATE pg_catalog."default" NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT users_email_key UNIQUE (email),
    CONSTRAINT users_username_key UNIQUE (username)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.users
    OWNER to postgres;

-- Table: public.usergroups

-- DROP TABLE IF EXISTS public.usergroups;

CREATE TABLE IF NOT EXISTS public.usergroups
(
    user_id integer NOT NULL,
    group_id integer NOT NULL,
    joined_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT usergroups_pkey PRIMARY KEY (user_id, group_id),
    CONSTRAINT usergroups_group_id_fkey FOREIGN KEY (group_id)
        REFERENCES public.groups (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT usergroups_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.usergroups
    OWNER to postgres;

-- Table: public.settlement

-- DROP TABLE IF EXISTS public.settlement;

CREATE TABLE IF NOT EXISTS public.settlement
(
    id integer NOT NULL DEFAULT nextval('settlement_id_seq'::regclass),
    group_id integer NOT NULL,
    payer_id integer NOT NULL,
    receiver_id integer NOT NULL,
    amount numeric(10,2) NOT NULL,
    date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    currency character varying(10) COLLATE pg_catalog."default" NOT NULL DEFAULT 'PLN'::character varying,
    CONSTRAINT settlement_pkey PRIMARY KEY (id),
    CONSTRAINT settlement_group_id_fkey FOREIGN KEY (group_id)
        REFERENCES public.groups (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT settlement_payer_id_fkey FOREIGN KEY (payer_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT settlement_receiver_id_fkey FOREIGN KEY (receiver_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.settlement
    OWNER to postgres;

-- Table: public.groups

-- DROP TABLE IF EXISTS public.groups;

CREATE TABLE IF NOT EXISTS public.groups
(
    id integer NOT NULL DEFAULT nextval('groups_id_seq'::regclass),
    name character varying(255) COLLATE pg_catalog."default" NOT NULL,
    created_by integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT groups_pkey PRIMARY KEY (id),
    CONSTRAINT groups_created_by_fkey FOREIGN KEY (created_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.groups
    OWNER to postgres;

-- Table: public.friends

-- DROP TABLE IF EXISTS public.friends;

CREATE TABLE IF NOT EXISTS public.friends
(
    user_id integer NOT NULL,
    friend_id integer NOT NULL,
    id integer NOT NULL DEFAULT nextval('friends_id_seq'::regclass),
    created_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT friends_pkey PRIMARY KEY (id),
    CONSTRAINT unique_friendship UNIQUE (user_id, friend_id),
    CONSTRAINT friends_friend_id_fkey FOREIGN KEY (friend_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT friends_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.friends
    OWNER to postgres;

-- Table: public.friendrequest

-- DROP TABLE IF EXISTS public.friendrequest;

CREATE TABLE IF NOT EXISTS public.friendrequest
(
    id integer NOT NULL DEFAULT nextval('friendrequest_id_seq'::regclass),
    sender_id integer NOT NULL,
    recipient_id integer NOT NULL,
    token uuid NOT NULL DEFAULT gen_random_uuid(),
    created_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status character varying(10) COLLATE pg_catalog."default" DEFAULT 'pending'::character varying,
    CONSTRAINT friendrequest_pkey PRIMARY KEY (id),
    CONSTRAINT friendrequest_recipient_id_fkey FOREIGN KEY (recipient_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT friendrequest_sender_id_fkey FOREIGN KEY (sender_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.friendrequest
    OWNER to postgres;

-- Table: public.expenseshares

-- DROP TABLE IF EXISTS public.expenseshares;

CREATE TABLE IF NOT EXISTS public.expenseshares
(
    expense_id integer NOT NULL,
    user_id integer NOT NULL,
    share numeric(10,2) NOT NULL,
    paid boolean DEFAULT false,
    paid_by integer,
    CONSTRAINT expenseshares_pkey PRIMARY KEY (expense_id, user_id),
    CONSTRAINT expenseshares_expense_id_fkey FOREIGN KEY (expense_id)
        REFERENCES public.expenses (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT expenseshares_paid_by_fkey FOREIGN KEY (paid_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT expenseshares_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.expenseshares
    OWNER to postgres;

-- Table: public.expenses

-- DROP TABLE IF EXISTS public.expenses;

CREATE TABLE IF NOT EXISTS public.expenses
(
    id integer NOT NULL DEFAULT nextval('expenses_id_seq'::regclass),
    group_id integer,
    description character varying(255) COLLATE pg_catalog."default",
    amount numeric(10,2) NOT NULL,
    currency character varying(3) COLLATE pg_catalog."default" NOT NULL,
    created_by integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    category character varying(50) COLLATE pg_catalog."default",
    custom_split boolean DEFAULT false,
    CONSTRAINT expenses_pkey PRIMARY KEY (id),
    CONSTRAINT expenses_created_by_fkey FOREIGN KEY (created_by)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT expenses_group_id_fkey FOREIGN KEY (group_id)
        REFERENCES public.groups (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.expenses
    OWNER to postgres;