# ANNCSU Navigator

Applicazione web Django per la consultazione dei servizi **ANNCSU – Archivio Nazionale dei Numeri Civici delle Strade Urbane** tramite **PDND – Piattaforma Digitale Nazionale Dati**.

Il progetto è pensato principalmente per i **CED e i servizi informatici delle Pubbliche Amministrazioni** che dispongono dell'e-service ANNCSU su PDND e vogliono mettere a disposizione degli operatori un'interfaccia web semplice per la consultazione dello stradario e degli accessi.

## Funzionalità

ANNCSU Navigator permette di:

- verificare l'esistenza di un odonimo;
- verificare l'esistenza di un accesso/civico;
- ricercare strade per denominazione parziale;
- esplorare tutti gli accessi appartenenti a una strada;
- filtrare localmente i civici di una strada;
- consultare il dettaglio di un singolo accesso;
- effettuare ricerche direttamente tramite progressivo nazionale ANNCSU;
- visualizzare il numero di richieste ANNCSU effettuate nella giornata;
- ridurre il numero di chiamate all'e-service tramite una cache persistente PostgreSQL;
- autenticare gli utenti tramite account locali Django oppure LDAP/Active Directory.

## Cache ANNCSU

L'e-service ANNCSU prevede un numero massimo di richieste giornaliere piuttosto contenuto, **ad oggi pari a 100 richieste al giorno**.

Per questo motivo ANNCSU Navigator implementa una cache persistente su PostgreSQL, in modo da evitare chiamate ripetute per dati già acquisiti.

La logica è pensata per riutilizzare il più possibile le informazioni già restituite dall'e-service.

Le ricerche degli odonimi vengono memorizzate e le aree restituite vengono associate al relativo `prognaz`.

Alla prima esplorazione di una strada vengono acquisiti tutti gli accessi tramite `elencoaccessiprog`. L'elenco completo viene quindi conservato in cache e utilizzato per le successive consultazioni e per il filtraggio dei civici.

I singoli accessi vengono inoltre indicizzati tramite il relativo `prognazacc`.

Questo permette, ad esempio, di evitare una nuova chiamata `prognazarea` per una strada già individuata oppure una chiamata `prognazacc` per un civico già ricevuto attraverso l'elenco completo degli accessi.

Finché la cache è valida, la consultazione della stessa strada e dei relativi accessi avviene quindi senza generare nuove richieste verso ANNCSU.

La durata della cache è configurabile dall'amministrazione Django. Il valore predefinito è **24 ore**.

L'applicativo mantiene inoltre un contatore giornaliero delle chiamate effettivamente inviate all'e-service ANNCSU. Le risposte servite dalla cache non incrementano il contatore.

## Requisiti

L'installazione prevista utilizza:

- Docker;
- Docker Compose;
- Python 3.12;
- Django 5.2;
- PostgreSQL 17;
- Gunicorn;
- WhiteNoise;
- un reverse proxy HTTPS;
- una chiave privata associata al client PDND.

## Installazione

Clonare il repository:

```bash
git clone https://github.com/perroneclaudio/anncsu-navigator.git
cd anncsu-navigator
```

Creare il file `.env` partendo dall'esempio:

```bash
cp .env.example .env
```

Compilare `.env` con i parametri della propria installazione.

Creare la directory destinata ai secret:

```bash
mkdir -p secrets
```

Copiare al suo interno la chiave privata utilizzata per PDND:

```text
secrets/pdnd_private_key.pem
```

Avviare l'applicazione:

```bash
docker compose up -d --build
```

Verificare lo stato dei container:

```bash
docker compose ps
```

Le migrazioni Django e `collectstatic` vengono eseguiti automaticamente all'avvio del container web.

## Configurazione PDND

La configurazione dell'e-service viene gestita tramite l'amministrazione Django.

Sono previsti, tra gli altri, i seguenti parametri:

- `client_id`;
- `purpose_id`;
- `kid`;
- issuer;
- subject;
- URL del token endpoint PDND;
- audience dell'assertion;
- audience dell'e-service;
- base URL dell'e-service;
- percorso della chiave privata;
- timeout delle richieste;
- durata della cache;
- limite giornaliero delle richieste.

La chiave privata viene normalmente resa disponibile al container nel percorso:

```text
/run/secrets/pdnd_private_key.pem
```

## Autenticazione

L'applicazione supporta due modalità di autenticazione:

```text
LOCAL
LDAP
```

Gli account `LOCAL` vengono gestiti direttamente da Django.

Gli account `LDAP` possono essere autenticati tramite LDAP/Active Directory configurando i relativi parametri nel file `.env`.

È possibile configurare un server LDAP principale e un server secondario di fallback.

Il fallback viene utilizzato in caso di indisponibilità del server principale e non in caso di credenziali errate.

## Reverse proxy

In produzione è consigliato pubblicare l'applicazione tramite HTTPS utilizzando un reverse proxy, ad esempio Nginx.

La configurazione Docker fornita espone il servizio web sull'interfaccia locale dell'host, lasciando al reverse proxy la pubblicazione verso l'esterno.

## Amministrazione

L'amministrazione Django permette di gestire:

- configurazione generale dell'applicazione;
- parametri PDND;
- durata della cache;
- limite giornaliero delle richieste;
- contenuto e stato della cache ANNCSU;
- storico del contatore giornaliero;
- utenti locali e configurazione degli account.

## Licenza

Il progetto è distribuito secondo i termini della **GNU Affero General Public License v3.0 (AGPL-3.0)**.

Il testo completo della licenza è disponibile nel file `LICENSE`.
