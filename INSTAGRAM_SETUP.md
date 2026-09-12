# Instagram avtomatik paylaşım (Meta + n8n)

## Hesab məlumatları

| Sahə | Dəyər |
|---|---|
| Meta App | `test` — App ID `892997936875804` |
| Instagram App ID | `2914679632200892` |
| Instagram hesabı | `ai.gencythe1` |
| IG User ID | `17841408322710419` |
| API bazası | `https://graph.instagram.com/v23.0` |
| Rejim | **API setup with Instagram login** (Facebook Page tələb olunmur) |

Aktiv icazələr (hər ikisi "Ready for testing"):

- `instagram_business_basic`
- `instagram_business_content_publish`

> App hazırda **In development** rejimindədir. Bu, yalnız Instagram Tester rolu
> olan hesab (`ai.gencythe1`) üçün işləyir — sizin öz hesabınız üçün kifayətdir.
> Başqa hesablara xidmət göstərmək üçün App Review lazımdır.

## Token

Token Meta dashboard-dan alınır və **yalnız bir dəfə göstərilir**:
`Use cases → Instagram API → API setup with Instagram login → 2. Generate access tokens → Generate token`

Token-i `.env` faylındakı `IG_ACCESS_TOKEN` sahəsinə yazın. **Git-ə commit etməyin.**

Token 60 gün etibarlıdır. Bitməzdən əvvəl yeniləmək üçün:

```bash
curl -s "https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=$IG_ACCESS_TOKEN"
```

Bunu ayda bir dəfə n8n Schedule Trigger ilə avtomatlaşdırmaq olar.

## n8n quraşdırması

1. **Credential yaradın**: n8n → Credentials → New → *Header Auth*
   - Name: `Authorization`
   - Value: `Bearer <IG_ACCESS_TOKEN>`
   - Credential adı: `Instagram Graph API`
2. `n8n_workflows/5_instagram_publish_workflow.json` faylını n8n-ə import edin.
3. Hər üç HTTP Request node-unda (`1. Create media container`,
   `2. Container statusunu yoxla`, `3. Paylaş`) həmin credential-ı seçin.
4. Workflow-u aktivləşdirin.

Token-i heç vaxt workflow JSON-una yazmayın — credential-da qalsın.

## İstifadə

Webhook: `POST /webhook/instagram/publish`

Şəkil postu:

```json
{
  "media_type": "IMAGE",
  "image_url": "https://example.com/post.jpg",
  "caption": "Mətn #hashtag"
}
```

Reels:

```json
{
  "media_type": "REELS",
  "video_url": "https://example.com/reel.mp4",
  "caption": "Mətn #hashtag",
  "share_to_feed": true
}
```

Cavab: `{"status":"published","media_id":"...","media_type":"..."}`

## Media tələbləri

Instagram media faylını **özü yükləyir**, ona görə URL public və birbaşa
əlçatan olmalıdır (localhost və ya auth arxasında olan link işləmir).

| | Şəkil | Reels |
|---|---|---|
| Format | JPEG | MP4 / MOV (H.264 + AAC) |
| Ölçü | ≤ 8 MB | ≤ 1 GB |
| Müddət | — | 3–900 saniyə |
| Aspect | 4:5 – 1.91:1 | 9:16 tövsiyə olunur |

Reels üçün video Instagram tərəfindən emal olunur — workflow container
`FINISHED` statusuna keçənə qədər 15 saniyəlik intervallarla yoxlayır
(maksimum ~5 dəqiqə).

## Limitlər

- 24 saat ərzində **25 paylaşım**.
- Carousel-də maksimum 10 element.

## Mövcud news workflow-u ilə əlaqə

`2_approval_publish_workflow.json` Telegram-da `/paylas <id>` əmri ilə
`/news/{id}/approve` endpoint-ini çağırır. Instagram-a real paylaşım üçün
həmin approve branch-indən bu workflow-un webhook-una `image_url` və
`instagram_caption` göndərilməlidir — yəni insan təsdiqi addımı qalır.
