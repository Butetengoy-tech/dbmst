-- Supabase PostgreSQL Schema for Swimming Performance Management System

-- Enable required extensions
create extension if not exists "uuid-ossp";

create type user_role as enum ('HeadCoach', 'AsstCoach', 'Swimmer');

-- USERS table mapping to Supabase auth.users
create table public.user_profiles (
    id uuid references auth.users(id) on delete cascade primary key,
    email text not null,
    role user_role not null default 'Swimmer',
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS (Row Level Security) for user_profiles
alter table public.user_profiles enable row level security;
create policy "Users can view their own profile" on public.user_profiles for select using (auth.uid() = id);

-- COACHES Table
create table public.coaches (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references public.user_profiles(id) on delete cascade,
    full_name text not null,
    level text check (level in ('Head', 'Assistant')) not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- SWIMMERS Table
create table public.swimmers (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references public.user_profiles(id) on delete cascade,
    coach_id uuid references public.coaches(id) on delete set null,
    full_name text not null,
    birthday date not null,
    gender text not null,
    height numeric(5,2),
    weight numeric(5,2),
    school_club text,
    registration_number text,
    medical_notes text,
    photo_url text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- COMPETITIONS Table
create table public.competitions (
    id uuid default uuid_generate_v4() primary key,
    name text not null,
    organizer text,
    venue text,
    date date not null,
    pool_type text check (pool_type in ('25m', '50m')) not null,
    season text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- EVENTS Table
create table public.events (
    id uuid default uuid_generate_v4() primary key,
    competition_id uuid references public.competitions(id) on delete cascade,
    stroke text not null,
    distance integer not null,
    category text check (category in ('Individual', 'Relay')) not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RACE_RESULTS Table
create table public.race_results (
    id uuid default uuid_generate_v4() primary key,
    event_id uuid references public.events(id) on delete cascade,
    swimmer_id uuid references public.swimmers(id) on delete cascade,
    heat integer,
    lane integer,
    time interval not null,
    split_times text, 
    rank integer,
    medal text,
    points integer,
    reaction_time interval,
    is_dq boolean default false,
    is_pb boolean default false,
    is_sb boolean default false,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- ATTENDANCE Table
create table public.attendance (
    id uuid default uuid_generate_v4() primary key,
    swimmer_id uuid references public.swimmers(id) on delete cascade,
    date date not null,
    type text check (type in ('Training', 'Competition')) not null,
    status text check (status in ('Present', 'Absent', 'Excused')) not null,
    notes text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);
