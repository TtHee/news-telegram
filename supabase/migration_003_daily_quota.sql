-- ============================================================
-- Pulse DB — Phase 5: Daily global quota + Creator plan
-- 在 Supabase Dashboard → SQL Editor 貼上執行
-- ============================================================

-- 1. 更新 profiles.plan 約束，加入 'creator'
ALTER TABLE public.profiles
  DROP CONSTRAINT IF EXISTS profiles_plan_check;

ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_plan_check
  CHECK (plan IN ('free', 'light', 'pro', 'creator'));


-- 2. 新增每日使用量追蹤表
CREATE TABLE IF NOT EXISTS public.daily_usage (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id    uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  date       date NOT NULL DEFAULT CURRENT_DATE,
  count      int NOT NULL DEFAULT 0,
  UNIQUE (user_id, date)
);

ALTER TABLE public.daily_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "daily_usage_select_own" ON public.daily_usage
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "daily_usage_insert_own" ON public.daily_usage
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "daily_usage_update_own" ON public.daily_usage
  FOR UPDATE USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_daily_usage_user_date ON public.daily_usage(user_id, date);


-- 3. 每日額度檢查 RPC
-- 方案額度：free=3, light=30, pro=100, creator=unlimited
CREATE OR REPLACE FUNCTION public.check_and_increment_daily_usage()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_user_id    uuid;
  v_plan       text;
  v_limit      int;
  v_today      date;
  v_current    int;
BEGIN
  -- 1. 取得當前用戶
  v_user_id := auth.uid();
  IF v_user_id IS NULL THEN
    RETURN jsonb_build_object('allowed', false, 'reason', 'not_authenticated');
  END IF;

  -- 2. 查詢用戶方案
  SELECT plan INTO v_plan
  FROM public.profiles
  WHERE id = v_user_id;

  IF v_plan IS NULL THEN
    RETURN jsonb_build_object('allowed', false, 'reason', 'no_profile');
  END IF;

  -- 3. Creator 直接放行
  IF v_plan = 'creator' THEN
    RETURN jsonb_build_object(
      'allowed', true,
      'plan', v_plan,
      'used', 0,
      'limit', 999999
    );
  END IF;

  -- 4. 判斷每日額度
  CASE v_plan
    WHEN 'free'  THEN v_limit := 3;
    WHEN 'light' THEN v_limit := 30;
    WHEN 'pro'   THEN v_limit := 100;
    ELSE v_limit := 3;
  END CASE;

  -- 5. 取得今日使用量
  v_today := CURRENT_DATE;

  SELECT count INTO v_current
  FROM public.daily_usage
  WHERE user_id = v_user_id
    AND date = v_today;

  IF v_current IS NULL THEN
    v_current := 0;
  END IF;

  -- 6. 檢查是否超額
  IF v_current >= v_limit THEN
    RETURN jsonb_build_object(
      'allowed', false,
      'reason', 'daily_quota_exceeded',
      'plan', v_plan,
      'used', v_current,
      'limit', v_limit
    );
  END IF;

  -- 7. 原子性遞增
  INSERT INTO public.daily_usage (user_id, date, count)
  VALUES (v_user_id, v_today, 1)
  ON CONFLICT (user_id, date)
  DO UPDATE SET count = public.daily_usage.count + 1;

  RETURN jsonb_build_object(
    'allowed', true,
    'plan', v_plan,
    'used', v_current + 1,
    'limit', v_limit
  );
END;
$$;


-- 4. 將創作者帳號升級（需要帳號已登入過至少一次）
-- 若尚未登入則此 UPDATE 不會影響任何行，登入後再執行即可
UPDATE public.profiles
SET plan = 'creator'
WHERE id = (
  SELECT id FROM auth.users
  WHERE email = 'chiharune2@gmail.com'
  LIMIT 1
);
