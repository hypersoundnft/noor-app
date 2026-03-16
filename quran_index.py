# Ayah counts per surah (114 surahs, total = 6236)
AYAH_COUNTS = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109,  # 1-10
    123, 111, 43, 52, 99, 128, 111, 110, 98, 135,    # 11-20
    112, 78, 118, 64, 77, 227, 93, 88, 69, 60,       # 21-30
    34, 30, 73, 54, 45, 83, 182, 88, 75, 85,         # 31-40
    54, 53, 89, 59, 37, 35, 38, 29, 18, 45,          # 41-50
    60, 49, 62, 55, 78, 96, 29, 22, 24, 13,          # 51-60
    14, 11, 11, 18, 12, 12, 30, 52, 52, 44,          # 61-70
    28, 28, 20, 56, 40, 31, 50, 40, 46, 42,          # 71-80
    29, 19, 36, 25, 22, 17, 19, 26, 30, 20,          # 81-90
    15, 21, 11, 8, 8, 19, 5, 8, 8, 11,               # 91-100
    11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6,      # 101-114
]

TOTAL_AYAHS = sum(AYAH_COUNTS)  # 6236

# Cumulative offsets: _OFFSETS[i] = index of first ayah of surah (i+1)
_OFFSETS = []
_cumulative = 0
for count in AYAH_COUNTS:
    _OFFSETS.append(_cumulative)
    _cumulative += count


def verse_index_to_surah_ayah(verse_index: int) -> tuple[int, int]:
    """Map a 0-based verse index (0–6235) to (surah_number, ayah_number).

    Both surah_number and ayah_number are 1-based.
    verse_index must be in range [0, TOTAL_AYAHS - 1].
    """
    if not (0 <= verse_index <= TOTAL_AYAHS - 1):
        raise ValueError(f"verse_index must be in [0, {TOTAL_AYAHS - 1}], got {verse_index}")
    # Binary search for the surah
    lo, hi = 0, len(_OFFSETS) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _OFFSETS[mid] <= verse_index:
            lo = mid
        else:
            hi = mid - 1
    surah_number = lo + 1  # 1-based
    ayah_number = verse_index - _OFFSETS[lo] + 1  # 1-based
    return surah_number, ayah_number
