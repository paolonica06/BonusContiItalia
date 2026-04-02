# Analytics Bonus Conti Italia

Questa base traccia automaticamente i click piu importanti del funnel:

- `guide_click`
- `contact_click`
- `channel_click`
- `offer_click`
- `source_click`
- `navigation_click`
- `outbound_click`

## Eventi gia coperti

Il file `assets/analytics.js` rileva in automatico:

- click verso guide interne
- click su WhatsApp
- click su Telegram diretto
- click sul canale Telegram
- click verso offerte ufficiali o siti esterni dai CTA
- click sulle fonti ufficiali
- navigazione interna da hero, menu, sticky bar e footer

Ogni evento include anche alcuni parametri utili:

- `page_type`
- `page_slug`
- `offer_slug`
- `placement`
- `link_text`
- `target_kind`
- `destination_slug`
- `outbound_host`

## Attivazione GA4

Per attivare Google Analytics 4:

1. Apri [Google Analytics](https://analytics.google.com/).
2. Crea una proprieta GA4.
3. Crea uno stream web per `bonusconti-italia.vercel.app` o per il tuo dominio finale.
4. Copia il `Measurement ID`, ad esempio `G-XXXXXXXXXX`.
5. Inseriscilo in [site-config.json](/Users/paolonica/Documents/GitHub/BonusContiItalia/data/site-config.json) dentro:

```json
"analytics": {
  "ga4_measurement_id": "G-XXXXXXXXXX"
}
```

6. Fai `commit` e `push`.

Da quel momento:

- GA4 inizia a ricevere pageview
- i click principali arrivano come custom event

## Eventi consigliati da segnare come conversioni

In GA4 ti conviene marcare come eventi chiave:

- `contact_click`
- `guide_click`
- `offer_click`
- `channel_click`

## Dimensioni personalizzate utili in GA4

Se vuoi analizzare bene il funnel, crea anche queste custom dimensions evento:

- `page_type`
- `page_slug`
- `offer_slug`
- `placement`
- `link_text`
- `target_kind`
- `destination_slug`
- `outbound_host`

## Modalita debug

Per controllare gli eventi nel browser senza attivare ancora GA4:

- apri il sito con `?analytics_debug=1`

Esempio:

- `https://bonusconti-italia.vercel.app/?analytics_debug=1`

In console vedrai gli eventi click generati dal sito.

## Plausible

Se preferisci Plausible:

1. crea il sito su Plausible
2. aggiungi il loro snippet ufficiale nelle pagine del sito
3. lascia attivo `assets/analytics.js`

Lo script del sito inviera gli stessi eventi custom anche a `window.plausible` quando il loro snippet e presente.
