# Marian's Splitter

Marian's Splitter je profesionální desktopová aplikace pro chytré a bezeztrátové rozdělování mediálních souborů (MP3 a MP4) do několika částí. Aplikace se pyšní stylovým designem v paletě **Obsidian Brutal Strength** (černá, jantarová a bílá) s maximálním důrazem na funkčnost.

## Hlavní funkce
- **Rozdělení na N částí**: Snadno rozdělte dlouhé záznamy (např. přednášky, záznamy streamů) na požadovaný počet stejně dlouhých dílů.
- **Inteligentní překryv (Overlap)**: Abyste nepřišli o žádné slovo mezi jednotlivými soubory, aplikace automaticky na konec každé části přidá N sekund (např. 5s) z části následující.
- **Rychlý bezeztrátový režim (FAST)**: Aplikace využívá přímé kopírování kodeku (`-c copy`) pro bleskurychlé zpracování bez ztráty kvality.
- **Zabezpečení proti přepisu**: Pokud se ve složce už nachází soubor stejného jména, aplikace ho nepřepíše, ale chytře nový soubor přečísluje.
- **Bezpečný chod**: Během rozdělování je rozhraní uzamčeno. Proces lze kdykoliv bezpečně zrušit vyhrazeným tlačítkem.

## Spuštění

**Varianta A: Přes Executable (.exe)**
Ve složce `dist` se nachází zkompilovaný soubor `Marians_Splitter.exe`. 
Stačí ho spustit – nepotřebujete nainstalovaný Python!
*(Poznámka: Pro běh programu je nutné, aby na daném PC byl dostupný balíček FFmpeg).*

**Varianta B: Přes Python**
1. Nainstalujte Python 3
2. Spusťte: `python media_splitter.py`

## Požadavky
- **FFmpeg** (v systémové proměnné PATH nebo ve stejné složce jako aplikace). Používá se pro detekci délky (`ffprobe`) a samotné rozdělení (`ffmpeg`).

## Design
Rozhraní je inspirováno "brutalistním" webovým designem, ovšem plně převedeno do nativního okenního prostředí Tkinter. Obsahuje responzivní konzoli pro přímý výstup událostí a chyb z FFmpeg pro snadnou diagnostiku.
