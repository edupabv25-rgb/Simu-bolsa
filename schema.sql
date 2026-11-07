-- Ejecutar en Supabase > SQL Editor. No insertar secretos en este script.
create table if not exists public.game_rooms (
  room_id text primary key,
  version bigint not null default 0,
  snapshot jsonb not null,
  updated_at timestamptz not null default now()
);
alter table public.game_rooms enable row level security;
revoke all on public.game_rooms from anon, authenticated;

create or replace function public.game_commit(
  p_room_id text, p_expected_version bigint, p_snapshot jsonb, p_event_id text
) returns bigint
language plpgsql security definer set search_path = public as $$
declare current_version bigint; current_snapshot jsonb;
begin
  select version, snapshot into current_version,current_snapshot
    from public.game_rooms where room_id=p_room_id for update;
  if not found then return -1; end if;
  if p_event_id = any(select jsonb_array_elements_text(coalesce(current_snapshot->'applied_ids','[]'::jsonb)))
    then return current_version;
  end if;
  if current_version <> p_expected_version then return -1; end if;
  update public.game_rooms set snapshot=p_snapshot,version=version+1,updated_at=now()
   where room_id=p_room_id;
  return current_version+1;
end;
$$;
revoke all on function public.game_commit(text,bigint,jsonb,text) from public,anon,authenticated;
grant execute on function public.game_commit(text,bigint,jsonb,text) to service_role;
