# Delega a Codex

Il limite settimanale di Claude è la risorsa più scarsa: Codex fa le implementazioni specificate,
Claude tiene regia, decisioni, revisione, screenshot e integrazione.

## Cosa delegare

- Implementazioni con brief e mockup approvati, refactoring, script Python, pulizie.
- Ricerche su materiale locale.

Restano a Claude: decisioni di prodotto, pagina di revisione, screenshot, commit/push, dati e regole sui codici invito.

## Come

Una worktree per lavoro, preparata da Claude:

```sh
git worktree add -b claude/issue-<N>-<slug> ~/bonusconti-backups/wt-<N> origin/main
codex exec -s workspace-write -C <worktree> -c model_reasoning_effort=high -o <rapporto.md> "<prompt>" < /dev/null
```

Usare la CLI Codex aggiornata. In background. Codex non ha rete e non scrive in git:
modifica i file, Claude fa commit.

## Checklist del prompt

- Worktree, branch, issue, file da leggere; le informazioni dell'issue nel prompt (niente `gh`).
- Per l'interfaccia: ogni elemento del mockup elencato; «nessun testo, stile o comportamento
  visibile nuovo oltre a quanto richiesto»; «il flusso UI (mockup, screenshot, ok di Paolo) lo
  gestisce Claude; implementa senza commit».
- Stile: «una istruzione per riga, funzioni su più righe, righe di 110 caratteri al massimo».
- Divieti: commit/push/stash/reset, lettura di `.env*`, segreti, codici invito nei file di test o nel rapporto, librerie nuove.
- Verifiche: `python3 scripts/check_site.py`; rapporto finale in italiano nel file di `-o`.

## Revisione di Claude, sempre

1. Diff completo: testi visibili, stili e link non richiesti; nessun codice invito duplicato o esposto.
2. Righe lunghe e stile.
3. Screenshot reali confrontati con il mockup, prima di mostrarli a Paolo.

## Codex esaurito

Avvisare Paolo (il limite ha un reset) e proseguire con un subagent Sonnet con lo stesso prompt.
