# Предварительные EEG-эксперименты

Эти скрипты относятся к отдельному направлению анализа Motor Imagery EEG и **не воспроизводят** численные результаты методологической статьи HFD–U1.

- `d2_synthetic_validation.py` — диагностика корреляционного наклона на синтетических временных рядах;
- `d2_eeg_stability.py` — исследование чувствительности оценки D2 для отдельных EEG-фрагментов;
- `classification_comparison.py` — исследовательское сравнение признаков HFD и спектральной мощности на BCI Competition IV Dataset 2a.

Для двух EEG-скриптов необходимы исходные файлы GDF, полученные самостоятельно на условиях датасета. Скрипты не являются подтверждением улучшения классификации, а их результаты нельзя переносить в статью HFD–U1 без отдельного эксперимента и аудита.

```bash
python -m pip install -r requirements.txt
python experiments/d2_synthetic_validation.py
python experiments/d2_eeg_stability.py --gdf "/path/to/A01T.gdf"
python experiments/classification_comparison.py --data-dir data/raw
```
