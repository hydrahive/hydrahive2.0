"""Character universe catalogue + random picker for the Buddy system."""
from __future__ import annotations

import random

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


def pick_character() -> tuple[str, str]:
    """Würfelt EINEN finalen Charakter — Universum + Name. Deterministisch
    in Python, kein LLM-Vertrauen mehr."""
    universe = random.choice(list(_UNIVERSE_CHARACTERS.keys()))
    name = random.choice(_UNIVERSE_CHARACTERS[universe])
    return universe, name
