---
name: medical-research
description: Wissenschaftliche & medizinische Recherche über offene APIs (PubMed, OpenAlex, ClinicalTrials.gov, openFDA, RxNorm, Gene/Krankheiten). Für Literatur-Suche, Studienlage, Wirkstoffe, Nebenwirkungen, Diagnosen.
when_to_use: Wenn medizinische/wissenschaftliche Fragen mit Quellen belegt werden sollen — Studien finden, Medikamente/Wechselwirkungen prüfen, Krankheiten/Gene/Symptome nachschlagen, klinische Studien suchen.
tools_required: [fetch_url]
---

# Medizinische & wissenschaftliche Recherche

Alle Quellen werden über **`fetch_url`** abgerufen (GET, JSON). Query-Strings
**URL-encoden**. Die meisten Quellen sind **schlüssellos** und funktionieren sofort.
Bei `401`/`403` einer Key-Quelle (CORE, ICD-11) hat der Admin noch keinen Key unter
**Health → Forschungs-APIs** hinterlegt → eine keyless Alternative nutzen.

**Vorgehen:** breit suchen (Literatur) → relevante IDs/DOIs → Details/Abstract holen →
mit Quelle (PMID/DOI/NCT-Nummer) zitieren. Nie ungeprüft behaupten — Treffer verlinken.

## 📚 Literatur & Studien

**PubMed (E-utilities)** — der Standard für med. Abstracts. Zwei Schritte:
```
# 1) Suchen → PMIDs
fetch_url GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=<query>&retmode=json&retmax=10
# 2) Abstracts holen
fetch_url GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=<pmid1,pmid2>&rettype=abstract&retmode=text
```

**Europe PMC** — wie PubMed, oft mit Volltext, ein Call:
```
fetch_url GET https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=<query>&format=json&resultType=core&pageSize=10
```

**OpenAlex** — Zitationen/Autoren/Journals (keyless):
```
fetch_url GET https://api.openalex.org/works?search=<query>&per-page=10
```

**Semantic Scholar** — KI-Suche + TLDR-Zusammenfassungen:
```
fetch_url GET https://api.semanticscholar.org/graph/v1/paper/search?query=<query>&fields=title,abstract,tldr,year,authors&limit=10
```

**Crossref** — DOI-Metadaten:
```
fetch_url GET https://api.crossref.org/works?query=<query>&rows=10
```

**CORE** (Key nötig) — Open-Access-Volltexte: `https://api.core.ac.uk/v3/search/works?q=<query>`

## 💊 Medikamente & Wirkstoffe

**openFDA** — Nebenwirkungen/Beipackzettel:
```
# Nebenwirkungs-Reports zu einem Wirkstoff
fetch_url GET https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:<drug>&limit=5
# Beipackzettel/Label
fetch_url GET https://api.fda.gov/drug/label.json?search=openfda.generic_name:<inn>&limit=3
```

**RxNorm (RxNav)** — Wirkstoff-Mapping (US):
```
fetch_url GET https://rxnav.nlm.nih.gov/REST/rxcui.json?name=<drug>
```
⚠️ Deutsche Präparate: openFDA/RxNorm sind US-zentriert — über den **Wirkstoff (INN)**
mappen, nicht über den Handelsnamen.

## 🧬 Krankheiten, Gene, Diagnosen

**MyGene / MyVariant** (keyless):
```
fetch_url GET https://mygene.info/v3/query?q=<gene-symbol>&species=human
fetch_url GET https://myvariant.info/v1/query?q=<variant>
```

**Open Targets** — Gen↔Krankheit↔Medikament (GraphQL, POST):
```
fetch_url POST https://api.platform.opentargets.org/api/v4/graphql
  body: {"query":"{ target(ensemblId:\"ENSG...\"){ approvedSymbol } }"}
  content_type: application/json
```

**HPO** — Symptome → Krankheiten: `https://ontology.jax.org/api/hp/search?q=<term>`

**ICD-11 (WHO)** — Diagnose-Codes, mehrsprachig. Braucht OAuth-Token (Admin) —
in v1 nur nutzbar, wenn unter Forschungs-APIs ein Token hinterlegt ist.

## 🔬 Klinische Studien

**ClinicalTrials.gov v2** (keyless):
```
fetch_url GET https://clinicaltrials.gov/api/v2/studies?query.term=<query>&pageSize=10
```
Treffer tragen eine **NCT-Nummer** (z.B. NCT01234567) — als Quelle zitieren.

---

**Genaue Parameter & Felder:** jede Quelle hat eine `docs_url` in der Registry —
bei Unsicherheit zur Query-Syntax dort nachsehen. Antworten sind JSON; relevante
Felder extrahieren, nicht den ganzen Body zurückgeben.
