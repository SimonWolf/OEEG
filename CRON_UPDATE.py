from src.leistung import Leistung
from src.ertrag import update_ertrag

leistung = Leistung()
for s in  ["muensingen", "karlsruhe", "badboll", "mettingen", "holzgerlingen", "tuebingen", "hospitalhof"]:
    leistung.download_days(s,365)

update_ertrag()