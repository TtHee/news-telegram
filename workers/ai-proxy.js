const GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions';
const MODEL = 'llama-3.3-70b-versatile';

const ROLE_MAP = {
  ai: '你是一位 AI 與科技領域專家，擅長分析人工智慧、半導體、軟體產業的趨勢與影響',
  finance: '你是一位專業財經分析師，擅長股市、總體經濟與金融市場分析',
  stock_tw: '你是一位專業財經分析師，專精台灣股市與產業分析',
  stock_us: '你是一位專業財經分析師，專精美國股市與科技股分析',
  global: '你是一位國際關係與地緣政治專家，擅長分析國際局勢與各國外交策略',
  whitehouse: '你是一位美國政治分析師，專精白宮政策、美國內政與國際影響',
  trump: '你是一位美國政治分析師，專精白宮政策、美國內政與國際影響',
  trends: '你是一位趨勢分析師，擅長解讀搜尋趨勢背後的社會脈動與大眾關注焦點',
  _global_analysis: '你是一位資深新聞分析師與財經專家，擅長從多則新聞中交叉比對、歸納因果關係，找出表面現象背後的深層原因',
};

const ALLOWED_ORIGINS = [
  'https://tthee.github.io',
  'https://news-telegram-bgxs.vercel.app',
  'http://localhost:3000',
  'http://127.0.0.1:3000',
];

// Rate limiter backed by Cloudflare KV (persistent across restarts)
const RATE_LIMIT_RPM = 20;
const RATE_LIMIT_WINDOW_SEC = 60;

async function checkRateLimit(ip, env) {
  const kv = env.RATE_LIMIT;
  if (!kv) return true; // KV not bound -> allow (dev fallback)

  const key = `rl:${ip}`;
  const record = await kv.get(key, 'json');
  const now = Date.now();

  if (!record || now - record.start > RATE_LIMIT_WINDOW_SEC * 1000) {
    await kv.put(key, JSON.stringify({ start: now, count: 1 }), {
      expirationTtl: RATE_LIMIT_WINDOW_SEC,
    });
    return true;
  }

  record.count++;
  if (record.count > RATE_LIMIT_RPM) return false;

  await kv.put(key, JSON.stringify(record), {
    expirationTtl: RATE_LIMIT_WINDOW_SEC,
  });
  return true;
}

function corsHeaders(origin) {
  const allowed = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    'Access-Control-Allow-Origin': allowed,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

function buildSystemPrompt(category, articleTitle, articleSummary) {
  const role = ROLE_MAP[category] || '你是一位新聞分析師';

  if (category === '_global_analysis') {
    // Global analysis mode: articleSummary contains all news
    return `${role}。
你正在分析以下所有今日新聞報導，協助讀者找出觀察到的現象之可能原因。
請用繁體中文回答，條理分明、有深度。
當你找到相關新聞時，請引用新聞編號和來源。
如果新聞中沒有直接相關的資訊，請誠實說明，並提供你的專業判斷。

=== 今日新聞列表 ===
${(articleSummary || '').slice(0, 12000)}`;
  }

  return `${role}。
你正在針對以下新聞回答讀者問題。請用繁體中文回答，簡潔精準、有深度。
如果讀者的問題涉及更廣泛的背景知識，請主動補充相關脈絡。

新聞標題：${articleTitle || '（無標題）'}
新聞摘要：${articleSummary || '（無摘要）'}`;
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const headers = corsHeaders(origin);

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers });
    }

    if (request.method !== 'POST') {
      return Response.json({ error: 'Method not allowed' }, { status: 405, headers });
    }

    // Rate limit check
    const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
    if (!(await checkRateLimit(ip, env))) {
      return Response.json(
        { error: 'AI 目前較忙，請稍後再試' },
        { status: 429, headers }
      );
    }

    try {
      const body = await request.json();
      const { category, articleTitle, articleSummary, messages } = body;

      if (!messages || !Array.isArray(messages) || messages.length === 0) {
        return Response.json({ error: '請輸入問題' }, { status: 400, headers });
      }

      // Validate limits
      if (messages.length > 20) {
        return Response.json({ error: '對話過長，請重新開始' }, { status: 400, headers });
      }

      const lastMsg = messages[messages.length - 1];
      if (lastMsg.content && lastMsg.content.length > 500) {
        return Response.json({ error: '訊息過長，請縮短後再試' }, { status: 400, headers });
      }

      const systemPrompt = buildSystemPrompt(category, articleTitle, articleSummary);

      const groqPayload = {
        model: MODEL,
        messages: [
          { role: 'system', content: systemPrompt },
          ...messages
            .filter(m => m.role === 'user' || m.role === 'assistant')
            .map(m => ({ role: m.role, content: String(m.content).slice(0, 500) })),
        ],
        temperature: 0.6,
        max_tokens: category === '_global_analysis' ? 2048 : 1024,
      };

      const groqResp = await fetch(GROQ_API_URL, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${env.GROQ_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(groqPayload),
      });

      if (!groqResp.ok) {
        const errText = await groqResp.text();
        console.error('Groq API error:', groqResp.status, errText);
        if (groqResp.status === 429) {
          return Response.json({ error: 'AI 目前較忙，請稍後再試' }, { status: 429, headers });
        }
        return Response.json({ error: 'AI 回應失敗，請稍後再試' }, { status: 502, headers });
      }

      const groqData = await groqResp.json();
      let reply = groqData.choices?.[0]?.message?.content || 'AI 無法回應';

      reply = reply.trim();

      return Response.json({ reply }, { headers });

    } catch (err) {
      console.error('Worker error:', err);
      return Response.json({ error: '伺服器錯誤，請稍後再試' }, { status: 500, headers });
    }
  },
};
