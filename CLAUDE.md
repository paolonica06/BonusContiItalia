@AGENTS.md

## Claude Code

Le regole sono in `AGENTS.md` e `docs/agents/`; qui solo le equivalenze.

- **Paolo lavora dal telefono**: mockup e screenshot si condividono con un Artifact privato
  (pagina di revisione del sito, separata da quella della dashboard) e con `open`; un percorso locale non basta.
- **Verifiche prima del push**: `python3 scripts/check_site.py`.
- **Lavoro non approvato**: resta in un branch `claude/issue-<N>-<slug>`, mai su `main`.
- **Delega**: implementazioni specificate a Codex, revisione e integrazione a Claude
  (`docs/agents/delega-codex.md`).
- **Token**: contesto piccolo, poche chiamate, deleghe dove possibile.
