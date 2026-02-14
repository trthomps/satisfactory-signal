# Changelog

## [0.5.1](https://github.com/trthomps/satisfactory-signal/compare/v0.5.0...v0.5.1) (2026-02-14)


### Bug Fixes

* make FRM client timeout configurable and polling loop non-blocking ([#16](https://github.com/trthomps/satisfactory-signal/issues/16)) ([6e367c1](https://github.com/trthomps/satisfactory-signal/commit/6e367c12c06a331aff52f776b73355470c19a79b))

## [0.5.0](https://github.com/trthomps/satisfactory-signal/compare/v0.4.2...v0.5.0) (2026-02-14)


### Features

* add Grafana graph rendering via /graph command ([#13](https://github.com/trthomps/satisfactory-signal/issues/13)) ([a0aa0b2](https://github.com/trthomps/satisfactory-signal/commit/a0aa0b2a811dded9db49b067879d97d81d058262))


### Bug Fixes

* debounce player join/leave to eliminate duplicates and camera mode spam ([#15](https://github.com/trthomps/satisfactory-signal/issues/15)) ([a7ee3b5](https://github.com/trthomps/satisfactory-signal/commit/a7ee3b58e22a7c50011101b4509f549c6e95e97f))

## [0.4.2](https://github.com/trthomps/satisfactory-signal/compare/v0.4.1...v0.4.2) (2026-02-06)


### Bug Fixes

* reinitialize chat timestamp when game server reconnects ([f6fcfaa](https://github.com/trthomps/satisfactory-signal/commit/f6fcfaae5b02af5a118b092df74dab7f027cac61))

## [0.4.1](https://github.com/trthomps/satisfactory-signal/compare/v0.4.0...v0.4.1) (2026-02-05)


### Bug Fixes

* update test for new storage output format ([52fc797](https://github.com/trthomps/satisfactory-signal/commit/52fc797ca9182e03b4194c170042858195b04e96))

## [0.4.0](https://github.com/trthomps/satisfactory-signal/compare/v0.3.1...v0.4.0) (2026-02-05)


### Features

* add search filter to prod command ([b106569](https://github.com/trthomps/satisfactory-signal/commit/b106569b731768d8fb1084a896df9442b4e83df8))
* add version and doggos commands ([043f412](https://github.com/trthomps/satisfactory-signal/commit/043f4123ea71a4e00d77026c83e1093478e3e131))


### Bug Fixes

* remove artificial limits on storage and prod commands ([c2c2505](https://github.com/trthomps/satisfactory-signal/commit/c2c2505126b357d4ff132b88e4c5ee5cc4d52270))

## [0.3.1](https://github.com/trthomps/satisfactory-signal/compare/v0.3.0...v0.3.1) (2026-02-05)


### Bug Fixes

* install dependencies from pyproject.toml in Dockerfile ([f981d37](https://github.com/trthomps/satisfactory-signal/commit/f981d3731f5505c3167c0fe5e8d693fc6ed1a651))

## [0.3.0](https://github.com/trthomps/satisfactory-signal/compare/v0.2.0...v0.3.0) (2026-02-05)


### Features

* add Helm chart for Kubernetes deployment ([939be3f](https://github.com/trthomps/satisfactory-signal/commit/939be3fe09cd46878909eded5b8796b6ff31eed8))
* add player event notifications for join, leave, and death ([503428b](https://github.com/trthomps/satisfactory-signal/commit/503428bbe06eb970f462ae1a673e2bd54dc47d60))
* add power outage notifications ([5d44d48](https://github.com/trthomps/satisfactory-signal/commit/5d44d488dda7df26aef5f49b96adbf0cd0a589e8))
* add server online/offline notifications ([c3b8a70](https://github.com/trthomps/satisfactory-signal/commit/c3b8a70149a0682665a80709141d306f0cce177f))


### Bug Fixes

* handle @UUID mention format from Signal ([3d08159](https://github.com/trthomps/satisfactory-signal/commit/3d081594c50b9fcc1d706de02861c2ce63b65996))
* handle image-only messages with no text ([e9dfe19](https://github.com/trthomps/satisfactory-signal/commit/e9dfe198fd27288de893819be4607c12f94b1fbe))
* resolve mention names from contacts API and sender cache ([0f0940c](https://github.com/trthomps/satisfactory-signal/commit/0f0940c62923246384e263aa8606b6b0f6339431))


### Documentation

* update README with Helm deployment and event notifications ([c89ab38](https://github.com/trthomps/satisfactory-signal/commit/c89ab38acfccfcb50dcbbfe36a010b5912b9a8c4))

## [0.2.0](https://github.com/trthomps/satisfactory-signal/compare/v0.1.2...v0.2.0) (2026-02-03)


### Features

* add emoji conversion and attachment handling for game compatibility ([1167a10](https://github.com/trthomps/satisfactory-signal/commit/1167a10be203d4ee4474b266ce7a549245963a86))
* handle Signal mentions ([@someone](https://github.com/someone)) in game chat ([a518d1c](https://github.com/trthomps/satisfactory-signal/commit/a518d1ceda65518a2df01176277e2dce210bf419))


### Bug Fixes

* remove unused imports in test files ([3525448](https://github.com/trthomps/satisfactory-signal/commit/3525448e80e973bebc69aecf76c62123bc54e9ab))


### Documentation

* add coverage badge and test instructions ([d6f8e76](https://github.com/trthomps/satisfactory-signal/commit/d6f8e7631c46d0fa8c1cb2a6e76fa7622180b9d0))
* add GitHub release badge to README ([07a0d29](https://github.com/trthomps/satisfactory-signal/commit/07a0d294ddf1eeb16f2510aaa60aa6d8c2e79eb2))

## [0.1.2](https://github.com/trthomps/satisfactory-signal/compare/v0.1.1...v0.1.2) (2026-02-03)


### Bug Fixes

* chain docker build in release workflow ([e3a8888](https://github.com/trthomps/satisfactory-signal/commit/e3a8888b55234b1e997a4895df7baa7f74eb2d7c))

## [0.1.1](https://github.com/trthomps/satisfactory-signal/compare/v0.1.0...v0.1.1) (2026-02-03)


### Bug Fixes

* add latest tag for version releases ([11d4921](https://github.com/trthomps/satisfactory-signal/commit/11d492183f09171126939198973bf32a348c6e51))
* add raw tag for workflow_dispatch builds ([fe16fed](https://github.com/trthomps/satisfactory-signal/commit/fe16fedfce8d24d2d6db3e4e031a7de5d8e36a20))
* add workflow_dispatch for manual tag builds ([2e6bbf5](https://github.com/trthomps/satisfactory-signal/commit/2e6bbf57a728915a57327b959ea2b3612af49646))
* trigger docker build on release publish ([5d79ed2](https://github.com/trthomps/satisfactory-signal/commit/5d79ed2f4837b7e83bd788e3750f95612a620e65))

## 0.1.0 (2026-02-03)


### Features

* initial release ([9e94861](https://github.com/trthomps/satisfactory-signal/commit/9e94861c64f2eb18a1572bb9ad78a82151318bf0))


### Documentation

* update README with commands and Docker usage ([b3da6d0](https://github.com/trthomps/satisfactory-signal/commit/b3da6d0033b361bab5da0ff9f0606aae2253c80e))
