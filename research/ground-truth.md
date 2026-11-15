# Ground truth: measurements to check forecasts against

Checked 2026-11-15. Which measured values exist in and near the forecast places, and whether LavinOko can use them
to verify the archived forecasts (`lavinoko-archive`).

## Summary

| Source | Snow depth | Other values | Near which places | Archive | Use |
|---|---|---|---|---|---|
| **UHMR automatic stations** (uhmr.gov.mk, "Актуелни податоци") | Yes, column "СНЕГ" (units not stated; some values implausible) | Hourly pressure, temperature, humidity, wind, precipitation | Popova Šapka, Mavrovo, Kruševo, Ponikva, Lazaropole | **None public: the page shows only the last ~3 hours** | Best match; needs collecting or UHMR's archive |
| UHMR manual 07:00 snow depth | Yes, cm | — | Popova Šapka, Mavrovo, Lazaropole, Kruševo, Požarane, Ǵurište, Berovo, Bitola | Only via news reports; full series on request from UHMR | Ask UHMR for past seasons |
| SYNOP reports (WMO, via OGIMET) | **No** snow-depth group in Jan 2026 | 3-hourly temperature, precipitation | Mavrovo (13576), Lazaropole (13577) | Yes (OGIMET) | Temperature and precipitation only; Lazaropole 74 % empty in a January week |
| NOA / meteo.gr Kaimaktsalan (Greece, 2090 m) | No | Daily temperature, precipitation, wind | Kajmakčalan; nearest high station to Kožuf (~45 km) | Monthly files | Temperature and wind at altitude; precipitation likely under-caught in snow **(verify gauge type)** |

No public measurement exists at **Kožuf**. The pilot needs its own station or the resort's measurements.

## UHMR automatic stations (the best source)

- Page: https://uhmr.gov.mk/aktuelni-podatoci/ — 67 stations, hourly, time in UTC+1 all year. Built from a CSV by
  a WordPress plugin (csv-to-sorttable); the CSV file itself is not linked.
- Variables: ПРИТИСОК (pressure), ТЕМПЕРАТУРА, ВЛАГА (humidity), БРЗИНА / ПРАВЕЦ (wind speed / direction),
  ВРНЕЖИ (precipitation), СНЕГ (snow).
- Stations matching forecast points:

  | UHMR station | Pressure (≈ height) | LavinOko point |
  |---|---|---|
  | Попова Шапка/Тетово | 827 hPa (≈ 1,700 m) | popova_sapka base, 1,663 m |
  | Маврови Анови | 879 hPa (≈ 1,250 m) | mavrovo base, 1,256 m |
  | Крушево | — | krusevo base, 1,214 m |
  | Пониква/Кочани | — | ponikva base, 1,506 m |
  | Лазарополе | 873 hPa (≈ 1,330 m) | none (between Mavrovo and Bistra) |

- Snow values on 2026-11-15 with no snow on the ground: Popova Šapka 0, Mavrovo 0, but Струга 7, Коџалија 150
  (constant), Лазарополе "####". Snow sensors need plausibility checks before any use.
- **Terms of use are not stated on the page. Ask UHMR before publishing anything derived from it.**

## Not usable

- WMO SYNOP from Macedonian stations carries no snow depth (checked 13576 Mavrovo and 13577 Lazaropole,
  15–22 Jan 2026). No Popova Šapka SYNOP station.

## Decision (2026-11-15)

Nothing is recorded from the UHMR page until UHMR agrees. The questions below go to UHMR first
(uhmr@meteo.gov.mk, the address on uhmr.gov.mk).

## Questions for UHMR

1. May LavinOko record the hourly automatic-station values and publish verification results based on them?
2. Is there an archive (CSV or API) of the automatic stations, and of the 07:00 manual snow depth, for past winters?
3. What are the units and sensor type of "СНЕГ", and which stations' snow sensors are reliable?
4. Are there stations at higher elevations than Popova Šapka (≈ 1,700 m)?

## Sources

- [UHMR — current data](https://uhmr.gov.mk/aktuelni-podatoci/)
- [OGIMET — SYNOP stations in North Macedonia](https://www.ogimet.com/cgi-bin/gsynres?lang=en&state=Macedonia&osum=no)
- [Meteopool — Lazaropole, WMO 13577](https://www.meteopool.org/en/wetterstation-lazaropole--wmo-13577-id3154)
- [NOA / meteo.gr — Kaimaktsalan monthly summary](http://penteli.meteo.gr/stations/kaimaktsalan/NOAAMO.TXT)
- [Libertas — UHMR snow depth report (68 cm Mavrovi Anovi)](https://libertas.mk/na-visoka-snezhna-pokrivka-od-68-sm-vo-mavrovi-anovi-na-mnogu-dozhd-vo-krushevo/)
- [Večer — 26 cm at Popova Šapka, 12 at Mavrovo](https://vecer.mk/makedonija/10ee43b0-be83-40be-b209-111748bbb4ee-1)
- [Balkanski glas — snow depth at Popova Šapka, 2021](https://balkanskiglasnavistinata.mk/2021/01/26/%D0%BD%D0%B0%D1%98%D0%BC%D0%BD%D0%BE%D0%B3%D1%83-%D1%81%D0%BD%D0%B5%D0%B3-%D0%BD%D0%B0-%D0%BF%D0%BE%D0%BF%D0%BE%D0%B2%D0%B0-%D1%88%D0%B0%D0%BF%D0%BA%D0%B0-40-%D1%81%D0%B0%D0%BD%D1%82%D0%B8%D0%BC/)
