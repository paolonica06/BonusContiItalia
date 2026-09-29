# Etichette

| Etichetta | Significato |
| --- | --- |
| `needs-triage` | Da valutare. Stato iniziale di ogni issue. |
| `needs-info` | In attesa di informazioni da Paolo. |
| `ready-for-agent` | Specificata a sufficienza: un agente può implementarla. |
| `ready-for-human` | Serve una decisione o un'azione di Paolo. |
| `wontfix` | Non verrà gestita. |
| `implemented-main` | Il commit è raggiungibile da `main`. |
| `verified-staging` | Verificata con prova reale riportata nell'issue (qui: sito live). |
| `bug`, `documentation`, `enhancement` | Tipo di lavoro. |

`needs-triage`, `needs-info`, `ready-for-agent` e `ready-for-human` sono mutuamente esclusive.
`implemented-main` e `verified-staging` non sostituiscono lo stato open/closed e non autorizzano
da sole un'implementazione.
