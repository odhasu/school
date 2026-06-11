# Verslag – Focus Timer

**Vak:** Informatica  
**Naam:** Oscar Graafmans  
**Niveau:** HAVO 4  

---

## Wat is mijn project?

Ik heb een app gemaakt die Focus Timer heet. Het is een programma dat je helpt om geconcentreerd te werken. Je zet een timer in, en de app telt af. Zo weet je hoe lang je nog bezig bent.

De app heeft drie pagina's:

- **Timer** – Hier stel je een tijd in, bijvoorbeeld 25 minuten. De app telt af en geeft een geluid als je klaar bent.
- **Games** – Hier zitten drie kleine spelletjes in: Snake, een reactietest en een geheugenspel. Dit is bedoeld als korte pauze.
- **Plan** – Hier kun je taken plannen voor de hele week. Je vult een taaknaam in, een dag, een starttijd en hoe lang het duurt. Als het tijd is, krijg je een melding.

De app werkt op Windows als een `.exe` bestand. Je hoeft Python niet te installeren om het te gebruiken.

---

## Hoe heb ik het gemaakt?

Ik heb de app geprogrammeerd in **Python**. Voor de interface heb ik de bibliotheek **CustomTkinter** gebruikt. Dit is een uitbreiding op het standaard Tkinter pakket en ziet er moderner uit.

Voor de achtergrond heb ik **Pillow** gebruikt. Daarmee genereer ik kleurverloop-afbeeldingen (gradiënten) die als achtergrond worden getoond. De gebruiker kan ook kiezen uit andere kleuren of een eigen foto uploaden.

De timer loopt in een aparte thread, zodat de interface niet bevriest terwijl de timer aftelt. Dit is een technische keuze die ik heb gemaakt omdat Tkinter anders vastloopt.

---

## GitHub en automatisch bouwen

Ik heb mijn code opgeslagen op **GitHub**. Dat is een platform waar je code kunt opslaan en delen. Zo kon ik mijn project makkelijk bijhouden en terugkijken wat ik eerder had veranderd.

Ik heb ook **GitHub Actions** gebruikt. Dit is een systeem dat automatisch acties uitvoert als ik nieuwe code upload. In mijn geval bouwt het systeem automatisch een `.exe` bestand van mijn Python code. Dat doe ik met het programma **PyInstaller**. Zo hoef ik dat niet elke keer zelf te doen.

De workflow draait op een Windows-server van GitHub. Zodra ik code upload, start de build vanzelf en staat het nieuwe `.exe` bestand binnen een paar minuten klaar om te downloaden.

---

## Claude Code

Ik heb tijdens dit project gebruik gemaakt van **Claude Code**. Dit is een AI-assistent die je helpt met programmeren. Ik kon vragen stellen over code en Claude Code stelde voor hoe ik dingen kon aanpassen of verbeteren.

Ik heb het gebruikt om functies toe te voegen, fouten op te sporen en de code netter te maken. De beslissingen heb ik zelf gemaakt, maar Claude Code hielp me sneller werken.

---

## Problemen die ik tegenkwam

Een probleem dat ik tegenkwam was dat de app crashte als ik het sloot. Dit gebeurde omdat er nog processen actief waren op de achtergrond, zoals timers en loops, die bleven draaien terwijl het venster al weg was. Hierdoor probeerde de app nog dingen te updaten in een scherm dat niet meer bestond.

Ik heb dit opgelost door al die actieve processen netjes te stoppen in de `on_close` functie, voordat het venster wordt gesloten. Daarna werkte het afsluiten correct.

---

## Reflectie

### Oorspronkelijk idee

In het begin was mijn idee om een simpele focustimer te maken. Gewoon een afteltimer waarbij je een tijd instelt en de app je waarschuwt als de tijd om is. Ik wilde het ook als een echt programma kunnen opstarten, dus niet via een website maar als een los bestand op je computer.

### Uiteindelijke uitwerking (ingeleverd project)

Uiteindelijk heb ik veel meer gemaakt dan alleen een timer. De app heeft drie pagina's gekregen: een timerpagina, een spelletjespagina met Snake, een reactietest en een geheugenspel, en een weekplanner waar je taken kunt plannen per dag met een starttijd en duur. Ook heb ik een focusmodus toegevoegd die volledig scherm gaat, en kun je de achtergrond aanpassen met kleurverloop of een eigen foto. Om de focusmodus te verlaten moet je een rekensommetje oplossen.

Het project is ingeleverd als een `.exe` bestand dat direct opgestart kan worden op Windows. Dit bestand is automatisch gebouwd via GitHub Actions.

### Reflectie

Tijdens dit project heb ik geleerd dat:

Het bouwen van een echte app veel meer werk is dan alleen code schrijven. Je moet nadenken over hoe alles samenwerkt, hoe de interface eruitziet, hoe je bugs oplost en hoe je het programma klaar maakt voor iemand anders om te gebruiken. Ik heb ook geleerd hoe je threads gebruikt in Python, zodat de timer aftelt zonder dat de rest van de app vastloopt.

**Wat goed ging was:**

Het opzetten van de interface. CustomTkinter maakte het vrij makkelijk om knoppen, labels en pagina's te maken. Ook het werkend krijgen van GitHub Actions ging soepel. Zodra ik de workflow had ingesteld, bouwde het automatisch een `.exe` elke keer als ik nieuwe code uploadde.

**Wat lastig was:**

De app crashte elke keer als ik hem afsloot. Dit was lastig om te vinden, want de fout zat niet in de zichtbare code maar in achtergrondprocessen die nog actief waren. Ik heb dit opgelost door alle lopende timers en loops netjes te stoppen voordat het venster werd gesloten.

**Als ik het opnieuw zou doen, zou ik:**

Eerder beginnen met het ontwerpen van de structuur van de app. Nu heb ik functies tussendoor toegevoegd waardoor de code soms wat onoverzichtelijk werd. Als ik het opnieuw deed, zou ik eerst opschrijven wat de app allemaal moet kunnen, en daarna pas beginnen met coderen.
