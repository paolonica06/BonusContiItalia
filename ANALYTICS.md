# Analytics Bonus Conti Italia

Il sito usa **Vercel Web Analytics**: statistiche di visita aggregate, anonime e senza cookie
(nessun banner cookie necessario). Google Analytics 4 e `assets/analytics.js` sono stati rimossi.

## Come funziona

Ogni pagina contiene lo snippet ufficiale per i siti statici:

```html
<script>window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };</script>
<script defer src="/_vercel/insights/script.js"></script>
```

Il file `/_vercel/insights/script.js` esiste solo sul sito pubblicato su Vercel e solo dopo l'attivazione.
In locale risponde 404: è normale e non rompe le pagine.

## Attivazione (da fare una volta, a cura di Paolo)

1. Apri Vercel, entra nel progetto del sito.
2. Vai su **Analytics**.
3. Premi **Enable**.

Dopo il prossimo deploy, le visite compaiono nella scheda Analytics del progetto
(pagine più viste, sorgenti, paesi, dispositivi).

## Cosa si misura

Solo le visite alle pagine (pageview). I click sui pulsanti non sono tracciati come eventi:
gli eventi personalizzati richiedono un piano a pagamento su Vercel, quindi non vengono usati
(regola: solo servizi gratuiti).

## Privacy

La pagina `privacy.html` descrive questo trattamento. Se cambia lo strumento di statistica,
aggiornare anche quella pagina.
