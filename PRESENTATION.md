# Təqdimat Ssenarisi — Forex Trading Bot

Təxmini müddət: 4-5 dəqiqə. Server əvvəlcədən işə salınmış olmalıdır:
`uvicorn main:app --host 0.0.0.0 --port 9999`, brauzerdə `http://localhost:9999` açıq.

**Bir gün əvvəl mütləq yoxlayın:** brauzerdə səs açıq olsun (demo düyməsinin "ding" səsi
üçün bir dəfə istənilən yerə klikləyin ki, brauzer avtoplay bloku götürülsün), internet
bağlantısı olsun (FX ticker və AI chat üçün), server ayrı terminalda arxa fonda işləsin.

---

## 1) Açılış — Dashboard (30 san)

`/` səhifəsini aç.

**De:** "Bu, tam avtomatlaşdırılmış bir Forex ticarət botudur — n8n ilə FastAPI-ni
birləşdirir. Yuxarıda canlı FX ticker, saytın adının yanında yaşıl 'CANLI' işığı görürsünüz —
bu, brauzerlə server arasında açıq WebSocket bağlantısını göstərir, səhifə heç vaxt
manual refresh olunmur."

- Statistika kartlarını göstər (açıq mövqələr, siqnallar, MAX_VOLUME, icazəli cütlər)
- Equity əyrisinə işarə et: "Bu, real PAPER balans tarixçəsidir, saxta rəqəm yoxdur —
  bağlanan hər trade buraya əlavə olunur."

## 2) Canlı Demo düyməsi — ƏSAS WOW MOMENTİ (60-90 san)

**De:** "İndi sizə bütün zəncirin necə işlədiyini canlı göstərəcəm."

Hero bölməsindəki **"🎬 Canlı Demo Başlat"** düyməsinə klikləyin.

- Overlay açılır, addımlar bir-bir "done" olur: bazar məlumatı → RSI qərarı →
  risk zənciri → icra → "Take-Profit-ə çatdı, bağlanır"
- Nəticə kartı görünür: cüt, BUY/SELL, giriş qiyməti, SL/TP
- **Səs eşidiləcək** (ding) və ekranın sağ yuxarısında toast bildirişi çıxacaq
- Overlay bağlananda geriyə qayıt, **equity əyrisinin yeni nöqtə ilə hərəkət etdiyini**
  göstər (qrafik animasiyalı yenidən çəkiləcək)

**De:** "Bu düymə, arxa planda sistemin özünün hər 15 dəqiqədə bir avtomatik etdiyi
eyni əməliyyatı — RSI hesablama, risk yoxlaması, icra, balans yenilənməsi — canlı sizin
qarşınızda edir. Heç nə saxta deyil, elə real backend pipeline-dır."

*(Bir neçə dəfə basmaqdan çəkinməyin — hər dəfə fərqli cüt/istiqamət çıxa bilər,
bu da təbii görünür.)*

## 3) Risk Kalkulyatoru (30-40 san)

Aşağı sürüşdür → "Risk Kalkulyatoru" panelinə.

**De:** "Bu, təkcə vizual bir alət deyil — real sistemin risk qaydalarına bağlıdır."

- Stop-loss sahəsini 300-ə dəyiş → lot ölçüsünün avtomatik dəyişdiyini göstər
- Sonra bir dəyəri sistemin MAX_VOLUME həddini aşacaq şəkildə dəyiş → qırmızı
  xəbərdarlığın çıxdığını göstər: "Bax, sistem özü risk limitini aşan mövqeyə icazə
  vermir."

## 4) AI Köməkçi (30-40 san)

Sağ-alt küncdəki 💬 düyməsinə bas.

**De:** "Saytda hər səhifədə əlçatan AI köməkçi də var — Groq LLM-ə qoşulub və
suallara **real verilənlər bazasından** cavab verir, uydurma rəqəm işlətmir."

Sual yaz və göndər, məsələn:
> "Hazırda hansı cütlərdə açıq mövqəm var?"

və ya

> "Strategiya necə işləyir?"

Cavabın dəqiq real mövqə detalları (qiymət, lot, tarix) ilə gəldiyini vurğula.

## 5) RSI Strategiya paneli (20 san)

Yuxarı sürüşdür, "Strategiya mühərriki" panelinə bax.

**De:** "Bu cədvəl hər 5 saniyədə WebSocket vasitəsilə özü yenilənir. RSI 30-dan aşağı
olsa BUY, 70-dən yuxarı olsa SELL siqnalı yaranır." "Siqnalı indi yarat" düyməsinə bas —
real API sorğusu ilə RSI yenidən hesablanır.

## 6) Xəbər analitikası (20 san)

`/news` səhifəsinə keç.

**De:** "Bu xəbərlər insan tərəfindən deyil, n8n-dəki AI workflow tərəfindən yazılıb —
amma heç biri avtomatik dərc olunmayıb. Admin Telegram-da `/paylas <id>` yazanda dərc
olunur. Tam insan nəzarətli AI content pipeline."

(İstəyə görə `/about` səhifəsində arxitektura sxemini də göstər.)

## 7) Bağlanış — Qiymətlər (20 san)

`/pricing` səhifəsinə keç, sürətlə aşağı sürüşdür.

**De:** "Layihə artıq məhsul kimi təqdim oluna bilər — üç paket, canlı statistika, FAQ.
Sistem defolt olaraq PAPER rejimindədir, real pul heç vaxt avtomatik riskə atılmır."

---

## Ehtiyat plan (əgər nəsə xarab olsa)

- **İnternet yoxdursa:** FX ticker və AI chat işləməyəcək, amma Canlı Demo düyməsi,
  risk kalkulyatoru, equity qrafiki, RSI siqnal cədvəli (əvvəlcədən keşlənmiş məlumatla)
  hamısı işləyəcək — buna görə demo düyməsi ilə başlamaq daha təhlükəsizdir.
- **Server dayanıbsa:** `uvicorn main:app --host 0.0.0.0 --port 9999` əmrini yenidən
  çalışdırın (`../../.venv/Scripts/python.exe -m uvicorn main:app --port 9999`).
- **Demo düyməsi "rejected" versə** (nadir hal, açıq mövqə limiti dolubsa): bunu da
  müsbətə çevirin — "Bax, risk mühərriki maksimum mövqe həddinə çatanda əl belə
  qoymur, bu da sistemin nə qədər ciddi risk nəzarəti etdiyini göstərir."
