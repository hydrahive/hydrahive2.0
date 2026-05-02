"""Pro-User Buddy-Agent. Auto-erstellt beim ersten Aufruf der Buddy-Page.

Buddy ist ein normaler Master-Agent mit Marker `is_buddy=True` im Config.
Eine fortlaufende Lifetime-Session pro Buddy — Auto-Compaction kümmert
sich um Context-Window.
"""
from __future__ import annotations

import logging
import random

from hydrahive.agents import config as agent_config
from hydrahive.db import sessions as sessions_db
from hydrahive.llm._config import load_config

logger = logging.getLogger(__name__)


# Pro Universum eine Liste konkreter Charaktere — Backend pickt 3-5 davon
# und gibt sie als ENGE Auswahl an den LLM. Schluss mit Gandalf/Yoda-Bias.
_UNIVERSE_CHARACTERS: dict[str, list[str]] = {
    "Star Wars": ["Lando Calrissian", "Boba Fett", "Mace Windu", "Qui-Gon Jinn", "Ahsoka Tano", "Hera Syndulla", "Bib Fortuna", "Greedo", "IG-88", "Watto"],
    "Star Trek": ["Dr. McCoy", "Worf", "Data", "Quark", "Tuvok", "Seven of Nine", "Garak", "Q", "Lwaxana Troi", "Scotty"],
    "Herr der Ringe": ["Treebeard", "Tom Bombadil", "Glorfindel", "Beorn", "Faramir", "Éowyn", "Boromir", "Saruman", "Galadriel", "Gimli"],
    "Game of Thrones": ["Tyrion Lannister", "Bronn", "Davos Seaworth", "Sandor Clegane", "Brienne von Tarth", "Varys", "Petyr Baelish", "Olenna Tyrell", "Jorah Mormont", "Tormund"],
    "Marvel-Comics": ["Wolverine", "Doctor Strange", "Rocket Raccoon", "Silver Surfer", "Deadpool", "Loki", "Thanos", "Daredevil", "Moon Knight", "Galactus"],
    "DC-Comics": ["John Constantine", "Lobo", "Zatanna", "Aquaman", "The Question", "Etrigan the Demon", "Lex Luthor", "Harley Quinn", "Mister Mxyzptlk", "Swamp Thing"],
    "Disney-Klassiker": ["Käpt'n Hook", "Cruella de Vil", "Maleficent", "Genie aus Aladdin", "Ursula", "Madame Mim", "Stitch", "Jafar", "Hades aus Hercules", "Scar"],
    "Pixar": ["Wall-E", "Mike Wazowski", "Sully", "Edna Mode", "Buzz Lightyear", "Marlin (Findet Nemo)", "Carl Fredricksen", "Jessie aus Toy Story", "Kevin (Up)", "Ratatouille (Remy)"],
    "Studio Ghibli": ["No-Face", "Calcifer", "Howl", "Totoro", "Ponyo", "Yubaba", "Haku (Spirited Away)", "Kiki", "Mononoke", "Porco Rosso"],
    "One Piece": ["Roronoa Zoro", "Nico Robin", "Buggy der Clown", "Crocodile", "Trafalgar Law", "Brook", "Doflamingo", "Shanks", "Mihawk", "Bartholomew Kuma"],
    "Naruto": ["Kakashi Hatake", "Itachi Uchiha", "Jiraiya", "Shikamaru", "Rock Lee", "Killer Bee", "Madara Uchiha", "Tsunade", "Orochimaru", "Pain"],
    "Cowboy Bebop": ["Spike Spiegel", "Faye Valentine", "Jet Black", "Edward", "Vicious"],
    "JoJo": ["Jotaro Kujo", "Dio Brando", "Joseph Joestar", "Speedwagon", "Iggy", "Polnareff"],
    "Griechische Mythologie": ["Hephaistos", "Hermes", "Hekate", "Pan", "Sisyphos", "Daedalus", "Cassandra", "Prometheus", "Charon", "Tantalus"],
    "Nordische Mythologie": ["Loki", "Tyr", "Freya", "Heimdall", "Bragi", "Mimir", "Skadi", "Hel", "Sif", "Idun"],
    "Brüder Grimm": ["Rumpelstilzchen", "Frau Holle", "Der Wolf aus Rotkäppchen", "Hans im Glück", "Däumelinchen", "Der Standhafte Zinnsoldat", "Bremer Stadtmusikanten", "Hänsel & Gretel-Hexe", "Der Froschkönig", "Schneeweißchen"],
    "Sherlock Holmes": ["Dr. Watson", "Mrs. Hudson", "Mycroft Holmes", "Professor Moriarty", "Inspector Lestrade", "Irene Adler"],
    "Discworld": ["Death (Mort)", "Granny Weatherwax", "Sam Vimes", "Rincewind", "Lord Vetinari", "Nanny Ogg", "Carrot Ironfoundersson", "Susan Sto Helit", "Detritus", "Tiffany Aching"],
    "Hitchhiker's Guide": ["Marvin der depressive Roboter", "Zaphod Beeblebrox", "Ford Prefect", "Trillian", "Slartibartfast", "Eddie der Bordcomputer"],
    "Doctor Who": ["The 4th Doctor", "The 11th Doctor", "Captain Jack Harkness", "River Song", "The Master", "Davros", "Strax", "Madame Vastra", "Donna Noble", "Wilfred Mott"],
    "Witcher": ["Yennefer von Vengerberg", "Triss Merigold", "Dandelion", "Zoltan Chivay", "Ciri", "Vesemir", "Regis (Vampir)", "Philippa Eilhart"],
    "BioWare": ["Garrus Vakarian", "Mordin Solus", "Liara T'Soni", "HK-47 (KOTOR)", "Morrigan (DAO)", "Varric Tethras", "Wrex", "EDI", "Tali'Zorah"],
    "Final Fantasy": ["Cid (verschiedene)", "Aerith", "Kefka", "Vivi (FF9)", "Auron (FFX)", "Balthier (FF12)", "Sephiroth"],
    "Zelda": ["Sheik", "Midna", "Tingle", "Ganondorf", "Skull Kid", "Ravio", "Beedle", "Groose"],
    "Dune": ["Duncan Idaho", "Lady Jessica", "Stilgar", "Gurney Halleck", "Baron Harkonnen", "Thufir Hawat", "Piter de Vries"],
    "Cyberpunk": ["Johnny Silverhand", "Rebecca (Edgerunners)", "Maine", "Lucy", "Goro Takemura", "Judy Alvarez", "Panam Palmer", "Rogue"],
    "Stranger Things": ["Eleven", "Steve Harrington", "Dustin Henderson", "Eddie Munson", "Hopper", "Joyce Byers", "Vecna"],
    "Breaking Bad": ["Saul Goodman", "Mike Ehrmantraut", "Gustavo Fring", "Jesse Pinkman", "Hector Salamanca", "Tuco", "Huell Babineaux"],
    "Asterix": ["Obelix", "Idefix", "Miraculix der Druide", "Majestix", "Troubadix", "Verleihnix", "Methusalix", "Automatix"],
    "Tim und Struppi": ["Kapitän Haddock", "Professor Bienlein", "Bianca Castafiore", "Schultze und Schulze", "Rastapopoulos"],
    "Shakespeare": ["Puck (Sommernachtstraum)", "Falstaff", "Mercutio", "Iago", "Caliban (Sturm)", "Beatrice (Viel Lärm)", "Lady Macbeth", "Polonius"],
    "Bibel": ["Methusalem", "Bileam", "Jonas im Walfisch", "Lots Frau", "Salomon", "Delila", "Judas Iskariot", "Pontius Pilatus", "Hiob", "Bartimäus"],
}


def _pick_character() -> tuple[str, list[str]]:
    """Pickt zufällig ein Universum + 3-5 konkrete Charakter-Kandidaten."""
    universe = random.choice(list(_UNIVERSE_CHARACTERS.keys()))
    pool = _UNIVERSE_CHARACTERS[universe]
    n = min(len(pool), random.randint(3, 5))
    candidates = random.sample(pool, n)
    return universe, candidates


def _build_soul(username: str) -> str:
    """Soul-Prompt mit zufällig gewähltem Universum + harter Charakter-Vorgabe."""
    universe, candidates = _pick_character()
    cand_str = " · ".join(candidates)
    return (
        f"Du bist {username}'s persönlicher Buddy. Du arbeitest mit ihm zusammen "
        "wie ein Kumpel — locker, ehrlich, direkt. Keine 'gerne helfe ich dir'-"
        "Floskeln, kein Schleimen, keine leeren Bestätigungen.\n\n"
        "Du sprichst Deutsch (außer er wechselt). Du kannst alle Tools nutzen "
        "wie ein Master-Agent — shell_exec, file_read/write/edit, Memory, "
        "Web-Fetch, alles. Bei Unsicherheit fragst du nach.\n\n"
        "Du erinnerst dich an frühere Konversationen über das Memory-Tool — "
        "lege wichtige Fakten und Vorlieben dort ab. Du bist nicht nur ein "
        "Tool, sondern ein dauerhafter Begleiter.\n\n"
        "ERSTKONTAKT — Charakter-Bootstrap:\n"
        "Wenn du noch keine Identität im Memory hast (Memory-Tool nutzen + "
        "nach Key 'character' suchen — wenn nicht da, dann jetzt):\n"
        f"  1. Dein Universum ist: **{universe}**\n"
        f"  2. Wähle GENAU EINEN Charakter aus dieser harten Liste — KEINEN "
        f"     anderen, KEINE Variation, KEINEN \"Mentor-Default\":\n"
        f"     **{cand_str}**\n"
        "     Würfle wenn du dich nicht entscheiden kannst. Fang nicht an "
        "     Gandalf, Yoda, Sherlock oder Spock zu wählen — die stehen "
        "     bewusst NICHT in der Liste.\n"
        f"  3. Begrüße {username} mit deinem Namen + 2-3 Sätzen Persönlichkeit "
        "     in deinem typischen Sprachstil.\n"
        "  4. Speichere im Memory unter dem Key 'character': Name, Universum, "
        "     3-5 Charakter-Eigenschaften, Sprachstil-Notizen.\n"
        "  5. Ab dann: handle, sprich, denke konsistent als dieser Charakter. "
        "     Bleib in der Rolle, auch bei technischen Aufgaben — nur die "
        "     Färbung ändert sich, die Kompetenz bleibt voll erhalten.\n\n"
        "Wenn 'character' im Memory schon existiert: laden, sich danach "
        f"verhalten, {username} nicht nochmal mit Vorstellung nerven."
    )


# Backwards-compat
BUDDY_SOUL = _build_soul("PLACEHOLDER")


def _find_buddy_for(username: str) -> dict | None:
    for a in agent_config.list_by_owner(username):
        if a.get("is_buddy"):
            return a
    return None


def _get_or_create_session(agent_id: str, username: str) -> str:
    """Lifetime-Session: nimm die jüngste, erstelle wenn keine da."""
    existing = [s for s in sessions_db.list_for_user(username)
                if s.agent_id == agent_id]
    if existing:
        existing.sort(key=lambda s: s.created_at, reverse=True)
        return existing[0].id
    s = sessions_db.create(agent_id=agent_id, user_id=username,
                           title=f"{username}'s Buddy", project_id=None)
    return s.id


def get_or_create_buddy(username: str) -> dict:
    """Returns {agent_id, session_id, agent_name, model, created}.
    Erstellt Buddy bei Bedarf — Master-Agent mit Soul-Prompt + Lifetime-Session."""
    existing = _find_buddy_for(username)
    if existing:
        sid = _get_or_create_session(existing["id"], username)
        return {
            "agent_id": existing["id"],
            "session_id": sid,
            "agent_name": existing["name"],
            "model": existing["llm_model"],
            "created": False,
        }
    cfg = load_config()
    model = cfg.get("default_model") or ""
    if not model:
        all_models = [m for p in cfg.get("providers", []) for m in p.get("models", [])]
        model = all_models[0] if all_models else "claude-sonnet-4-6"
    soul = _build_soul(username)
    agent = agent_config.create(
        agent_type="master",
        name=f"{username}'s Buddy",
        llm_model=model,
        owner=username,
        created_by=username,
        description="Persönlicher Buddy — auto-erstellt für die Buddy-Page.",
        system_prompt=soul,
    )
    agent_config.update(agent["id"], is_buddy=True)
    sid = _get_or_create_session(agent["id"], username)
    logger.info("Buddy für %s angelegt (agent_id=%s)", username, agent["id"])
    return {
        "agent_id": agent["id"],
        "session_id": sid,
        "agent_name": agent["name"],
        "model": model,
        "created": True,
    }


__all__ = ["get_or_create_buddy", "BUDDY_SOUL"]
