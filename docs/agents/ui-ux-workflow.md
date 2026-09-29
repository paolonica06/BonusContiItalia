# Workflow UI/UX approval-first

## Regola

Ogni modifica visibile (layout, testi, colori, comportamento, micro-modifiche comprese) passa da
mockup e approvazione esplicita di Paolo **prima** dell'implementazione definitiva.
Non fare commit su `main`, push o consegna di lavoro visibile non approvato.

## Sequenza

1. Issue dedicata; preparare il mockup in locale.
2. Screenshot reali, sempre due: **mobile 390px** e **desktop 1280px**.
3. Pubblicarli sulla **pagina di revisione privata del sito** (Artifact separato da quello della
   dashboard) e aprirla con `open`; Paolo lavora dal telefono, un percorso locale non basta.
4. Attendere l'approvazione. Se chiede modifiche: aggiornare, nuovi screenshot, ripresentare.
5. Dopo l'ok: implementare, eseguire `python3 scripts/check_site.py`, screenshot della pagina
   reale a 390px e 1280px, confrontarli con il mockup approvato.
6. Solo poi commit e push su `main`, poi verifica sul sito live.

## Lavoro non approvato

Resta in un branch `claude/issue-<N>-<slug>` (con un backup `.patch` se serve), mai su `main`.
Niente testi, stili o comportamenti visibili non approvati: se un dettaglio non è nel mockup, non si aggiunge.

## Pagina di revisione

Ogni voce mostra: issue, descrizione breve, screenshot mobile e desktop, pulsanti approva / modifica.
Ogni nuova voce da approvare genera una notifica push a Paolo.
