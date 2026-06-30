-- 1. Create a function to automatically create a user profile when someone signs up
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.user_profiles (id, email, role)
  values (new.id, new.email, 'Swimmer');
  return new;
end;
$$;

-- 2. Attach the trigger to the Supabase auth.users table
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- 3. Create a secure RPC function to promote a user to HeadCoach or AsstCoach
create or replace function public.promote_to_staff(
  target_user_id uuid,
  target_role text,
  secret_token text,
  target_full_name text default null,
  target_email text default null
)
returns void
language plpgsql
security definer set search_path = public
as $$
begin
  -- Check if the secret token matches the expected backend secret
  if secret_token != 'WeagonsAdmin123!@#' then
    raise exception 'Unauthorized to promote staff';
  end if;

  -- Ensure the role is valid
  if target_role not in ('HeadCoach', 'AsstCoach') then
    raise exception 'Invalid staff role';
  end if;

  -- Upsert the user profile to guarantee it exists (fixes missing trigger issues)
  if target_email is not null then
      insert into public.user_profiles (id, email, role)
      values (target_user_id, target_email, target_role::user_role)
      on conflict (id) do update set role = excluded.role;
  else
      update public.user_profiles
      set role = target_role::user_role
      where id = target_user_id;
  end if;
  
  -- Create the coach record automatically
  insert into public.coaches (user_id, full_name, level)
  select 
    target_user_id,
    coalesce(target_full_name, 'Coach ' || split_part(coalesce(target_email, (select email from public.user_profiles where id = target_user_id)), '@', 1)),
    case when target_role = 'HeadCoach' then 'Head' else 'Assistant' end
  where not exists (select 1 from public.coaches where user_id = target_user_id);
end;
$$;

-- --------------------------------------------------------------------------------------
-- 4. DISABLE RLS ON CORE TABLES (For Flask Backend Operations)
-- --------------------------------------------------------------------------------------
-- Because the Flask backend currently connects to Supabase using the anon key (SUPABASE_KEY),
-- it acts as an unauthenticated client to the database. To allow the backend to insert
-- data (like uploading Excel spreadsheets), we need to disable RLS on these tables.
-- The Flask backend handles security and permissions via the @role_required decorators.
ALTER TABLE public.competitions DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.events DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.race_results DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.swimmers DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.coaches DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.attendance DISABLE ROW LEVEL SECURITY;
