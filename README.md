# localbooks

Server HTTP minimale (solo HTML, nessuna dipendenza oltre Python 3) per scaricare
ebook sul Kobo dalla rete di casa. Serve la cartella `~/Books` e pubblica il nome
`books.local` via mDNS (Avahi), così non serve ricordarsi l'IP.

## Installazione (Ubuntu)

```bash
./install.sh
```

Lo script:

- installa `avahi-utils` e copia il server in `/usr/local/bin/localbooks`
- crea `~/Books` se non esiste
- crea e avvia il servizio systemd `localbooks` (parte a ogni avvio, gira come
  il tuo utente, sulla porta 80 senza root grazie a `CAP_NET_BIND_SERVICE`)
- apre le porte 80/tcp e 5353/udp se `ufw` è attivo

Se la porta 80 è già usata da un altro programma (es. un container Docker),
scegline un'altra: `PORT=8088 ./install.sh` → `http://books.local:8088/`.

Rimozione: `./uninstall.sh` (la cartella `~/Books` non viene toccata).

## Uso dal Kobo

1. Copia gli ebook in `~/Books` (le sottocartelle sono supportate).
2. Sul Kobo: *Altro → Funzioni beta → Browser web*.
3. Apri `http://books.local/` e tocca un libro per scaricarlo.

Suggerimento: usa file `.kepub.epub` (convertibili con
[kepubify](https://pgaskin.net/kepubify/)) per avere statistiche e impaginazione
migliori.

### Se `books.local` non funziona

Non tutti i firmware Kobo risolvono i nomi `.local` (mDNS). Alternative, in
ordine di comodità:

- **Nome del PC dal router**: molti router registrano i nomi dei dispositivi,
  es. `http://yoga7.fritz.box/`, `http://yoga7.lan/` o `http://yoga7.home/`.
- **IP aggiuntivo fisso sul PC** (consigliato): aggiungi un secondo indirizzo
  alla connessione Wi-Fi di casa, scelto fuori dal range DHCP del router, e
  salvalo come segnalibro sul Kobo:
  ```bash
  nmcli con mod "<nome-connessione>" +ipv4.addresses 192.168.1.200/24
  nmcli con up "<nome-connessione>"
  ```
- **IP fisso**: imposta una prenotazione DHCP sul router per il PC e salva
  l'indirizzo come segnalibro nel browser del Kobo.

L'IP attuale è mostrato nei log: `journalctl -u localbooks -n 20`.

## Configurazione

Variabili d'ambiente (modificabili in `/etc/systemd/system/localbooks.service`):

| Variabile         | Default       |
|-------------------|---------------|
| `LOCALBOOKS_DIR`  | `~/Books`     |
| `LOCALBOOKS_PORT` | `80`          |
| `LOCALBOOKS_NAME` | `books.local` |

Avvio manuale senza installare: `LOCALBOOKS_PORT=8080 ./localbooks.py`
