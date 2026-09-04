# Copy — Artificial Life editions

One section per piece. Hook and data block as they appear in frame, then the
caption in English and Polish.

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
