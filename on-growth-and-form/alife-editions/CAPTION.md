# Copy — Artificial Life editions

One section per piece. Hook and data block as they appear in frame, then the
caption in English and Polish.

---

# `highway_langtons-ant_alife`

Hook, in frame: **Every one of them builds the same road. / Nobody has proved why.**

Data block, in frame:

```
Langton's ant (1986)  ·  24 of them, one grid
right on white · left on black · flip · step forward
about 10,000 steps of chaos, then a 104-step loop
colour is how long ago an ant stood here
```

The citation is in-frame, so the caption does not repeat it.

---

### English

An ant on a grid of black and white squares.

On a white square it turns right, on a black square it turns left, and either
way it flips the square it was standing on and steps forward. Right on white,
left on black, flip, step forward — nine words, and that is the entire rule.
No memory, no randomness, nothing to tune. Chris Langton wrote it down in 1986.

For about ten thousand steps the ant makes a small symmetric mess. Then, with
nothing changing about the rule and nothing added to the grid, it starts
building a road: a 104-step cycle that shifts the pattern two cells diagonally
and then repeats, forever. Every ant does this. It is a theorem that the trail
can never stay bounded — the ant always escapes whatever it has built — but the
road itself has never been proved, only observed, in every starting
configuration anyone has tried.

There are twenty-four of them here on one grid, and that part is not in the
rule at all. The ants cannot see each other. The only thing an ant can read is
the cell underneath it, and the only thing it can change is that same cell, so
everything they do to each other goes through the floor: a road driven into
another ant's rubbish reads the wrong colours and falls back into chaos, and a
patch some other ant has already tidied can launch a road early.

Colour is how long ago an ant stood there — violet is everything already built,
white is where one is standing now. Every road runs at forty-five degrees
because every road is the same road: the 104-step cycle comes in four
orientations and in nothing else.

Nobody designed it. It is not in the rule and it is not in the starting
conditions. It is what nine words do when you leave them running.

---

### Polski

Mrówka na siatce czarnych i białych pól.

Na białym polu skręca w prawo, na czarnym w lewo, w obu przypadkach odwraca
kolor pola, na którym stała, i robi krok naprzód. W prawo na białym, w lewo na
czarnym, odwróć, krok — dziewięć słów i to jest cała reguła. Żadnej pamięci,
żadnej losowości, nic do strojenia. Chris Langton zapisał ją w 1986 roku.

Przez jakieś dziesięć tysięcy kroków mrówka robi mały symetryczny bałagan.
Potem, bez żadnej zmiany w regule i bez niczego dołożonego do siatki, zaczyna
budować drogę: 104-krokowy cykl, który przesuwa wzór o dwa pola po przekątnej i
powtarza się bez końca. Robi to każda mrówka. Jest twierdzenie, że ślad nigdy
nie pozostaje ograniczony — mrówka zawsze ucieka temu, co zbudowała — ale samej
drogi nikt nie udowodnił. Została wyłącznie zaobserwowana, w każdej konfiguracji
początkowej, jakiej ktokolwiek spróbował.

Tutaj jest ich dwadzieścia cztery na jednej siatce, a tego reguła nie obejmuje
w ogóle. Mrówki się nawzajem nie widzą. Jedyne, co mrówka potrafi odczytać, to
pole pod sobą, i jedyne, co potrafi zmienić, to dokładnie to samo pole — więc
wszystko, co robią sobie nawzajem, idzie przez podłogę: droga wjeżdżająca w
śmieci innej mrówki odczytuje złe kolory i rozsypuje się z powrotem w chaos, a
kawałek siatki, który ktoś już posprzątał, potrafi wypuścić drogę wcześniej.

Kolor to czas, jaki minął, odkąd stała tu mrówka — fiolet to wszystko, co już
zbudowane, biel to miejsce, w którym któraś stoi teraz. Każda droga biegnie pod
czterdziestoma pięcioma stopniami, bo każda droga jest tą samą drogą: ten
104-krokowy cykl występuje w czterech orientacjach i w żadnej innej.

Nikt tego nie zaprojektował. Nie ma tego w regule ani w warunkach początkowych.
To jest to, co robi dziewięć słów, kiedy zostawić je włączone.

---

### Which one would go out

The English is the source and the Polish is a translation rather than a gloss —
`ograniczony` for *bounded* is the word a Polish reader would expect from the
theorem, and the rule is given in Polish in its own nine words rather than
transliterated.

One judgement call: the caption states that the road has never been proved,
only observed, while the unboundedness of the trail *is* a theorem. Those two
sentences are easy to collapse into "nobody knows why it happens", which is
what the hook says and is looser than the truth. They stay separate. If the
caption has to be cut for length, cut the paragraph about the twenty-four
sharing a grid — the picture carries that on its own.

---

# `protocell_particle-motion_alife`

Hook, in frame: **The rule has no membrane in it. / Everything on screen has one.**

Data block, in frame:

```
primordial particle system (Schmickl 2016)
count the neighbours · turn · step forward
2,016 particles · three more every ten steps
colour is how many neighbours a particle has
```

The citation is in-frame, so the caption does not repeat it.

### English

Two thousand particles on a torus, and one rule that moves them.

A particle counts how many others are inside its own radius, splits them into
the ones on its left and the ones on its right, turns by a fixed angle plus a
little more for every neighbour it can see — towards whichever side is emptier
— and steps forward. That is the whole law. Thomas Schmickl and colleagues
published it in 2016. There is no force in it, no attraction, no species, no
chemistry, and nothing anywhere that says the word cell.

What comes out are cells. Bounded bodies with a dense core, a ring holding them
closed, and loose particles drifting in the gaps. They deform, they shove each
other, and they keep condensing out of the soup for as long as there is loose
material left to make one from.

They do not divide, and it would be a better story if they did — so it was
measured rather than assumed. When a new cell appears, the nearest cell that
already existed is a median of two cell-diameters away, and only 3% turn up
within one diameter. At the density the paper itself uses, none do. These are
not children. Each one condenses on its own account out of whatever happened to
drift together.

The one thing here that is not in the paper is the trickle: three new particles
every ten steps, dropped in at random. Without it a world this size organises
everything it has in the first two seconds and then merely coarsens, which is a
still photograph with a caption on it.

Colour is the only quantity the rule reads — how many neighbours a particle
has. Violet is a particle alone in the soup, amber is one in a wall, white is a
core.

### Polski

Dwa tysiące cząstek na torusie i jedna reguła, która nimi porusza.

Cząstka liczy, ile innych znajduje się w jej promieniu, dzieli je na te po
lewej i te po prawej stronie swojego kierunku, skręca o stały kąt plus trochę
więcej za każdego widzianego sąsiada — w stronę tej połowy, która jest pustsza
— i robi krok naprzód. To cała reguła. Thomas Schmickl i współpracownicy
opublikowali ją w 2016 roku. Nie ma w niej żadnej siły, żadnego przyciągania,
żadnych gatunków, żadnej chemii ani niczego, co mówiłoby słowo komórka.

Wychodzą z tego komórki. Zamknięte ciała z gęstym jądrem, obwódką, która trzyma
je w całości, i wolnymi cząstkami dryfującymi w przerwach. Odkształcają się,
rozpychają nawzajem i kondensują się z zupy tak długo, jak długo zostaje z
czego.

Nie dzielą się, a byłaby to lepsza historia, gdyby się dzieliły — więc zostało
to zmierzone, a nie założone. Kiedy pojawia się nowa komórka, najbliższa z już
istniejących jest w medianie dwie średnice komórki dalej, a tylko 3% pojawia
się bliżej niż jedną średnicę. Przy gęstości, której używa sam artykuł, nie ma
takich wcale. To nie są dzieci tamtych. Każda kondensuje się na własny rachunek
z tego, co akurat zdryfowało w jedno miejsce.

Jedyne, czego nie ma w artykule, to strużka: trzy nowe cząstki co dziesięć
kroków, wrzucane losowo. Bez niej świat tej wielkości organizuje wszystko, co
ma, w pierwszych dwóch sekundach, a potem już tylko się zgrubia — czyli jest
zdjęciem z podpisem.

Kolor to jedyna wielkość, którą reguła odczytuje — liczba sąsiadów cząstki.
Fiolet to cząstka sama w zupie, bursztyn to cząstka w ścianie, biel to jądro.

### Which one would go out

The English is the source. `strużka` for the trickle and `zgrubia` for
coarsening are the words that keep the mechanism intact; softening either into
a metaphor would hide what the drive actually is.

The paragraph about division is the one that has to stay. Every published
description of this system, including the paper's own title, invites the reader
to see reproduction here, and this implementation does not do it — 3% against a
cell diameter is the number, and 0% at the paper's density. Cutting that
paragraph would leave a caption that lets the viewer assume it. If length
forces a cut, cut the colour paragraph: the data block already says what colour
means.

---

# `replicator_langtons-loops_alife`

Hook, in frame: **Each was built by the one beside it. / Only the edge is still building.**

Data block, in frame:

```
Langton's loops · self-replicating automaton (1984)
circulate · extend · turn left · cut free
one loop becomes 345 · 100 still working
colour is steps since a cell last changed
```

The citation is in-frame, so the caption does not repeat it.

---

## English

A single square of cells, and one rule about its four neighbours. Eight states,
219 lines of transition table, and nothing anywhere in them about copying.

Inside the loop a train of signals goes round and round: a 7 extends the arm by
one cell, a 4 turns it left. That train is the machine and it is also the
machine's blueprint. Circulating, it pushes an arm out; arriving at the arm's
tip, the same signals build with it. Four extensions and a turn, four times
over, and the arm has closed into a second loop holding its own copy of the
train. The daughter's first act is to cut itself free.

Von Neumann asked in 1948 whether a machine could build a machine as
complicated as itself, and answered with a universal constructor too large for
anyone to run. Codd cut it down in 1968. Langton cut it down again in 1984 by
giving up on universality: this loop cannot compute anything at all. It can
only reproduce.

What the colony does with that, nobody wrote. A loop with no free space beside
it cannot finish an arm, and a jammed loop pulls back into a shell that never
moves again. So the thing grows only on its surface: 345 loops here, and 100 of
them still working. The rest is a lattice of identical husks, every one of them
a machine that finished.

## Polish

Jeden kwadrat komórek i jedna reguła mówiąca o czterech sąsiadach. Osiem
stanów, 219 wierszy tablicy przejść — i ani słowa o kopiowaniu.

W pętli krąży ciąg sygnałów: siódemka wydłuża ramię o jedną komórkę, czwórka
skręca je w lewo. Ten ciąg jest maszyną i jest zarazem jej własnym planem.
Krążąc, wypycha ramię na zewnątrz; docierając na jego koniec, tymi samymi
sygnałami buduje. Cztery wydłużenia i skręt, i tak cztery razy, aż ramię domyka
się w drugą pętlę z własną kopią ciągu. Pierwsze, co robi córka, to odcina się
od matki.

W 1948 roku von Neumann zapytał, czy maszyna może zbudować maszynę równie
skomplikowaną jak ona sama, i odpowiedział konstruktorem uniwersalnym zbyt
wielkim, by ktokolwiek go uruchomił. Codd zmniejszył go w 1968. Langton
zmniejszył go jeszcze raz w 1984, rezygnując z uniwersalności: ta pętla nie
potrafi obliczyć niczego. Potrafi się tylko powielać.

Tego, co z tym robi kolonia, nie napisał nikt. Pętla, która nie ma obok siebie
wolnego miejsca, nie dokończy ramienia, a zablokowana wciąga je z powrotem i
zostaje skorupą, która już się nie poruszy. Więc całość rośnie wyłącznie po
powierzchni: tutaj 345 pętli, z czego 100 wciąż pracuje. Reszta to krata
identycznych skorup — każda z nich to maszyna, która skończyła.
