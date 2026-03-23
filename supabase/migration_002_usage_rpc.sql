-- ============================================================
-- Pulse DB — Phase 4-4: 額度檢查 RPC
-- 在 Supabase Dashboard → SQL Editor 貼上執行
-- ============================================================

-- 方案額度對照表
-- Free:  0 次/每則（不可使用 AI 對話）
-- Light: 5 次/每則/每月
-- Pro:   30 次/每則/每月

create or replace function public.check_and_increment_usage(
  p_article_id text
)
returns jsonb
language plpgsql
security definer
as $$
declare
  v_user_id    uuid;
  v_plan       text;
  v_limit      int;
  v_month      text;
  v_current    int;
begin
  -- 1. 取得當前用戶
  v_user_id := auth.uid();
  if v_user_id is null then
    return jsonb_build_object('allowed', false, 'reason', 'not_authenticated');
  end if;

  -- 2. 查詢用戶方案
  select plan into v_plan
  from public.profiles
  where id = v_user_id;

  if v_plan is null then
    return jsonb_build_object('allowed', false, 'reason', 'no_profile');
  end if;

  -- 3. 判斷額度上限
  case v_plan
    when 'free' then v_limit := 0;
    when 'light' then v_limit := 5;
    when 'pro' then v_limit := 30;
    else v_limit := 0;
  end case;

  if v_limit = 0 then
    return jsonb_build_object(
      'allowed', false,
      'reason', 'plan_no_ai',
      'plan', v_plan
    );
  end if;

  -- 4. 取得當月使用量
  v_month := to_char(now(), 'YYYY-MM');

  select count into v_current
  from public.usage_counts
  where user_id = v_user_id
    and article_id = p_article_id
    and month = v_month;

  if v_current is null then
    v_current := 0;
  end if;

  -- 5. 檢查是否超額
  if v_current >= v_limit then
    return jsonb_build_object(
      'allowed', false,
      'reason', 'quota_exceeded',
      'plan', v_plan,
      'used', v_current,
      'limit', v_limit
    );
  end if;

  -- 6. 原子性遞增（upsert）
  insert into public.usage_counts (user_id, article_id, month, count)
  values (v_user_id, p_article_id, v_month, 1)
  on conflict (user_id, article_id, month)
  do update set count = public.usage_counts.count + 1;

  return jsonb_build_object(
    'allowed', true,
    'plan', v_plan,
    'used', v_current + 1,
    'limit', v_limit
  );
end;
$$;
