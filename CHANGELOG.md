# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Maps now displayed in popup, this allows old maps and locked maps to have a
  place in papyri. Inspired by the Hermiton Herald.
- CHANGELOG
- Logo
- support for 1.16 and custom dimensions
### Fixed
- Windows path issues #21
- Slightly better support for modded servers #18
### Changed
- using NEAREST filter to keep pixelated Minecraft feel in some cases
  [@AndrewKvalheim](https://github.com/AndrewKvalheim)
- changed stylesheet to keep map pixelated at low zoom levels [@AndrewKvalheim](https://github.com/AndrewKvalheim)

## [1.0.0] - 2020-01-23
### Added
- Now using leaflet and a new tile rendering engine
- lots of performance improvements
### Removed
- dependency on vips and openseadragon
### Fixed
- Windows fixes [@TimoMeijer](https://github.com/TimoMeijer)
- Docker support [@TimoMeijer](https://github.com/TimoMeijer)

## [0.8.4] - 2018-10-14
### Added
- grid overlay
- spawn chunks overlay
- player overlay
- soring maps by time

## [0.8.3] - 2018-10-12
### Added
- mca file display
### Changed
- more pixelation to keep the Minecraft feel 
## [0.8.2] - 2018-10-11
### Added
- sort by map ID
- banner icons
- option to include unlimitedtracking
- live coords

## [0.8.0] - 2018-10-03
### Removed
- mdwiki generation
- book pois

## [0.7.0] - 2018-03-21
### Removed
- mdwiki in template

## [0.6.0] - 2018-03-07
### Added
- banner POIs
- MIT license

## [0.5.0] - 2018-02-24
### Changed
- increased size of possible rendered map

## [0.3.0] - 2018-02-03
### Added
- map ID overlay
- map statistics

## [0.2.0] - 2018-01-23
### Added
- customize POI colors
### Changed
- prepare for 1.13 book nbt/json changes

## [0.1.0] - 2018-01-07
### Added
- logging
- Books as POI

## [0.0.0] - 2018-01-06
### Added
- Initial commit
