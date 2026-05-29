"""Vorbefüllte Forschungs-API-Quellen.

Endpoints/Auth nach offizieller Doku der jeweiligen API. Keyless-Quellen sind
default aktiv; Key/OAuth-Quellen (CORE, ICD-11) starten disabled, bis ein Key/
Token eingetragen ist. Optionaler Key (PubMed/openFDA/Semantic Scholar) = höheres
Rate-Limit, aber needs_key=False.
"""
from hydrahive.research.models import ResearchApi

SEED: list[ResearchApi] = [
    # --- Literatur & Studien-Texte ---
    ResearchApi(
        id="pubmed", name="PubMed / NCBI E-utilities", category="literatur",
        base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
        url_pattern="https://eutils.ncbi.nlm.nih.gov/*",
        docs_url="https://www.ncbi.nlm.nih.gov/books/NBK25501/",
        description="36 Mio+ medizinische Abstracts — der Standard.",
        needs_key=False, auth_type="query", auth_param="api_key",
        rate_limit="3 req/s ohne Key, 10/s mit Key", enabled=True),
    ResearchApi(
        id="europepmc", name="Europe PMC", category="literatur",
        base_url="https://www.ebi.ac.uk/europepmc/webservices/rest/",
        url_pattern="https://www.ebi.ac.uk/europepmc/*",
        docs_url="https://europepmc.org/RestfulWebService",
        description="Wie PubMed, oft mit Open-Access-Volltext.",
        needs_key=False, auth_type="none", enabled=True),
    ResearchApi(
        id="openalex", name="OpenAlex", category="literatur",
        base_url="https://api.openalex.org/",
        url_pattern="https://api.openalex.org/*",
        docs_url="https://docs.openalex.org/",
        description="Offener Wissenschafts-Katalog (Zitationen, Autoren, Journals).",
        needs_key=False, auth_type="none", polite_email_param="mailto",
        rate_limit="Polite-Pool mit mailto = schneller", enabled=True),
    ResearchApi(
        id="semanticscholar", name="Semantic Scholar (S2)", category="literatur",
        base_url="https://api.semanticscholar.org/graph/v1/",
        url_pattern="https://api.semanticscholar.org/*",
        docs_url="https://api.semanticscholar.org/api-docs/",
        description="KI-gestützte Paper-Suche, TLDRs, Zitationsgraph.",
        needs_key=False, auth_type="header", auth_param="x-api-key",
        rate_limit="optionaler Key = höheres Limit", enabled=True),
    ResearchApi(
        id="crossref", name="Crossref", category="literatur",
        base_url="https://api.crossref.org/",
        url_pattern="https://api.crossref.org/*",
        docs_url="https://api.crossref.org/swagger-ui/index.html",
        description="Metadaten zu ~150 Mio Publikationen, DOI-Auflösung.",
        needs_key=False, auth_type="none", polite_email_param="mailto", enabled=True),
    ResearchApi(
        id="core", name="CORE", category="literatur",
        base_url="https://api.core.ac.uk/v3/",
        url_pattern="https://api.core.ac.uk/*",
        docs_url="https://api.core.ac.uk/docs/v3",
        description="Größte Sammlung von Open-Access-Volltexten. Key nötig.",
        needs_key=True, auth_type="bearer", enabled=False),
    ResearchApi(
        id="biorxiv", name="bioRxiv / medRxiv", category="literatur",
        base_url="https://api.biorxiv.org/",
        url_pattern="https://api.biorxiv.org/*",
        docs_url="https://api.biorxiv.org/",
        description="Preprints (neueste Forschung vor Peer-Review).",
        needs_key=False, auth_type="none", enabled=True),
    # --- Medikamente & Wirkstoffe ---
    ResearchApi(
        id="openfda", name="openFDA", category="medikamente",
        base_url="https://api.fda.gov/",
        url_pattern="https://api.fda.gov/*",
        docs_url="https://open.fda.gov/apis/",
        description="FDA: Nebenwirkungen, Rückrufe, Beipackzettel, Medizinprodukte.",
        needs_key=False, auth_type="query", auth_param="api_key",
        rate_limit="optionaler Key = höheres Limit", enabled=True),
    ResearchApi(
        id="rxnorm", name="RxNorm / RxNav (NLM)", category="medikamente",
        base_url="https://rxnav.nlm.nih.gov/REST/",
        url_pattern="https://rxnav.nlm.nih.gov/*",
        docs_url="https://lhncbc.nlm.nih.gov/RxNav/APIs/",
        description="Normalisierte Arzneimittel-Namen, Wirkstoff-Mapping (US-zentriert).",
        needs_key=False, auth_type="none", enabled=True),
    # --- Krankheiten, Gene, Diagnosen ---
    ResearchApi(
        id="icd11", name="ICD-11 API (WHO)", category="krankheiten_gene",
        base_url="https://id.who.int/icd/",
        url_pattern="https://id.who.int/icd/*",
        docs_url="https://icd.who.int/icdapi",
        description="Offizielle Diagnose-Codes, mehrsprachig (auch DE). OAuth — in v1 "
                    "Token manuell als Bearer eintragen.",
        needs_key=True, auth_type="bearer", enabled=False),
    ResearchApi(
        id="mygene", name="MyGene.info", category="krankheiten_gene",
        base_url="https://mygene.info/v3/",
        url_pattern="https://mygene.info/*",
        docs_url="https://docs.mygene.info/",
        description="Gene-Annotation.", needs_key=False, auth_type="none", enabled=True),
    ResearchApi(
        id="myvariant", name="MyVariant.info", category="krankheiten_gene",
        base_url="https://myvariant.info/v1/",
        url_pattern="https://myvariant.info/*",
        docs_url="https://docs.myvariant.info/",
        description="Genetische Varianten.", needs_key=False, auth_type="none", enabled=True),
    ResearchApi(
        id="opentargets", name="Open Targets", category="krankheiten_gene",
        base_url="https://api.platform.opentargets.org/api/v4/graphql",
        url_pattern="https://api.platform.opentargets.org/*",
        docs_url="https://platform-docs.opentargets.org/data-access/graphql-api",
        description="Gen↔Krankheit↔Medikament-Zusammenhänge (GraphQL).",
        needs_key=False, auth_type="none", enabled=True),
    ResearchApi(
        id="hpo", name="Human Phenotype Ontology (HPO)", category="krankheiten_gene",
        base_url="https://ontology.jax.org/api/",
        url_pattern="https://ontology.jax.org/*",
        docs_url="https://ontology.jax.org/api/",
        description="Symptome → Krankheiten.", needs_key=False, auth_type="none", enabled=True),
    # --- Klinische Studien ---
    ResearchApi(
        id="clinicaltrials", name="ClinicalTrials.gov API v2", category="studien",
        base_url="https://clinicaltrials.gov/api/v2/",
        url_pattern="https://clinicaltrials.gov/api/*",
        docs_url="https://clinicaltrials.gov/data-api/api",
        description="Alle registrierten klinischen Studien weltweit.",
        needs_key=False, auth_type="none", enabled=True),
]
