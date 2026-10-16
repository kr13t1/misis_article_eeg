# Метаданные статьи для переноса в шаблон МИСИС

## Название на русском

Исследование фрактальных характеристик ЭЭГ-сигналов для классификации состояний моторного воображения

## Название на английском

Investigation of Fractal Features of EEG Signals for Motor Imagery State Classification

## Аннотация на русском

В работе исследуется применимость фрактальных характеристик электроэнцефалографических сигналов для классификации состояний моторного воображения. Рассматриваются фрактальная размерность Хигучи (HFD) и корреляционная размерность D2, оцениваемая по реконструированному пространству состояний. Методика включает проверку реализации на синтетических сигналах, анализ чувствительности D2 к задержке, размерности вложения и диапазону радиусов, а также план сопоставления фрактальных признаков со спектральным базовым уровнем на наборе BCI Competition IV 2a. Предварительные результаты показывают, что оценка корреляционного наклона чувствительна к выбору масштаба и размерности вложения; на текущем пилотном фрагменте не установлено убедительное плато, позволяющее интерпретировать наклон как устойчивую оценку D2. Поэтому пилотные наблюдения рассматриваются как методологическая проверка, а не как доказательство улучшения классификации. Окончательные выводы о полезности фрактальных признаков требуют единого межсубъектного протокола и сравнения на одинаковых разбиениях данных.

## Abstract

This study investigates the applicability of fractal features of electroencephalographic signals to motor imagery state classification. It considers Higuchi fractal dimension (HFD) and correlation dimension D2 estimated from a reconstructed state space. The methodology includes validation on synthetic signals, sensitivity analysis of D2 with respect to delay, embedding dimension, and radius range, and a planned comparison of fractal features with a spectral baseline on BCI Competition IV 2a. Preliminary results indicate that the estimated correlation slope is sensitive to the selected scale range and embedding dimension; a convincing scaling plateau has not been established in the current pilot segment. The pilot observations are therefore treated as methodological diagnostics rather than evidence of improved classification. Final conclusions about the utility of fractal features require a consistent cross-subject evaluation protocol and comparisons on identical data splits.

## Ключевые слова

ЭЭГ; моторное воображение; фрактальная размерность Хигучи; корреляционная размерность; реконструкция пространства состояний; классификация; интерфейс мозг-компьютер.

## Keywords

EEG; motor imagery; Higuchi fractal dimension; correlation dimension; state-space reconstruction; classification; brain-computer interface.

## Данные автора и классификационные коды

Заполнить в `article.tex` по требованиям шаблона и руководителя: ФИО автора/авторов, организация, e-mail, коды ГРНТИ/ASJC/OECD. Не публиковать личные данные, если автор не согласовал их публикацию.

## Как подключить основной текст

В исходном `article.tex` шаблона сохраните команды класса и титульной части. В точке, где начинаются разделы основного текста, подключите:

```latex
\input{article_body}
```

Убедитесь, что в преамбуле доступны `amsmath` и `amssymb`, поскольку используются математические формулы. В конце документа настройте библиографию согласно оригинальному `Makefile` и шаблону; файл базы литературы называется `references.bib`.
