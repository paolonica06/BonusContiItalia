# Automazioni Bonus Conti Italia

Questo file e il punto di partenza per automatizzare il progetto senza rompere il sito statico che hai gia online.

## Cosa ho impostato

- `data/offers.json`
  Un file unico con le offerte principali e i campi piu utili per automazioni, Telegram, blog e confronto offerte.
- `data/site-config.json`
  Config generale del sito e delle pubblicazioni.
- `scripts/render_telegram_post.py`
  Genera un messaggio Telegram per una promo partendo dai dati centrali.
- `scripts/generate_telegram_card.py`
  Genera una card promo per Telegram. Se `OPENAI_API_KEY` e disponibile, puo usare uno sfondo AI; altrimenti usa un layout locale elegante.
- `scripts/send_telegram.py`
  Invia un messaggio su Telegram usando il bot token e il chat id, con supporto a testo o foto + caption + pulsanti.
- `.github/workflows/telegram-offer.yml`
  Workflow GitHub Actions che puo essere lanciato a mano o a orario, ruota automaticamente le offerte e genera anche l'immagine promo.
- `scripts/build_blog_draft.py`
  Genera bozze blog periodiche dalle offerte, con o senza OpenAI.
- `.github/workflows/blog-weekly.yml`
  Workflow GitHub Actions che crea una bozza blog schedulata o manuale.
- `scripts/build_content_pack.py`
  Genera pacchetti contenuto per Telegram, video verticali, caption social, idee blog, CTA, overlay copy e risposte rapide DM.
- `.github/workflows/content-machine.yml`
  Workflow GitHub Actions che crea in automatico pacchetti contenuto nei giorni lavorativi.
- `scripts/build_vertical_scripts.py`
  Genera script verticali separati per Reel, TikTok o Shorts con hook, parlato, overlay, CTA e caption.
- `.github/workflows/vertical-machine.yml`
  Workflow GitHub Actions che crea in automatico script verticali dedicati.
- `.env.example`
  Elenco chiaro dei segreti che dovrai configurare.

## Cosa posso fare io nel prossimo step

Posso continuare io con uno o piu di questi blocchi:

1. rendere il sito data-driven
   In pratica: home, tabella confronto e guide vengono generate da `data/offers.json`.

2. automatizzare gli aggiornamenti del sito
   Creo script e workflow che aggiornano pagine, ricostruiscono il sito e fanno deploy automatico.

3. automatizzare Telegram
   Posso trasformare il workflow attuale in un sistema reale di alert, update promo e annunci canale.

4. creare la base del blog automatico
   Posso generare bozze articoli dai dati delle offerte.

5. preparare la factory per video verticali
   Posso creare script che generano hook, caption, script e testo overlay.

6. rafforzare il sistema immagini
   Posso aggiungere varianti grafiche, sfondi AI piu forti o template diversi per conto, app e investimenti.

## Cosa devi fare tu per forza

Questi passaggi richiedono account, token o autorizzazioni esterne. Qui sotto li trovi in ordine.

### 1. Telegram bot

1. Apri Telegram.
2. Cerca `@BotFather`.
3. Scrivi `/newbot`.
4. Scegli nome e username del bot.
5. Copia il token finale.

Poi:

1. Crea o apri il tuo canale Telegram.
2. Aggiungi il bot come admin del canale.
3. Recupera il `chat_id` del canale o gruppo dove vuoi pubblicare.

Segreti da salvare:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### 2. GitHub Secrets

Nel repository GitHub:

1. Vai su `Settings`
2. Vai su `Secrets and variables`
3. Vai su `Actions`
4. Crea questi secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `SITE_BASE_URL`

### 3. Dominio del sito

Quando avrai il dominio definitivo, inseriscilo:

- in `data/site-config.json`
- nel secret `SITE_BASE_URL`

### 4. Vercel

Se vuoi deploy automatico:

1. collega il repo a Vercel
2. crea un deploy hook
3. salva il valore come:

- `VERCEL_DEPLOY_HOOK_URL`

### 5. OpenAI per articoli piu naturali

Se vuoi bozze blog generate da IA con testo piu naturale:

1. crea una API key OpenAI
2. salvala nei GitHub Secrets come:

- `OPENAI_API_KEY`

Se questo secret manca, la generazione blog continua a funzionare in modalita template.

Lo stesso secret viene usato anche per gli sfondi immagine AI dei post Telegram. Se manca, il canale continua comunque a pubblicare le card con il design locale.

## Comandi locali utili

Genera un messaggio Telegram per BBVA:

```bash
python3 scripts/render_telegram_post.py --slug bbva --base-url https://tuodominio.it
```

Invia un messaggio Telegram:

```bash
python3 scripts/render_telegram_post.py --slug bbva --base-url https://tuodominio.it | python3 scripts/send_telegram.py
```

Genera una card promo Telegram:

```bash
python3 scripts/generate_telegram_card.py --slug bbva --base-url https://tuodominio.it --out tmp/telegram/bbva-card.png
```

Genera una bozza blog template per una singola offerta:

```bash
python3 scripts/build_blog_draft.py --mode offer --slug bbva --base-url https://tuodominio.it
```

Genera una bozza blog riepilogativa:

```bash
python3 scripts/build_blog_draft.py --mode roundup --base-url https://tuodominio.it
```

Genera una bozza blog con OpenAI:

```bash
OPENAI_API_KEY=... python3 scripts/build_blog_draft.py --mode roundup --base-url https://tuodominio.it --use-openai
```

Genera un content pack template per l'offerta del giorno:

```bash
python3 scripts/build_content_pack.py --mode offer --slug auto --base-url https://tuodominio.it
```

Genera un content pack per Revolut:

```bash
python3 scripts/build_content_pack.py --mode offer --slug revolut --base-url https://tuodominio.it
```

Genera un piano contenuti settimanale:

```bash
python3 scripts/build_content_pack.py --mode weekly --base-url https://tuodominio.it
```

Genera un content pack con OpenAI:

```bash
OPENAI_API_KEY=... python3 scripts/build_content_pack.py --mode offer --slug bbva --base-url https://tuodominio.it --use-openai
```

Genera script verticali per l'offerta del giorno:

```bash
python3 scripts/build_vertical_scripts.py --slug auto --base-url https://tuodominio.it
```

Genera script verticali per buddybank:

```bash
python3 scripts/build_vertical_scripts.py --slug buddybank --base-url https://tuodominio.it
```

Genera script verticali con OpenAI:

```bash
OPENAI_API_KEY=... python3 scripts/build_vertical_scripts.py --slug bbva --base-url https://tuodominio.it --use-openai
```

## Workflow blog pronto all'uso

- Ogni lunedi GitHub Actions genera automaticamente una bozza `roundup` in `content/blog/drafts/`.
- Da `Actions -> Blog Draft Generator` puoi anche lanciare a mano:
  - una bozza riepilogativa
  - una bozza per una singola offerta
  - una bozza con OpenAI, se hai configurato `OPENAI_API_KEY`

## Workflow contenuti pronto all'uso

- Ogni giorno lavorativo GitHub Actions genera automaticamente un content pack in `content/machine/packs/`.
- Da `Actions -> Content Machine` puoi anche lanciare a mano:
  - un pack per una specifica offerta
  - un pack automatico dell'offerta del giorno
  - un piano editoriale settimanale
  - una versione con OpenAI, se hai configurato `OPENAI_API_KEY`

## Workflow verticali pronto all'uso

- Ogni giorno lavorativo GitHub Actions genera automaticamente uno script verticale in `content/machine/verticals/`.
- Da `Actions -> Vertical Script Machine` puoi anche lanciare a mano:
  - lo script dell'offerta del giorno
  - uno script dedicato a una singola offerta
  - una versione con OpenAI, se hai configurato `OPENAI_API_KEY`

## Roadmap consigliata

### Fase 1

- Telegram automatico
- dati centrali offerte
- workflow GitHub base
- blog automatico base

### Fase 2

- sito generato da dati
- deploy automatico
- alert su cambi promo

### Fase 3

- bozze blog automatiche
- script video e caption

### Fase 4

- pubblicazione semi-automatica video/social
- controllo promo con parser e diff
