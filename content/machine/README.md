# Content Machine

Questa cartella contiene i pacchetti contenuto generati automaticamente dalle offerte attive.

## Struttura

- `packs/`
  Pacchetti singoli per una specifica offerta.
- `plans/`
  Piani editoriali settimanali.
- `verticals/`
  Script verticali gia divisi in varianti hook, overlay, CTA e caption.
- `daily/`
  Pacchetti giornalieri completi con card, messaggio Telegram, script verticali, caption e brief.

## Output tipici

Ogni content pack include:

- dati chiave dell'offerta
- angoli contenuto
- hook per video verticali
- script video breve
- caption social
- varianti Telegram
- traccia story o carousel
- testo overlay per video o card
- titoli blog / SEO
- risposte rapide per DM
- CTA e link rapidi
- brief visual per card o cover

Gli script dentro `verticals/` includono invece varianti gia pronte per Reel, TikTok o Shorts.

La cartella `daily/` e il punto piu comodo da usare ogni giorno: dentro trovi un pacchetto unico gia pronto da pubblicare.

## Modalita operative

- Senza `OPENAI_API_KEY`
  Il sistema usa template intelligenti costruiti dai dati reali.

- Con `OPENAI_API_KEY`
  Il sistema puo generare pacchetti piu naturali tramite OpenAI.
