# Forex news to Instagram agent (n8n)

## Safety rule

This workflow creates an Instagram **draft** first. Publishing must stay behind
a human approval step until its accuracy and tone have been reviewed.

## Workflow shape

1. **Schedule Trigger**: every 30 minutes during the selected Forex sessions.
2. **RSS Read**: collect items from reputable sources (central-bank releases,
   official economic calendars, Reuters or another licensed news provider).
3. **Code node - deduplicate**: normalize the URL and ignore an item already
   stored in n8n Data Store.
4. **AI analysis**: return strictly valid JSON with:
   `headline_az`, `summary_az`, `affected_pairs`, `impact` (`LOW|MEDIUM|HIGH`),
   `direction` (`BULLISH|BEARISH|MIXED|UNKNOWN`), `why`, `confidence`, and
   `source_url`.
5. **IF**: continue only if `impact` is `HIGH` or `MEDIUM` and confidence is at
   least 70. Never turn this output directly into a trading signal.
6. **AI post writer**: write an Azerbaijani Instagram caption with a short risk
   disclaimer, three to five relevant hashtags, and the source URL. It must not
   promise returns or issue buy/sell instructions.
7. **Approval**: send the caption and source link to Telegram/Slack/email. The
   message must contain Approve and Reject links pointing to an n8n Webhook.
8. **Approved branch**: use the Instagram Graph API to publish only after the
   approval webhook is received. Store the post ID, source URL, and timestamp.
9. **Rejected branch**: log the rejection and mark the source URL as processed.

## AI analysis prompt

Use this system instruction in the analysis node:

> You are a cautious Forex news analyst. Analyse only the supplied source. Do
> not invent facts, prices, or economic releases. Separate facts from market
> interpretation. Produce valid JSON only. This is informational content, not
> investment advice. If the source is insufficient, set impact to LOW and
> direction to UNKNOWN.

## Required credentials

- An AI provider API key in n8n Credentials.
- A news provider/RSS source allowed by its terms of use.
- A Meta Business account, Facebook Page and Instagram professional account for
  the Instagram Graph API node.
- A private approval channel (Telegram, Slack, or email).

## Connection to the trading bot

Keep the news workflow and `/webhook/signal` separate. A later signal workflow
may consume only structured, reviewed news data and must still provide an
`entry_price` and `stop_loss`; the Python risk checks remain authoritative.

## Example paper-trading payload

```json
{
  "symbol": "EURUSD",
  "action": "BUY",
  "volume": 0.01,
  "source": "TECHNICAL",
  "entry_price": 1.085,
  "stop_loss": 1.082,
  "take_profit": 1.091,
  "confidence_score": 72
}
```
