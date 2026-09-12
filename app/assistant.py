"""Site AI assistant: answers questions about the bot and the caller's own PAPER trades.

Uses the same Groq (llama-3.1-8b-instant) model the n8n news pipeline uses, called
directly over HTTP so no extra SDK dependency is needed. Every answer is grounded
in a live snapshot of the database -- the model is told not to invent numbers.
"""
import logging

import requests
from sqlalchemy.orm import Session

from app.core import settings
from app.db_models import Position, SignalLog, TradeHistory

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"
REQUEST_TIMEOUT = 15

SYSTEM_PROMPT = """Sən Forex Trading Bot saytının AI köməkçisisən.

Sistemin necə işlədiyi haqqında ümumi bilik (sual gələndə bundan istifadə et):
- RSI(14) strategiya mühərriki: Frankfurter/ECB-nin gündəlik bağlanış qiymətlərindən Wilder RSI(14)
  hesablayır. RSI 30-dan aşağıdırsa BUY, 70-dən yuxarıdırsa SELL siqnalı yaranır, aralıqda siqnal yoxdur.
  Bu, backend-də hər 15 dəqiqədən bir avtomatik işləyir, dashboard-dakı "Siqnalı indi yarat" düyməsi ilə
  də əl ilə tetiklənə bilər.
- AI xəbər analitikası: n8n workflow-u hər 6 saatdan bir federalreserve.gov xəbərlərini oxuyur, Groq LLM
  ilə təhlil edir; yalnız MEDIUM/HIGH təsirli və 70%+ etibarlı xəbərlər Telegram-a qaralama kimi göndərilir,
  admin `/paylas <id>` yazanda /news səhifəsində dərc olunur.
- Lot ölçüsü: sabit deyil, hər siqnalda dinamik hesablanır — cari PAPER balansının müəyyən faizi
  (risk/sövdə) risk edilir, bu məbləğ stop-loss məsafəsinə bölünərək lot tapılır (balans artdıqca/azaldıqca
  lot də mütənasib dəyişir). MAX_VOLUME isə real ölçü deyil, sadəcə mütləq təhlükəsizlik tavanıdır.
- Risk zənciri: hər siqnal əvvəlcə risk yoxlamasından keçir (icazəli cüt, təhlükəsizlik tavanı, məcburi
  stop-loss/take-profit, cüt başına maksimum açıq mövqe), yalnız keçəndə icra olunur.
- Rejimlər: sistem defolt PAPER-dədir (real order yoxdur, sadəcə simulyasiya); DEMO rejim yalnız açıq
  şəkildə aktivləşdirilibsə MetaTrader5 demo hesabına order göndərir; real pulla LIVE ticarət bu sistemdə yoxdur.

Qaydalar:
- Yalnız bu saytın funksiyaları, ticarət mexanizmi, risk qaydaları və istifadəçinin
  aşağıda verilmiş canlı PAPER mövqələri/siqnalları haqqında cavab ver.
- Cavablarını Azərbaycan dilində, qısa (maksimum 4-5 cümlə) və konkret ver.
- Yalnız aşağıda verilən canlı məlumata əsaslan -- rəqəm, qiymət və ya nəticə uydurma.
  Məlumat yoxdursa, açıq şəkildə "bu barədə məlumat yoxdur" de.
- Bu, investisiya məsləhəti DEYİL -- gələcək bazar hərəkəti haqqında proqnoz vermə,
  yalnız mövcud sistemin nə etdiyini izah et.
- Sistem defolt olaraq PAPER (simulyasiya) rejimindədir, real pul riskə atılmır.
- Sualın sayt/bot ilə əlaqəsi yoxdursa, nəzakətlə mövzuya yönləndir.
"""


def _build_context(db: Session) -> str:
    open_positions = db.query(Position).filter(Position.status == "OPEN").order_by(Position.created_at.desc()).all()
    recent_trades = db.query(TradeHistory).order_by(TradeHistory.closed_at.desc()).limit(5).all()
    recent_signals = db.query(SignalLog).order_by(SignalLog.created_at.desc()).limit(5).all()

    from app.sizing import current_balance
    balance = current_balance(db)

    lines = [
        f"Ticarət rejimi: {settings.trading_mode}",
        f"İcazəli valyuta cütləri: {', '.join(settings.allowed_symbols)}",
        f"Cari PAPER balansı: ${balance:,.2f}",
        f"Sövdə başına risk: {settings.risk_per_trade_pct}% (lot ölçüsü buna görə dinamik hesablanır)",
        f"Mütləq təhlükəsizlik tavanı (lot): {settings.max_volume}",
        f"Açıq mövqə sayı: {len(open_positions)}",
    ]

    if open_positions:
        lines.append("Açıq mövqələr:")
        for p in open_positions:
            opened = p.created_at.strftime("%d %b %H:%M") if p.created_at else "-"
            lines.append(f"- {p.symbol} {p.order_type} {float(p.volume)} lot, giriş qiyməti {float(p.entry_price)}, açılıb {opened}")
    else:
        lines.append("Hazırda açıq mövqe yoxdur.")

    if recent_trades:
        lines.append("Son bağlanmış PAPER trade-lər:")
        for t in recent_trades:
            closed = t.closed_at.strftime("%d %b %H:%M") if t.closed_at else "-"
            lines.append(f"- {t.symbol}: nəticə {float(t.profit_loss):+.2f} USD, bağlanıb {closed}")

    if recent_signals:
        lines.append("Son qeydə alınan siqnallar:")
        for s in recent_signals:
            lines.append(f"- {s.symbol} {s.action} ({s.signal_source})")

    return "\n".join(lines)


def _call_groq(messages: list[dict], max_tokens: int = 500) -> str | None:
    """Returns the model's reply text, or None if the call failed (caller decides the fallback)."""
    try:
        response = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": messages, "temperature": 0.3, "max_tokens": max_tokens},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        logger.exception("Groq request failed")
        return None


def ask(db: Session, message: str, history: list[dict]) -> str:
    if not settings.groq_api_key:
        return "AI köməkçisi hazırda aktiv deyil (GROQ_API_KEY təyin olunmayıb)."

    context = _build_context(db)
    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n\nCanlı sistem məlumatı:\n" + context}]
    for item in history[-6:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content[:2000]})
    messages.append({"role": "user", "content": message[:2000]})

    reply = _call_groq(messages)
    if reply is None:
        return "Üzr istəyirəm, hazırda cavab verə bilmirəm. Bir az sonra yenidən cəhd edin."
    return reply


MARKET_ANALYSIS_PROMPT = """Sən Forex bazarını təhlil edən AI analitikisən.

Aşağıda hər izlənilən valyuta cütü üçün son bağlanış qiyməti və hesablanmış RSI(14) dəyəri verilib.
Bu real göstəricilərə əsaslanaraq bazarın hazırkı vəziyyətini Azərbaycan dilində, 3-5 cümləlik qısa,
konkret təhlil şəklində izah et: hansı cütlər alış-təzyiqi (RSI aşağı) və ya satış-təzyiqi (RSI yuxarı)
altındadır, hansı neytral zonadadır.

Qaydalar:
- Yalnız verilən RSI/qiymət rəqəmlərinə əsaslan, başqa məlumat uydurma.
- Gələcək qiymət PROQNOZU vermə (“sabah qalxacaq” kimi ifadələr işlətmə) — yalnız hazırkı texniki
  vəziyyəti təsvir et.
- Cavabın SONUNDA, ayrıca sətirdə, dəyişmədən dəqiq bu xəbərdarlığı yaz:
  "⚠️ Bu, investisiya tövsiyəsi deyil — yalnız texniki göstəricilərin ümumi xülasəsidir."
"""


def analyze_market() -> str:
    if not settings.groq_api_key:
        return "AI analitiki hazırda aktiv deyil (GROQ_API_KEY təyin olunmayıb)."

    from app.signal_engine import preview_signals
    readings = [r for r in preview_signals() if r.get("rsi") is not None]
    if not readings:
        return "Bazar məlumatı hazırda əlçatan deyil — bir az sonra yenidən cəhd edin."

    data_lines = "\n".join(
        f"- {r['symbol']}: qiymət {r['last_price']}, RSI(14) {r['rsi']}" for r in readings
    )
    messages = [
        {"role": "system", "content": MARKET_ANALYSIS_PROMPT},
        {"role": "user", "content": f"Cari göstəricilər:\n{data_lines}"},
    ]

    reply = _call_groq(messages, max_tokens=400)
    if reply is None:
        return "Üzr istəyirəm, bazar analizi hazırda hazırlana bilmədi. Bir az sonra yenidən cəhd edin."
    return reply
