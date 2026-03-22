-- ============================================================
-- Pulse DB Schema — Phase 4-3
-- 在 Supabase Dashboard → SQL Editor 貼上執行
-- ============================================================

-- 1. profiles — 用戶資料 + 方案等級
-- 註冊時自動建立，綁定 auth.users
create table public.profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  avatar_url  text,
  plan        text not null default 'free' check (plan in ('free', 'light', 'pro')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

alter table public.profiles enable row level security;

-- 用戶只能讀寫自己的 profile
create policy "profiles_select_own" on public.profiles
  for select using (auth.uid() = id);

create policy "profiles_update_own" on public.profiles
  for update using (auth.uid() = id);

-- 新用戶註冊時自動建立 profile
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, display_name, avatar_url)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name'),
    new.raw_user_meta_data ->> 'avatar_url'
  );
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();


-- 2. subscribed_topics — 用戶訂閱的主題
create table public.subscribed_topics (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references public.profiles(id) on delete cascade,
  topic      text not null,
  created_at timestamptz not null default now(),
  unique (user_id, topic)
);

alter table public.subscribed_topics enable row level security;

create policy "topics_select_own" on public.subscribed_topics
  for select using (auth.uid() = user_id);

create policy "topics_insert_own" on public.subscribed_topics
  for insert with check (auth.uid() = user_id);

create policy "topics_delete_own" on public.subscribed_topics
  for delete using (auth.uid() = user_id);


-- 3. saved_chats — 智庫：儲存的 AI 對話
create table public.saved_chats (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references public.profiles(id) on delete cascade,
  article_id  text not null,
  title       text not null,
  topic       text,
  messages    jsonb not null default '[]',
  created_at  timestamptz not null default now()
);

alter table public.saved_chats enable row level security;

create policy "chats_select_own" on public.saved_chats
  for select using (auth.uid() = user_id);

create policy "chats_insert_own" on public.saved_chats
  for insert with check (auth.uid() = user_id);

create policy "chats_delete_own" on public.saved_chats
  for delete using (auth.uid() = user_id);


-- 4. usage_counts — 每月 AI 對話額度追蹤
create table public.usage_counts (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references public.profiles(id) on delete cascade,
  article_id  text not null,
  month       text not null,  -- '2026-03' 格式，方便按月重置
  count       int not null default 0,
  unique (user_id, article_id, month)
);

alter table public.usage_counts enable row level security;

create policy "usage_select_own" on public.usage_counts
  for select using (auth.uid() = user_id);

create policy "usage_insert_own" on public.usage_counts
  for insert with check (auth.uid() = user_id);

create policy "usage_update_own" on public.usage_counts
  for update using (auth.uid() = user_id);


-- 5. 索引
create index idx_topics_user on public.subscribed_topics(user_id);
create index idx_chats_user on public.saved_chats(user_id);
create index idx_chats_user_topic on public.saved_chats(user_id, topic);
create index idx_usage_user_month on public.usage_counts(user_id, month);


-- 6. updated_at 自動更新
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger profiles_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();
