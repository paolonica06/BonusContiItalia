# Issue tracker: GitHub

Issue e specifiche vivono in GitHub Issues; usa la CLI `gh`.

## Comandi

- Creare: `gh issue create` (parte da `needs-triage`).
- Leggere: `gh issue view <n> --comments`.
- Elencare: `gh issue list --state open --json number,title,labels`.
- Commentare: `gh issue comment <n> --body "..."`.
- Etichette: `gh issue edit <n> --add-label "..."` / `--remove-label "..."`.
- Chiudere: `gh issue close <n> --comment "..."`.

Le PR non sono una superficie di richieste.

## Ciclo di lavoro

1. **Issue**: ogni modifica ha la sua issue. Si implementa solo una issue `ready-for-agent`.
2. **Implementazione**: su branch se la modifica è visibile e non ancora approvata
   (vedi `ui-ux-workflow.md`); altrimenti direttamente sul lavoro locale.
3. **Verifiche**: `python3 scripts/check_site.py` deve dare exit 0, più le prove del caso.
4. **Commit**: descrittivo, solo i file del lavoro, riferimento all'issue.
5. **Push su `main`**: Vercel pubblica da `main` in produzione, quindi le verifiche vengono SEMPRE prima.
6. **Verifica sul sito live** (`bonusconti-italia.vercel.app`): pagine, link, aspetto reale.
7. **Chiusura con prove**: il commento indica commit, criteri soddisfatti, comandi e risultati,
   verifica sul live, limiti e issue residue. Mai codici invito nel commento.

Applica `implemented-main` quando il commit è su `main`; `verified-staging` solo con una prova
reale riportata nell'issue (qui vale anche per la verifica sul sito live).
Chiudi dopo la verifica, non quando il codice è scritto.
