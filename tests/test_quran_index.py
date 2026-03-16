import pytest
from quran_index import verse_index_to_surah_ayah, TOTAL_AYAHS

def test_total_ayahs():
    assert TOTAL_AYAHS == 6236

def test_first_verse():
    surah, ayah = verse_index_to_surah_ayah(0)
    assert surah == 1
    assert ayah == 1

def test_last_verse_of_surah_1():
    surah, ayah = verse_index_to_surah_ayah(6)
    assert surah == 1
    assert ayah == 7

def test_first_verse_of_surah_2():
    surah, ayah = verse_index_to_surah_ayah(7)
    assert surah == 2
    assert ayah == 1

def test_last_verse_of_quran():
    surah, ayah = verse_index_to_surah_ayah(6235)
    assert surah == 114
    assert ayah == 6

def test_index_zero_returns_first_verse():
    surah, ayah = verse_index_to_surah_ayah(0)
    assert surah == 1 and ayah == 1

def test_out_of_range_raises():
    import pytest
    with pytest.raises(ValueError):
        verse_index_to_surah_ayah(6236)
    with pytest.raises(ValueError):
        verse_index_to_surah_ayah(-1)
