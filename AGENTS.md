# BonusContiItalia: istruzioni per gli agenti

## Cos'è il progetto

Hub dei codici invito bancari di Paolo (BBVA, buddybank, Revolut, Trade Republic).
Sito statico vanilla HTML/CSS/JS su Vercel: `bonusconti-italia.vercel.app`.
**Obiettivo n.1**: la gente trova il sito da Google e usa il codice invito di Paolo.

## Repository

Prima di lavorare verifica che `origin` sia `paolonica06/BonusContiItalia`; se non lo è, fermati e chiedi.
Tracker: GitHub Issues (`docs/agents/issue-tracker.md`).

## Mappa dei file

- `index.html`, `bonus-*.html`, `come-iniziare.html`: pagine del sito; stile in `style.css`.
- `assets/`: logo, icone.
- `data/offers.json`: offerte, bonus, link e codici invito. Fonte unica dei dati.
- `data/site-config.json`: configurazione del sito.
- `content/`: contenuti generati (blog, pacchetti giornalieri, script).
- `scripts/*.py`: generatori di contenuti e invii Telegram (solo libreria standard).
- `.github/workflows/`: automazioni (blog, content machine, Telegram, verticali).
- `AUTOMAZIONI.md`, `ANALYTICS.md`: note operative.
- Niente `package.json`: nessuna build. Vercel pubblica i file così come sono.

## Verifiche

```sh
python3 scripts/check_site.py
```

Controlla JSON, meta di ogni pagina, link interni, dicitura referral («Link con il mio codice invito» in ogni pagina con link invito), privacy.html linkata da ogni pagina, compilazione degli script.
Exit 1 = errori: non fare push.
Per le modifiche visibili servono anche screenshot reali (`docs/agents/ui-ux-workflow.md`).

## Flusso

Issue → implementazione → verifiche → commit → push su `main` → verifica sul sito live → chiusura con prove.
**Vercel pubblica `main` in produzione**: le verifiche vengono SEMPRE prima del push.
Dettagli in `docs/agents/issue-tracker.md`.

## Documenti

- `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`: tracker ed etichette.
- `docs/agents/ui-ux-workflow.md`: mockup e approvazione per ogni modifica visibile.
- `docs/agents/delega-codex.md`: come delegare a Codex.
- `docs/agents/regole.md`: regole non negoziabili (costi, segreti, codici, referral).

## Regole in breve

- Solo servizi gratuiti.
- Nessun segreto nei file o in chat; i codici invito non compaiono mai in resoconti, issue, commit o log.
- Non inventare cifre dei bonus.
- Niente testi o comportamenti visibili non approvati.
- Non leggere `.env*`.
- Un commit per lavoro, solo dei file di quel lavoro.
