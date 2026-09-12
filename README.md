# Forex Trading Bot — n8n + FastAPI

Avtomatlaşdırılmış Forex köməkçisi: xəbər analitikası, insan təsdiqi və risk-nəzarətli
ticarət icrasını bir araya gətirən layihə. Avtomasiya **n8n**-də, qərar/risk məntiqi
**FastAPI** backend-də, nəticələr isə bu sənədin təsvir etdiyi saytda göstərilir.

## Sürətli başlanğıc

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 9999
```

Sonra brauzerdə: `http://localhost:9999`

Mühit dəyişənləri `.env.example` faylında nümunə göstərilib — həqiqi `.env` git-ə
düşmür (`.gitignore`-da var), MT5 və verilənlər bazası kimliklərini orada saxlayın.

## Sayt səhifələri

| Yol | Təsvir |
|---|---|
| `/` | İdarə paneli — açıq mövqələr, son siqnallar, canlı FX ticker |
| `/news` | n8n xəbər agentinin təsdiqlənmiş çıxışları |
| `/about` | Arxitekturanın izahı, hər iki n8n workflow-un addım-addım təsviri |
| `/docs` | Avtomatik yaradılan API sənədləri (Swagger) |

## API endpoint-ləri

| Metod & yol | Kim çağırır | Nə edir |
|---|---|---|
| `POST /webhook/signal` | n8n / TradingView / RSI mühərriki | Ticarət siqnalını qəbul edir, risk yoxlamasından keçirir, PAPER/DEMO rejimində icra edir |
| `GET /signals/preview` | dashboard (avtomatik, 60 s-də bir) | Hər icazəli cüt üçün cari RSI(14) dəyərini hesablayır, heç bir sifariş açmır |
| `POST /signals/run-now` | dashboard-dakı düymə / n8n / cron | RSI mühərrikini bir dəfə işə salır, RSI 30-dan aşağı/70-dən yuxarı olan cütlər üçün real siqnal yaradır |
| `POST /paper/quote` | simulyasiya skripti | PAPER mövqələr üçün qiymət yeniləyir, stop-loss/take-profit toxunduqda mövqeni bağlayır |
| `POST /news/draft` | n8n xəbər təhlili workflow-u | AI təhlilini + şəkil linkini **DRAFT** kimi saxlayır, qısa `id` qaytarır |
| `POST /news/{id}/approve` | n8n təsdiq workflow-u (`/paylas <id>`) | Qaralamanı PUBLISHED edir, `/news`-də görünür |
| `POST /news/{id}/reject` | n8n təsdiq workflow-u (`/rədd <id>`) | Qaralamanı rədd edir (audit üçün saxlanılır, saytda göstərilmir) |
| `POST /news/publish` | əl ilə test / köhnə inteqrasiya | Mətni birbaşa PUBLISHED kimi yaradır (draft addımı olmadan) |
| `GET /news/posts` | inteqrasiya/yoxlama | Yalnız PUBLISHED xəbərləri (şəkil linki daxil) JSON kimi qaytarır |
| `GET /health` | monitorinq | Bot statusunu qaytarır |

## Bot həqiqətən necə "işləyir"

Backend işə düşən kimi (`main.py` → `start_signal_engine`) arxa fonda bir tapşırıq **hər 15
dəqiqədən bir** özü RSI(14)-ü hesablayır (`app/signal_engine.py`) və hədd keçildikdə
`process_signal`-ı çağırıb siqnalı eyni risk zəncirindən keçirir — yəni bot artıq sadəcə "kimsə
siqnal göndərəndə reaksiya verən" deyil, öz-özünə bazarı yoxlayan bir prosesdir. Bunu təqdimatda
gözləmədən göstərmək üçün idarə panelindəki **"Siqnalı indi yarat"** düyməsi eyni mühərriki dərhal
işə salır.

Qiymət mənbəyi Frankfurter/ECB-nin pulsuz, açar tələb etməyən gündəlik məzənnə API-sidir
(`app/market_data.py`) — internet lazımdır, broker hesabı yox. İstəsəniz eyni tetiklənməni
`n8n_workflows/3_rsi_signal_trigger_workflow.json`-u n8n-ə import edərək (Schedule → HTTP Request
→ `POST /signals/run-now`) n8n tərəfindən də edə bilərsiniz — backend-dəki daxili planlaşdırıcı
ilə paralel işləyə bilər, biri digərini əvəz etmir.

## n8n workflow faylları

`n8n_workflows/` qovluğunda üç JSON var, hər birini n8n-də **Import from File** ilə yükləyə bilərsiniz:

1. `1_news_analysis_workflow.json` — xəbər təhlili. **v2**: LLM sərt JSON qaytarır, Code node
   Pollinations.ai (pulsuz, açarsız) ilə xəbərə uyğun şəkil linki qurur, qaralamanı
   `POST /news/draft`-a göndərir, Telegram-a şəkil + səliqəli Markdown mesaj + `/paylas <id>`
   göndərir.
2. `2_approval_publish_workflow.json` — Telegram təsdiqi və dərc. **v2**: admin uzun mətn yazmır,
   sadəcə `/paylas <id>` və ya `/rədd <id>` yazır (səliqəsizlik/səhv riski aradan qalxır),
   workflow müvafiq `POST /news/{id}/approve` və ya `/reject` çağırır və nəticəni geri yazır.
3. `3_rsi_signal_trigger_workflow.json` — RSI mühərrikini n8n-dən tetikləmək üçün əlavə/ixtiyari workflow.

> **Diqqət:** `image_url` sahəsini birbaşa Pollinations.ai-dan gələn URL kimi saxlayırıq (şəkli
> özümüz yükləyib saxlamırıq) — sadə və sürətlidir, amma şəkil yalnız o URL əlçatan olduqca
> görünəcək. Telegram node-un `sendPhoto` üçün şəkil sahəsinin adı n8n versiyanıza görə fərqli ola
> bilər (`file` və ya ayrı "Image URL" sahəsi) — import etdikdən sonra bir dəfə yoxlayın.

> **DB sxemi dəyişdi:** `news_posts` cədvəlinə `image_url`, `approved_at` sütunları əlavə olundu
> və `status` defolt dəyəri `DRAFT`-a çevrildi. Bu layihə hələ dev mərhələsindədir və köhnə sınaq
> məlumatları önəmli deyil, ona görə ən sadə yol — Postgres-də `DROP TABLE news_posts;` edib
> serveri yenidən başladın (cədvəl `Base.metadata.create_all` ilə yeni sxemlə avtomatik yaranacaq).

## n8n workflow-ları

### 1) Xəbər təhlili (Schedule → RSS → Groq AI → Telegram)

- Hər 6 saatdan bir `federalreserve.gov` rəsmi elanlarını oxuyur (son 3 xəbər).
- Groq (`llama-3.1-8b-instant`) hər xəbəri Azərbaycan dilində təhlil edir: xülasə,
  təsir edən valyuta cütləri, təsir dərəcəsi, istiqamət, etibar faizi.
- Nəticə Telegram-a **qaralama** kimi göndərilir — heç nə avtomatik dərc olunmur.

### 2) Təsdiq və dərc (Telegram Trigger → Code → HTTP Request)

- Admin Telegram-da `/paylas <mətn>` yazanda workflow işə düşür.
- Kod node mətni çıxarır və `POST http://host.docker.internal:9999/news/publish`
  ünvanına göndərir.
- FastAPI bunu bazaya yazır, sayt `/news` səhifəsində göstərir.

> **Qeyd:** n8n Docker daxilində işləyirsə, backend-ə `host.docker.internal` adı ilə
> müraciət edir. Backend-i həmişə `9999` portunda saxlayın (və ya n8n workflow-larındakı
> URL-i uyğunlaşdırın).

## Bu sessiyada edilən dəyişikliklər

1. **Kritik bug düzəldildi** — `app/api.py` mövcud olmayan `app/paper.py`-dan idxal
   edirdi, bu səbəbdən server ümumiyyətlə başlamırdı. `app/paper.py` yaradıldı:
   PAPER mövqələr üçün stop-loss/take-profit izlənməsi və avtomatik bağlanma.
2. **Tam yeni dizayn** — `templates/base.html` + `static/dashboard.css` müasir
   "trading terminal" görünüşünə köçürüldü: canlı FX ticker (frankfurter.app-dan),
   animasiyalı şam qrafiki, naviqasiya paneli.
3. **Yeni səhifələr** — `/news` (xəbər lenti) və `/about` (arxitektura izahı) əlavə
   olundu, `app/web.py`-ə uyğun route-lar yazıldı.
4. Bu README hazırlandı.
5. **RSI siqnal mühərriki əlavə olundu** — `app/market_data.py` (pulsuz gündəlik FX qiymətləri),
   `app/strategies.py` (Wilder RSI(14)), `app/signal_engine.py` (qərar + siqnal qurma). Backend
   özü hər 15 dəqiqədən bir yoxlayır (`main.py`), `GET /signals/preview` və `POST /signals/run-now`
   endpoint-ləri əlavə olundu, dashboard-a canlı RSI paneli və "Siqnalı indi yarat" düyməsi
   qoyuldu, `n8n_workflows/` qovluğu (üç workflow, o cümlədən n8n-dən tetiklənə bilən üçüncü
   variant) yaradıldı.
6. **Xəbər axını DRAFT/PUBLISHED-ə keçirildi və şəkil əlavə olundu** — `NewsPost` modelinə
   `image_url`/`approved_at`, `POST /news/draft`, `POST /news/{id}/approve`,
   `POST /news/{id}/reject` endpoint-ləri; `/news` səhifəsi indi yalnız təsdiqlənmiş xəbərləri,
   generasiya olunan şəkillə birlikdə göstərir. n8n workflow-ları (1 və 2) həm formatı
   səliqələşdirmək, həm də şəkil + qısa ID-əsaslı təsdiqi dəstəkləmək üçün yenidən yazıldı.

## Təhlükəsizlik prinsipləri

- Sistem defolt olaraq **PAPER** (simulyasiya) rejimindədir.
- Xəbər heç vaxt avtomatik dərc olunmur — insan Telegram-da təsdiqləməlidir.
- Ticarət siqnalları sərt risk qaydalarından keçir (`app/risk.py`): icazəli cüt,
  maksimum həcm, məcburi stop-loss/take-profit, cüt başına açıq mövqe limiti.
- DEMO rejimdə belə, sifariş yalnız açıq şəkildə təsdiqlənmiş MT5 **demo** serverinə
  göndərilir (`app/core.py` → `can_send_mt5_demo_orders`).

## Məlum məhdudiyyətlər / növbəti addımlar

- RSI strategiyası **gündəlik** bağlanış qiymətlərinə əsaslanır (Frankfurter/ECB pulsuz API-nin
  imkanı budur) — intraday/scalping siqnalı üçün broker-in real vaxt qiymət feed-i lazımdır.
- İkinci n8n workflow-da təsdiq mexanizmi Telegram mətn əmri ilədir (link-əsaslı
  approve/reject deyil) — sadə, amma genişləndirilə bilər.
- Instagram-a həqiqi avtomatik dərc inteqrasiyası yoxdur; `/news/publish`
  `instagram_status: DRAFT_READY` qaytarır, faktiki paylaşım hələlik əldə edilir.
- Pip-əsaslı stop-loss/take-profit (`app/signal_engine.py`) sabit dəyərlərdir; ATR-əsaslı
  dinamik hesablama gələcək təkmilləşdirmə üçün yaxşı namizəddir.
